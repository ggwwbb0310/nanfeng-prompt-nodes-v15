"""南风H3 V8.1 智能分镜：服务端读取.env，逐图看图后调用语言模型。"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import mimetypes
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
SKILL_DIR = ROOT / "storyboard-skill"
SKILL_PATH = SKILL_DIR / "SKILL.md"
SKILL_REFERENCE_PATHS = (
    SKILL_DIR / "references" / "base-en.txt",
    SKILL_DIR / "references" / "ref-en.txt",
)
MAX_IMAGES = 9
MAX_VIDEOS = 3
MAX_AUDIOS = 3
MAX_IMAGE_BYTES = 30 * 1024 * 1024
_VISION_ANALYSIS_CACHE: dict[tuple[str, str, str], str] = {}
_VISION_ANALYSIS_CACHE_LIMIT = 64
VISION_CACHE_PATH = ROOT / ".vision-analysis-cache.json"
_STORYBOARD_JOBS: dict[str, "StoryboardJob"] = {}
_JOB_LOCK = threading.Lock()
CONFIG_FIELDS = (
    "NANFENG_VISION_BASE_URL", "NANFENG_VISION_API_KEY", "NANFENG_VISION_MODEL", "NANFENG_VISION_PROTOCOL",
    "NANFENG_TEXT_BASE_URL", "NANFENG_TEXT_API_KEY", "NANFENG_TEXT_MODEL", "NANFENG_TEXT_PROTOCOL",
    "NANFENG_TEXT_NS_STORYBOARD_BASE_URL", "NANFENG_TEXT_NS_STORYBOARD_API_KEY", "NANFENG_TEXT_NS_STORYBOARD_MODEL", "NANFENG_TEXT_NS_STORYBOARD_PROTOCOL",
)
CONFIG_PUBLIC_FIELDS = (
    "NANFENG_VISION_BASE_URL", "NANFENG_VISION_MODEL",
    "NANFENG_TEXT_BASE_URL", "NANFENG_TEXT_MODEL",
)
CONFIG_PROTOCOLS = {"chat_completions", "responses"}
STORYBOARD_MODES = {
    "ref2va": "多参 Ref2VA",
    "i2va": "I2V 图生视频",
    "reference_i2va": "非首帧I2V（图片参考）",
    "oneshot_continuation": "一镜到底续写",
    "continuation_cuts": "连续续写（允许切镜）",
    "t2va": "T2V 文生视频",
    "fl2va": "首尾帧 FL2VA",
}
PORTABLE_NS_SKILL_PATH = ROOT / "ns-storyboard-skill" / "SKILL.md"
SKILL_PROFILES = {
    "regular_storyboard": {"label": "常规提示词分镜", "description": "根据参考素材生成标准连续分镜提示词。", "skill_path": SKILL_PATH, "legacy_text_keys": True},
    "ns_storyboard": {"label": "NS提示词分镜", "description": "使用NS提示词分镜Skill生成连续分镜。", "skill_path": PORTABLE_NS_SKILL_PATH, "legacy_text_keys": False},
}


def skill_profile(skill_id: str | None = None) -> tuple[str, dict]:
    requested = str(skill_id or "regular_storyboard").strip()
    if requested not in SKILL_PROFILES:
        raise ValueError("提示词Skill无效")
    return requested, SKILL_PROFILES[requested]


def skill_text_keys(skill_id: str) -> tuple[str, str, str, str]:
    key, profile = skill_profile(skill_id)
    if profile.get("legacy_text_keys"):
        return ("NANFENG_TEXT_BASE_URL", "NANFENG_TEXT_API_KEY", "NANFENG_TEXT_MODEL", "NANFENG_TEXT_PROTOCOL")
    suffix = re.sub(r"[^A-Z0-9]+", "_", key.upper()).strip("_")
    return tuple(f"NANFENG_TEXT_{suffix}_{name}" for name in ("BASE_URL", "API_KEY", "MODEL", "PROTOCOL"))


class TransientAPIError(RuntimeError):
    """网络/上游瞬时故障：任务层可以安全继续等待并重试。"""


class StoryboardFormatError(ValueError):
    """已付费文本已返回但格式不标准：只做本地解析，不得重新付费请求。"""


class StoryboardCancelled(RuntimeError):
    """The user cancelled before another paid API stage could begin."""


def _load_vision_cache() -> None:
    if not VISION_CACHE_PATH.exists():
        return
    try:
        rows = json.loads(VISION_CACHE_PATH.read_text(encoding="utf-8"))
        for item in rows if isinstance(rows, list) else []:
            _VISION_ANALYSIS_CACHE[(str(item["base"]), str(item["model"]), str(item["digest"]))] = str(item["text"])
    except Exception:
        pass


def _save_vision_cache() -> None:
    rows = [{"base": k[0], "model": k[1], "digest": k[2], "text": v} for k, v in _VISION_ANALYSIS_CACHE.items()]
    temp = VISION_CACHE_PATH.with_suffix(VISION_CACHE_PATH.suffix + ".tmp")
    temp.write_text(json.dumps(rows[-_VISION_ANALYSIS_CACHE_LIMIT:], ensure_ascii=False), encoding="utf-8")
    os.replace(temp, VISION_CACHE_PATH)


class StoryboardJob:
    def __init__(self, job_id: str, payload: dict):
        self.id, self.payload = job_id, payload
        self.status, self.stage = "running", "准备任务"
        self.result, self.error, self.cancelled = None, "", False
        self.cancel_event = threading.Event()

    def public(self) -> dict:
        return {"job_id": self.id, "status": self.status, "stage": self.stage,
                "result": self.result if self.status == "completed" else None,
                "error": self.error if self.status == "failed" else ""}


def _run_storyboard_job(job: StoryboardJob) -> None:
    """Run one paid pipeline exactly once; request_model owns bounded transport retries."""
    job.stage = "逐图分析并生成完整分镜"
    try:
        value = generate_storyboard(job.payload, cancel_event=job.cancel_event)
        job.result = asyncio.run(value) if hasattr(value, "__await__") else value
        if job.cancelled:
            job.status, job.stage = "cancelled", "已取消"
        else:
            job.status, job.stage = "completed", "完成"
    except Exception as exc:
        job.error = str(exc)
        if job.cancelled:
            job.status, job.stage = "cancelled", "已取消"
        else:
            job.status, job.stage = "failed", "API请求失败，未自动重跑完整任务"


_load_vision_cache()


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values


def config_status(env: dict[str, str] | None = None, skill_id: str = "regular_storyboard") -> dict:
    cfg = env or load_env()
    skill_profile(skill_id)
    vision = all(cfg.get(k, "").strip() for k in (
        "NANFENG_VISION_API_KEY", "NANFENG_VISION_BASE_URL", "NANFENG_VISION_MODEL"
    ))
    text_keys = skill_text_keys(skill_id)
    text = all(cfg.get(k, "").strip() for k in text_keys[:3])
    return {"vision_configured": vision, "text_configured": text, "skill_exists": SKILL_PATH.exists(), "skill_id": skill_id}


def config_for_browser(env: dict[str, str] | None = None, skill_id: str = "regular_storyboard") -> dict:
    """Return editable non-secret fields for the selected Skill; secrets remain booleans."""
    cfg = env or load_env()
    key, profile = skill_profile(skill_id)
    text_base, text_key, text_model, text_protocol = skill_text_keys(key)
    result = config_status(cfg, key)
    result.update({key: cfg.get(key, "") for key in ("NANFENG_VISION_BASE_URL", "NANFENG_VISION_MODEL", text_base, text_model)})
    result["NANFENG_TEXT_BASE_URL"] = cfg.get(text_base, "")
    result["NANFENG_TEXT_MODEL"] = cfg.get(text_model, "")
    result["vision_key_saved"] = bool(cfg.get("NANFENG_VISION_API_KEY", "").strip())
    result["text_key_saved"] = bool(cfg.get(text_key, "").strip())
    result["skill_label"] = profile["label"]
    result["skill_description"] = profile["description"]
    result["skills"] = [{"id": item_id, "label": item["label"], "description": item["description"]} for item_id, item in SKILL_PROFILES.items()]
    return result


def normalize_base_url(value: str) -> str:
    """Normalize an OpenAI-compatible base URL to end at /v1."""
    base = str(value or "").strip().rstrip("/")
    if not base:
        return ""
    base = re.sub(r"/(?:chat/completions|responses|models)$", "", base, flags=re.I).rstrip("/")
    if not re.search(r"/v\d+$", base, re.I):
        base += "/v1"
    return base


def _validate_config_payload(payload: dict) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("配置参数格式错误")
    values: dict[str, str] = {}
    for key in CONFIG_FIELDS:
        value = payload.get(key)
        if value is None:
            continue
        if key.endswith("_PROTOCOL"):
            continue
        if not isinstance(value, str):
            raise ValueError(f"{key}必须是文本")
        value = value.strip()
        if "\n" in value or "\r" in value:
            raise ValueError(f"{key}不能包含换行")
        values[key] = value
    for key in ("NANFENG_VISION_BASE_URL", "NANFENG_TEXT_BASE_URL", "NANFENG_TEXT_NS_STORYBOARD_BASE_URL"):
        value = values.get(key)
        if value and not re.match(r"^https?://", value, re.I):
            raise ValueError(f"{key}必须以http://或https://开头")
        if value:
            values[key] = normalize_base_url(value)
    for key in ("NANFENG_VISION_PROTOCOL", "NANFENG_TEXT_PROTOCOL"):
        value = values.get(key)
        if value and value not in CONFIG_PROTOCOLS:
            raise ValueError(f"{key}只支持chat_completions或responses")
    return values


def save_config(payload: dict, path: Path = ENV_PATH) -> dict:
    """Atomically update package .env; browser text fields map to the selected Skill."""
    current = load_env(path)
    skill_id, _profile = skill_profile(payload.get("skill_id", "regular_storyboard"))
    text_base, text_key, text_model, text_protocol = skill_text_keys(skill_id)
    normalized = dict(payload)
    if skill_id != "regular_storyboard":
        for generic, selected in (("NANFENG_TEXT_BASE_URL", text_base), ("NANFENG_TEXT_API_KEY", text_key), ("NANFENG_TEXT_MODEL", text_model)):
            if generic in normalized:
                normalized[selected] = normalized[generic]
                normalized.pop(generic, None)
    values = _validate_config_payload(normalized)
    for key, value in values.items():
        if key.endswith("_API_KEY") and not value:
            continue
        current[key] = value
    current["NANFENG_VISION_PROTOCOL"] = "chat_completions"
    current["NANFENG_TEXT_PROTOCOL"] = "chat_completions"
    lines = ["# 南风H3 V8.1 智能分镜API配置（仅服务端读取）"]
    for key in CONFIG_FIELDS:
        lines.append(f"{key}={current.get(key, '')}")
        if key == "NANFENG_VISION_PROTOCOL":
            lines.append("")
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    os.replace(temp, path)
    return config_for_browser(current, payload.get("skill_id", "regular_storyboard"))


def clear_config(path: Path = ENV_PATH) -> dict:
    blank = {key: "" for key in CONFIG_FIELDS}
    blank["NANFENG_VISION_PROTOCOL"] = "chat_completions"
    blank["NANFENG_TEXT_PROTOCOL"] = "chat_completions"
    lines = ["# 南风H3 V8.1 智能分镜API配置（仅服务端读取）"]
    for key in CONFIG_FIELDS:
        lines.append(f"{key}={blank[key]}")
        if key == "NANFENG_VISION_PROTOCOL":
            lines.append("")
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    os.replace(temp, path)
    return config_for_browser(blank)


def _endpoint(base_url: str, protocol: str) -> str:
    base = base_url.rstrip("/")
    suffix = "/responses" if protocol == "responses" else "/chat/completions"
    return base if base.endswith(suffix) else base + suffix


def resolve_discovery_credentials(requested_base: str, requested_key: str, saved_base: str, saved_key: str) -> tuple[str, str]:
    """Never send a saved credential to a caller-selected endpoint."""
    base = normalize_base_url(requested_base or saved_base)
    key = str(requested_key or "").strip()
    if key:
        return base, key
    if base != normalize_base_url(saved_base):
        raise ValueError("更换Base URL时必须同时填写对应API Key")
    return base, str(saved_key or "").strip()


def list_models(base_url: str, api_key: str, timeout: int = 60) -> list[str]:
    base = normalize_base_url(base_url)
    if not base or not api_key.strip():
        raise ValueError("请先填写Base URL和API Key")
    req = urllib.request.Request(
        base.rstrip("/") + "/models",
        headers={"Accept": "application/json", "Authorization": f"Bearer {api_key.strip()}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"识别模型失败 HTTP {exc.code}: {body[:500]}") from exc
    except Exception as exc:
        raise RuntimeError(f"识别模型连接失败：{exc}") from exc
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"模型接口返回的不是JSON：{body[:300]}") from exc
    raw = data.get("data", data.get("models", [])) if isinstance(data, dict) else data
    models: list[str] = []
    for item in raw if isinstance(raw, list) else []:
        value = item.get("id") or item.get("name") if isinstance(item, dict) else item
        if isinstance(value, str) and value.strip():
            models.append(value.strip())
    models = sorted(set(models), key=str.lower)
    if not models:
        raise RuntimeError("中转/models没有返回可用模型ID")
    return models


def _extract_text(data: dict) -> str:
    choices = data.get("choices") if isinstance(data, dict) else None
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    if choice.get("finish_reason") == "length" or data.get("status") == "incomplete":
        raise StoryboardFormatError("模型输出达到上限，拒绝使用截断内容；未重复付费请求")
    content = choice.get("message", {}).get("content") if isinstance(choice.get("message"), dict) else None
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        text = "\n".join(str(x.get("text", "")) for x in content if isinstance(x, dict)).strip()
        if text:
            return text
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"].strip()
    pieces = []
    for item in data.get("output", []):
        for part in item.get("content", []):
            value = part.get("text") or part.get("output_text")
            if isinstance(value, str):
                pieces.append(value)
    text = "\n".join(pieces).strip()
    if not text:
        choices = data.get("choices") if isinstance(data, dict) else None
        choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        details = usage.get("completion_tokens_details") if isinstance(usage.get("completion_tokens_details"), dict) else {}
        reasoning_used = bool(message.get("reasoning_content")) or int(details.get("reasoning_tokens") or 0) > 0
        if choice.get("finish_reason") == "length" or reasoning_used:
            raise StoryboardFormatError("模型已返回但正文为空：输出预算可能被思考过程耗尽；未重复付费请求")
        raise StoryboardFormatError("模型已返回成功响应但正文为空；未重复付费请求")
    return text


def _is_official_deepseek(base_url: str) -> bool:
    """Only send DeepSeek-specific fields to the official endpoint, preserving relay compatibility."""
    from urllib.parse import urlparse
    try:
        return (urlparse(normalize_base_url(base_url)).hostname or "").lower() == "api.deepseek.com"
    except Exception:
        return False


def _supports_reasoning_effort(model: str) -> bool:
    """Only models verified with this parameter receive it; generic relays stay untouched."""
    value = str(model or "").strip().lower()
    return value == "gpt-5.6-sol" or value.startswith("gpt-5.6-sol-")


def request_model(base_url: str, api_key: str, model: str, messages: list[dict], *, protocol: str = "chat_completions",
                  temperature: float = 0.0, timeout: int = 300, attempts: int = 5,
                  max_output_tokens: int | None = None, disable_reasoning: bool = False,
                  stream: bool = False) -> str:
    protocol = protocol.strip().lower() or "chat_completions"
    if protocol == "responses":
        payload = {"model": model, "input": messages, "stream": False}
        if max_output_tokens is not None:
            payload["max_output_tokens"] = int(max_output_tokens)
    else:
        payload = {"model": model, "messages": messages, "temperature": temperature, "stream": bool(stream)}
        if max_output_tokens is not None:
            payload["max_tokens"] = int(max_output_tokens)
        if disable_reasoning:
            if _is_official_deepseek(base_url):
                payload["thinking"] = {"type": "disabled"}
            elif _supports_reasoning_effort(model):
                payload["reasoning_effort"] = "none"
    last_error: Exception | None = None
    for attempt in range(max(1, attempts)):
        req = urllib.request.Request(
            _endpoint(base_url, protocol),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_type = str(getattr(response, "headers", {}).get("content-type", "")).lower()
                if stream and protocol == "chat_completions" and "text/event-stream" in content_type:
                    chunks: list[str] = []
                    completed = False
                    truncated = False
                    for raw_line in response:
                        line = raw_line.decode("utf-8", "replace").strip()
                        if not line.startswith("data:"):
                            continue
                        event = line[5:].strip()
                        if event == "[DONE]":
                            completed = True
                            break
                        data = json.loads(event)
                        choices = data.get("choices") or []
                        if choices:
                            choice = choices[0]
                            delta = choice.get("delta") or {}
                            content = delta.get("content")
                            if isinstance(content, str):
                                chunks.append(content)
                            finish_reason = choice.get("finish_reason")
                            if finish_reason:
                                truncated = truncated or finish_reason == "length"
                                completed = True
                    text = "".join(chunks).strip()
                    if truncated:
                        raise StoryboardFormatError("模型输出达到上限，拒绝使用截断内容；未重复付费请求")
                    if not completed:
                        raise StoryboardFormatError("流式API连接提前结束，拒绝使用可能截断的分镜；未重复付费请求")
                    if not text:
                        raise RuntimeError("流式API返回为空")
                    return text
                body = response.read().decode("utf-8", "replace")
            data = json.loads(body)
            text = _extract_text(data)
            return text
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            if exc.code not in {408, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"API HTTP {exc.code}: {body[:800]}") from exc
            last_error = RuntimeError(f"API HTTP {exc.code}: {body[:800]}")
        except (urllib.error.URLError, ssl.SSLError, ConnectionError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
        except StoryboardFormatError:
            raise
        except RuntimeError as exc:
            raise StoryboardFormatError(f"模型已返回但内容无法使用：{exc}；未重复付费请求") from exc
        except Exception as exc:
            last_error = exc
        if attempt + 1 < max(1, attempts):
            time.sleep(1.5 * (attempt + 1))
    raise TransientAPIError(f"API连接或返回失败（本轮已重试{max(1, attempts)}次）：{last_error}") from last_error


def resolve_input_images(names: list[str]) -> list[dict]:
    import folder_paths

    images = []
    for index, raw in enumerate(names[:MAX_IMAGES], 1):
        name = str(raw or "").strip()
        if not name or name in {"未选择", "None", "null"}:
            continue
        path = Path(folder_paths.get_annotated_filepath(name)).resolve()
        input_root = Path(folder_paths.get_input_directory()).resolve()
        if input_root not in path.parents and path != input_root:
            raise ValueError(f"图片{index}不在ComfyUI input目录")
        if not path.is_file():
            raise FileNotFoundError(f"图片{index}不存在：{name}")
        size = path.stat().st_size
        if size > MAX_IMAGE_BYTES:
            raise ValueError(f"图片{index}超过30MB")
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            raise ValueError(f"图片{index}只支持JPEG、PNG、WebP")
        images.append({"index": index, "name": path.name, "mime": mime, "base64": base64.b64encode(path.read_bytes()).decode("ascii")})
    return images


def resolve_input_media(names: list[str], kind: str, limit: int) -> list[dict]:
    """Resolve uploaded video/audio names without decoding expensive media."""
    import folder_paths

    items = []
    input_root = Path(folder_paths.get_input_directory()).resolve()
    for index, raw in enumerate(names[:limit], 1):
        name = str(raw or "").strip()
        if not name or name in {"未选择", "None", "null"}:
            continue
        path = Path(folder_paths.get_annotated_filepath(name)).resolve()
        if input_root not in path.parents and path != input_root:
            raise ValueError(f"{kind}{index}不在ComfyUI input目录")
        if not path.is_file():
            raise FileNotFoundError(f"{kind}{index}不存在：{name}")
        items.append({"index": index, "name": path.name})
    return items


def vision_messages(image: dict) -> list[dict]:
    index = image["index"]
    text = (
        f"你现在只分析一张参考图片，固定编号是@图片{index}。严格分类为人物图、场景图、产品或道具图三类之一。"
        "提取人物身份、外貌、服装、姿态和朝向，或场景空间结构、光线、时间天气，或道具材质、颜色、朝向和状态。"
        "只分析当前图片，不关联其他图片，不编造。不要自行添加其他@图片编号。"
    )
    return [{"role": "user", "content": [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": f"data:{image['mime']};base64,{image['base64']}"}},
    ]}]


async def analyze_images(images: list[dict], cfg: dict[str, str], cancel_event: threading.Event | None = None) -> str:
    semaphore = asyncio.Semaphore(max(1, min(3, len(images) or 1)))

    async def one(image: dict) -> str:
        async with semaphore:
            if cancel_event is not None and cancel_event.is_set():
                raise StoryboardCancelled("任务已取消")
            digest = hashlib.sha256(image["base64"].encode("ascii")).hexdigest()
            cache_key = (normalize_base_url(cfg["NANFENG_VISION_BASE_URL"]), cfg["NANFENG_VISION_MODEL"], digest)
            cached = _VISION_ANALYSIS_CACHE.get(cache_key)
            if cached is not None:
                return f"@图片{image['index']}：{cached}"
            raw = await asyncio.to_thread(
                request_model,
                cfg["NANFENG_VISION_BASE_URL"], cfg["NANFENG_VISION_API_KEY"], cfg["NANFENG_VISION_MODEL"],
                vision_messages(image), protocol=cfg.get("NANFENG_VISION_PROTOCOL", "chat_completions"), temperature=0.0,
                timeout=60, attempts=1, max_output_tokens=1200, disable_reasoning=True,
            )
            if cancel_event is not None and cancel_event.is_set():
                raise StoryboardCancelled("任务已取消")
            clean = re.sub(r"^\s*@图片\d+\s*[:：]\s*", "", raw).strip()
            if len(_VISION_ANALYSIS_CACHE) >= _VISION_ANALYSIS_CACHE_LIMIT:
                _VISION_ANALYSIS_CACHE.pop(next(iter(_VISION_ANALYSIS_CACHE)))
            _VISION_ANALYSIS_CACHE[cache_key] = clean
            _save_vision_cache()
            return f"@图片{image['index']}：{clean}"

    return "\n\n".join(await asyncio.gather(*(one(image) for image in images)))


def validate_mode(mode: str, images: list[dict], videos: list[dict]) -> str:
    mode = str(mode or "ref2va").strip().lower()
    if mode not in STORYBOARD_MODES:
        raise ValueError("提示词模式无效")
    if mode in {"reference_i2va", "oneshot_continuation", "continuation_cuts"} and not 1 <= len(images) <= 9:
        raise ValueError("非首帧I2V需要1到9张视觉参考图片")
    required = {"t2va": 0, "i2va": 1, "fl2va": 2}
    if mode in required and len(images) != required[mode]:
        labels = {"t2va": "T2V文生视频不能使用参考图片", "i2va": "I2V图生视频必须且只能使用@图片1", "fl2va": "首尾帧必须使用@图片1首帧和@图片2尾帧"}
        raise ValueError(labels[mode])
    if mode != "ref2va" and videos:
        raise ValueError("参考视频只支持多参Ref2VA模式")
    if mode == "ref2va" and not images and not videos:
        raise ValueError("多参模式至少需要1张参考图片或参考视频")
    return mode


def mode_contract(mode: str, count: int) -> str:
    if mode == "continuation_cuts":
        return f"输出{count}段，段1起编号、---分隔，参考说明加三段正文。默认连续，用户明确说切、切到、反打或硬切即允许指定位置切镜，不要求必须写硬字；不可擅自加切镜。每段只说本段分配对白，明确无对白段不加新话。保留身份场景与动作状态，未知段尾软承接。整组预算联合分配。此模式仅改提示词，不断开latent或修改分组；存在重叠锚定时切镜安排在重叠之后，不声称首帧硬切有保证。"
    if mode == "oneshot_continuation":
        return f"严格输出{count}段，标题依次为段1到段{count}，段间用---分隔。所有段属于同一个连续长镜头：首段由图片建立可见起始状态，后续段以实际传入的latent动作和机位为准，图片只保留身份外观与场景身份，不恢复原图姿势。规划时尚未生成后续latent，不得将计划段尾当成已观察事实，不预设精确手位、机位或上段对白已说完；只写简洁、可承接实际动作的软轨迹和有限的下一步意图，不无限延续动作，不罗列条件分支。不切镜不重置，机位变化只能连续发生。每段输出参考职责说明及integrated_multimodal_description、overall_soundscape、non_diegetic_music三段。中间段末无需强制停稳。只使用程序提供的名义时长与重叠帧数，不虚构采样时长或精确生成终态。"
    common = f"严格输出{count}段。从段1开始依次编号到段{count}；每个标题行只能写对应的‘段N’，不得写‘段1到段{count}’或其他文字。段之间用---分隔。每段必须是可直接复制使用的完整官方提示词。相邻两段必须作为一个整体联合设计：先联合规划段N尾镜与段N+1首镜，再分别写入两段。下一段首镜继承上一段尾镜的站位关系、前中后景、左右位置、朝向、视线、距离、遮挡、动作阶段、道具状态和180度动作轴；切镜只改变观察位置，不改变世界状态。跨段边界必须形成可剪辑的镜头变化，优先用动作轴内的正反打、反应镜头，或有动机的景别/机位变化；除非用户明确要求连续同镜头，段N尾镜与段N+1首镜不得使用相同景别且相同机位角度。不得为了变化而瞬移、越轴、左右互换、重置动作或跳过动作。下一段第一帧就必须落在上一段尾镜的状态：不得先闪出默认构图、参考图原始姿势、错误人数或错误机位，不得重新建立人物站位或让动作重新起势；换景别或换角度只能发生在状态继承成立之后，并保持人物数量、唯一实例、接触点、遮挡、动作相位、光线和轴线连续。"
    if mode == "ref2va":
        return common + "当前模式为Ref2VA多参。Ref2VA多参素材只提供身份、外观、场景、道具、风格或动作参考，不锁定任何Picture为0.00秒首帧；不得在段首先闪现或完整展示任一参考素材的原始画面，不得轮播、拼贴或从参考图原始构图/姿势起步。每段00:00直接生成该段目标剧情构图：第一段直接进入用户要求的开场，后续段直接生成承接上一段尾镜世界状态的目标画面；所有素材从第一帧起按各自语义职责融合。每段严格依次输出subject_definitions、summary、retention_analysis、detailed_description、overall_soundscape、non_diegetic_music六段，使用<Subject N>/<Picture N>。"
    if mode == "reference_i2va":
        return common + "当前为自定义非首帧I2V图片参考写法。每段先用英文声明Picture 1只提供视觉参考，不定义首帧或开场构图；然后依次输出integrated_multimodal_description、overall_soundscape、non_diegetic_music。只解除参考图的像素级首帧绑定和原始景别构图；人物身份、服装、发型、人数、初始姿势、身体朝向、视线、双手位置、接触点、道具、场景布局、天气、光线和空间关系默认全部保留，不得因换景别而重置。首个可见画面直接使用用户要求的景别；仅用户要求时改变机位，保持轴线与自然透视。画外肢体仍保持原状态；后续动作从继承状态自然发展，不是全程冻结。禁止首帧对齐句及Ref2VA六段结构。"
    if mode == "i2va":
        return common + "当前模式为I2VA图生视频。每段先写@图片1对应Picture 1在0.00秒的官方首帧对齐句，再依次输出integrated_multimodal_description、overall_soundscape、non_diegetic_music。"
    if mode == "fl2va":
        return common + "当前模式为FL2VA首尾帧。每段先写Picture 1对齐0.00秒、Picture 2对齐该段结束时刻的官方首尾对齐句，再依次输出integrated_multimodal_description、overall_soundscape、non_diegetic_music。"
    return common + "当前模式为T2VA文生视频。不得写任何Picture/Video/Audio引用或对齐句；每段严格依次输出integrated_multimodal_description、overall_soundscape、non_diegetic_music。"


def video_reference_contract(videos: list[dict] | None) -> str:
    """Append video semantics without altering the established image-only prompt path."""
    items = videos or []
    if not items:
        return ""
    manifest = "\n".join(f"@视频{x['index']}：{x['name']} -> <Video {x['index']}>" for x in items)
    return (
        "\n\n新增参考视频槽位（这是对原正常Skill的追加功能；不得删改、替换或弱化上文任何原有规则）：\n"
        f"{manifest}\n\n"
        "参考视频追加合同：<Video N>严格对应上传视频槽N。仅当用户要求参考视频动作、照视频跳舞、动作迁移、节奏参考或运镜参考时使用。"
        "目标人物的身份和全部可见外观唯一来自<Picture N>；舞蹈编排、身体力学、动作时序、节奏、重心转移、手臂轨迹、肩胯运动、头发运动时序及用户指定运镜动作来自<Video N>。"
        "<Picture N>仍只是身份/外观参考，不得变成首帧、关键帧、姿势、裁切或构图锚点；目标视频首帧已经完成替换，不得闪现参考图、源视频人物、拼贴或过渡变形。"
        "必须在subject_definitions中分别定义目标<Subject N>、<Picture N>的独占外观职责和<Video N>的纯动作职责；"
        "在summary中明确identity replacement + motion transfer；在retention_analysis中把目标人物及图片写为fully_preserved，把视频写为attribute_transfer；"
        "在detailed_description和每个Shot中持续写明同一目标人物执行视频动作，并保持图片中的脸、发型、妆容、服装、饰品及其他可见特征。"
        "不得复制或混合视频人物的身份、脸、发型、发色、妆容、肤质、饰品、纹身、服装、体貌或个人视觉特征；不得忽略已上传视频，不得写‘没有提供动作参考视频’或把参考动作说成模型原创。"
    )


def validate_continuation_context(context_length: int | None, duration_seconds: float) -> None:
    """Planning-only validation; never coerce or override a selected runtime window."""
    if context_length is None:
        return
    if type(context_length) is not int or context_length not in (5, 22, 39, 56):
        raise ValueError("context_length必须为所选控件支持的5、22、39或56帧，不支持0或隐式覆盖")
    if context_length / 24 >= duration_seconds:
        raise ValueError("重叠窗口不小于名义请求时长，无法安排重叠后的新内容；请调整时长或context_length")


def storyboard_messages(skill: str, idea: str, count: int, images: list[dict], analysis: str,
                        videos: list[dict] | None = None, audios: list[dict] | None = None,
                        mode: str = "ref2va", duration_seconds: float = 5.0,
                        context_length: int | None = None) -> list[dict]:
    manifest = "\n".join(f"@图片{x['index']}：{x['name']}" for x in images) or "无图片"
    duration_label = f"{duration_seconds:g}"
    duration_contract = f"硬性时长先决条件：每个分镜对应{duration_label}秒视频。必须先按{duration_label}秒重新规划动作密度、镜头数量、对白长度、动作收束和段尾状态；不得按默认5秒或其他时长写作。\n"
    if mode in {"oneshot_continuation", "continuation_cuts"}:
        duration_contract = (
            f"每段名义请求时长：{duration_label}秒；按此预算动作和对白，不代表已验证的采样或交付时长。首段无续写裁切。"
            "后续段开头重叠跟随实际钉住的运动，不要求停顿或冻结；被裁重叠内不安排新的关键事件或新对白，新的动作推进在重叠之后自然衔接。\n"
        )
        total_requested = count * duration_seconds
        segment_windows = "；".join(
            f"段{i + 1}：本组名义进度{i * duration_seconds:g}–{(i + 1) * duration_seconds:g}秒"
            for i in range(count)
        )
        duration_contract += (
            f"本次连续组整体预算：{count}段 × 每段{duration_label}秒 = {total_requested:g}秒名义总时长。\n"
            f"分段规划区间：{segment_windows}。\n"
            "先按本组整体预算联合规划剧情、对白顺序、情绪递进与一次完整运镜，再把不同阶段分配到各段。"
            "用户说开场、途中、最后，默认指本组开头、全组过程、最后一段结束，不是每段都执行一遍；用户明确指定段号时优先遵守。"
            "不得让第一段提前完成全组终点，不得把全部对白复制到每段，也不得为填满总时长编造重复动作或新台词。"
            "上述区间只是规划进度标签，不是拼接后精确时间码；每段输出仍用从00:00起的本段局部时间，"
            "后续段须避开本段裁除的上下文窗口。实际可交付时长受帧数对齐和重叠裁剪影响，不能声称名义总时长就是最终成片时长。"
            "阶段目标保持软约束，实际latent决定当前动作和机位，不为赶计划终点跳动作或切镜。\n"
        )
        if context_length is None:
            duration_contract += "未提供context_length，数值重叠窗口未知；不得编造默认帧数或秒数。\n"
        else:
            validate_continuation_context(context_length, duration_seconds)
            duration_contract += (
                f"所选context_length={context_length}帧；仅后续段开头这{context_length}帧为续写上下文并被裁去。"
                f"按24fps仅换算该帧窗口：{context_length}/24={context_length / 24:.6g}秒；"
                "这不是采样时长量化公式，不据此声称精确交付时长，不修改所选帧数。\n"
            )
    messages = [
        {"role": "system", "content": "严格执行下面的H3官方提示词Skill和当前模式契约，只输出正式结果，不解释。\n\n" + skill},
        {"role": "user", "content": (
            f"当前官方模式：{STORYBOARD_MODES[mode]}\n"
            f"{duration_contract}"
            f"{mode_contract(mode, count)}\n\n"
            f"用户想法：\n{idea or '请根据参考素材合理创作。'}\n\n"
            f"固定上传槽位：\n{manifest}\n\n逐图看图结果：\n{analysis or '无'}\n\n"
            "禁止追问。图片编号严格绑定上传槽位，不重排、不编造；用户原有对白必须保留说话人、原意和顺序。"
        )},
    ]
    if mode == "ref2va" and videos:
        messages[1]["content"] += video_reference_contract(videos)
    return messages


def parse_storyboard(text: str, count: int) -> dict:
    raw = re.sub(r"```(?:text)?|```", "", str(text)).strip()
    global_match = re.search(r"全局提示词\s*[:：]\s*([\s\S]*?)(?=\n\s*(?:---\s*)?\n?\s*段\s*1\b|$)", raw)
    global_prompt = global_match.group(1).strip() if global_match else ""
    matches = list(re.finditer(r"(?m)^\s*段\s*(\d+)\s*[:：]?\s*$", raw))
    if any(int(match.group(1)) != index for index, match in enumerate(matches, 1)):
        raise StoryboardFormatError("模型返回的段号存在跳号、重复或顺序错误")
    segments = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        segments.append(raw[match.start():end].strip().rstrip("-").strip())
    if len(segments) != count:
        if count == 1 and not matches and raw:
            segments = [raw]
        else:
            blocks = [x.strip() for x in re.split(r"(?m)^\s*---+\s*$", raw) if x.strip()]
            if len(blocks) == count:
                segments = [f"段{i}\n\n{block}" for i, block in enumerate(blocks, 1)]
            else:
                raise StoryboardFormatError(f"模型返回{len(segments)}段，但要求{count}段；原始完整输出已收到，未重复生成")
    return {"global": global_prompt, "segments": segments, "raw": raw}


_RUNTIME_COMPACT_CONTRACT = """# H3 official runtime contract
Privately plan a continuity ledger before output. Across segments preserve identity, clothing, screen-left/right, depth, facing, gaze, 180-degree axis, prop owner/hand/state, action phase, lighting, and stable speaker IDs. Segment N+1 starts from the exact visible end state of segment N; cuts change viewpoint, not world state. Use one feasible principal action or short exchange per requested duration, concrete physical transitions, readable faces/hands/props, and no invented dialogue, characters, music, or scene changes. Final official fields are English; preserve user dialogue and visible text verbatim in their original language. `non_diegetic_music` is `N/A` unless explicitly requested.

