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
well-lit image when possible. Prototype at 720p, eight seconds or less, and use
an explicit audio mode. Compile `generate_audio=false` for post-only or silent
routes. For approved visible dialogue, use `audio_mode=audio_reference`,
`generate_audio=true`, a locked ElevenLabs V3 reference, and a complete compact
sound brief. Review the entire clip, especially seconds five through eight.
Change one variable per iteration.

Do not describe a 720p-to-1080p regeneration as an upscale that preserves
motion. The live Seedance CLI contract exposes no seed parameter, so a new
resolution generation can change motion and composition. When an approved
motion must remain intact, inspect the live `video_upscale` or
`topaz_video` contract instead.

## Prompt compiler order

The compiler emits:

1. shot count, total duration, aspect ratio, and shot mode;
2. an instruction to begin on the provided start-image framing;
3. subject and one primary action;
4. one primary camera movement plus framing/focus;
5. setting, lighting, and mood in one compact clause;
6. numbered timecoded beats only for approved experimental multi-shot;
7. end state and at most three critical invariants;
8. one compact audio clause containing the voice requirement, complete
   ambience, zero to three synchronized effects, music state, and exclusions.

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

## Image-input policy and reference manifest

The start image is guidance, not a pixel lock. Its adherence is usually best
served by a minimum-sufficient package, but “fewer is always better” is not a
provider guarantee. One documented production run showed two extra wide
composition references pulling a tight start image wide; that is evidence for
a cautious default, not proof that every additional reference degrades every
shot.

Use one of three explicit profiles:

1. `start_only` — default. Exactly one `start_image`, no `image_references`, no
   `end_image`. Express the exit state in the prompt.
2. `start_plus_essential_reference` — recovery experiment only. A prior
   start-only job must identify the failure; hold prompt/model/settings fixed
   and add exactly one indispensable character, location, prop, product, or
   style reference with a matching manifest role.
3. `start_end_transition` — exact arrival composition only. Requires a
   `motivated_transition`, no extra image reference, and a simple physically
   plausible path between the two frames. Avoid it for visible dialogue,
   complex choreography, or large angle/location changes; use an editorial cut
   or dedicated bridge instead.

Character/location/prop/style references are therefore consumed by the image
model by default, but one may enter the video call after evidence-led escalation.
If identity drifts, first shorten/reset and improve the start frame before
testing that exception.

Keep start-frame composition inputs outside the video-call references. This is
an image-composition record, not a Seedance transport manifest:

```json
{
  "semantic_role": "character",
  "composition_role": "character_reference",
  "source": "media/images/CHAR_001_v3.png",
  "controls": ["identity", "hair", "wardrobe"],
  "locked_asset_id": "CHAR_001",
  "prompt_alias": null
}
```

For an essential-reference escalation, add a video transport manifest entry
whose `transport_field` is `image_references`, whose semantic role equals the
policy role, and whose `controls` list states only what it is meant to preserve.
Store `baseline_job_id`, `baseline_failure`, `rationale`, and
`changed_variable`. Never invent web `@` aliases for a CLI command.

Apply the live limits fail-closed (the default image budget is consumed during
start-frame composition; only a documented escalation adds a video reference):

- production policy: one start image; zero image references by default, or
  exactly one after documented escalation; optional end image only under the
  mutually exclusive motivated-transition profile;
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
- `audio_reference`: only for visible dialogue after a clean ElevenLabs
  `eleven_v3` conditioning reference is locked; at least one audio and one
  visual reference are required. Complete `sound_design.dialogue`, `ambience`,
  `synchronized_effects`, `music`, and `exclusions` before compilation. Generate
  the full production sound with the picture and preserve the rendered track
  when it passes QC;
- `native_sfx` and `native_dialogue`: compiler-compatible but outside the Sonol
  production policy.

The live contract currently defaults `generate_audio` to true. Every execution
command must therefore include the compiler's explicit boolean. Do
not let a prototype inherit the provider default.

An audio reference is generative guidance, not transparent audio transport. Do
not promise sample-identical ElevenLabs output or perfect compliance. The native
track remains a candidate until transcript, pronunciation, lip-sync,
sound-event timing, unwanted-sound, and technical QC pass. If a required sound
fails, simplify the brief and regenerate before proposing an external repair.

## Iteration and QC

Before submission, review the start image as a motion initial condition: final
first-frame intent, exact aspect ratio, no collage/labels, readable key subject,
compatibility with the first action, and off-frame-reveal risk. Put crucial
identity/location facts inside the frame when possible. Do not expect the model
to reconstruct unseen space or hidden anatomy exactly from a still.

Compare the output against the exact shot contract rather than asking whether
it looks generally cinematic:

- rendered first frame against the submitted start image; record dimension,
  SSIM, and PSNR evidence if useful, but decide framing/identity semantically;
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
