"""Durable V15 batch coordinator. No sampler changes, retries or global interrupts."""
import asyncio
import copy
import hashlib
import json
import logging
import os
from pathlib import Path
import uuid
import time
from urllib.parse import urlsplit

PREFIX = '/nanfeng/v15/h3/continuation/batches'
V15 = 'NanFengH3MultiReferenceGeneratorV15'
TERMINAL = {'success', 'failed', 'cancelled', 'blocked_restart', 'blocked_ambiguous'}
MAX_BYTES = 32 * 1024 * 1024


class BatchScheduler:
    def __init__(self, directory, executor):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.executor = executor
        self.batches = {}
        self.lock = asyncio.Lock()
        self.task = None
        for path in self.directory.glob('*.json'):
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if str(uuid.UUID(data['id'])) != path.stem:
                    continue
                # Any previously attempted batch must be explicitly started as a NEW batch.
                # History is volatile across process restarts; never infer success from a latent file.
                if data['state'] not in TERMINAL and data.get('attempted'):
                    data['state'] = 'blocked_restart'
                    data['message'] = 'Server restarted after submission intent; start a fresh batch. No jobs replayed.'
                    self._save(data)
                self.batches[data['id']] = data
            except Exception:
                logging.exception('V15 scheduler: unreadable state left untouched: %s', path.name)
        self.batches = dict(sorted(self.batches.items(), key=lambda item: item[1].get('created_at', 0)))

    def _save(self, data):
        path = self.directory / (data['id'] + '.json')
        temp = path.with_suffix('.tmp')
        with open(temp, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)

    @staticmethod
    def public(data):
        return {k: data.get(k) for k in ('id', 'state', 'cursor', 'total', 'prompt_id', 'message', 'node_id')}

    async def enqueue(self, request):
        raw = json.dumps(request, ensure_ascii=False, allow_nan=False).encode()
        if len(raw) > MAX_BYTES:
            raise ValueError('Batch exceeds 32 MiB')
        request = json.loads(raw)  # detach from caller forever
        batch_id = request.get('batch_id')
        if not isinstance(batch_id, str) or str(uuid.UUID(batch_id)) != batch_id:
            raise ValueError('batch_id must be canonical UUID')
        digest = hashlib.sha256(raw).hexdigest()
        async with self.lock:
            if batch_id in self.batches:
                existing = self.batches[batch_id]
                if existing['digest'] != digest:
                    raise ValueError('batch_id already belongs to a different snapshot')
                return self.public(existing)
            if len(self.batches) >= 128 or sum(p.stat().st_size for p in self.directory.glob('*.json')) + len(raw) > 512*1024*1024:
                raise ValueError('Scheduler retention limit reached; archive terminal state files while server is stopped')
            jobs = request.get('jobs')
            node_id = request.get('node_id')
            if not isinstance(node_id, str) or not isinstance(jobs, list) or not 1 <= len(jobs) <= 256:
                raise ValueError('Expected node_id and 1..256 jobs')
            previous = None
            groups = set()
            for job in jobs:
                payload = job.get('payload', {})
                output = payload.get('output', {})
                target = output.get(node_id, {})
                if target.get('class_type') != V15 or not isinstance(target.get('inputs'), dict):
                    raise ValueError('Missing V15 target in snapshot')
                if any(k != node_id and v.get('class_type') == V15 and v.get('inputs', {}).get('启用潜空间续写') for k, v in output.items()):
                    raise ValueError('Another enabled continuation node in snapshot')
                if job.get('continuation') is True:
                    desc = job.get('descriptor')
                    if not isinstance(desc, dict) or any(not isinstance(desc.get(k), str) or not 1 <= len(desc[k]) <= 256 for k in ('workflow', 'node', 'group', 'run')):
                        raise ValueError('Invalid continuation descriptor')
                    if desc['node'] != node_id or type(desc.get('index')) is not int:
                        raise ValueError('Invalid node/index')
                    group = (desc['workflow'], desc['group'])
                    if previous and previous[0] == group:
                        if desc['index'] != previous[1] + 1:
                            raise ValueError('Continuation index gap')
                    else:
                        if desc['index'] != 1 or group in groups:
                            raise ValueError('Each contiguous group must begin fresh at index 1')
                        groups.add(group)
                    previous = (group, desc['index'])
                    # Server-owned fresh run namespace; user snapshots cannot resume stale latent files.
                    desc['run'] = batch_id
                    target['inputs']['启用潜空间续写'] = True
                    target['inputs']['潜空间续写任务'] = json.dumps(desc, ensure_ascii=False)
                elif job.get('continuation') is False and job.get('descriptor') is None:
                    previous = None
                    target['inputs']['启用潜空间续写'] = False
                    target['inputs']['潜空间续写任务'] = ''
                else:
                    raise ValueError('Invalid per-job routing descriptor')
            data = dict(id=batch_id, created_at=time.time_ns(), digest=digest, state='queued', cursor=0, total=len(jobs),
                        jobs=jobs, node_id=node_id, client_id=request.get('client_id', ''),
                        attempted=False, prompt_id=None, message='Accepted; browser may close')
            self._save(data)  # acknowledgement only after durable write
            self.batches[batch_id] = data
            return self.public(data)

    async def cancel(self, batch_id):
        async with self.lock:
            data = self.batches[batch_id]
            if data['state'] not in TERMINAL:
                data['state'] = 'cancelled'
                data['message'] = 'Only this batch stopped; already submitted prompt may finish. Files retained.'
                self._save(data)
            return self.public(data)

    async def tick(self):
        # Single worker: one outstanding native prompt for this scheduler, not one per browser.
        data = next((b for b in self.batches.values() if b['state'] not in TERMINAL), None)
        if data is None:
            return
        if data['state'] == 'queued':
            data.update(state='submitting', attempted=True, prompt_id=str(uuid.uuid4()))
            self._save(data)  # crash fence BEFORE any side effect
            try:
                result = await self.executor.submit(copy.deepcopy(data['jobs'][data['cursor']]['payload']), data['prompt_id'], data['client_id'])
                if data['state'] == 'cancelled':
                    return
                if result.get('prompt_id') != data['prompt_id']:
                    data.update(state='failed', message='Native prompt validation rejected the job; later jobs stopped')
                else:
                    data.update(state='running', message='Waiting for native execution success', missing=0)
            except Exception:
                if data['state'] != 'cancelled':
                    data.update(state='blocked_ambiguous', message='Submission outcome unknown; never retried. Inspect native queue, then start fresh.')
                logging.exception('V15 batch submission outcome unknown')
            self._save(data)
        elif data['state'] == 'running':
            result = await self.executor.status(data['prompt_id'])
            if data['state'] == 'cancelled':
                return
            if result == 'success':
                data['cursor'] += 1
                data.update(state='success' if data['cursor'] == data['total'] else 'queued', message='Previous job completed successfully', missing=0)
            elif result == 'failed':
                data.update(state='failed', message='Native execution failed; later jobs stopped')
            elif result == 'missing':
                data['missing'] = data.get('missing', 0) + 1
                if data['missing'] >= 3:
                    data.update(state='failed', message='Prompt removed or history missing; later jobs stopped')
            else:
                data['missing'] = 0
            self._save(data)

    async def run(self):
        while True:
            try:
                await self.tick()
            except Exception:
                logging.exception('V15 scheduler paused this tick; no submission retry')
            await asyncio.sleep(1)


