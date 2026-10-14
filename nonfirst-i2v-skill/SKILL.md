---
name: H3官方提示词
description: 用户明确说“H3官方提示词”或“用H3官方写”时调用；先做连续性与空间审计，再输出精简的MiniMax官方英文结构。不得与“海螺H3提示词”或本地中文流程混用。
---

# H3 Official Prompt — Continuity-First Production

## Goal

Generate a MiniMax H3 official-structure prompt that is executable, concise, and continuity-safe. Correctness outranks decorative detail. Never expose internal planning unless the user asks for it.

## 1. Fixed custom writing mode

Only write non-first-frame image-reference prompts. This is a custom writing style, not an official inference mode. Picture 1 is visual reference, never a pixel-aligned first frame. Do not select I2VA or Ref2VA output structures.

## 2. Build a Private Continuity Ledger Before Writing

Create a compact internal ledger in Chinese or terse structured notes. Do not output it by default.

For every segment and shot, track:

- **Identity:** stable subject label, appearance, clothing, distinguishing features, speaker ID.
- **Frame position:** screen-left/center/right and foreground/midground/background.
- **Body state:** facing direction, head/eye direction, pose, leading foot, occupied hands.
- **Relationship:** who faces whom, relative distance, occlusion, and movement path.
- **Props:** owner, hand used, open/closed/intact/broken state, fixed scene location.
- **Scene anchors:** doors, windows, table, vehicle, entrances, exits, and their stable directions.
- **Camera:** shot size, camera side of the action axis, angle, motion, and subject scale.
- **Action phase:** exact start state, observable transition, and end state.
- **Audio:** speaker, dialogue order, carry-over, ambience, and requested music.

If the user supplies multiple segments, the end ledger of segment N becomes the start ledger of segment N+1 unless an explicit transition changes it.

## 3. Hard Continuity Rules

### Cross-Segment Handoff

- Segment N+1 must begin from segment N's final visible state: same identity, costume, location, screen direction, pose, gaze, prop ownership/state, lighting, and camera-axis side unless the user explicitly changes one.
- When a previous segment ending is available, inherit its world and action state, never its pixels as a locked first frame. Requested reframing is already established in the first visible frame.
- Continue the unfinished action from its current phase. Never restart, repeat, skip, or reverse it.
- State only the inherited facts needed to prevent drift; do not re-narrate the previous segment.

### Boundary Pair Design

- Treat the final shot of segment N and the opening shot of segment N+1 as one jointly designed edit pair, not as two independently invented shots. Plan the pair before writing either segment.
- Preserve the exact world state across the cut: screen-left/right, foreground/midground/background, facing and eyeline, distance, occlusion, action phase, hand/prop state, travel direction, and the established side of the 180-degree axis.
- The boundary must provide a useful editorial change. Prefer an axis-safe shot/reverse shot, an immediate reaction shot, or a motivated change of shot size or camera angle that reveals new information.
- Unless the user explicitly requests one uninterrupted matching viewpoint, the final shot of segment N and the first shot of segment N+1 must not use the same shot size and the same camera angle. Change at least shot size, camera angle, or viewed subject while preserving spatial continuity.
- For dialogue or face-to-face action, use shot/reverse shot with matching eyelines and stable left/right relationship. Do not mirror the characters, cross the axis, reset the pose, or teleport them merely to create variety.
- If a continuous same-view handoff is genuinely necessary, carry visible motion across the boundary or use a deliberate match-on-action; never restart the action at 00:00.

### Within-Segment Spatial Logic

- Establish all important subjects and scene anchors at the start of each shot.
- Use camera-relative terms (`screen-left/right`) for composition and scene-relative anchors (`beside the door`, `behind the table`) for physical space. Do not silently swap them.
- Preserve the 180-degree action axis across cuts. If crossing the axis is required, show a motivated continuous camera move or a neutral re-establishing shot.
- Preserve eyelines and travel direction across cuts.
- Define each prop transfer as visible hand-to-hand or place-to-pickup action. No teleportation or unexplained hand switching.
- A cut changes viewpoint, not world state. The new shot begins at the exact state reached before the cut.

