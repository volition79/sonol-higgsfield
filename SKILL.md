---
name: sonol-higgsfield
description: Orchestrate approval-gated Higgsfield video productions from requirements interview through storyboard, asset and shot planning, live CLI schema and credit checks, Seedance generation, voice routing, continuity and Korean-text QC, FFmpeg finishing, and a persistent local production dashboard. Use when a user asks to plan, generate, manage, review, resume, or finish a multi-shot Higgsfield film, ad, story, campaign, or narrated video with controlled cost, reusable characters, references, audio, approvals, and selective regeneration.
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
   - The user's available credits and approved budget cover the next paid job.
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
generation parameters, and expected splice points before generation.

### 4. Discover the live model contract and estimate cost

Read [model-routing.md](references/model-routing.md). Always run the unfiltered
model/workflow lists and then inspect the selected contract. Never copy a stale
enum from this skill into a paid command.

For `seedance_2_0` or `seedance_2_0_mini`, read
[seedance-2-0-production.md](references/seedance-2-0-production.md). Default to
one controlled shot, 720p prototypes no longer than eight seconds, and explicit
native-audio off. Use experimental timecoded multi-shot only after the user
accepts whole-clip regeneration risk.

Record cost arguments on each planned shot, then run:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/estimate_costs.py" <production>
```

Present economy, recommended, and highest-quality scenarios. Require explicit
user approval of a credit ceiling before a paid generation. Never infer a cash
or KRW value for free, promotional, or unknown-price credits.

### 5. Create and approve animatic and reference assets

Use a low-cost image model for the animatic and a quality/identity model for
final references. Use GPT Image for images containing important Korean text,
then run `ocr_check.py` before user review. Treat OCR as a gate, not proof of
visual quality.

Move each asset through:

`DRAFT -> INTERNAL_QC_PASSED -> USER_REVIEW -> USER_APPROVED -> LOCKED_FOR_VIDEO`

Only the user may approve. If content or metadata changes, increment its
version and invalidate the previous approval. Do not queue a final video from
an asset that is not `LOCKED_FOR_VIDEO`.

### 6. Generate one bounded shot at a time

Prefer Seedance 2.0 for serious general video. Respect the live reference and
duration limits. Pack only references that materially control the shot; split
the shot when the reference budget or state transition becomes ambiguous.

Submit with `--wait --json` only after the guarded runner has re-fetched the
selected contract and matched the execution arguments to the approved quote.
If a wait is interrupted before a job ID is returned, do not retry blindly;
reconcile provider history first because the original job may still exist.
Never silently replace the selected model. If the preferred contract fails
twice for the same reason, change the prompt, reference package, duration, or
model with a recorded rationale and renewed cost approval when needed.

After storing the approved model/workflow arguments in the shot's `execution`
object and moving it to `READY`, use the guarded paid runner:

```bash
python3 "$SONOL_HIGGSFIELD_SKILL/scripts/run_shot.py" \
  <production> <shot_id> --execute-paid
```

Add `--authorize-local-upload` only when the user approved the local reference
files. The runner rechecks gates, exact per-shot estimate, remaining ceiling,
and current account credits before submission; it records the job without
persisting private result URLs.

### 7. Inspect immediately and route audio conditionally

Inspect every completed shot before generating the next dependent shot. Read
[audio-qc.md](references/audio-qc.md) and classify the shot:

- Dialogue with acceptable original voice: retain it.
- Dialogue requiring a consistent voice: use the live `voice_change` contract
  or a separately authorized ElevenLabs path.
- Narration without visible speech: generate TTS separately.
- Non-dialogue: retain acceptable ambience; do not run voice change.
- Silence/music-led: construct audio only in finishing.

Use `speech2text` for transcript evidence when available. Use FFmpeg for
extraction, trimming, time stretch, muxing, and assembly. Do not describe
speech separation, lip-sync scoring, or character continuity as automatic
unless a concrete provider or deterministic checker produced evidence.

### 8. Verify continuity and repair selectively

Extract the end of the previous shot and the start of the next with
`media_pipeline.py`. Compare face, hair, costume, body and hand pose, gaze,
movement direction, prop and location state, camera axis, lens feel, exposure,
color, ambience, dialogue timing, and narrative emotion.

Repair in this order: edit point, J/L cut, common ambience, grade, minor speed
adjustment, cutaway, bridge shot, transition clip, then next-shot regeneration.
Generate a four-second-or-longer transition when the live model minimum
requires it and trim locally to the intended one-to-three-second edit.

### 9. Finish and deliver

Require transcript, technical, lip-sync/manual, continuity, and user-review
gates before marking a shot final. Assemble only accepted versions. Apply
dialogue replacement before ambience, effects, music, ducking, captions, and
final grade. Update actual credits, job IDs, retry counts, and the dashboard.

Deliver the final file or URL with duration, aspect, model ledger, approved
cost versus actual cost, regenerated shots, QC gaps, and any manual checks still
required.

## Non-Negotiable Gates

- Never start paid generation before requirements and budget are user-approved.
- Never approve or queue a shot without a complete provider-compiled and validated `shot_grammar`.
- Never combine multiple primary camera moves unless the user accepts an experimental A/B test.
- Never insert web `@character`, `@style`, `@motion`, or `@audio` aliases into a CLI prompt unless the live CLI schema explicitly exposes alias binding.
- Never let Seedance inherit its current `generate_audio=true` default; compile an explicit shot audio route.
- Never execute a paid command whose normalized argument fingerprint differs from the approved per-shot quote.
- Never claim a lens number, camera preset, or prompt-soft instruction guarantees the rendered result.
- Never infer user approval from silence, model output, or an earlier version.
- Never generate final video from an unlocked asset or unapproved shot board.
- Never allow a model fallback to increase cost without renewed approval.
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

Use a real paid smoke generation only after the user approves its quoted cost.
