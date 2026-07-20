# Production workflow and recovery

## Contents

- Phase exits
- Resume protocol
- Failure recovery
- Deliverables

## Phase exits

### A. Requirements

Exit only when all required requirement fields are `CONFIRMED`, the user has
reviewed the consolidated specification, and `requirements_lock.status` is
`LOCKED`. A later requirement change unlocks it and invalidates cost approval.

### B. Script and plan

Exit only when the timecoded script fits the approved duration, every scene and
shot has a stable ID, shot durations sum to the target, and each shot has all
eight continuity fields. Keep one camera purpose, one primary action, and one
primary camera movement per shot. Produce one to three intent-first grammar
recommendations, record the selected `shot_grammar` and rationale, compile it
for the live provider contract, and require full grammar validation. Record
planned edit points.

### C. Cost

Exit only when the live CLI has quoted all three explicit scenarios and the
user has approved one scenario and credit ceiling. A scenario is a real set of
CLI arguments, not a multiplier applied to another quote. Store a canonical
fingerprint per shot. Approval binds to those fingerprints; any prompt, model,
duration, resolution, mode, reference, audio, or execution change clears quotes
and approval.

### D. Assets

Exit only when required character, location, prop, product, graphic, and key
frame assets have passed internal review and explicit user review. Korean-text
assets also require OCR evidence. Final video consumes only versioned
`LOCKED_FOR_VIDEO` assets.

### E. Shot board

Exit per shot only after start/end/reference choices, prompt, duration, model,
audio plan, continuity handoff, and provider-compiled cinematography grammar are
approved and locked. Board approval is version-specific. Any grammar change
returns the board to `DRAFT`, increments the generation version, and resets QC.
Store the approved provider call and its generated fingerprint as
`generation.execution = {"mode":"model|workflow","argv":[...],"fingerprint":"sha256:..."}`.

### F. Generation

Generate one dependent shot at a time. Record the exact job ID, arguments,
model contract snapshot, result path, and actual credits. Inspect before the
next shot that depends on its end state.

### G. QC and finish

Exit only after technical, transcript, lip-sync/manual, visual, cinematography,
continuity, and user review checks are passed or explicitly not applicable. Apply audio and
grade in a deterministic final timeline, then probe the exported file.

## Resume protocol

1. Run `sonol_higgsfield.py validate <production>`.
   If it reports an older schema version, run `sonol_higgsfield.py migrate <production>`
   explicitly, inspect the new draft grammars, and do not assume old approvals carry over.
2. Read `data/project.json`, then the newest events in `data/history.json`.
3. Refresh the live schema if the previous snapshot is from another session or
   the CLI version changed.
4. Reconcile completed provider jobs by job ID; do not resubmit an ambiguous
   job merely because a local wait was interrupted.
5. Resume from the earliest failed gate, not the latest-looking media file.
6. Refresh `dashboard/project-data.js` after reconciliation.

## Failure recovery

### Provider command rejected before submission

No credit-bearing job is known. Reinspect the current model/workflow contract,
correct flags, requote, and record the reason. Do not silently switch model.

### Submission returned a job ID but waiting failed

Use `higgsfield generate get <job_id>` or `wait <job_id>`. Treat a retry as a
new paid job and ask again if it could exceed the remaining ceiling.

### Media fails internal QC

Record which check failed and preserve the rejected version. Prefer edit-point,
audio, or local finishing repairs first. Regenerate only the affected shot or
bridge and increment its version.

### Cost quote requires uploading local media

The estimator blocks this by default because even a quote may upload input.
Explain the file and purpose, then rerun with `--allow-media-upload` only after
the user authorizes that upload.

### Credits are lower than the approved scenario

Stop before submission. Offer a newly quoted lower-cost scenario, shorter
scope, lower resolution, or delayed paid generation. Never translate credits
to cash unless Higgsfield provides an authoritative price for that account.

## Deliverables

- Final encoded video and `ffprobe` evidence.
- Timecoded script and shot ledger.
- Approved asset/version list.
- Model/workflow/job ledger and schema snapshot.
- Estimated, approved, and actual credits.
- QC ledger with automated evidence and manual gaps separated.
- Production dashboard and split JSON state.
