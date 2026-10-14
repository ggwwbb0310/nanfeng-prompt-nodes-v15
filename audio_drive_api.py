"""V11 智能音频驱动专属API配置；与智能分镜凭据完全隔离。"""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from . import storyboard_api as storyboard_core

ROOT = Path(__file__).resolve().parent
AUDIO_DRIVE_ENV_PATH = ROOT / ".audio-drive.env"
AUDIO_DRIVE_SKILL_DIR = ROOT / "audio-drive-skill"
AUDIO_DRIVE_SKILL_PATH = AUDIO_DRIVE_SKILL_DIR / "SKILL.md"
AUDIO_DRIVE_SKILL_REFERENCE_PATHS = (
    AUDIO_DRIVE_SKILL_DIR / "references" / "base-en.txt",
    AUDIO_DRIVE_SKILL_DIR / "references" / "ref-en.txt",

)
AUDIO_DRIVE_SKILL_PROFILES = {
    "regular_storyboard": AUDIO_DRIVE_SKILL_PATH,
    "ns_storyboard": AUDIO_DRIVE_SKILL_DIR / "profiles" / "ns-storyboard" / "SKILL.md",
}
CONFIG_FIELDS = (
    "NANFENG_AUDIO_DRIVE_VISION_BASE_URL",
    "NANFENG_AUDIO_DRIVE_VISION_API_KEY",
    "NANFENG_AUDIO_DRIVE_VISION_MODEL",
    "NANFENG_AUDIO_DRIVE_TEXT_BASE_URL",
    "NANFENG_AUDIO_DRIVE_TEXT_API_KEY",
    "NANFENG_AUDIO_DRIVE_TEXT_MODEL",
    "NANFENG_AUDIO_DRIVE_TEXT_NS_STORYBOARD_BASE_URL",
    "NANFENG_AUDIO_DRIVE_TEXT_NS_STORYBOARD_API_KEY",
    "NANFENG_AUDIO_DRIVE_TEXT_NS_STORYBOARD_MODEL",
)


def audio_drive_text_keys(skill_id: str) -> tuple[str, str, str, str]:
    requested = str(skill_id or "regular_storyboard").strip()
    if requested not in AUDIO_DRIVE_SKILL_PROFILES:
        raise ValueError("智能音频驱动提示词Skill无效")
    if requested == "regular_storyboard":
        return requested, "NANFENG_AUDIO_DRIVE_TEXT_BASE_URL", "NANFENG_AUDIO_DRIVE_TEXT_API_KEY", "NANFENG_AUDIO_DRIVE_TEXT_MODEL"
    return requested, "NANFENG_AUDIO_DRIVE_TEXT_NS_STORYBOARD_BASE_URL", "NANFENG_AUDIO_DRIVE_TEXT_NS_STORYBOARD_API_KEY", "NANFENG_AUDIO_DRIVE_TEXT_NS_STORYBOARD_MODEL"