# Runtime compact Ref2VA contract
- Keep each `<Subject N>`, `<Picture N>`, `<Video N>`, and `<Audio N>` bound to one meaning across all sections.
- Ref2VA order is exactly: `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, `non_diegetic_music`.
- Define every reference label before reuse. Use `[Shot 1]` without a timestamp; later cuts use `[Shot 2] At MM:SS.mmm` with strictly increasing times inside the requested duration.
- Assign stable speakers `(S1)`, `(S2)` by first vocal event, preserve dialogue verbatim, use `<scenetrans>` when speech crosses a cut, and `<cutoff>` only when the video ending truncates speech.
- Put synchronized dialogue and foley in `detailed_description`; reserve `overall_soundscape` for ambience and physical sound summary.

# Runtime compact base-mode contract
- Emit the applicable picture-alignment instruction first, followed by one blank line and exactly `integrated_multimodal_description`, `overall_soundscape`, `non_diegetic_music`.
- I2VA: `<Picture 1>` is the first frame of `[Shot 1]` at 0.00 seconds.
- FL2VA: align the first picture to 0.00 and the last picture to the exact requested duration in the actual final shot.
- L2VA: align `<Picture 1>` to the exact requested duration in the actual final shot; infer a compatible opening and visibly converge on that frame.
- Never invent, renumber, or reuse an unresolved reference label.
"""


def load_storyboard_skill(mode: str = "ref2va", skill_id: str = "regular_storyboard") -> str:
    if mode == "continuation_cuts":
        folder = "continuation-cuts-ns-skill" if skill_id == "ns_storyboard" else "continuation-cuts-skill"
        return (ROOT / folder / "SKILL.md").read_text(encoding="utf-8")
    if mode == "oneshot_continuation":
        folder = "oneshot-continuation-ns-skill" if skill_id == "ns_storyboard" else "oneshot-continuation-skill"
        return (ROOT / folder / "SKILL.md").read_text(encoding="utf-8")
    if mode == "reference_i2va":
        folder = "nonfirst-i2v-ns-skill" if skill_id == "ns_storyboard" else "nonfirst-i2v-skill"
        return (ROOT / folder / "SKILL.md").read_text(encoding="utf-8")
    selected_path = skill_profile(skill_id)[1]["skill_path"]
    if selected_path.exists() and skill_id == "ns_storyboard":
        return selected_path.read_text(encoding="utf-8")
    if not SKILL_PATH.exists():
        return "输出适合MiniMax H3官方结构的连续视频提示词。"
    # Inject only the execution-critical subset of the 16-24K references.
    # Runtime compact Ref2VA contract: preserve one meaning per <Subject N>/<Picture N>;
    # use six sections in the order declared above; define each label before reuse;
    # detailed_description uses [Shot 1], then [Shot 2] At MM:SS.mmm with strictly
    # increasing cut times; bind stable speakers as (S1), (S2), keep dialogue verbatim;
    # use <scenetrans> across cuts and <cutoff> only at the video end; put synchronized
    # dialogue/foley in detailed_description and ambience in overall_soundscape.
    # Runtime compact base-mode contract: emit the applicable first/last-frame alignment
    # instruction before the three fields; Picture 1 is Shot 1 at 0.00 for I2VA, FL2VA
    # aligns first and last pictures to 0.00 and the exact duration, and L2VA aligns its
    # picture to the last shot at the exact duration. Never invent unresolved labels.
    return _RUNTIME_COMPACT_CONTRACT


def storyboard_output_budget(segment_count: int) -> int:
    """Bound output so OpenAI-compatible proxies do not spend minutes on hidden reasoning."""
    count = max(1, min(12, int(segment_count)))
    return min(8000, 800 + 600 * count)


async def generate_storyboard(payload: dict, cfg: dict[str, str] | None = None, cancel_event: threading.Event | None = None) -> dict:
    config = cfg or load_env()
    skill_id, profile = skill_profile(payload.get("skill_id", "regular_storyboard"))
    text_base_key, text_api_key, text_model_key, text_protocol_key = skill_text_keys(skill_id)
    status = config_status(config, skill_id)
    if not status["text_configured"]:
        raise ValueError("语言模型API尚未在节点包.env完整配置")
    count = int(payload.get("segment_count", 1))
    if count < 1 or count > 12:
        raise ValueError("分镜段数必须为1到12")
    duration_seconds = float(payload.get("duration_seconds", 5.0))
    if duration_seconds < 1.0 or duration_seconds > 15.0:
        raise ValueError("视频时长必须为1到15秒")
    names = payload.get("images") or []
    video_names = payload.get("videos") or []
    audio_names = payload.get("audios") or []
    if not isinstance(names, list):
        raise ValueError("图片参数格式错误")
    if not isinstance(video_names, list) or not isinstance(audio_names, list):
        raise ValueError("视频或音频参数格式错误")
    images = resolve_input_images(names)
    videos = resolve_input_media(video_names, "视频", MAX_VIDEOS)
    audios = resolve_input_media(audio_names, "音频", MAX_AUDIOS)
    mode = validate_mode(payload.get("mode", "ref2va"), images, videos)
    if mode in {"oneshot_continuation", "continuation_cuts"} and count < 2:
        raise ValueError("一镜到底续写至少需要2段")
    if mode in {"oneshot_continuation", "continuation_cuts"}:
        validate_continuation_context(payload.get("context_length"), duration_seconds)
    if images and not status["vision_configured"]:
        raise ValueError("已添加图片，但看图API尚未在节点包.env完整配置")
    skill = load_storyboard_skill(mode) if skill_id == "regular_storyboard" else load_storyboard_skill(mode, skill_id)
    try:
        analysis = await analyze_images(images, config, cancel_event=cancel_event) if images else ""
    except StoryboardFormatError as exc:
        raise StoryboardFormatError(f"看图阶段：{exc}") from exc
    if cancel_event is not None and cancel_event.is_set():
        raise StoryboardCancelled("任务已取消")
    messages = storyboard_messages(skill, str(payload.get("idea", "")).strip(), count, images, analysis, videos, audios, mode, duration_seconds,
                                   **({"context_length": payload.get("context_length")} if mode in {"oneshot_continuation", "continuation_cuts"} else {}))
    result = await asyncio.to_thread(
        request_model,
        config.get(text_base_key, ""), config.get(text_api_key, ""), config.get(text_model_key, ""), messages,
        protocol=config.get(text_protocol_key, "chat_completions"), temperature=0.7, timeout=180, attempts=1,
        max_output_tokens=storyboard_output_budget(count), disable_reasoning=True,
        stream=config.get(text_protocol_key, "chat_completions") == "chat_completions",
    )
    parsed = parse_storyboard(result, count)
    parsed["vision_analysis"] = analysis
    return parsed


def register_routes() -> None:
    try:
        from aiohttp import web
        from server import PromptServer
    except Exception:
        return

    prompt_server = getattr(PromptServer, "instance", None)
    if prompt_server is None:
        return
    routes = prompt_server.routes

    @routes.get("/nanfeng/v15/h3/storyboard/config")
    async def get_config(request):
        return web.json_response(config_for_browser(skill_id=request.query.get("skill_id", "regular_storyboard")))

    @routes.post("/nanfeng/v15/h3/storyboard/config")
    async def update_config(request):
        try:
            return web.json_response({"ok": True, **save_config(await request.json())})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    @routes.delete("/nanfeng/v15/h3/storyboard/config")
    async def delete_config(_request):
        try:
            return web.json_response({"ok": True, **clear_config()})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    @routes.post("/nanfeng/v15/h3/storyboard/models")
    async def discover_models(request):
        try:
            payload = await request.json()
            kind = str(payload.get("kind", "vision")).strip().lower()
            if kind not in {"vision", "text"}:
                raise ValueError("模型类型必须是vision或text")
            cfg = load_env()
            prefix = "NANFENG_VISION" if kind == "vision" else "NANFENG_TEXT"
            base_url, api_key = resolve_discovery_credentials(
                str(payload.get("base_url", "")).strip(), str(payload.get("api_key", "")).strip(),
                cfg.get(f"{prefix}_BASE_URL", ""), cfg.get(f"{prefix}_API_KEY", ""),
            )
            models = await asyncio.to_thread(list_models, base_url, api_key)
            return web.json_response({"ok": True, "base_url": normalize_base_url(base_url), "models": models})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    @routes.post("/nanfeng/v15/h3/storyboard/generate")
    async def generate(request):
        try:
            payload = await request.json()
            return web.json_response({"ok": True, **(await generate_storyboard(payload))})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    @routes.post("/nanfeng/v15/h3/storyboard/jobs")
    async def create_job(request):
        job_id = uuid.uuid4().hex
        job = StoryboardJob(job_id, await request.json())
        with _JOB_LOCK:
            _STORYBOARD_JOBS[job_id] = job
        threading.Thread(target=_run_storyboard_job, args=(job,), daemon=True, name=f"nanfeng-storyboard-{job_id[:8]}").start()
        return web.json_response({"ok": True, "job_id": job_id})

    @routes.get("/nanfeng/v15/h3/storyboard/jobs/{job_id}")
    async def get_job(request):
        job = _STORYBOARD_JOBS.get(request.match_info["job_id"])
        if job is None:
            return web.json_response({"ok": False, "error": "任务不存在"}, status=404)
        return web.json_response({"ok": True, **job.public()})

    @routes.delete("/nanfeng/v15/h3/storyboard/jobs/{job_id}")
    async def cancel_job(request):
        job = _STORYBOARD_JOBS.get(request.match_info["job_id"])
        if job is None:
            return web.json_response({"ok": False, "error": "任务不存在"}, status=404)
        if job.status in {"completed", "failed", "cancelled"}:
            return web.json_response({"ok": True, "status": job.status})
        job.cancelled = True
        job.cancel_event.set()
        return web.json_response({"ok": True, "status": "cancelling"})


register_routes()
