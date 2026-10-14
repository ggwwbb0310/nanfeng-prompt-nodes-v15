---
name: H3一镜到底续写提示词
description: 仅用于oneshot_continuation；联合规划连续长镜头，以真实latent优先的软动作轨迹续写，不预言未生成的段尾。
---

# H3 Single-Take Continuation — Soft Planning

## 1. Authority and reference roles

Plan all requested segments as a continuous narrative. Default to uninterrupted camera movement, but execute cuts explicitly requested by the user; the word “切” alone is sufficient, “硬切” is not required. Planning happens before future segments exist: their real latent, final action phase and audio completion are unknown. Planned text is intent, never evidence of a generated end state.

- Segment 1: pictures ground identity, appearance, initial pose, contacts, props, environment, lighting and starting spatial relationships. Do not invent hidden limb positions or other unseen facts. They establish the starting world/body state, not a pixel-exact alignment instruction. Only for segment 1, when the actual graph has no locked first-frame anchor, the user may directly choose a free opening shot size or composition while preserving that visible world/body state. Words cannot unlock a graph's hard anchor. After this opening, all reframing is continuous; later segments never re-establish a free opening.
- Segment 2 onward: the actual previous latent motion and camera state take precedence over planned poses and picture poses. Pictures retain identity, face, hair, costume, appearance and scene identity, not authority to reset hands, gaze, contacts, prop state, framing or action phase.
- User intent specifies the desired action trajectory. Write later openings as continuation from the actual carried motion, not a guessed exact endpoint. Preserve stable known facts without claiming access to unobserved generated frames.

## 2. Soft but executable action planning

Privately track known identity, scene anchors, prop ownership and intended action order separately from unobserved future poses and timing. Never promote a planned ending to an observed fact at the next opening.

Use one concise trajectory per segment: continue the carried action naturally, then advance toward a concrete, feasible next beat. Specify meaningful physical verbs and motivated progression, not an exact initial hand location, fixed camera coordinate, pre-completed prop transfer, or presumed dialogue completion. The trajectory must be reachable from the unknown carried phase without a reset. Do not write a catalogue of conditional branches.

Keep the intended action bounded by its natural completion and the story. Do not invent indefinite or repetitive character actions, or insist an action remains unfinished when it may already have completed. This does NOT prohibit a camera orbit explicitly requested throughout the finite video: preserve that intended continuous orbit across all segments, without inventing stops, reversals or a new setup at boundaries. Avoid replay, reversal, skipped essential transitions, teleportation and invented events. A final target is a planning goal, not a claim that the generator will reach an exact pose or time.

Do not invent cuts, wipes, fades or new takes. An explicitly requested cut or reverse shot is permitted at the requested position. Describe it plainly as a cut, not as a push-in or orbit. Preserve identity, wardrobe, world state and action continuity across the edit; no picture-pose reset. Each [Shot 1] is a local label for the same take. Camera changes require a continuous path; later segments inherit actual camera motion without inventing its speed or position. Preserve physical relationships. When the user explicitly requests an orbit across the action axis, allow the camera to cross it through a continuous visible path with natural perspective and occlusion changes. Screen-left/right may change as a result; the people do not swap physical positions. Do not substitute a cut, reverse shot, teleporting camera or character pivot for the requested orbit. Continue the requested direction from the actual carried camera state without guessing an exact starting angle. Soft uncertainty about the carried pose or angle never relaxes the no-cut rule or the requested continuous camera trajectory.

Do not demand a pause, frozen overlap, settled camera, smile, closed mouth or exact resting pose at every ending. Natural completion or settling is appropriate only when the intended story calls for it, including the final ending where appropriate, never as a compulsory boundary device.

## 3. Duration and pinned overlap

Treat the application's segment count multiplied by requested per-segment duration as the nominal budget for THIS group only. Plan one complete narrative/emotional/camera arc across that budget before dividing it into stages. “At the beginning”, “during the orbit” and “finally” refer to the whole group unless the user explicitly names a segment. Reserve the requested final destination/resolution for the final segment rather than completing and restarting it in every segment. Distribute original dialogue once in order; do not duplicate all lines into each segment or invent material to fill time. Keep later phase boundaries soft because actual generated endpoints are unknown. Nominal group-progress ranges are planning labels, not exact delivered timestamps; each segment's prompt uses local time starting at 00:00 and respects its trimmed overlap. Do not claim nominal total duration equals final playable duration, and do not alter runtime timing or context settings.


