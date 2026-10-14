// Pure queue planner and dependency-aware submission, independently testable.
export const V15_TYPE='NanFengH3MultiReferenceGeneratorV15';
export function planContinuation(shots, start, identity, scope='following') {
  if(!Number.isInteger(start)||start<0||start>=shots.length)throw new Error('无效的当前分镜。');
  if(!['current','following'].includes(scope))throw new Error('无效的运行范围。');
  let end=shots.length;
  if(scope==='current') {
    const group=String(shots[start].continuationGroupId||'');
    if(group) {
      // Current means the WHOLE authored group, never the later groups.
      const members=shots.map((s,i)=>String(s.continuationGroupId||'')===group?i:-1).filter(i=>i>=0);
      start=members[0];end=members.at(-1)+1;
      if(end-start!==members.length||members.some(i=>!String(shots[i].prompt||'').trim()))throw new Error('当前连续组必须是相邻非空分镜；请修复分组后重试。');
    } else end=start+1;
  }
  const jobs=[]; let priorIndex=-2, priorGroup='', ordinal=0, block=0;
  for(let i=start;i<end;i++) {
    const shot=shots[i]; if(!String(shot.prompt||'').trim()) continue;
    const group=String(shot.continuationGroupId||'');
    if(!group){jobs.push({index:i,continuation:false,descriptor:null});priorIndex=-2;priorGroup='';continue;}
    if(i!==priorIndex+1||group!==priorGroup){ordinal=0;block++;}
    ordinal++;
    // A one-member suffix is an explicit fresh first clip (index 1), never a stale resume.
    jobs.push({index:i,continuation:true,descriptor:{...identity,group:`${group}:block-${block}`,index:ordinal}});
    priorIndex=i;priorGroup=group;
  }
  if(!jobs.length)throw new Error('运行范围内没有非空分镜。');
  return jobs;
}
export function applyContinuationJob(payload,nodeId,job) {
  const target=payload.output?.[String(nodeId)];
  if(target?.class_type!==V15_TYPE)throw new Error('无法定位当前V15执行节点。');
  target.inputs['启用潜空间续写']=job.continuation===true;
  target.inputs['潜空间续写任务']=job.continuation?JSON.stringify(job.descriptor):'';
  return payload;
}
// Narrow native Run route: disabled/unrelated workflows retain the original call and arguments.
// No graphToPrompt override and no API interception: our runner submits directly to api.queuePrompt.
export function installCurrentGroupQueue(app,report=message=>globalThis.alert(message)) {
  if(app.queuePrompt===app.__nfh3V15CurrentQueueInstalled||typeof app.queuePrompt!=='function')return;
  const previous=app.queuePrompt;
  app.queuePrompt=async function(...args) {
    if(app.__nfh3V15IndependentBatch)return previous.apply(this,args);
    const candidates=(app.graph?.nodes||app.graph?._nodes||[]).filter(n=>
      n.type===V15_TYPE&&!n.muted&&n.mode!==2&&n.mode!==4&&
      n.widgets?.some(w=>w.name==='启用潜空间续写'&&w.value===true));
    if(!candidates.length)return previous.apply(this,args);
    // Only executable targets count; muted/pruned/other workflows are never rerouted.
    const snapshot=await app.graphToPrompt();
    const targets=candidates.filter(n=>snapshot.output?.[String(n.id)]?.class_type===V15_TYPE);
    if(!targets.length)return previous.apply(this,args);
    if(targets.length!==1){report('同一工作流一次只运行一个启用续写的V15节点。');return;}
    if(Number(args[1]??1)!==1||Number(args[0]??0)!==0){report('连续组运行请使用普通队列、批次数量1，避免重复整组。');return;}
    const target=targets[0];
    if(typeof target.__nfh3RunCurrentGroup!=='function'){report('V15分镜面板尚未就绪，请刷新前端后重试。');return;}
    return target.__nfh3RunCurrentGroup();
  };
  app.__nfh3V15CurrentQueueInstalled=app.queuePrompt;
}
export async function waitForContinuation(api,promptId,cancelled,delay=ms=>new Promise(r=>setTimeout(r,ms))) {
  let missing=0;
  for(;;){
    if(cancelled()) throw new Error('已停止后续续写；已提交任务未被中断。再次运行使用新链。');
    const response=await api.fetchApi(`/history/${encodeURIComponent(promptId)}`);
    if(!response.ok) throw new Error(`读取任务状态失败 HTTP ${response.status}；未提交下一段。`);
    const record=(await response.json())[promptId];
    if(record){
      if(record.status?.status_str==='error') throw new Error(`前段 ${promptId} 执行失败，续写已停止。`);
      if(record.status?.completed===true&&record.status?.status_str==='success') return;
    }
    const q=await api.fetchApi('/queue');
    if(!q.ok) throw new Error('无法确认队列，续写停止。');
    const queue=await q.json();
    const present=[...(queue.queue_running||[]),...(queue.queue_pending||[])].some(x=>x[1]===promptId);
    missing=present?0:missing+1;
    if(missing>=3) throw new Error('前段已取消或历史被清除，续写停止；请重新开始。');
    await delay(1000);
  }
}
export const BATCH_ENDPOINT='/nanfeng/v15/h3/continuation/batches';
export async function batchRequest(api,path='',body){
  const response=await api.fetchApi(BATCH_ENDPOINT+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  let data;try{data=await response.json();}catch{throw new Error(`V15后台队列不可用（HTTP ${response.status}）；请手动重启ComfyUI后刷新，无前端等待回退。`);}
  if(!response.ok)throw new Error(data.error||`V15后台队列未加载（HTTP ${response.status}）；请手动重启ComfyUI。`);
  return data;
}
// Resolves on durable acknowledgement, NEVER on rendering/history completion.
export async function submitContinuation({jobs,build,api,nodeId,batchId=globalThis.crypto.randomUUID()}){
  const snapshots=[];
  for(const job of jobs)snapshots.push({...job,payload:structuredClone(await build(job))});
  const result=await batchRequest(api,'',{batch_id:batchId,node_id:String(nodeId),client_id:api.clientId||'',jobs:snapshots});
  if(result.id!==batchId)throw new Error('后台批次确认不匹配；请查看批次状态，勿重复点击。');
  return result;
}
