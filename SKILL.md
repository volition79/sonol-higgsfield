---
name: sonol-higgsfield
description: Orchestrate approval-gated Higgsfield video productions from requirements interview through storyboard, director-selected shot boundaries, Seedance generation with ElevenLabs V3-conditioned native dialogue audio, continuity and Korean-text QC, FFmpeg finishing, recent-actual credit guidance, and a persistent local dashboard. Use when a user asks to plan, generate, manage, review, resume, or finish a multi-shot Higgsfield film, ad, story, campaign, or narrated video with reusable characters, references, audio, approvals, and selective regeneration.
---

# Sonol Higgsfield

Build a finished video as a controlled production, not as a loose collection of
generation calls. Use the Higgsfield CLI as the canonical execution contract.
Treat the official Higgsfield Skills as routing guidance and MCP as an optional
adapter whose live tool schema must be visible before use.

## Bootstrap

1. Locate this skill directory and set `SONOL_HIGGSFIELD_SKILL` to it.
2. Run the deterministic preflight before planning a paid generation:

   ```bash
   python3 "$SONOL_HIGGSFIELD_SKILL/scripts/inspect_live_schema.py" \
     --output <production>/data/higgsfield-live-schema.json
   ```

3. Require all of the following:
   - `higgsfield` is installed and authenticated.
   - A billing workspace is selected.
   - The requested model or workflow appears in the live CLI schema.
   - The account has available credits and the user approved a project credit ceiling.
4. Use MCP only when its URL ends in `/mcp`, its handshake succeeds, and the
   exact required tool schema is available in the current session. Otherwise
   continue through the CLI without claiming MCP parity.
5. Read [higgsfield-live-contract.md](references/higgsfield-live-contract.md)
   before the first live call in a session.

## Initialize A Production

Create the durable state and dashboard before asking production questions:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" init \
  <production> --name "<project name>"
```

The production directory is the source of truth. Keep generated media under
`media/`; keep behavior state under `data/`; never treat chat memory or a
rendered dashboard as authoritative.

## Mandatory Workflow

### 1. Interview and lock requirements

Read [requirements-interview.md](references/requirements-interview.md). Extract
already-supplied facts first. Ask one unresolved high-value question at a time.
Write every answer immediately with `set-requirement` and preserve the states
`CONFIRMED`, `INFERRED`, `UNKNOWN`, and `CONFLICT`.

Do not generate final assets while any required field is `UNKNOWN` or
`CONFLICT`. Show the completed production specification and require an explicit
user approval before running `lock-requirements --actor user`.

Store the non-negotiable turning points as explicit anchor beats and require
the user to lock them before any paid shot:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" lock-story \
  <production> '[{"id":"BEAT_001","description":"<fixed turn>"}]' --actor user
```

### 2. Create the dashboard and production plan

Initialization creates the static dashboard template and split JSON state.
Refresh it after every state mutation:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" dashboard <production>
```

Read [dashboard.md](references/dashboard.md) before adding fields or changing
the dashboard contract. Serve interactive approvals only on loopback:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/dashboard_server.py" <production>
```

### 3. Plan story, assets, scenes, and shots

Write a timecoded script, then split it into short shots with one camera purpose
and one primary action each. Read [film-grammar-core.md](references/film-grammar-core.md)
and [shot-continuity.md](references/shot-continuity.md). Use the JSON catalog only
when selecting or validating a technique; do not load all 148 records into the
conversation by default.

