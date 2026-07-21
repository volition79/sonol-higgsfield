# Model and workflow routing

Use this as a decision tree, then verify the selected live schema and account balance.

## Images

- Important Korean text, layout, design, or art direction: begin with
  `gpt_image_2`; run OCR and visual review.
- Character/reference fidelity from supplied images: consider the current Nano
  Banana variant that accepts the needed reference count and resolution.
- Cheap animatic or composition exploration: inspect a low-cost image model such
  as `z_image` or the cheapest suitable live contract.
- Persistent real-person identity: Soul may improve identity consistency, but
  training is separate, may require a paid plan, and needs likeness consent.

## Video

- General multi-reference film shot: inspect `seedance_2_0` first.
- Low-cost motion test: inspect `seedance_2_0_mini` and compare its limits.
- A model-specific need such as motion control, reframe, or drawn guidance:
  inspect the corresponding live model/workflow. Never force every shot through
  one model if the contract cannot express it.

For Seedance video, pass exactly one `start_image`. Default to no other image
input. After a documented start-only failure, a controlled A/B recovery may add
exactly one essential image reference. Add `end_image` only under a mutually
exclusive motivated-transition profile when exact arrival matters more than
motion freedom. Use video references only when motion or camera
language materially matters and its rationale is recorded. Use audio references
only for the locked visible-dialogue conditioning reference.

## Audio

- No visible dialogue: default to `native_sfx`; specify the complete ambience,
  key synchronized effects, music state, and exclusions before generation, then
  preserve the accepted Seedance track.
- No visible dialogue after repeated native-sound failure: use `post_only` only
  after the user approves external reconstruction as a repair exception.
- Intentionally silent final shot: use `none`.
- Off-screen narration: use `post_only`, generate authorized TTS separately, and
  mix locally. For Korean, audition pronunciation before the full film.
- Visible dialogue: generate and lock a clean ElevenLabs `eleven_v3`
  conditioning reference, specify the whole soundscape and key synchronized
  effects in the Seedance prompt, inspect the jointly generated audio manually,
  and preserve the rendered native track when it passes QC.
- Transcript evidence: use `speech2text` or `clip_transcriber` when appropriate.

Do not use `voice_change` as dialogue separation or general cleanup. Keep music,
effects, and room tone out of the conditioning reference; describe them in the
Seedance sound brief instead.

## Reference-only credit arithmetic

Do not call the live cost endpoint or construct quality scenarios. When actual
transactions exist for the same provider, execution mode, resolution, and
generated-audio flag, calculate mean credits per second times shot duration
times planned attempts. Show the observed min/max range. If no matching sample
exists, report `UNAVAILABLE`; never invent a provider multiplier or unit rate.

## Fallback rule

After two failures with the same diagnosed cause, present a recorded change to
prompt, reference package, duration, or model. Recalculate reference arithmetic
when the execution profile changes. Renew the project ceiling only when the user
wants to raise it or remaining capacity is exhausted.
