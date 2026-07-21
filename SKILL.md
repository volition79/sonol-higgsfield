---
name: sonol-higgsfield
description: Route and orchestrate Higgsfield video work across Cinema Studio 3.5, Seedance, quick clips, and approval-gated serial productions, with native directing axes, minimum-sufficient prompts, ElevenLabs V3-conditioned dialogue, adaptive continuity, QC, recovery, and a persistent dashboard. Use for films, stories, campaigns, or controlled shots needing expressive camera direction, reusable characters, selective regeneration, provider recovery, or production state; route ads and explainers to Higgsfield's official dedicated workflows first.
---

# Sonol Higgsfield

Build a finished video as a controlled production, not as a loose collection of
generation calls. Use the Higgsfield CLI as the canonical discovery, account,
provider-history, and reconciliation contract. Use the audited web UI only for
web-only controls or a confirmed pre-job CLI defect.
Treat the official Higgsfield Skills as routing guidance and MCP as an optional
adapter whose live tool schema must be visible before use.

## Bootstrap

1. Locate this skill directory and set `SONOL_HIGGSFIELD_SKILL` to it.
2. Run the deterministic preflight before planning a managed paid generation:

   ```bash
   python3 "$SONOL_HIGGSFIELD_SKILL/scripts/inspect_live_schema.py" \
     --output <production>/data/higgsfield-live-schema.json
   ```

3. Require all of the following:
   - `higgsfield` is installed and authenticated.
   - A billing workspace is selected.
   - The requested model or workflow appears in the live CLI schema.
   - The account has available credits and the user approved either a project
     credit ceiling or the official direct workflow's own spend confirmation.
4. Use MCP only when its URL ends in `/mcp`, its handshake succeeds, and the
   exact required tool schema is available in the current session. Otherwise
   continue through the CLI without claiming MCP parity.
5. Read [higgsfield-live-contract.md](references/higgsfield-live-contract.md)
   before the first live call in a session.
6. Before a web route, read [web-ui-runtime.md](references/web-ui-runtime.md).
   Require the user to complete login, 2FA, captcha, passkey, and consent in the
   visible browser. Never request or inspect credentials, codes, cookies, or tokens.

## Route Before Initializing

Read [director-intelligence.md](references/director-intelligence.md) and run
`director_intelligence.py route` before creating Sonol state. Select by intent:

- `QUICK_CLIP`: one or two exploratory clips; use the official
  `higgsfield-generate` skill and CLI directly.
- `NATIVE_MULTISHOT`: one Seedance generation with two to four simple numbered,
  timecoded beats inside 15 seconds.
- `CONTROLLED_SHOT`: one core shot per generation when dialogue, acting,
  product interaction, or camera precision carries the result.
- `SERIAL_STORY`: multiple jobs, continuity, selective regeneration, or more
  than 15 seconds; use Sonol state and recovery.
- `OFFICIAL_WORKFLOW`: use Marketing Studio for ads and
  `higgsfield-video-explainer` for explainers. Add Sonol only for optional audit
  or downstream QC, not as the default owner.

Set `LIGHT`, `TARGETED`, or `FULL` approval depth. Reserve `FULL` for high-cost, multi-job, or long projects. If a managed production is needed, persist the
choice with `set-production-policy`. Do not initialize a dashboard merely to
make a quick official generation.

Route the provider per shot using
[cinema-studio-3-5-production.md](references/cinema-studio-3-5-production.md).
Leave a balanced Seedance/Cinema tie unresolved for a representative A/B.

## Initialize A Managed Production

Create durable state only after the router selects a managed mode:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/sonol_higgsfield.py" init \
  <production> --name "<project name>" --mode <routed_mode> \
  --approval-profile <LIGHT|TARGETED|FULL>
