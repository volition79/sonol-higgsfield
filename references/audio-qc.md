# Audio routing and QC

## Route each shot

Classify before generation and confirm after output:

| Situation | Route |
|---|---|
| Visible dialogue, acceptable native voice | Retain original; transcript and lip-sync review |
| Visible dialogue, voice must be consistent | Authorized voice-change workflow; inspect source mix first |
| Off-screen narration | Generate TTS separately and mix locally |
| Ambience/SFX only | Retain acceptable native sound or build locally |
| Music-led/silent | Do not run voice change; construct final mix |

`voice_change` is not a general audio cleanup tool. Do not apply it to a full
mix without checking whether dialogue can be replaced without damaging music,
effects, or room tone.

## Korean dialogue

Maintain a pronunciation sheet with original spelling, desired spoken form,
numbers/units, English names, abbreviations, and pause/emphasis cues. Generate a
short audition before a long paid batch. Compare the transcript with the locked
script, then listen manually for pronunciation, prosody, natural pauses, and
name/brand accuracy.

OCR does not validate speech. Speech-to-text does not prove pronunciation or
lip sync. Keep their evidence separate.

## Lip-sync review

No objective automatic lip-sync scorer was confirmed in the observed live
schema. Therefore classify lip-sync as manual unless an explicit checker is
integrated later. Inspect at normal speed and frame-by-frame around consonant
closures and phrase boundaries. Record `PASSED`, `FAILED`, or
`MANUAL_REQUIRED`; never fabricate a numeric score.

## Mix order

1. Lock accepted picture edit.
2. Apply dialogue replacement or TTS.
3. Restore or create ambience and room tone.
4. Add effects and Foley.
5. Add music and automation.
6. Duck music under intelligible dialogue.
7. Apply captions and final grade.
8. Check peaks, clipping, silence, channel layout, sample rate, and A/V duration.

For professional delivery, set a loudness target appropriate to the destination
and verify with an available meter. If no integrated loudness meter was run,
report that gap rather than claiming broadcast compliance.

## Deterministic local tools

- `media_pipeline.py probe`: stream, codec, duration, dimensions, fps evidence.
- `extract-audio`: lossless PCM working file.
- `trim`: exact local repair segment.
- `stretch`: pitch-preserving A/V speed adjustment using `atempo`.
- `mux`: replace/mix-ready audio onto picture.
- `concat`: deterministic re-encode of accepted shot sequence.

These tools do not perform dialogue separation, denoising, mastering, or visual
continuity scoring.