Treat the story as a sequential adaptive plan, not a fixed shot-by-shot
blueprint. Lock the anchor beats (the story's non-negotiable turning points) and
any recorded dialogue or narration masters; keep the connective tissue between
anchors flexible. Video generation is hard to control, so after each accepted
shot, analyze its boundary frame and micro-adjust the next shot's action,
framing, and prompt to what the footage actually gave you — never the other way
around. Do not pre-produce start frames for the whole board: compose only the
first shot's start image up front, and compose later start images just-in-time
at editorial cuts and scene resets using the then-current story state.

Translate plain intent into two or three explainable alternatives:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" recommend-grammar \
  "<what changes and what the viewer should feel>" \
  --genre <genre> --platform <platform> --provider <job_type> --top 3
```

Explain the tradeoff and `why` for each option. After the user chooses, store
the selected `shot_grammar`, compile it for the selected live provider, and
apply it:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" compile-grammar \
  <production> <shot_id> --provider <job_type> --subject "<subject>" \
  --setting "<setting>" --action "<one action>" --exit-state "<handoff>" \
  --live-schema <production>/data/higgsfield-live-schema.json --apply
```

Do not advance the board beyond `DRAFT` until `validate-grammar --complete`
passes. Default to one primary camera movement. Treat `native_structured`,
`native_reference`, `prompt_soft`, `web_only`, `post_only`, `unreliable`, and
`unsupported` as distinct claims. A web preset or remembered MCP feature is not
a CLI-native field.

Assign stable IDs such as `CHAR_001`, `LOCATION_001`, `PROP_001`, `SCENE_001`,
and `SHOT_001`.

For every shot, record the prior context, current goal, emotion, visual state,
action, camera state, audio state, next-shot setup, reference package,
generation parameters, expected splice points, and one director-approved
boundary strategy. Choose `continuous_match`, `motivated_transition`,
`editorial_cut`, or `scene_reset`; never inherit a previous frame merely because
one exists.

### 4. Discover the live model contract and approve the budget ceiling

Read [model-routing.md](references/model-routing.md). Always run the unfiltered
model/workflow lists and then inspect the selected contract. Never copy a stale
enum from this skill into a paid command.

For `seedance_2_0` or `seedance_2_0_mini`, read
[seedance-2-0-production.md](references/seedance-2-0-production.md). Default to
one controlled shot and 720p prototypes no longer than eight seconds. Compile
native audio off explicitly for post-only and silent routes; compile it on
explicitly for the approved visible-dialogue audio-reference route. Use
experimental timecoded multi-shot only after the user
accepts whole-clip regeneration risk.

Do not call the Higgsfield live cost endpoint or build economy, recommended, and
highest-quality quote scenarios. After requirements are locked, ask the user for
one total project credit ceiling and record explicit acceptance that jobs can be
submitted without an exact provider quote:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" approve-budget \
  <production> <max_credits> --actor user
```

For optional planning guidance only, run `estimate_costs.py <production>
--attempts <count>`. It performs no provider call and uses only matching recent
actual transactions for the same provider, mode, resolution, and audio flag.
Report `UNAVAILABLE` when no sample exists. Label every number
`REFERENCE_ONLY`, never a quote or spending guarantee. Never invent a unit rate
or cash/KRW conversion.

### 5. Create and approve animatic and reference assets

Use a low-cost image model for the animatic and a quality/identity model for
final references. Use GPT Image for images containing important Korean text,
then run `ocr_check.py` before user review. Treat OCR as a gate, not proof of
visual quality.

Character, location, prop, and style references normally exist to **compose the
start image**. Start with that finished frame alone. Additional video-call
image guidance is an evidence-led exception: after a documented start-only
failure, A/B test exactly one indispensable reference with every other variable
held fixed. Never add a stack of speculative references.

Before board approval, record the v7 start-image review: it is the final first
frame, matches the requested aspect, contains no collage/labels, makes the key
subject readable, supports the first action, and states off-frame-reveal risk.
A technically sharp image can still be a poor motion initial condition.

Move each asset through:

`DRAFT -> INTERNAL_QC_PASSED -> USER_REVIEW -> USER_APPROVED -> LOCKED_FOR_VIDEO`

Only the user may approve. If content or metadata changes, increment its
version and invalidate the previous approval. Do not queue a final video from
an asset that is not `LOCKED_FOR_VIDEO`.

### 6. Generate one bounded shot at a time

Prefer Seedance 2.0 for serious general video. Respect the live reference and
duration limits.

Apply the minimum-sufficient image contract, enforced by the generation gate:

- Every paid video call carries **exactly one start image** — the previous
  accepted shot's boundary frame on a chain, or a freshly composed keyframe at
  a cut/reset.
- Default `image_input_policy.mode=start_only`: no `image_references` and no
  `end_image`; describe the intended exit state in the prompt.
- Escalate to `start_plus_essential_reference` only after persisting the failed
  baseline job, failure diagnosis, semantic role, rationale, and the single
  changed variable. It carries exactly one matching manifest reference.
- Use `start_end_transition` only for a declared `motivated_transition` whose
  exact arrival composition matters and whose motion is simple and plausible.
  Do not use it for dialogue, complex action, or a large angle/location jump.
- `audio_references` only for the locked dialogue reference on a visible-dialogue
  route (the start image satisfies the visual-reference requirement).
- If identity drifts late, first shorten/reset and improve the start image; only
  then test one essential identity reference under the documented A/B rule.

Keep the prompt compact and high-probability: shot spec, subject and one
action, one camera move, lighting and mood, an explicit instruction to begin
from the supplied start-image composition without reframing before motion, and
the exit state. Long
enumerations of invariants and reference descriptions lower compliance.
The compiler enforces the selected image-input profile, rejects an `end_image`
outside `motivated_transition`, and emits at most three critical invariants.

Submit with `--wait --json` only after the guarded runner has re-fetched the
selected contract, confirmed remaining project-ceiling capacity, and checked
the current account balance.
If a wait is interrupted before a job ID is returned, do not retry blindly;
reconcile provider history first because the original job may still exist.
Never silently replace the selected model. If the preferred contract fails
twice for the same reason, change the prompt, reference package, duration, or
model with a recorded rationale and renewed ceiling approval when needed.

After storing the approved model/workflow arguments in the shot's `execution`
object and moving it to `READY`, use the guarded paid runner:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/run_shot.py" \
  <production> <shot_id> --execute-paid
```

Add `--authorize-local-upload` only when the user approved the local reference
files. The runner rechecks gates, remaining ceiling, and current account credits
before submission and never calls `generate cost`. Without an exact quote, the
ceiling is a preflight control, not a guaranteed hard cap on one submitted job.

### 7. Inspect immediately and route audio conditionally

Inspect every completed shot before generating the next dependent shot. Read
[audio-qc.md](references/audio-qc.md) and choose exactly one route:

- `NO_DIALOGUE_POST`: generate picture with `audio_mode=post_only`; build room
  tone, ambience, Foley, effects, and music in finishing.
- `INTENTIONAL_SILENCE`: use `audio_mode=none` only when the final shot itself
  must remain silent.
- `OFFSCREEN_NARRATION`: generate picture with `audio_mode=post_only`; create
  narration separately, store its approved master path and SHA-256 fingerprint,
  and add it only in the final mix.
- `VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO`: approve a clean ElevenLabs
  `eleven_v3` dialogue reference first and pass it through Seedance
  `audio_references` with `audio_mode=audio_reference`. Before compilation,
  specify dialogue performance, ambience, zero to three synchronized effects,
  music or `none`, and excluded sounds in `seedance_plan.sound_design`. Generate
  picture and complete production sound together, then preserve the
  Seedance-rendered native track after transcript, pronunciation, lip-sync,
  sound-sync, and technical QC.

Keep voice IDs, pronunciation sheet, speaker assignment, and reference path in the
shot record. Multiple visible speakers require distinct locked voices or an
authorized ElevenLabs dialogue workflow. Treat the V3 file as a conditioning
reference, not a transparent final waveform; never claim Seedance preserves it
sample-for-sample.

Use `speech2text` for transcript evidence when available. Use FFmpeg for
extraction, trimming, time stretch, muxing, and assembly. Do not describe
speech separation, lip-sync scoring, or character continuity as automatic
unless a concrete provider or deterministic checker produced evidence.

### 8. Direct boundaries, verify continuity, and repair selectively

Run the sequential adaptive loop after every accepted shot:

1. Extract boundary candidates with `media_pipeline.py boundary-frames`. It
   persists eight frames from the final 0.5 seconds and scores each with FFmpeg
   `blurdetect`. Lowest blur is a default recommendation, not the director.
2. Analyze that frame against the story plan: pose, gaze, props, framing,
   lighting, emotional state.
3. Micro-adjust the next shot's action and prompt to match the frame, keeping
   the anchor beats, locked dialogue references, and narration masters fixed.
4. Classify the incoming edit and wire exactly one start image.

Boundary strategies:

- `continuous_match`: the accepted previous boundary frame becomes the next
  `start_image`, alone. A pre-designed keyframe is analysis input for story
  re-alignment only — it is never transported in the video call.
- `motivated_transition`: normally still use start-only plus a prompt exit
  state. Add the planned keyframe as `end_image` only when an exact arrival is
  more important than motion freedom, preferably in a dedicated simple bridge.
  In `set-boundary`, omit `--planned-keyframe` for prompt-only; supplying it
  explicitly selects the end-image profile.
- `editorial_cut`: for reverse angles, reactions, inserts, decisive shot-size
  changes, or hard cuts, do not inherit the previous frame; compose a new
  start image now from locked references and the current story state.
- `scene_reset`: for a new place, time, style, or story unit, do not inherit
  the previous frame; compose a new start image now. Cuts and resets also
  break the error accumulation of a long chained sequence — prefer one when
  quality has visibly drifted.

The current CLI exposes no native `middle_image`. Never claim that a generic
image reference is temporally pinned to the middle of a clip.

Immediately after generation, extract the actual first frame and compare it to
the submitted image. `media_pipeline.py compare-start-frame` records dimensions,
SSIM, and PSNR as technical evidence only; framing, identity, and semantic
composition still require visual judgment. The start image is strong guidance,
not a pixel lock.

Extract the accepted previous clip with `media_pipeline.py boundary-frames`,
then persist the director decision with `sonol_higgsfield.py set-boundary`. For
example:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" set-boundary \
  <production> <shot_id> continuous_match \
  --previous-shot-id <previous_shot_id> --previous-frame <accepted_end.png> \
  --planned-keyframe <current_keyframe.png> --reason "<director rationale>"
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" record-start-image-review \
  <production> <shot_id> '<assessment-json>' PASSED --notes "<risk rationale>"
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/media_pipeline.py" compare-start-frame \
  <submitted_start.png> <rendered_first.png>
```

After generation, persist first-frame comparison and the semantic boundary
reading. The technical selector is deterministic; pose, gaze, hands, props,
framing, lighting, and emotion remain an agent/director judgment that must be
recorded rather than claimed as an automatic vision score:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" record-start-frame-qc \
  <production> <shot_id> <rendered_first.png> PASSED
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" record-boundary-analysis \
  <production> <shot_id> <selected_boundary.png> '<observations-json>' \
  '<boundary-selection-json>' "<next-story adjustment>"
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" set-adaptive-story \
  <production> <next_shot_id> '["BEAT_001"]' "<adjustment rationale>" \
  NOT_APPLICABLE --previous-shot-id <shot_id>
```

Schema v7 blocks paid generation until the start image passes preparation
review, and blocks the next shot until the immediate previous shot is generated,
user-accepted, first-frame-QC passed, boundary-analyzed, and bound to the next
adaptive plan. A cut/reset start image must carry just-in-time provenance after
that previous shot. Chained shots must use the exact recorded boundary frame.

Extract the end of the previous shot and the start of the next with
`media_pipeline.py`. Compare face, hair, costume, body and hand pose, gaze,
movement direction, prop and location state, camera axis, lens feel, exposure,
color, ambience, dialogue timing, and narrative emotion.

Repair in this order: edit point, J/L cut, common ambience, grade, minor speed
adjustment, cutaway, bridge shot, transition clip, then next-shot regeneration.
For visible dialogue with native production audio, do not add replacement
dialogue, ambience, Foley, effects, or music by default. If its required sound
fails QC, simplify the sound brief and regenerate the affected shot; external
replacement is an explicitly approved exception requiring a synchronization and
lost-effects recovery plan.
Generate a four-second-or-longer transition when the live model minimum
requires it and trim locally to the intended one-to-three-second edit.

### 9. Finish and deliver

Require transcript, technical, lip-sync/manual, continuity, and user-review
gates before marking a shot final. Assemble only accepted versions. For visible
dialogue, keep the Seedance-rendered track as the complete production sound and
use `media_pipeline.py preserve-audio` when a copy-only finishing pass is needed.
Do not add creative audio stems after generation by default; limit finishing to
technical checks, stream-preserving assembly, captions, and grade. Keep
`strip-audio` and `final-mix` for post-only routes or an explicitly approved
repair exception. Update actual credits, job IDs, retry counts, and the dashboard.

Deliver the final file or URL with duration, aspect, model ledger, approved
ceiling, reference-only arithmetic when available, actual credits, regenerated
shots, QC gaps, and any manual checks still required.

## Non-Negotiable Gates

- Never start paid generation before requirements and budget are user-approved.
- Never approve or queue a shot without a complete provider-compiled and validated `shot_grammar`.
- Never add video-call image references speculatively. Default to start-only;
  after a recorded failure, allow exactly one essential reference as a
  controlled A/B variable. Only a motivated transition may add an `end_image`.
- Never pre-produce start frames beyond the next shot to generate; compose them
  just-in-time from the current story state.
- Never queue a dependent shot without a user-locked story contract, accepted
  prior shot, boundary-analysis ID, passed first-frame QC, and matching JIT
  start-image provenance.
- Never treat recorded dialogue or narration as fixed without its approved
  SHA-256 fingerprint in both the audio plan and adaptive story snapshot.
- Never accept a shot without comparing its actual first frame to the submitted
  start image.
- Never treat SSIM, PSNR, or lowest blur as an automatic creative approval.
- Never combine multiple primary camera moves unless the user accepts an experimental A/B test.
- Never insert web `@character`, `@style`, `@motion`, or `@audio` aliases into a CLI prompt unless the live CLI schema explicitly exposes alias binding.
- Never let Seedance inherit its current `generate_audio=true` default; compile an explicit shot audio route.
- Never queue visible dialogue without a complete compact sound brief covering
  voice, ambience, synchronized effects, music state, and exclusions.
- Never discard or creatively overdub an accepted visible-dialogue native track
  unless the user approves an exceptional recovery plan.
- Never present recent-actual arithmetic as a live quote, fixed price, or hard spending guarantee.
- Never claim a lens number, camera preset, or prompt-soft instruction guarantees the rendered result.
- Never infer user approval from silence, model output, or an earlier version.
- Never generate final video from an unlocked asset or unapproved shot board.
- Never continue after the approved project ceiling is exhausted; request a renewed ceiling.
- Never mark a shot final while required QC or adjacent-shot continuity fails.
- Never report MCP, voice separation, OCR, lip-sync, or visual QC as successful
  without direct evidence from that exact run.
- Never store OAuth tokens, credentials, private media URLs, or raw secrets in
  production JSON, the dashboard, logs, or schema snapshots.
- Always update history and dashboard state after a successful mutation.

Read [approval-cost-policy.md](references/approval-cost-policy.md) for the
complete state and budget rules and [workflow.md](references/workflow.md) for
recovery paths and phase exit criteria. Read
[capability-matrix.md](references/capability-matrix.md) before promising that a
requested function is native, MCP-backed, locally automated, or manual.

## Verification

Before delivery or packaging, run:

```bash
python3 -m unittest discover -s "$SONOL_HIGGSFIELD_SKILL/tests" -v
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/validate_shot_grammar.py" \
  <grammar.json> --complete
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" validate <production>
python3 /root/.agents/skills/skill-creator/scripts/quick_validate.py \
  "$SONOL_HIGGSFIELD_SKILL"
```

Use a real paid smoke generation only after the user approves the project credit
ceiling and acknowledges execution without an exact live quote.