### Action Path

Every major action follows:

`start state → one observable transition path → end state/reaction`

Use concrete physical verbs. Do not bundle several independent major actions into one instant. Do not let camera motion compete with a complex body action unless both are essential.

## 4. Identity and Framing Safety

- Use stable `<Subject N>` labels in Ref2VA and stable natural-language identity anchors in base modes.
- Repeat only the few identity traits needed to prevent drift; do not redescribe the complete character in every shot.
- For character-action prompts, default to close shot, medium close-up, or medium shot. Avoid distant, ultra-wide, establishing-wide framing, or characters occupying a small part of the image unless explicitly requested.
- Keep faces, hands, and the action-critical prop readable.

## 5. Duration and Information Budget

Fit content to the requested duration before drafting:

- Treat the runtime-provided current video duration as a hard prerequisite for every generated storyboard segment. Before writing, explicitly budget that exact number of seconds; never silently assume a default duration.
- Scale action density, number of shots/cuts, dialogue length, reaction time, and end-state settling to that exact per-segment duration. A simple action such as dancing should be expanded only as far as the available seconds can visibly support, not padded with unrelated events.

- Default to one principal action or one short exchange per segment.
- Prefer one continuous shot for short action clips and FL2VA interpolation.
- Add a cut only when it reveals necessary new information; do not cut merely to vary shot size.
- Reserve time for the action to settle into the requested final state.
- Check that dialogue can be spoken naturally within the available duration while leaving time for visible action and reaction.
- If requested content cannot fit, simplify secondary action/camera/ambience first. Never delete, reorder, translate, or change user-provided dialogue. If it still cannot fit, explicitly warn the user instead of silently compressing it into impossible timing.

## 6. Prompt Compression Hierarchy

Keep, in this order:

1. reference identity and world-state preservation without first-frame pixel alignment;
2. subject identity;
3. initial spatial and object state;
4. main action path and final state;
5. camera framing/axis needed for readability;
6. dialogue and synchronized essential sound;
7. minimal ambience.

Remove first:

- repeated appearance descriptions;
- plot-summary duplication;
- decorative texture and mood adjectives;
- unnecessary camera amplitude/speed labels;
- redundant restatements across Ref2VA sections;
- invented music or secondary action.

There is no mandatory 350–500-word target. Length follows information load. A short prompt that preserves all executable constraints is preferred over a long prompt with diluted priorities.

## 7. Language and Output

- Use internal Chinese planning when useful for logic checks.
- Write final official fields and rewrite sections in English.
- Preserve dialogue, lyrics, and visible text in their original language.
- Keep the original speaker, meaning, wording, punctuation, and dialogue order. Integrate dialogue naturally into shot action; do not create a separate dialogue field.
- “No subtitles” means no rendered captions; it never means delete spoken dialogue.
- Default `non_diegetic_music` to `N/A` unless the user explicitly requests music or the referenced soundtrack must be retained.
- Do not invent dialogue, narration, music, extra characters, scene changes, or major actions merely to enrich the prompt.

## 8. Required output for every segment

Accept 1–9 reference pictures. Preserve the actual uploaded slot numbers as <Picture N>; never collapse multiple pictures into Picture 1 or invent additional people. For multiple pictures, adapt the reference-role paragraph to state each supplied picture’s role. Keep the same three output sections below. A single picture retains the established behavior; extra pictures do not introduce first-frame alignment.

Begin with this reference-role paragraph, adapted to the visible image and user intent:
For the target video, <Picture 1> provides visual reference for the subject's identity, facial features, hairstyle, costume, posture, hand placement, and the same surrounding environment, lighting and spatial relationships. The reference image does not define the target video's first frame or opening composition.

Then output exactly these three labels in order:
integrated_multimodal_description: [Shot 1] ...
overall_soundscape: ...
non_diegetic_music: N/A

