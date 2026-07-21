# Cinema Studio 3.5 production route

Use this route when camera character, genre treatment, lighting, or grade is a
load-bearing part of the shot. Do not make it the universal default: use
Seedance for proven ElevenLabs V3-conditioned visible dialogue, fragile acting
or object interaction, native timecoded multi-shot, and continuity-first work.

## Live CLI contract

Verified with Higgsfield CLI 1.1.19 on 2026-07-21. The job type is
`cinematic_studio_video_3_5`. It is absent from `model list`, but its contract
is directly available through both `model get` and `workflow get`. Treat the
list mismatch as a discovery warning, not as proof that the contract is absent.
The executable generation path is the model path:

```bash
higgsfield generate create cinematic_studio_video_3_5 --prompt "..." ...
```

Do not call `higgsfield generate workflow cinematic_studio_video_3_5`; the
1.1.19 workflow runner rejects it. Store Sonol execution mode as `model`, and
refresh the live contract immediately before compilation.

Native structured fields currently include:

- `camera_style`: `classic_static`, `silent_machine`, `one_take`, `epic_scale`,
  `intimate_observer`, `impossible_camera`, `documentary_snap`, `raw_chaos`,
  `dreamy_flow`
- `light_scheme`: `soft_cross`, `contre_jour`, `overhead_fall`, `window`,
  `practicals`, `silhouette`
- `color_grading`: `naturalistic_clean`, `bleached_warm`, `hyper_neon`,
  `teal_orange_epic`, `sodium_decay`, `cold_steel`, `bleach_bypass`,
  `classic_bw`
- `genre`: `auto`, `action`, `horror`, `comedy`, `noir`, `drama`, `epic`
- duration, aspect ratio, resolution, prompt language, prompt enhancement,
  generated audio, multi-shot mode, and media references

These are broad directing families. Exact dolly, pan, orbit, crane, focal
length, aperture, and lens-body choices are not separate CLI fields in this
contract. Keep the exact move in the minimum-sufficient prompt and label its
support `prompt_soft`. Web-only camera and lens panels must not be described as
CLI-native.

The live contract permits at most 15 total media references. `style_prompt` is
mutually exclusive with `camera_style`, `light_scheme`, and `color_grading`.

## Per-shot routing

Prefer Cinema 3.5 when at least one of these is true and no stronger stability
constraint overrides it:

- expressive cinematography is the declared priority;
- camera character is essential to the result;
- genre, lighting, or grade must be more than descriptive prose;
- a previous Seedance result was an animated still or repeatedly missed the
  same camera intent.

Prefer Seedance when visible dialogue must use the proven ElevenLabs V3
conditioning route, a native timecoded sequence is requested, continuity is
load-bearing, or precise acting/object interaction has higher priority than
camera character. For a balanced shot with no decisive signal, return both
candidates and ask for a representative A/B instead of silently choosing.

## Prompt and first-frame policy

Set the broad native axes first. Put only the load-bearing action, exact camera
move, dynamic scene change, exit state, and two or three critical invariants in
the text prompt. Do not repeat the chosen camera style, light scheme, or grade
as ornamental prose.

The default first-frame instruction is `match_then_release`: match the supplied
frame, then allow the planned move to reframe naturally. Use
`preserve_composition` only when composition stability is the shot's actual
goal. Use `identity_anchor_only` when an immediate, deliberate reframe is more
important. This avoids turning every start image into a static-composition
constraint.

## Audio and validation

Cinema 3.5 may generate native non-dialogue sound when a complete sound brief
is supplied. Preserve the accepted native track. Do not silently move the
production ElevenLabs V3 visible-dialogue route to Cinema 3.5: its
audio-reference behavior is not yet established as equivalent to Seedance.
Run a separately approved A/B first and evaluate pronunciation, voice identity,
lip sync, effects timing, and native-track quality.

For the first use in a production, compare one representative shot against the
current Seedance route with the story action, start image, duration, and output
resolution held constant. Change only provider-specific direction. Record
`ANIMATED_STILL_RESULT`, `CAMERA_STYLE_MISS`, `NO_PARALLAX`,
`GENRE_LOOK_MISS`, or another standard reject reason before changing the next
variable.