def load_config(path: Path = AUDIO_DRIVE_ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in CONFIG_FIELDS:
            values[key.strip()] = value.strip().strip('"\'')
    return values


def normalize_base_url(value: str) -> str:
    base = str(value or "").strip().rstrip("/")
    if not base:
        return ""
    base = re.sub(r"/(?:chat/completions|responses|models)$", "", base, flags=re.I).rstrip("/")
    if not re.search(r"/v\d+$", base, re.I):
        base += "/v1"
    return base


def browser_config(config: dict[str, str] | None = None, skill_id: str = "regular_storyboard") -> dict:
    cfg = config or load_config()
    skill_id, text_base, text_key, text_model = audio_drive_text_keys(skill_id)
    return {
        "skill_id": skill_id,
        "vision_configured": all(cfg.get(key, "").strip() for key in CONFIG_FIELDS[:3]),
        "text_configured": all(cfg.get(key, "").strip() for key in (text_base, text_key, text_model)),
        "NANFENG_AUDIO_DRIVE_VISION_BASE_URL": cfg.get("NANFENG_AUDIO_DRIVE_VISION_BASE_URL", ""),
        "NANFENG_AUDIO_DRIVE_VISION_MODEL": cfg.get("NANFENG_AUDIO_DRIVE_VISION_MODEL", ""),
        "NANFENG_AUDIO_DRIVE_TEXT_BASE_URL": cfg.get(text_base, ""),
        "NANFENG_AUDIO_DRIVE_TEXT_MODEL": cfg.get(text_model, ""),
        "vision_key_saved": bool(cfg.get("NANFENG_AUDIO_DRIVE_VISION_API_KEY", "").strip()),
        "text_key_saved": bool(cfg.get(text_key, "").strip()),
    }


def _validated(payload: dict) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("配置参数格式错误")
    result: dict[str, str] = {}
    for key in CONFIG_FIELDS:
        if key not in payload:
            continue
        value = payload[key]
        if not isinstance(value, str):
            raise ValueError(f"{key}必须是文本")
        value = value.strip()
        if "\n" in value or "\r" in value:
            raise ValueError(f"{key}不能包含换行")
        if key.endswith("_BASE_URL") and value:
            if not re.match(r"^https?://", value, re.I):
                raise ValueError(f"{key}必须以http://或https://开头")
            value = normalize_base_url(value)
        result[key] = value
    return result


def _write(config: dict[str, str], path: Path = AUDIO_DRIVE_ENV_PATH) -> None:
    lines = ["# V11 智能音频驱动专属API配置（禁止与智能分镜混用）"]
    lines.extend(f"{key}={config.get(key, '')}" for key in CONFIG_FIELDS)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    os.replace(temp, path)


def save_config(payload: dict, path: Path = AUDIO_DRIVE_ENV_PATH) -> dict:
    current = load_config(path)
    skill_id, text_base, text_key, text_model = audio_drive_text_keys(payload.get("skill_id", "regular_storyboard"))
    normalized = dict(payload)
    for generic, selected in (
        ("NANFENG_AUDIO_DRIVE_TEXT_BASE_URL", text_base),
        ("NANFENG_AUDIO_DRIVE_TEXT_API_KEY", text_key),
        ("NANFENG_AUDIO_DRIVE_TEXT_MODEL", text_model),
    ):
        if generic in normalized:
            normalized[selected] = normalized.pop(generic)
    normalized.pop("skill_id", None)
    for key, value in _validated(normalized).items():
        if key.endswith("_API_KEY") and not value:
            continue
        current[key] = value
    _write(current, path)
    return browser_config(current, skill_id)


def clear_config(path: Path = AUDIO_DRIVE_ENV_PATH) -> dict:
    blank = {key: "" for key in CONFIG_FIELDS}
    _write(blank, path)
    return browser_config(blank)


def list_models(base_url: str, api_key: str, timeout: int = 60) -> list[str]:
    base = normalize_base_url(base_url)
    key = str(api_key or "").strip()
    if not base or not key:
        raise ValueError("请先填写Base URL和API Key")
    request = urllib.request.Request(
        base.rstrip("/") + "/models",
        headers={"Accept": "application/json", "Authorization": f"Bearer {key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
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
    models = []
    for item in raw if isinstance(raw, list) else []:
        value = (item.get("id") or item.get("name")) if isinstance(item, dict) else item
        if isinstance(value, str) and value.strip():
            models.append(value.strip())
    models = sorted(set(models), key=str.lower)
    if not models:
        raise RuntimeError("中转/models没有返回可用模型ID")
    return models


def build_reference_manifest(segments: list[dict]) -> dict:
    """Deduplicate source files while retaining every segment/slot assignment."""
    if not isinstance(segments, list) or not segments:
        raise ValueError("至少需要一个音频分段")
    unique_images: dict[str, dict] = {}
    normalized_segments = []
    for fallback_index, raw in enumerate(segments, 1):
        if not isinstance(raw, dict):
            raise ValueError("分段参数格式错误")
        segment_index = int(raw.get("segment_index", fallback_index))
        start = float(raw.get("start", 0))
        end = float(raw.get("end", start))
        duration_seconds = float(raw.get("duration_seconds", end - start))
        if duration_seconds < 1.0 or duration_seconds > 15.0:
            raise ValueError(f"第{segment_index}段整数时长必须在1到15秒之间；请调整音频打点后再生成")
        duration_seconds = float(max(1, math.ceil(duration_seconds)))
        refs = []
        for slot_index, filename in enumerate(raw.get("images") or [], 1):
            filename = str(filename or "").strip()
            if not filename:
                continue
            usage = {"segment_index": segment_index, "slot_index": slot_index}
            entry = unique_images.setdefault(filename, {"filename": filename, "global_index": len(unique_images) + 1, "usages": []})
            entry["usages"].append(usage)
            refs.append({"slot_index": slot_index, "filename": filename, "global_index": entry["global_index"]})
        normalized_segments.append({
            "segment_index": segment_index, "start": start, "end": end,
            "duration_seconds": duration_seconds, "images": refs,
        })
    return {"segments": normalized_segments, "unique_images": list(unique_images.values())}


def _audio_drive_skill(
    timeline_only: bool = False,
    skill_id: str = "regular_storyboard",
    runtime_skill_text: str = "",
) -> str:
    if skill_id not in AUDIO_DRIVE_SKILL_PROFILES:
        raise ValueError("智能音频驱动提示词Skill无效")
    sections = []
    if skill_id == "ns_storyboard" and str(runtime_skill_text or "").strip():
        sections.append(str(runtime_skill_text).strip())
    else:
        profile_path = AUDIO_DRIVE_SKILL_PROFILES[skill_id]
        if profile_path.exists():
            sections.append(profile_path.read_text(encoding="utf-8"))
    reference_name = "base-en.txt" if timeline_only else "ref-en.txt"
    ref = AUDIO_DRIVE_SKILL_DIR / "references" / reference_name
    if ref.exists():
        sections.append(f"\n\n---\n\n# Embedded reference: {ref.name}\n\n{ref.read_text(encoding='utf-8')}")
    fallback = (
        "输出MiniMax H3官方I2VA分镜提示词。" if timeline_only else "输出MiniMax H3官方Ref2VA分镜提示词。"
    )
    return "".join(sections) or fallback


def _ds_batch_transport_contract(expected: list[int]) -> str:
    indices = [int(index) for index in expected]
    index_text = "、".join(map(str, indices))
    example_rows = ",".join(
        json.dumps({"segment_index": original_index, "text": "该原始段号对应的完整最终提示词"}, ensure_ascii=False)
        for original_index in indices
    )
    return (
        "\n\n【DS批量传输合同；只约束外层封装，不改变上述Skill正文规则】\n"
        "JSON只是批量传输外壳；每个text值内部仍是完整最终提示词，必须完整执行上述Skill。\n"
        f"本次唯一合法原始段号依次为：{index_text}。不得重编号为1、2、3，不得遗漏、重复或新增。\n"
        "每个对象只能有segment_index和text两个字段；text不得改名为prompt或content。\n"
        f"只返回一个JSON对象，不加代码围栏、说明或前后文字：{{\"segments\":[{example_rows}]}}"
    )


def _parse_generated_segments(text: str, expected: list[int]) -> dict[int, str]:
    clean = re.sub(r"```(?:json)?|```", "", str(text)).strip()
    try:
        data = json.loads(clean)
        rows = data.get("segments", []) if isinstance(data, dict) else data
        result = {int(row["segment_index"]): str(row["text"]).strip() for row in rows if isinstance(row, dict)}
    except Exception:
        result = {}
        matches = list(re.finditer(r"(?m)^\s*段\s*(\d+)\s*[:：]?\s*$", clean))
        for offset, match in enumerate(matches):
            end = matches[offset + 1].start() if offset + 1 < len(matches) else len(clean)
            result[int(match.group(1))] = clean[match.end():end].strip().rstrip("-").strip()
    if any(index not in result or not result[index] for index in expected):
        raise ValueError("语言模型未返回全部分段，已保留原始响应但未写入错误映射")
    return result


async def generate_audio_drive_storyboards(payload: dict) -> dict:
    cfg = load_config()
    timeline_only = bool(payload.get("timeline_only", False))
    from .retired_mode_guard import reject_retired_fields
    reject_retired_fields(payload)
    for segment in payload.get("segments") or []:
        reject_retired_fields(segment)
    skill_id = str(payload.get("skill_id", "regular_storyboard")).strip()
    skill_id, text_base_key, text_api_key, text_model_key = audio_drive_text_keys(skill_id)
    status = browser_config(cfg, skill_id)
    if not status["text_configured"]:
        raise ValueError("当前提示词Skill的智能音频驱动语言模型API尚未完整配置")
    if skill_id not in AUDIO_DRIVE_SKILL_PROFILES:
        raise ValueError("智能音频驱动提示词Skill无效")
    manifest = build_reference_manifest(payload.get("segments") or [])
    unique = manifest["unique_images"]
    if unique and not status["vision_configured"]:
        raise ValueError("分段中存在图片，但智能音频驱动看图API尚未完整配置")

    # 每张唯一图片只看一次；随后用usage表绑定回“第N段/图片M”，避免重复付费和错位。
    analysis = ""
    if unique:
        resolved = storyboard_core.resolve_input_images([item["filename"] for item in unique])
        vision_cfg = {
            "NANFENG_VISION_BASE_URL": cfg["NANFENG_AUDIO_DRIVE_VISION_BASE_URL"],
            "NANFENG_VISION_API_KEY": cfg["NANFENG_AUDIO_DRIVE_VISION_API_KEY"],
            "NANFENG_VISION_MODEL": cfg["NANFENG_AUDIO_DRIVE_VISION_MODEL"],
            "NANFENG_VISION_PROTOCOL": "chat_completions",
        }
        analysis_rows = await asyncio.gather(*(storyboard_core.analyze_images([image], vision_cfg) for image in resolved))
    else:
        analysis_rows = []
    for item, text in zip(unique, analysis_rows):
        item["analysis"] = text

    mapping_lines = []
    for item in unique:
        uses = "、".join(f"第{x['segment_index']}段图片{x['slot_index']}" for x in item["usages"])
        mapping_lines.append(f"全局素材{item['global_index']}={item['filename']}；用于：{uses}；看图结果：{item.get('analysis', '无')}")
    segment_lines = []
    for segment in manifest["segments"]:
        refs = "、".join(f"图片{x['slot_index']}=全局素材{x['global_index']}" for x in segment["images"]) or "无图片"
        segment_lines.append(
            f"第{segment['segment_index']}段：{segment['duration_seconds']:g}秒；槽位映射：{refs}"
        )
    expected = [row["segment_index"] for row in manifest["segments"]]
    timeline_instruction = (
        "这是纯时间轴规划，不存在音频内容、节奏、对白或声音参考。只根据用户创意、每段秒数和该段图片决定这一段做什么；不得虚构听到音乐、对白、节拍或音效。"
        if timeline_only else
        "这些区间来自真实音频裁切；可按用户创意和素材规划画面，但不要编造未提供的具体台词。"
    )
    mode_instruction = (
        "每个纯时间轴分段严格输出I2VA官方格式。必须以“For the target video, at 0.00 seconds into the target video”首帧对齐句开头，"
        "将该段图片1作为0.00秒唯一首帧并从它连续向后发展；随后只按顺序输出"
        "integrated_multimodal_description、overall_soundscape、non_diegetic_music三个字段。"
        "该段有多张图片时，只有图片1是首帧，其余图片仅作人物、场景、物体或动作语义参考，不得当成尾帧或额外关键帧。"
        "不得输出FL2VA首尾帧对齐句，也不得要求图片2对齐结束时间；不得输出Ref2VA的subject_definitions、summary、retention_analysis或detailed_description。"
        if timeline_only else
        "为每个音频裁切段分别生成一个完整Ref2VA官方提示词。"
    )
    system_content = "严格执行以下智能音频驱动独立Skill。只输出结果，不解释。\n\n" + _audio_drive_skill(
        timeline_only, skill_id, payload.get("skill_text", "")
    )
    if skill_id == "ns_storyboard":
        system_content += _ds_batch_transport_contract(expected)
    temperature = 0.0 if skill_id == "ns_storyboard" else 0.7
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": (
            f"{mode_instruction}每段必须严格使用该段自己的duration_seconds，"
            "图片编号以该段槽位为准；同一全局素材可能映射到不同段/槽位，禁止按全局编号改写段内图片编号。\n\n"
            f"用户自然语言创意：\n{str(payload.get('idea', '')).strip() or '根据素材合理创作。'}\n\n"
            f"时间轴模式说明：{timeline_instruction}\n\n"
            f"本次共选择{len(expected)}段；保留原始段号，不得把第23、24、25段重排为第1、2、3段。\n"
            "分段与秒数：\n" + "\n".join(segment_lines) + "\n\n"
            "唯一图片看图与映射（每张只看一次）：\n" + ("\n".join(mapping_lines) or "无图片") + "\n\n"
            "严格输出JSON；segment_index必须使用上面给出的原始段号，例如只选择23、24、25时输出：{\"segments\":[{\"segment_index\":23,\"text\":\"完整分镜\"}]}。"
        )},
    ]
    raw = await asyncio.to_thread(
        storyboard_core.request_model,
        cfg[text_base_key], cfg[text_api_key],
        cfg[text_model_key], messages,
        protocol="chat_completions", temperature=temperature, timeout=600,
        max_output_tokens=min(24000, 4200 + 1800 * len(expected)), disable_reasoning=True,
    )
    parsed = _parse_generated_segments(raw, expected)
    return {
        "segments": [{**segment, "text": parsed[segment["segment_index"]]} for segment in manifest["segments"]],
        "vision_manifest": unique,
    }


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

    @routes.get("/nanfeng/v15/h3/audio-drive/config")
    async def get_audio_drive_config(request):
        return web.json_response(browser_config(skill_id=request.query.get("skill_id", "regular_storyboard")))

    @routes.post("/nanfeng/v15/h3/audio-drive/config")
    async def update_audio_drive_config(request):
        try:
            return web.json_response({"ok": True, **save_config(await request.json())})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    @routes.delete("/nanfeng/v15/h3/audio-drive/config")
    async def delete_audio_drive_config(_request):
        try:
            return web.json_response({"ok": True, **clear_config()})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    @routes.post("/nanfeng/v15/h3/audio-drive/models")
    async def discover_audio_drive_models(request):
        try:
            payload = await request.json()
            kind = str(payload.get("kind", "vision")).strip().lower()
            if kind not in {"vision", "text"}:
                raise ValueError("模型类型必须是vision或text")
            cfg = load_config()
            prefix = "NANFENG_AUDIO_DRIVE_VISION" if kind == "vision" else "NANFENG_AUDIO_DRIVE_TEXT"
            base_url = str(payload.get("base_url", "")).strip() or cfg.get(f"{prefix}_BASE_URL", "")
            api_key = str(payload.get("api_key", "")).strip() or cfg.get(f"{prefix}_API_KEY", "")
            models = list_models(base_url, api_key)
            return web.json_response({"ok": True, "base_url": normalize_base_url(base_url), "models": models})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)

    @routes.post("/nanfeng/v15/h3/audio-drive/generate")
    async def generate_audio_drive(request):
        try:
            return web.json_response({"ok": True, **(await generate_audio_drive_storyboards(await request.json()))})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=400)


register_routes()