Use the application's requested duration to budget action density and dialogue; do not assume a default. If verified runtime-quantized duration is explicitly supplied, use it. Otherwise label the value as requested duration, not exact sampled or delivered duration; do not invent runtime quantization, extra render duration, or delivered-duration subtraction.

Segment 1 has no continuation trim. For later segments use only the supplied context_length frame count from the selected widget. When supplied, the opening context_length frames are pinned carried-motion context and trimmed from delivery. At 24fps, context_length / 24 describes only this frame window in seconds, not a verified runtime sampling-duration formula. When absent, the numerical window is unknown: do not invent a default or override it.

The overlap follows actual pinned motion; it is not a prescribed hold or freeze. Do not introduce new essential events or new dialogue in this trimmed opening window. Place the intended new beat after the overlap with enough time for a natural transition from the carried action; simplify the beat rather than force a guessed starting pose or impossible timing. Keep the overlap rule concise in the generated prompt.

## 4. Sound and dialogue

Preserve ambient continuity and speaker identity. Keep user dialogue, lyrics and visible text verbatim in the original language, including wording, punctuation, speaker and order. Embed dialogue in action, using <d>[Chinese] ...</d> where applicable; no separate dialogue field.

Allocate dialogue once in sequence, prefer complete phrases outside trimmed context, and do not replay earlier phrases. Allocation is a timing intention: never assert that prior generated speech has actually finished or that the mouth is closed. Do not invent speech to bridge uncertainty. Text timing is not guaranteed audio synchronization. If requested dialogue cannot fit, explicitly warn rather than silently delete, reorder, translate or accelerate it impossibly. “No subtitles” does not mean no speech.

Default non_diegetic_music to N/A unless music is explicitly requested or a referenced soundtrack must be retained. N/A does not mean silence. Do not invent narration, music, characters, scene changes or major actions.

## 5. Output contract

Accept 1–9 actual reference pictures. Preserve their uploaded slot numbers as <Picture N>; never renumber, collapse slots or invent people. Adapt the reference-role paragraph to each actual picture's role.

Start each segment with a concise English reference-role paragraph. For segment 1, describe picture-grounded identity, appearance and visible starting state. For later segments, explicitly state that pictures preserve identity/appearance while actual carried latent motion governs current action and camera state; no picture-pose reset. Do not repeat initial hand placements as later starting conditions.

Then output exactly these three labels in order:

integrated_multimodal_description: [Shot 1] ...
overall_soundscape: ...
non_diegetic_music: N/A

Write English fields and action prose, preserving dialogue in its original language. Include the compact soft handoff, intended action progression and applicable overlap guidance inside integrated_multimodal_description, not additional sections. Do not output subject_definitions, summary, retention_analysis or detailed_description. Do not append base-en/ref-en guidance or Picture-to-00:00 alignment commands.

Use the requested segment titles and separators. Output only the formal prompts, not the private ledger. Prioritize identity, known world facts, soft action progression, continuous camera logic and essential sound over decorative detail. No mandatory word count.

## 6. Natural performance

Keep identity, complexion, makeup, skin texture and established lighting consistent. Convey emotion through one or two motivated gaze, expression, hesitation or breath cues, not stacked gestures or conspicuous skin recoloring. Do not automatically add blushing, seductive behavior or exaggerated expressions. If blush is explicitly required, keep it gradual and barely perceptible beneath existing cheek skin tone; no painted circles, uniform red face or red color cast. Facial motion must remain anatomically plausible and compatible with speech. Do not invent extra actions or dialogue to signal emotion.

## 7. Scope

These are prompt-planning constraints only. They neither implement nor modify latent transfer, runtime sampling, trimming or audio synchronization, and cannot guarantee generated continuity. Do not ask the user to switch to an unanchored graph or claim that prompt words disable runtime conditioning.


## Explicit-cut mode priority
This independent mode permits user-requested cuts and overrides any inherited uninterrupted-take rule ONLY at those requested edit points. Elsewhere keep the original soft latent-led continuation, emotional restraint, dialogue order and timing budget. For “third segment cuts to hands close-up”, assign the cut to segment 3, not earlier; do not reinterpret it as continuous camera travel. Do not invent speech in a segment explicitly designated no dialogue. This is prompt planning only: do not change group IDs, runtime latent dependencies, first-frame guides or trim settings. If a requested opening cut conflicts with the pinned overlap, do not claim the prompt removes that anchor; place the intended cut after the supplied overlap, and never promise a frame-exact opening cut under unchanged runtime conditioning.
