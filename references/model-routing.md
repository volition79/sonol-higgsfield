# Model and workflow routing

Use this as a decision tree, then verify the selected live schema and cost.

## Images

- Important Korean text, layout, design, or art direction: begin with
  `gpt_image_2`; run OCR and visual review.
- Character/reference fidelity from supplied images: consider the current Nano
  Banana variant that accepts the needed reference count and resolution.
- Cheap animatic or composition exploration: quote a low-cost image model such
  as `z_image` or the cheapest suitable live contract.
- Persistent real-person identity: Soul may improve identity consistency, but
  training is separate, may require a paid plan, and needs likeness consent.

## Video

- General multi-reference film shot: inspect `seedance_2_0` first.
- Low-cost motion test: inspect `seedance_2_0_mini` and compare its limits.
- A model-specific need such as motion control, reframe, or drawn guidance:
  inspect the corresponding live model/workflow. Never force every shot through
  one model if the contract cannot express it.

Prefer start/end references for explicit boundary control. Use image references
for identity, costume, location, product, and visual language. Use video
references only when motion or camera language materially matters. Use audio
references only when the selected contract documents their effect.

## Audio

- Native generated dialogue/ambience: enable it only when the live video model
  supports it and the shot plan calls for it.
- Consistent replacement voice on visible dialogue: inspect `voice_change`,
  list current voices, quote duration, and validate transcript/lip sync.
- Off-screen narration: route through an authorized TTS model/workflow, then mix
  locally. For Korean, audition pronunciation before generating the full film.
- Music or sound effects: inspect `seed_audio` or another current audio contract.
- Transcript evidence: use `speech2text` or `clip_transcriber` when appropriate.

Do not apply voice change to ambience-only or silent shots. Do not assume it can
separate speech cleanly from music or effects. If the source mix is inseparable,
prefer a clean audio plan from the outset or an explicitly integrated stem
separation tool.

## Cost scenarios

Every scenario must contain explicit command arguments per shot:

```json
{
  "cost_options": {
    "economy": ["seedance_2_0_mini", "--prompt", "...", "--duration", "4", "--resolution", "720p", "--generate-audio", "false"],
    "recommended": ["seedance_2_0", "--prompt", "...", "--duration", "5", "--resolution", "720p", "--generate-audio", "false"],
    "highest_quality": ["seedance_2_0", "--prompt", "...", "--duration", "5", "--resolution", "4k", "--mode", "std", "--generate-audio", "false"]
  }
}
```

Do not approximate the other scenarios with multipliers. Quote the exact live
commands because resolution, duration, mode, provider, and account pricing can
change nonlinearly.

Seedance currently defaults native audio on, so every scenario must state
`--generate-audio true|false` explicitly. Prototype with false. Enable it only
for an approved `native_sfx`, `native_dialogue`, or `audio_reference` plan.

## Fallback rule

After two failures with the same diagnosed cause, present a recorded change to
prompt, reference package, duration, or model. Requote whenever inputs or model
change. Renew approval if the new total can exceed the existing ceiling.