class NativeExecutor:
    """Invoke the installed /prompt handler, preserving its hooks/validation/queue semantics.

    No loopback URL, credentials, invented queue priority or duplicate validation implementation.
    """
    def __init__(self, server):
        self.server = server
        self.handler = next(route.handler for route in server.routes if route.method == 'POST' and route.path == '/prompt')

    async def submit(self, payload, prompt_id, client_id):
        body = {'prompt': payload['output'], 'prompt_id': prompt_id, 'client_id': client_id,
                'extra_data': {'extra_pnginfo': {'workflow': payload.get('workflow', {})}}}
        class Request:
            headers = {}
            async def json(self):
                return body
        response = await self.handler(Request())
        return json.loads(response.body)

    async def status(self, prompt_id):
        queue = self.server.prompt_queue
        record = queue.get_history(prompt_id=prompt_id).get(prompt_id)
        if record:
            status = record.get('status', {})
            if status.get('status_str') == 'error':
                return 'failed'
            if status.get('completed') is True and status.get('status_str') == 'success':
                return 'success'
        running, pending = queue.get_current_queue()
        return 'pending' if any(item[1] == prompt_id for item in running + pending) else 'missing'


def attach_routes(server, scheduler):
    from aiohttp import web

    @web.middleware
    async def private_state(request, handler):
        if request.path.rstrip('/') in ('/view', '/api/view'):
            parts = '/'.join(request.query.get(k, '') for k in ('filename', 'subfolder')).replace(chr(92), '/')
            if '.nanfeng_v15_jobs' in parts.split('/'):
                raise web.HTTPForbidden(text='Private scheduler state')
        return await handler(request)
    if hasattr(server, 'app'):
        server.app.middlewares.append(private_state)

    def guard(request):
        if request.headers.get('Sec-Fetch-Site') == 'cross-site' or request.content_type != 'application/json':
            raise web.HTTPForbidden(text='Same-origin JSON required')
        origin = request.headers.get('Origin')
        if origin and urlsplit(origin).netloc != request.host:
            raise web.HTTPForbidden(text='Cross-origin batch access rejected')
        if not origin and request.remote not in ('127.0.0.1', '::1', None):
            raise web.HTTPForbidden(text='Same-origin browser or loopback required')

    @server.routes.post(PREFIX)
    async def enqueue(request):
        guard(request)
        try:
            if request.content_length and request.content_length > MAX_BYTES:
                raise ValueError('Batch exceeds 32 MiB')
            body = await request.read()
            if len(body) > MAX_BYTES:
                raise ValueError('Batch exceeds 32 MiB')
            return web.json_response(await scheduler.enqueue(json.loads(body)), status=202)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            return web.json_response({'error': str(exc)}, status=400)

    @server.routes.get(PREFIX)
    async def listing(request):
        return web.json_response({'batches': [scheduler.public(b) for b in scheduler.batches.values()
            if not request.query.get('node_id') or b['node_id'] == request.query['node_id']]})

    @server.routes.get(PREFIX + '/{batch_id}')
    async def status(request):
        data = scheduler.batches.get(request.match_info['batch_id'])
        return web.json_response(scheduler.public(data) if data else {'error': 'Unknown batch'}, status=200 if data else 404)

    @server.routes.post(PREFIX + '/{batch_id}/cancel')
    async def cancel(request):
        guard(request)
        try:
            return web.json_response(await scheduler.cancel(request.match_info['batch_id']))
        except KeyError:
            return web.json_response({'error': 'Unknown batch'}, status=404)


def register_routes():
    try:
        import folder_paths
        from server import PromptServer
    except ImportError:
        return
    server = getattr(PromptServer, 'instance', None)
    if server is None:
        return
    scheduler = BatchScheduler(Path(folder_paths.get_output_directory()) / '.nanfeng_v15_jobs', NativeExecutor(server))
    attach_routes(server, scheduler)

    async def startup(app):
        scheduler.task = asyncio.create_task(scheduler.run())

    async def cleanup(app):
        if scheduler.task:
            scheduler.task.cancel()
            try:
                await scheduler.task
            except asyncio.CancelledError:
                pass
    server.app.on_startup.append(startup)
    server.app.on_cleanup.append(cleanup)


register_routes()
