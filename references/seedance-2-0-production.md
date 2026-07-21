# Seedance 2.0 production contract

Read this file whenever a shot uses `seedance_2_0` or
`seedance_2_0_mini`. The current authenticated CLI contract remains the final
authority. The official tutorial and prompting guide inform the workflow, but
marketing language is not a deterministic compliance guarantee.

Official sources:

- <https://higgsfield.ai/blog/generating-with-seedance-2-0>
- <https://higgsfield.ai/blog/seedance-prompting-guide>

## Safe default

Use `controlled_single_shot` unless the user explicitly accepts an experimental
multi-shot generation. Start image-to-video with a sharp, front-facing,
well-lit image when possible. Prototype at 720p, eight seconds or less, and
`generate_audio=false` through `audio_mode=post_only`. Review the entire clip, especially seconds five through
eight. Change one variable per iteration.

Do not describe a 720p-to-1080p regeneration as an upscale that preserves
motion. The live Seedance CLI contract exposes no seed parameter, so a new
resolution generation can change motion and composition. When an approved
motion must remain intact, inspect the live `video_upscale` or
`topaz_video` contract instead.

## Prompt compiler order

The compiler emits:

1. shot count, total duration, aspect ratio, and shot mode;
2. subject and one primary action;
3. setting and lighting;
4. one primary camera movement plus framing/focus;
5. mood and style;
6. numbered timecoded beats only for approved experimental multi-shot;
7. end state, camera invariants, and audio route.

Use precise camera verbs such as `dolly in`, `truck left`, `arc shot`,
`push in`, `pull back wide`, `handheld follow`, `crane up`, or `orbital move`.
Treat their execution as prompt-soft and verify the rendered clip. Functional
constraints such as `no cuts`, `no zoom`, and `natural head movement` are
allowed because they define the camera plan. Avoid generic negative-prompt
lists.

`controlled_single_shot` rejects cuts, montage language, multiple timed beats,
or a shot count other than one. `seedance_multishot_experimental` requires:

- explicit user approval in `experimental_approved`;
- two or more shots;
- exactly one `{time, action}` beat per shot;
- acceptance that one failed internal beat normally requires regenerating the
  full provider clip.

## Reference manifest

**Single-start-image video contract.** The start image is guidance, not a
pixel lock: when a video call also carries `image_references`, the model
blends all of them and can reframe the opening away from the start image
entirely (verified in production, 2026-07: a tight two-shot start image plus
two wide composition references opened wide). Therefore a paid Seedance call
carries exactly one `start_image`; `end_image` only for a declared motivated
transition; `audio_references` only for a locked dialogue master. Character,
location, prop, and style references are consumed by the image model that
composes the start frame, never by the video call. Add one tight face
reference back only as a recorded retry against observed late-clip identity
drift. Always instruct the prompt to begin exactly on the provided start image
framing, and QC the rendered first frame against the submitted start image.

Keep semantic intent separate from the CLI transport:

```json
{
  "semantic_role": "character",
  "transport_field": "image_references",
  "source": "media/images/CHAR_001_v3.png",
  "controls": ["identity", "hair", "wardrobe"],
  "locked_asset_id": "CHAR_001",
  "prompt_alias": null
}
```

Allowed transport fields are `start_image`, `end_image`,
`image_references`, `video_references`, and `audio_references`. The Higgsfield
web guide describes semantic `@character`, `@style`, `@motion`, and `@audio`
references, but the current CLI schema exposes only transport arrays. Keep
`prompt_alias` null and never invent `@` aliases for a CLI command.

Apply the live limits fail-closed (under the single-start-image contract the
image budget is consumed by the start-frame composition step, not the video
call):

- images plus start/end: at most 9;
- videos: at most 3;
- audios: at most 3;
- all references including start/end: at most 12;
- audio references require at least one image, video, start image, or end
  image — the start image satisfies this;
- fast mode permits only 480p or 720p.

The official pages contain shorthand that can sound contradictory about
reference totals. Follow the current CLI CEL rules captured for the exact
model, not a remembered prose count.

## Audio routing

Choose exactly one `audio_mode`:

- `post_only`: default; generate picture without audio and construct all
  non-dialogue, narration, ambience, effects, and music during finishing;
- `none`: only for an intentionally silent final shot;
- `audio_reference`: only for visible dialogue after the final ElevenLabs
  `eleven_v3` master is locked; at least one audio and one visual reference are
  required. Discard the Seedance-rendered track and remux the untouched master;
- `native_sfx` and `native_dialogue`: compiler-compatible but outside the Sonol
  production policy.

The live contract currently defaults `generate_audio` to true. Every execution
command must therefore include the compiler's explicit boolean. Do
not let a prototype inherit the provider default.

## Iteration and QC

Compare the output against the exact shot contract rather than asking whether
it looks generally cinematic:

- rendered first frame against the submitted start image (framing jump = fail);
- primary action and final state;
- camera movement, framing, axis, and prohibited cuts/zoom;
- identity, wardrobe, product, location, and reference roles;
- motion stability through the full duration;
- dialogue/SFX timing and lip sync when applicable;
- continuity handoff to adjacent shots.

Record the one changed variable and preserve the prior candidate. A successful
prompt does not prove the next generation will reproduce it exactly.

## Paid execution binding

Compile against a schema snapshot no older than 24 hours. Store the selected
contract hash in `shot_grammar.provider_binding.schema_contract_hash` and store
the execution argument fingerprint for drift detection. Do not call the live
cost endpoint. Immediately before a paid call, re-fetch
the selected live model/workflow contract and reject contract, prompt, native
parameter, or argument drift.
