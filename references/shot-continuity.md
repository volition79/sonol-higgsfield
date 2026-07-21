# Shot design and continuity

## Shot record

Every shot must resolve these before board approval:

1. `previous_scene_context`: the exact physical and narrative end state inherited.
2. `current_shot_goal`: one narrative purpose.
3. `emotional_continuity`: incoming emotion, change, and outgoing emotion.
4. `visual_continuity`: character, costume, product, prop, location, time, light.
5. `action_continuity`: pose, gaze, hand, direction, velocity, and prop state.
6. `camera_continuity`: axis, framing, height, lens feel, movement, exposure.
7. `audio_continuity`: dialogue boundary, ambience bed, music phase, J/L cut.
8. `next_scene_setup`: the end state deliberately handed to the next shot.

Also record duration, purpose, model, reference package, required locked assets,
audio route, prompt, version, intended edit points, and the incoming boundary
decision.

## Director boundary decision

Choose one strategy before compiling every shot. Store its reason, previous
shot ID, frame paths, and transport roles in the approved shot board. Every
strategy resolves to **exactly one start image** in the video call. The table
describes boundary intent; an end image is still optional and exceptional.

| Strategy | Use when | Start image | Planned keyframe |
|---|---|---|---|
| `continuous_match` | Scene, axis, action, and visual flow continue | Previous accepted boundary frame, alone | `analysis_only`: informs story re-alignment and the prompt; never transported |
| `motivated_transition` | A simple camera move or bridge changes composition | Previous accepted boundary frame | Prompt exit state by default; optional `end_image` only when exact arrival matters |
| `editorial_cut` | Reverse angle, reaction, insert, hard cut, or decisive shot-size change | Freshly composed keyframe, required | Same image (it is the start image) |
| `scene_reset` | Place, time, style, or story unit changes | Freshly composed keyframe, required | Same image (it is the start image) |

Extract the accepted previous clip's boundary frame, never a rejected
candidate's frame. `media_pipeline.py boundary-frames` samples eight candidates
from the final 0.5 seconds and recommends the lowest FFmpeg `blurdetect` mean,
preferring the later candidate on a tie. Persist every candidate. A director may
choose another candidate when pose, expression, hands, props, edit rhythm, or
narrative state is better, but must store its path and reason. Do not propagate a frame before visual QC
because identity, hand, prop, or background defects would become the next
generation's initial condition.

Compose cut/reset start images just-in-time: run the locked character,
location, and prop references through the image model with the current story
state, not from a start-frame batch produced before generation began. Cuts and
resets also reset the quality drift a long chain accumulates.

The current Seedance CLI has no native `middle_image`. Do not pretend a generic
reference is time-pinned. When arrival at a composition matters, first try a
prompt exit state; use a bridge shot's `end_image` only when the destination is
exact and the transition is simple, then start the following shot from the
accepted rendered boundary rather than assuming pixel-perfect arrival.
For `set-boundary motivated_transition`, omit `--planned-keyframe` for the
default prompt-only route; providing it explicitly selects the end-image route.

## Sequential adaptive story loop

The story plan is a map; the footage is the territory. After each accepted
shot:

1. Extract and QC the boundary frame.
2. Read the frame like a director: pose, gaze, hands, props, framing, light,
   emotion.
3. Re-align the next shot's action, dialogue staging, and prompt to that frame.
   Anchor beats and recorded audio masters stay fixed; if a re-alignment would
   contradict a recorded line, re-record that line instead of bending the
   footage.
4. Wire the boundary, compile a compact prompt, and generate.
5. Compare the new clip's actual first frame against the submitted start image
   before accepting it.

Persist these steps with `record-start-frame-qc`,
`record-boundary-analysis`, and `set-adaptive-story`. The state gate requires
the previous user acceptance, first-frame pass, analysis ID, current locked
story-contract version, and JIT start provenance before a dependent shot can be
queued. Semantic observations remain explicit agent/director judgments; only
frame sampling and blur scoring are automatic.

## Structured shot grammar