Never output subject_definitions, summary, retention_analysis or detailed_description sections. Never write a Picture-to-00:00 alignment instruction. Do not append base-en/ref-en guidance.

## 9. Free opening composition and continuous performance

- The first visible frame is already the requested shot size, camera angle and composition. Never show the source composition before reframing. If no new shot size or composition is requested, retain the reference framing by default. Do not independently redesign the opening.
- Identity and costume are grounded in the image. Pose and environment are preserved from Picture 1 by default, not optional. Preserve identity, face, hair, costume, accessories, subject count, seated/standing posture, torso/head orientation, eyeline, hand placement, contact points, props, scene layout, weather, lighting and spatial relationships. Only release pixel-exact first-frame alignment and source shot-size/composition. Change camera angle only when the user requests it, preserving the action axis and natural perspective. Subsequent requested actions evolve from this inherited state; preservation does not mean freezing the performance.
- Separate fixed world state (body orientation, hands, contact with surfaces, props, lighting, eyeline and action axis) from changing expression, action and camera motion. Offscreen limbs still exist in their stated positions.
- Default to one continuous shot within each segment. Do not add cuts unless requested or narratively necessary. Across segments explicitly carry the previous end state; the model has no invisible memory of earlier clips.
- Write timed action/performance phases fitted to the requested duration. Gentle dialogue can use longer expressive beats; fast action needs dense natural-speed beats, not forced slow preparation.
- Keep user dialogue verbatim with its speaker and order, embedded in action as <d>[Chinese] ...</d> where applicable. Text timing is guidance, not guaranteed audio synchronization.
- Specify an actionable final state for the next segment. Keep ambient sound consistent; N/A means no non-diegetic music, not silence.
- Only prompt generation is affected. The user must select an unanchored reference-generation graph separately; do not claim words can unlock a first_frame or timed Guide.

## 10. Natural emotional performance and restrained skin response

- Convey emotion through motivated performance, not conspicuous skin recoloring. For shyness, affection, embarrassment, tension or excitement, first use a small change of gaze, eyelid tension, a restrained mouth-corner movement, a brief hesitation or a subtle breath. Select only one or two fitting cues; do not mechanically stack gestures, add seductive behavior or exaggerate expressions.
- Do not automatically add blushing when the user only requests emotion. Preserve Picture 1's baseline complexion, makeup, skin texture, exposure and established lighting. Emotional warmth means expression and delivery, not warm/red lighting or red skin.
- If blushing is explicitly requested or narratively essential, describe at most a barely perceptible, gradual natural warmth localized beneath the cheeks' existing skin tone, with natural pores and tonal variation retained. Keep the forehead, nose, ears, neck and overall complexion unchanged unless explicitly requested. Existing blush in the reference must not be intensified.
- Never turn blushing into saturated red cheeks, symmetric painted circles, new cosmetic blush, a uniform red face, a sudden color switch, glowing skin, cartoon marks or a red color cast. Avoid affirmative phrases such as “bright red”, “deeply flushed”, “crimson cheeks” and repeated blush instructions that amplify the effect.
- In the generated prompt prefer one concise positive cue, for example: “Her gaze softens and a restrained smile forms; her natural complexion remains consistent.” If a visible blush is required: “An almost imperceptible warmth develops beneath her cheeks' natural skin tone, while the rest of her complexion and the lighting remain unchanged.” Do not dump this entire prohibition list into every shot.
- Let emotion develop from the dialogue and previous state with natural timing. Small facial movements must remain anatomically plausible and consistent with speaking; do not stretch smiles, over-raise brows, enlarge eyes, deform the face or insert involuntary-looking twitches. Do not replace requested dialogue or add new actions just to signal emotion.
- This is a prompt-writing constraint, not a guarantee of the video model's color fidelity. Keep first-frame/framing freedom and all existing identity, pose, scene and lighting preservation rules unchanged.

