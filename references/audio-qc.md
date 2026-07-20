# Audio routing and QC

## Route each shot

Classify before generation and confirm after output:

| Situation | Route |
|---|---|
| No visible dialogue; ambience/SFX/music will be added | `NO_DIALOGUE_POST`; Seedance `post_only`, then construct locally |
| Final shot is deliberately silent | `INTENTIONAL_SILENCE`; Seedance `none` |
| Off-screen narration | `OFFSCREEN_NARRATION`; Seedance `post_only`, TTS and mix separately |
| Visible dialogue | `VISIBLE_DIALOGUE_ELEVENLABS_V3`; lock the V3 master, use it as Seedance audio reference, discard generated track, remux master |

Do not retain provider-native dialogue under this production route. Do not use
`voice_change` as a general cleanup or stem separation tool. The locked
ElevenLabs master is the source of truth; Seedance receives a copy only to guide
visible speech timing.

## ElevenLabs V3 master

For visible speech, finish audio before paid video generation:

1. Assign stable `voice_id` values per speaker and use model `eleven_v3`.
2. Lock script wording, pronunciation, emotional direction, pauses, and timing.
3. Generate and approve one clean master without music, effects, or room tone.
4. Store the master path in `audio.dialogue_master_path` and
   `references.audios`; keep at least one visual reference for Seedance.
5. Compile `audio_mode=audio_reference` and `generate_audio=true`.
6. After generation, review lip sync manually, strip the Seedance-rendered
   audio, and remux the unchanged approved master.

For multiple visible speakers, use distinct locked voices and either an
authorized ElevenLabs dialogue workflow or separately timed speaker tracks.
Do not claim multi-speaker support from the bundled single-speaker helper unless
the exact live tool/API contract proves it.

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
2. Strip the generated video track when external audio is authoritative.
3. Apply the untouched dialogue master or off-screen TTS.
4. Restore or create ambience and room tone.
5. Add effects and Foley.
6. Add music and automation.
7. Duck music under intelligible dialogue.
8. Apply captions and final grade.
9. Check peaks, clipping, silence, channel layout, sample rate, and A/V duration.

For professional delivery, set a loudness target appropriate to the destination
and verify with an available meter. If no integrated loudness meter was run,
report that gap rather than claiming broadcast compliance.

## Deterministic local tools

- `media_pipeline.py probe`: stream, codec, duration, dimensions, fps evidence.
- `extract-audio`: lossless PCM working file.
- `trim`: exact local repair segment.
- `stretch`: pitch-preserving A/V speed adjustment using `atempo`.
- `mux`: replace/mix-ready audio onto picture.
- `strip-audio`: remove the Seedance-rendered track without re-encoding picture.
- `final-mix`: combine external dialogue, ambience, effects, and music while
  mapping picture only from the generated video.
- `concat`: deterministic re-encode of accepted shot sequence.

These tools do not perform dialogue separation, denoising, mastering, or visual
continuity scoring.