```

The production directory is the source of truth. Keep generated media under
`media/`; keep behavior state under `data/`; never treat chat memory or a
rendered dashboard as authoritative.

## Adaptive Managed Workflow

### 1. Interview and lock requirements

Read [requirements-interview.md](references/requirements-interview.md). Extract
already-supplied facts first. Ask one unresolved high-value question at a time.
Write every answer immediately with `set-requirement` and preserve the states
`CONFIRMED`, `INFERRED`, `UNKNOWN`, and `CONFLICT`.

For `FULL`, do not generate final assets while a required field is `UNKNOWN` or
`CONFLICT`; show the specification and require explicit approval before
`lock-requirements --actor user`. For `TARGETED`, lock only the load-bearing
shot, assets, and spend boundary. For `LIGHT`, rely on the compiled provider
contract, prepared input, explicit audio route, and spend boundary rather than
forcing the full interview and board sequence.

In `FULL` serial stories, store non-negotiable turning points as explicit
anchor beats and lock them before dependent paid shots:

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

Write a timecoded script, then choose boundaries by purpose. A single
generation may be a controlled shot or a native multi-shot sequence; splitting
is a risk-control recommendation, not a universal law. Read
[film-grammar-core.md](references/film-grammar-core.md)
and [shot-continuity.md](references/shot-continuity.md). Use the JSON catalog only
when selecting or validating a technique; do not load all 148 records into the
conversation by default.

For a `SERIAL_STORY`, treat the story as a sequential adaptive plan, not a fixed
shot-by-shot blueprint. Lock the anchor beats and
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

For each `FULL` serial shot, record context, goal, continuity, references,
generation parameters, splice points, and one approved boundary strategy.
Never inherit a previous frame merely because one exists.

Before board approval, use the five advisory commands described in
[director-intelligence.md](references/director-intelligence.md). They never
auto-select a camera, split a shot, change cost, or replace approved meaning.

### 4. Discover the live model contract and approve the budget ceiling

Read [model-routing.md](references/model-routing.md). Always run the unfiltered
model/workflow lists and then inspect the selected contract. Never copy a stale
enum from this skill into a paid command.

For `seedance_2_0` or `seedance_2_0_mini`, read
[seedance-2-0-production.md](references/seedance-2-0-production.md). Use a
controlled shot for load-bearing precision, or native multi-shot for two to
four simple timed beats within one clip. Prototype at 720p and no longer than
eight seconds when the chosen test permits it. Compile
native audio on explicitly for the default no-dialogue native-sound route and
the approved visible-dialogue audio-reference route. Compile it off only for
intentional silence, off-screen narration, or a user-approved post-only repair. Use
native multi-shot only when exact dialogue, precise acting, and fragile object
interaction are not load-bearing; explain that any failed beat may require
regenerating the whole clip.

Do not call the Higgsfield live cost endpoint or build economy, recommended, and
highest-quality quote scenarios. Ask for one total project credit ceiling and
record acceptance that jobs can be submitted without an exact provider quote;
`FULL` requires its requirement lock first:

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

Before paid managed generation, record the v9 start-image review: it is the final first
frame, matches the requested aspect, contains no collage/labels, makes the key
subject readable, supports the first action, and states off-frame-reveal risk.
A technically sharp image can still be a poor motion initial condition.

For `FULL` and for load-bearing assets in `TARGETED`, move each asset through:

`DRAFT -> INTERNAL_QC_PASSED -> USER_REVIEW -> USER_APPROVED -> LOCKED_FOR_VIDEO`

Only the user may approve a locked board version. `LIGHT` does not require the
entire asset workflow. If locked content or metadata changes, increment its
version and invalidate the previous approval. Do not queue a final video from
an asset that is not `LOCKED_FOR_VIDEO`.

### 6. Generate with the routed unit of work

Use the routed provider, not a universal default. Cinema 3.5 executes as CLI
mode `model` through `generate create`; bind its broad style/light/grade/genre
fields natively and keep exact moves and lens claims prompt-soft. Respect the
selected live contract's reference and duration limits.

Apply the minimum-sufficient image contract, enforced by the generation gate:

- A managed image-to-video call carries one authoritative start image. Inherit
  the previous accepted boundary only for a true continuous match; otherwise
  use a freshly composed just-in-time keyframe.
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

Use a minimum-sufficient prompt. Put the load-bearing action, expression,
camera, object change, reveal, or exit state early; then include only the
subject motion, one primary camera intent, relevant lighting, audio brief, and
needed end state. A simple shot is usually short, while dialogue, emotion,
transitions, and native multi-shot may need more words. Word ranges are warnings,
not gates. Remove static re-description already supplied by the start image and
long invariant lists, but never delete meaning only to hit a number.
The compiler enforces the selected image-input profile, rejects an `end_image`
outside `motivated_transition`, and emits at most three critical invariants.
For image-to-video, default to `match_then_release`; preserve the initial
composition only when composition stability is load-bearing.

Submit without provider waiting only after the guarded runner has re-fetched
the selected contract, confirmed remaining project-ceiling capacity, and
checked the current account balance. The runner first persists a `SUBMITTING`
attempt, then invokes `generate create`, and stores the returned job ID before
any wait. Do not combine paid submission and a long queue wait in one process.
If submission ends without a recognized job ID, keep it
`SUBMISSION_AMBIGUOUS`; never retry blindly because the original job may exist.
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

Observe or recover that attempt separately:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/run_shot.py" \
  <production> <shot_id> --reconcile [--wait] [--job-id <provider_job_id>]
```

