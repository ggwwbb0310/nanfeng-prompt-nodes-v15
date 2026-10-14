"""V15-only disk-backed AV continuation; upstream owns H3 layout math."""
import hashlib
import json

UPSTREAM = ("MiniMaxH3MotionContext", "MiniMaxH3MotionContextLoadLatent",
            "MiniMaxH3MotionContextSaveLatent", "MiniMaxH3MotionContextTrim")


def continuation_plan(enabled, raw, node_id, context_length="22", audio_context_length=24):
    if not enabled:
        return None
    if str(context_length) not in {"5", "22", "39", "56"}:
        raise ValueError("V15 context_length 必须为 5/22/39/56。")
    if isinstance(audio_context_length, bool) or not 0 <= int(audio_context_length) <= 240:
        raise ValueError("V15 audio_context_length 必须为 0～240。")
    try:
        data = json.loads(raw)
        for key in ("workflow", "node", "group", "run"):
            if not isinstance(data[key], str) or not data[key] or len(data[key]) > 256:
                raise ValueError(key)
        index = data["index"]
        if isinstance(index, bool) or not isinstance(index, int) or not 1 <= index <= 9999:
            raise ValueError("index")
        if data["node"] != str(node_id):
            raise ValueError("node identity")
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("V15 潜空间续写请使用“生成当前及后续分镜”；缺少有效的工作流/节点/连续组/本次运行编号。重新批量运行会从当前段安全重置。") from exc
    identity = json.dumps([data[k] for k in ("workflow", "node", "group", "run")], ensure_ascii=False)
    folder = "nanfeng_v15_context/" + hashlib.sha256(identity.encode()).hexdigest()
    return {"folder": folder, "index": index, "context_length": str(context_length),
            "audio_context_length": int(audio_context_length)}


def require_upstream():
    import nodes
    missing = [name for name in UPSTREAM if name not in nodes.NODE_CLASS_MAPPINGS]
    if missing:
        raise RuntimeError("V15 潜空间续写需要加载 ComfyUI-H3-Motion-Context；请在任务结束后手动重启。缺少: " + ", ".join(missing))


class NanFengV15CommitContinuation:
    """Only save a complete AV latent after both decoders and AV trim succeed.

    Outputs are passthroughs, so saving is a required ancestor of delivery,
    not an unreferenced side effect that expansion pruning could discard.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"latent": ("LATENT",), "images": ("IMAGE",),
            "audio": ("AUDIO",), "folder": ("STRING", {"default": ""}),
            "clip_index": ("INT", {"default": 1, "min": 1, "max": 9999})}}

    RETURN_TYPES = ("IMAGE", "AUDIO")
    FUNCTION = "commit"
    CATEGORY = "南风/V15/internal"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def commit(self, latent, images, audio, folder, clip_index):
        import re
        import nodes
        if not re.fullmatch(r"nanfeng_v15_context/[0-9a-f]{64}", folder):
            raise ValueError("V15 continuation folder must be an isolated generated namespace")
        samples = latent.get("samples")
        parts = list(samples.unbind()) if hasattr(samples, "unbind") else list(samples)
        if len(parts) != 2 or parts[0].ndim != 5 or parts[1].ndim != 4:
            raise ValueError("V15 continuation requires the final sampler's paired H3 AV LATENT, not IMAGE/video-only LATENT")
        if parts[0].shape[0] != 1 or parts[1].shape[0] != 1:
            raise ValueError("V15 continuation supports batch_size=1 only")
        saver = nodes.NODE_CLASS_MAPPINGS["MiniMaxH3MotionContextSaveLatent"]()
        saver.save(latent=latent, filename_prefix=folder + "/clip", clip_index=clip_index)
        return (images, audio)