Before board approval, resolve `dramatic_beat`, viewer feeling, shot size,
angle/height/roll, lens family and camera distance, depth/focus, one primary
movement and speed, composition, lighting/color, blocking, screen direction and
axis side, duration, transition, rationale, provider support level, compiled
prompt/native parameters, QC plan, and evidence IDs. The shot duration and
grammar duration must match.

Use `film-technique-catalog.json` for stable IDs and failures, and
`higgsfield-technique-support.json` to decide whether an item is structured,
reference-guided, prompt-soft, web-only, post-only, unreliable, or unsupported.
Validate the stored grammar before internal board QC. Lens millimeters are
creative hints, so record the intended angle of view, distance, perspective,
and depth effect as well.

## Reference hierarchy

The video call and the start-frame composition step have different transports:

**Video call (minimum-sufficient image contract):**

- Start frame controls entry composition and state — it is the only image the
  video call carries.
- End frame constrains arrival composition — optional under a
  `motivated_transition`, never the default continuity mechanism.
- One essential image reference may be tested only after a documented
  start-only failure, with one changed variable and a matching manifest role.
- A previous boundary frame becomes a start frame only for `continuous_match`
  or `motivated_transition`.
- Audio reference carries only the locked dialogue conditioning reference on a
  visible-dialogue route.
- Video reference (motion/camera behavior) requires an explicit recorded
  rationale; it is not part of the default contract.

**Start-frame composition step (image model):**

- Character asset controls face, hair, body, costume, and stable details.
- Location asset controls geometry, weather, lighting, and persistent objects.
- Prop/product asset controls exact shape, label, color, orientation, and wear.

Identity control normally comes from the composed start image. If identity
drifts late, shorten/reset and improve that frame first. If the exact same
diagnosed failure persists, A/B test one identity reference; do not add several
references or change the prompt at the same time.

For Seedance, record each reference in `references.manifest` with its semantic
role, CLI transport field, source, controlled traits, locked asset ID, and a
null `prompt_alias`. Read
[seedance-2-0-production.md](seedance-2-0-production.md) for the exact manifest
and live count rules; the count budget applies to the composition step.

## Prompt structure

Keep the prompt compact and high-probability. Write it in this order when the
model accepts natural language:

1. Shot spec: count, duration, aspect, single continuous shot.
2. Instruction to begin from the supplied composition without reframing before motion.
3. Who and where, then one primary action.
4. One camera move with framing/focus.
5. Lighting, palette, and mood in one clause.
6. Exit state that sets up the next shot.

Include only the two or three invariants that the shot cannot survive
breaking. Long enumerations of invariants and reference descriptions lower
compliance. Avoid asking for multiple scene changes in one short generation.
Avoid negative prompt lists unless the selected schema supports them.

Generate this ordered camera clause with `render_shot_prompt.py` or the
`compile-grammar` CLI command; do not freehand a second, divergent camera plan.

## Boundary inspection

Use `media_pipeline.py boundary-frames` on adjacent accepted candidates. Review
the frames side by side and play the cut with audio. Check:

- face proportions, hairline, skin tone, makeup, age;
- costume silhouette, material, fasteners, accessories;
- hand pose, finger count/occlusion, gaze and body weight;
- product/logo shape, label orientation, prop ownership and position;
- background geometry, weather, time of day, shadow direction;
- screen direction, 180-degree axis, lens scale, camera height and movement;
- exposure, white balance, saturation, contrast, grain and sharpness;
- ambience, dialogue timing, breath, music phase and emotional energy.

## Repair ladder

Use the cheapest, least destructive valid repair first:

1. Move the edit point.
2. Use a J-cut or L-cut.
3. Add common room tone/ambience.
4. Match grade, exposure, grain, and loudness.
5. Apply a minor pitch-preserving speed change.
6. Insert an approved cutaway.
7. Generate a bridge shot or transition clip.
8. Regenerate only the next failing shot.

If the provider minimum is four seconds but the edit needs one or two, generate
a compliant bridge and trim locally. Preserve source and trimmed versions in
the ledger.