With no stored ID, automatic history recovery binds only one high-confidence
match using provider, prompt hash, stable parameters, and submission time. Zero
or multiple matches remain ambiguous for manual selection. A wait interruption
with a known ID becomes `REMOTE_UNKNOWN` and remains safe to query again. New
planning gates apply only before submission; they never block recording a
provider-completed result or its actual cost. If the provider omits credits,
record a pending reconciliation and any account-balance delta as non-authoritative
evidence. A user may continue with `--acknowledge-pending-costs`; the attempt
history records that risk acceptance. Above-ceiling actual cost is always
recorded and flagged `ceiling_breach`; it is never hidden by the ceiling gate.

For Cinema Studio 3.5, if one controlled CLI call is rejected before job
creation with a confirmed media/IP gate and provider history shows no job, stop
the retry loop. Use native computer use, an exposed browser/Playwright tool, or
the bundled loopback-CDP fallback in that order. Ask the user to log in visibly,
change the selected image's default `Reference` role to `Start Frame`, verify the
`Start` badge and approved settings, and click Generate exactly once. Then bind
the provider job without inventing a second local attempt:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/run_shot.py" \
  <production> <shot_id> --reconcile --job-id <provider_job_id> \
  --submission-surface web_ui --credits <actual> --result-path <downloaded-file>
