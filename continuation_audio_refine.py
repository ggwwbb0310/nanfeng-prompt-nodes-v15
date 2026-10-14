"""V15-only protected audio refinement using installed upstream mask + native sampler.

Motion Context carries keyframes in CONDITIONING, not a latent noise mask.
Keep those keyframes, freeze the complete trimmed head (including a partial audio
cell), and any intersecting audio anchor. Never use upstream's convenience
sampler: it replaces the audio mask with all ones. No frozen-video cache.
"""
import math
import logging


def validate_settings(audio_denoise=0.3, steps=4, sampler_name="euler", scheduler="simple"):
    import comfy.samplers
    if type(audio_denoise) not in (int, float) or not math.isfinite(audio_denoise) or not 0.01 <= audio_denoise <= 1.0:
        raise ValueError("V15 续写音频降噪强度必须在 0.01–1.0 之间。")
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("V15 续写音频精修步数必须是 1–100 的整数。")
    if sampler_name not in comfy.samplers.KSampler.SAMPLERS:
        raise ValueError("V15 续写音频采样器不在当前 ComfyUI 支持列表中。")
    if scheduler not in comfy.samplers.KSampler.SCHEDULERS:
        raise ValueError("V15 续写音频调度器不在当前 ComfyUI 支持列表中。")
    return dict(audio_denoise=audio_denoise, steps=steps, sampler_name=sampler_name, scheduler=scheduler)


def should_refine(enabled, plan, requested):
    return (enabled is True and requested is True and isinstance(plan, dict)
            and type(plan.get("index")) is int and plan["index"] > 1
            and isinstance(plan.get("folder"), str) and bool(plan["folder"]))


def require_upstream():
    import nodes
    if "H3AudioRefineMask" not in nodes.NODE_CLASS_MAPPINGS:
        raise RuntimeError("V15 续写音频精修需要 ComfyUI-H3-AudioRefine；请在任务结束后手动重启加载。")


def protected_mask(latent, conditioning, trim_frames):
    import torch
    import nodes
    from comfy.nested_tensor import NestedTensor
    from comfy.ldm.minimax.model import FRAME_RESCALE
    require_upstream()
    samples = latent["samples"]
    if not getattr(samples, "is_nested", False) or len(samples.unbind()) != 2:
        raise ValueError("V15 audio refine requires exactly two packed AV streams")
    # Actual upstream validator and mask builder, with video explicitly frozen.
    masked = nodes.NODE_CLASS_MAPPINGS["H3AudioRefineMask"]().apply(latent, video_denoise=0.0)[0]
    video, audio = samples.unbind()
    if type(trim_frames) is not int or trim_frames <= 0:
        raise ValueError("V15 later-clip audio refine requires a positive actual trim_frames")
    vm, am = masked["noise_mask"].unbind()
    am = am.clone()
    am[..., :min(audio.shape[-1], math.ceil(trim_frames * FRAME_RESCALE))] = 0
    found = False
    for _, extra in conditioning:
        for kf in extra.get("minimax_keyframes", []):
            anchor = kf.get("audio_latent")
            if anchor is None:
                continue
            found = True
            start = float(kf["resolved_frame_index"]) * FRAME_RESCALE
            end = start + anchor.shape[-1]
            if not math.isfinite(start) or not math.isfinite(end):
                raise ValueError("V15 audio anchor has a nonfinite position")
            lo, hi = max(0, math.floor(start)), min(audio.shape[-1], math.ceil(end))
            if hi > lo:
                am[..., lo:hi] = 0
    if not found:
        raise ValueError("V15 later-clip audio refinement is missing Motion Context audio anchors")
    # Preserve any additional native zero/fractional audio denoise restrictions.
    old = latent.get("noise_mask")
    if old is not None:
        if not getattr(old, "is_nested", False) or len(old.unbind()) != 2:
            raise ValueError("V15 audio refine refuses an unknown AV noise-mask layout")
        old_audio = old.unbind()[1].to(device=am.device, dtype=am.dtype)
        if old_audio.ndim != 4 or old_audio.shape[-2:] != audio.shape[-2:]:
            raise ValueError("V15 audio refine refuses a mismatched audio mask")
        if not torch.isfinite(old_audio).all() or not ((old_audio >= 0) & (old_audio <= 1)).all():
            raise ValueError("V15 audio refine refuses invalid audio mask values")
        am = am * old_audio
    masked["noise_mask"] = NestedTensor((vm, am))
    return masked


def restore_protected(source, refined, mask):
    import torch
    from comfy.nested_tensor import NestedTensor
    video, audio = source["samples"].unbind()
    rv, ra = refined["samples"].unbind()
    if rv.shape != video.shape or ra.shape != audio.shape:
        raise ValueError("V15 audio refinement changed AV shapes")
    am = mask["noise_mask"].unbind()[1].to(audio.device)
    # Selection (not arithmetic blending) preserves signed zeros and exact bits.
    result = source.copy()
    result["samples"] = NestedTensor((video, torch.where(am == 0, audio, ra.to(audio))))
    return result


class NanFengV15ContinuationAudioRefine:
    @classmethod
    def INPUT_TYPES(cls):
        import comfy.samplers
        return {"required": {"model": ("MODEL",), "conditioning": ("CONDITIONING",),
            "latent": ("LATENT",), "trim_frames": ("INT", {"default": 22, "min": 1}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            "audio_denoise": ("FLOAT", {"default": 0.3, "min": 0.01, "max": 1.0, "step": 0.01}),
            "steps": ("INT", {"default": 4, "min": 1, "max": 100}),
            "sampler_name": (comfy.samplers.KSampler.SAMPLERS, {"default": "euler"}),
            "scheduler": (comfy.samplers.KSampler.SCHEDULERS, {"default": "simple"})}}
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "refine"
    CATEGORY = "南风/V15/internal"

    def refine(self, model, conditioning, latent, trim_frames, seed,
               audio_denoise=0.3, steps=4, sampler_name="euler", scheduler="simple"):
        import nodes
        validate_settings(audio_denoise, steps, sampler_name, scheduler)
        masked = protected_mask(latent, conditioning, trim_frames)
        logging.info("[V15 audio refine] steps=%s denoise=%s sampler=%s scheduler=%s cfg=1 trim_frames=%s",
                     steps, audio_denoise, sampler_name, scheduler, trim_frames)
        # Clean pre-LoRA ModelPatcher branch, same underlying H3 allocation. Native
        # model management switches/unpatches clones; no fresh UNET/model cache.
        # CFG stays 1: this continuation path has no independent negative branch.
        refined = nodes.common_ksampler(model, seed, steps, 1.0, sampler_name, scheduler,
            conditioning, conditioning, masked, denoise=audio_denoise)[0]
        return (restore_protected(latent, refined, masked),)
