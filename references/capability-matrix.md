# Capability and implementation matrix

Use this matrix to distinguish the three Higgsfield surfaces from the local
orchestration supplied by this skill.

| Production function | Higgsfield CLI / backend | Official Higgsfield Skills | MCP | sonol-higgsfield |
|---|---|---|---|---|
| Account, workspace, credits | Native CLI | Preflight guidance | Possible; inspect schema | Redacted preflight and budget gate |
| Model/workflow discovery | Native live schema | Routing recommendations | Only if tools visible | Snapshot, drift detection, contract selection |
| Exact generation cost | Native `generate cost`, intentionally unused | Provider guidance may recommend quotes | Unknown until schema visible | No live quote; recent-actual arithmetic plus project ceiling |
| Image generation/reference inputs | Native models | Model routing | Likely, not assumed | Versioned asset plan, OCR and user lock |
| Video generation/start/end/multi-reference | Native models including current Seedance contracts | Seedance routing | Likely, not assumed | Per-shot board, reference packing, job ledger |
| Provider job wait/get/list | Native CLI | Execution guidance | Unknown until schema visible | Resume protocol and deterministic job IDs |
| Native generated audio | Model-dependent | Routing guidance | Model-dependent | Shot-level audio classification |
| Voice change | Live workflow exists | Route when requested | Unknown until schema visible | Not used as cleanup or stem separation |
| TTS/audio/music | Native current audio models | Model routing | Unknown until schema visible | ElevenLabs V3 dialogue master, narration plan, external final mix |
| Speech transcript | Current data models | Optional QC route | Unknown until schema visible | Evidence ledger; not treated as pronunciation proof |
| Requirements interview | Not a backend function | Partial conversational guidance | No evidence | Four-state interview, explicit user lock |
| Script/timecode/shot decomposition | Not a provider contract | Partial workflow guidance | No evidence | Required durable scene/shot state |
| Professional film grammar catalog | Camera controls and Cinema fields cover a subset | Prompt/routing examples | Exact tools must be visible | 15 axes, 148 source-linked techniques, aliases, failures and QC |
| Intent-to-technique recommendation | Not a deterministic backend feature | Conversational guidance | No evidence | Deterministic 1–3 options with plain rationale and genre/platform priors |
| Provider-specific camera compilation | Cinema 3.5 has structured style/light/grade; other models accept prompts/references | Model-specific guidance | Only after live schema | Native/reference/prompt/web/post support classifier and live-schema validation |
| Camera-technique compliance scoring | No deterministic guarantee | Manual inspection | No proven score | Conflict checks before generation and explicit cinematography QC after generation |
| Asset and shot approvals | Not a provider contract | Conversational gates only | No evidence | Versioned state machines and user-only authority |
| Cross-shot continuity | References help generation | Prompt/reference advice | No semantic automatic score confirmed | Four boundary strategies, automatic final-0.5s blur selection, required semantic analysis record, first-frame QC, and sequential/JIT state gates |
| Korean on-screen text check | Image model may render text | Model recommendation | No automatic checker confirmed | Tesseract `kor+eng` text-presence gate plus review |
| Korean pronunciation | TTS/transcript tools help | Audio routing advice | No automatic score confirmed | Pronunciation sheet, audition, transcript and manual listen |
| Objective lip-sync scoring | No observed scoring contract | Manual review required | No evidence | `MANUAL_REQUIRED`/pass/fail gate; no invented score |
| Dialogue stem separation | No observed dedicated contract | No proven automation | No evidence | Explicit unsupported boundary; integrate another tool if authorized |
| FFmpeg finishing | Not provider-side generation | May recommend local FFmpeg | No | Probe, frames, strip audio, external-stem final mix, trim, concat, stretch, mux |
| Selective regeneration | CLI can resubmit jobs | Workflow recommendation | Tool-dependent | Version/reset/retry state and repair ladder |
| Local production dashboard | No | No | No | Bootstrap/Vanilla industrial dashboard, split JSON, history |

## Implementation status

### Fully implemented locally

- Durable split JSON production state with atomic writes and backup.
- Four-state requirements interview and explicit user lock.
- Versioned asset and shot approval machines.
- Paid-generation interlocks, project ceiling preflight, and reconciliation.
- Scene, shot, eight-field continuity, boundary, reference, audio, QC, and job ledgers.
- Versioned `shot_grammar` state with approval invalidation and generation gate.
- Source-linked 148-technique catalog, 13 genre and 7 platform profiles.
- Deterministic recommender, provider compiler, conflict validator, live enum,
  freshness, and contract-fingerprint checks.
- Recent matching actual-credit arithmetic with explicit `REFERENCE_ONLY` status.
- Guarded paid shot runner with live balance, execution fingerprint,
  re-fetched provider contract, prompt/native-param, ceiling, upload, strict
  job-ID, and actual-cost reconciliation checks.
- Redacted live CLI/model/workflow/account/MCP preflight.
- Korean/English OCR text-presence checker.
- FFmpeg/ffprobe finishing helpers.
- Schema v5 story-anchor, adaptive-analysis, first-frame-QC, JIT provenance,
  and recorded-audio SHA-256 gates.
- Responsive local dashboard with random token and stale-version protection.
- Dashboard grammar readiness, rationale, provider, and support-level views.
- Unit, CLI, HTTP, policy, state persistence, and helper tests.

### Implemented as live provider routing

- Image/video/audio/TTS/transcript/voice-change calls are deliberately routed to
  the authenticated CLI after contract inspection and approval. The skill does
  not duplicate provider APIs or store OAuth tokens.
- MCP may replace a CLI call only after the current session exposes the exact
  tool schema. An MCP endpoint does not imply parity with every CLI command.

### Deliberately manual or conditional

- Visual aesthetics, face/costume/prop continuity, lip sync, pronunciation, and
  edit quality require human review unless a concrete checker is added later.
- Dialogue/music/effects separation requires a separately authorized stem tool.
- Soul training is optional, consent-sensitive, account/plan-dependent, and not
  a prerequisite when approved reference images are sufficient.
- Paid smoke generation is not part of installation testing; it requires the
  user's project-ceiling approval and unpriced-job risk acknowledgement.

## Feasibility conclusion

The production workflow is feasible with the CLI as the canonical provider
surface and this skill as the local orchestration layer. There is no structural
blocker to requirements, assets, shots, approvals, cost control, generation,
audio routing, selective repair, finishing, or dashboard operation. The hard
parts are quality-control judgment and identity/audio consistency, not missing
state machinery. Treat them as explicit manual/conditional gates instead of
claiming unsupported automation.