```

The web browser session is never spend approval. Apply the same remaining
ceiling check and explicit approval as the CLI path, and query provider history
before reacting to a missing toast or timeout.

### 7. Inspect immediately and route audio conditionally

Inspect every completed shot before generating the next dependent shot. Read
[audio-qc.md](references/audio-qc.md) and choose exactly one route:

- `NO_DIALOGUE_NATIVE_SOUND`: default when nobody visibly speaks. Use
  `audio_mode=native_sfx`, describe the complete ambience, zero to three
  synchronized effects, music or `none`, and exclusions, then preserve the
  QC-passed native track without creative overdubs.
- `NO_DIALOGUE_POST`: user-approved repair exception only. Generate picture
  with `audio_mode=post_only` and construct the explicitly authorized stems.
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
sample-for-sample or guarantees the same timing, timbre, or fidelity.

Use `speech2text` for transcript evidence when available. Use FFmpeg for
extraction, trimming, time stretch, muxing, and assembly. Do not describe
speech separation, lip-sync scoring, or character continuity as automatic
unless a concrete provider or deterministic checker produced evidence.

### 8. Direct boundaries, verify continuity, and repair selectively

Run the sequential adaptive loop for dependent `SERIAL_STORY` shots. A cut or
reset still reviews the accepted clip for story consequences, but it does not
require extracting or inheriting a boundary frame merely because one exists:

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
- `motivated_transition`: may inherit the prior boundary only when the action
  truly continues; otherwise compose a new start image. Normally use start-only
  plus a prompt exit state. Add a distinct `--end-keyframe` only when an exact
  arrival is more important than motion freedom, preferably in a simple bridge.
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

Use `media_pipeline.py boundary-frames` only for an inherited chain, then persist
the decision with `set-boundary`. Record preparation with
`record-start-image-review`; after generation use `compare-start-frame` and
`record-start-frame-qc`. For inherited chains, also use
`record-boundary-analysis` and bind the next plan with `set-adaptive-story`.
Semantic pose, gaze, hands, props, framing, lighting, and emotion remain a
director judgment, not an automatic score.

Schema v10 blocks paid managed generation until the start image passes
preparation review. `FULL` serial production also requires the locked story and
adaptive plan. A cut/reset needs the previous shot accepted and a just-in-time
start provenance, but does not require boundary analysis. An inherited chain
additionally requires passed first-frame QC, boundary analysis, and the exact
recorded boundary frame.

Extract the end of the previous shot and the start of the next with
`media_pipeline.py`. Compare face, hair, costume, body and hand pose, gaze,
movement direction, prop and location state, camera axis, lens feel, exposure,
color, ambience, dialogue timing, and narrative emotion.

Repair in this order: edit point, J/L cut, common ambience, grade, minor speed
adjustment, cutaway, bridge shot, transition clip, then next-shot regeneration.
For native production audio, do not add replacement dialogue, ambience, Foley,
effects, or music by default. If required sound fails QC, simplify the sound
brief and regenerate the affected shot; external replacement is an explicitly
approved exception requiring a synchronization and lost-effects recovery plan.
Generate a four-second-or-longer transition when the live model minimum
requires it and trim locally to the intended one-to-three-second edit.

### 9. Finish and deliver

Require transcript, technical, lip-sync/manual, continuity, and user-review
gates before marking a shot final. Assemble only accepted versions. For
no-dialogue native sound and visible dialogue, keep the Seedance-rendered track
as the complete production sound and use `media_pipeline.py preserve-audio`
when a copy-only finishing pass is needed.
Do not add creative audio stems after generation by default; limit finishing to
technical checks, stream-preserving assembly, captions, and grade. Keep
`strip-audio` and `final-mix` for post-only routes or an explicitly approved
repair exception. Update actual credits, job IDs, retry counts, and the dashboard.

Deliver the final file or URL with duration, aspect, model ledger, approved
ceiling, reference-only arithmetic when available, actual credits, regenerated
shots, QC gaps, and any manual checks still required.

## Non-Negotiable Gates

- Route the task before initializing Sonol. Prefer official Marketing Studio and
  video-explainer workflows for their matching intents.
- Every paid generation needs an explicit spend boundary or the provider's own
  confirmation. Require the full requirements, story, board, asset, and
  continuity approval chain only when the selected profile is `FULL`.
- Never submit a managed shot without a provider-compiled, live-schema-validated
  `shot_grammar`, prepared start image, explicit audio route, and applicable
  `LIGHT`, `TARGETED`, or `FULL` gates.
- Never add video-call image references speculatively. Default to start-only;
  after a recorded failure, allow exactly one essential reference as a
  controlled A/B variable. Only a motivated transition with a load-bearing
  arrival composition may add an `end_image`.
- Inherit the previous boundary frame only for true continuity. Cuts and resets
  use just-in-time start images; they do not require boundary-frame analysis.
- In `FULL` serial work, do not pre-produce start frames beyond the next shot.
- Treat prompt length, shot splitting, performance cues, camera alternatives,
  and failure classification as advisory unless a contradiction, live schema,
  or paid-submission safety condition creates a real blocker.
- Never treat recorded dialogue or narration as fixed without its approved
  SHA-256 fingerprint in both the audio plan and adaptive story snapshot.
- Never accept a shot without comparing its actual first frame to the submitted
  start image.
- Never treat SSIM, PSNR, or lowest blur as an automatic creative approval.
- Prefer one primary camera move per controlled shot. Use a native multi-shot
  plan when several simple timed beats serve the intent; do not force every
  generation into one shot.
- Never insert web `@character`, `@style`, `@motion`, or `@audio` aliases into a CLI prompt unless the live CLI schema explicitly exposes alias binding.
- Never let Seedance inherit its current `generate_audio=true` default; compile an explicit shot audio route.
- Never equate Cinema 3.5 dialogue references with the proven Seedance V3 route
  without an approved pronunciation/lip-sync A/B.
- Never queue native audio without a complete compact sound brief covering
  dialogue state, ambience, synchronized effects, music state, and exclusions.
- Never discard or creatively overdub an accepted native production track
  unless the user approves an exceptional recovery plan.
- Never present recent-actual arithmetic as a live quote, fixed price, or hard spending guarantee.
- Never claim a lens number, camera preset, or prompt-soft instruction guarantees the rendered result.
- Never infer user approval from silence, model output, or an earlier version.
- Never automate Higgsfield web authentication. The user enters login, 2FA,
  captcha, passkey, and consent in the visible browser; do not inspect secrets.
- Never treat an attached Cinema image as a start frame until its visible role
  says `Start`; the web composer initially assigns selected assets `Reference`.
- In `TARGETED` or `FULL`, never generate from a required unlocked asset or an
  unapproved load-bearing shot board. `LIGHT` deliberately omits the full board.
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
