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
audio route, prompt, cost arguments, version, and intended edit points.

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

- Start frame controls entry composition and state.
- End frame controls handoff composition and state.
- Character asset controls face, hair, body, costume, and stable details.
- Location asset controls geometry, weather, lighting, and persistent objects.
- Prop/product asset controls exact shape, label, color, orientation, and wear.
- Video reference controls motion or camera behavior.
- Audio reference controls only what the live model contract documents.

For Seedance, record each reference in `references.manifest` with its semantic
role, CLI transport field, source, controlled traits, locked asset ID, and a
null `prompt_alias`. Read
[seedance-2-0-production.md](seedance-2-0-production.md) for the exact manifest
and live count rules.

Do not spend the reference budget on redundant mood images. If identity,
environment, action, and two boundaries cannot fit unambiguously, simplify or
split the shot.

## Prompt structure

Write the prompt in this order when the model accepts natural language:

1. Who and where, tied to reference IDs.
2. Entry state and primary action.
3. Camera/framing/movement.
4. Lighting, palette, texture, and atmosphere.
5. Audio behavior only if the contract supports it.
6. Exit state that sets up the next shot.
7. Explicit invariants: face, costume, product, logo, direction, axis.

Avoid asking for multiple scene changes in one short generation. Avoid negative
prompt lists unless the selected schema supports them.

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
