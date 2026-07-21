# Audio routing and QC

## Route each shot

Classify before generation and confirm after output:

| Situation | Route |
|---|---|
| No visible dialogue; ambience/SFX/music will be added | `NO_DIALOGUE_POST`; Seedance `post_only`, then construct locally |
| Final shot is deliberately silent | `INTENTIONAL_SILENCE`; Seedance `none` |
| Off-screen narration | `OFFSCREEN_NARRATION`; Seedance `post_only`, TTS and mix separately |
| Visible dialogue | `VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO`; use a locked V3 reference and a complete sound brief, then preserve the QC-passed Seedance native track |

For visible dialogue, treat the approved ElevenLabs file as a conditioning
reference for voice, performance, pronunciation, timing, and lip movement. It
is not a transparent pass-through or a promise of sample-identical output. The
Seedance-rendered track is the candidate production mix because it contains the
jointly generated dialogue, ambience, and synchronized effects. Do not use
`voice_change` as a general cleanup or stem separation tool.

## ElevenLabs V3 dialogue reference

For visible speech, finish audio before paid video generation:

1. Assign stable `voice_id` values per speaker and use model `eleven_v3`.
2. Lock script wording, pronunciation, emotional direction, pauses, and timing.
3. Generate and approve one clean reference without music, effects, or room tone.
4. Store it in `audio.dialogue_reference_path` and `references.audios`, and
   store `audio.dialogue_reference_sha256`; the sole
   `start_image` satisfies Seedance visual-reference requirements.
5. Complete `seedance_plan.sound_design` with:
   - `dialogue`: language, speaker, delivery, and exact-reference behavior;
   - `ambience`: the complete background soundscape, or `none`;
   - `synchronized_effects`: zero to three essential visible event sounds;
   - `music`: the intended music state, or `none`;
   - `exclusions`: up to four unwanted sound categories.
6. Compile `audio_mode=audio_reference` and `generate_audio=true`. The compiler
   emits the sound brief as one compact audio clause in the Seedance prompt.
7. After generation, review transcript, pronunciation, voice consistency,
   lip sync, effect timing, ambience, unwanted sounds, and technical quality.
8. When all gates pass, set `generated_track_policy=PRESERVE`, keep
   `final_mix_required=false`, and retain the Seedance-rendered native track.

Do not list incidental sounds one by one. Specify the whole acoustic space and
only the one to three effects whose timing matters to the picture. A missing or
incorrect required sound normally triggers a simpler brief and shot
regeneration, not an automatic post-production overdub.

For multiple visible speakers, use distinct locked voices and either an
authorized ElevenLabs dialogue workflow or separately timed speaker tracks.
Do not claim multi-speaker support from the bundled single-speaker helper unless
the exact live tool/API contract proves it.

For off-screen narration, store `audio.narration_master_path` and
`audio.narration_master_sha256`. It is never sent to Seedance; it is protected
as the authoritative recording and added in the final external mix. Adaptive
story revisions must snapshot the matching dialogue or narration fingerprint
and explicitly declare `UNCHANGED` or `RERECORDED`.

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

## Finishing policy

For `VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO`:

1. Lock the accepted picture and native production track together.
2. Do not add replacement dialogue, ambience, Foley, effects, or music by
   default; those creative requirements belonged in the generation brief.
3. Use `preserve-audio` for a copy-only remux when needed.
4. Apply only technical finishing that the user accepts, such as stream-safe
   assembly, captions, grade, and verified level correction.
5. Check transcript, pronunciation, lip sync, sound-event sync, peaks,
   clipping, silence, channel layout, sample rate, and A/V duration.

For `NO_DIALOGUE_POST` or `OFFSCREEN_NARRATION`, build the authorized external
mix from its planned stems. `INTENTIONAL_SILENCE` receives no audio. External
replacement of a visible-dialogue track is an exception: record the reason,
obtain user approval, and require word/phoneme alignment plus a plan to preserve
or rebuild any lost generated effects. A single global time offset is not
sufficient evidence.

For professional delivery, set a loudness target appropriate to the destination
and verify with an available meter. If no integrated loudness meter was run,
report that gap rather than claiming broadcast compliance.

## Deterministic local tools

- `media_pipeline.py probe`: stream, codec, duration, dimensions, fps evidence.
- `extract-audio`: lossless PCM working file.
- `trim`: exact local repair segment.
- `stretch`: pitch-preserving A/V speed adjustment using `atempo`.
- `mux`: replace/mix-ready audio onto picture.
- `preserve-audio`: copy the generated picture and native audio streams without
  adding or replacing creative stems.
- `strip-audio`: remove the Seedance-rendered track without re-encoding picture.
- `final-mix`: combine external dialogue, ambience, effects, and music while
  mapping picture only from the generated video; it is for post-only routes or
  an approved replacement exception, not the visible-dialogue default.
- `concat`: deterministic re-encode of accepted shot sequence.

These tools do not perform dialogue separation, denoising, mastering, automatic
ducking, or visual continuity scoring. `final-mix` uses fixed stem gains and
loudness normalization; do not report sidechain ducking unless another verified
process actually performed it.
