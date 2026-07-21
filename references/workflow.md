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
`LOCKED`. A later requirement change unlocks it and invalidates reference-only arithmetic.

### B. Script and plan

Exit only when the timecoded script fits the approved duration, every scene and
shot has a stable ID, shot durations sum to the target, and each shot has all
eight continuity fields. Keep one camera purpose, one primary action, and one
primary camera movement per shot. Produce one to three intent-first grammar
recommendations, record the selected `shot_grammar` and rationale, compile it
for the live provider contract, and require full grammar validation. Record
planned edit points and one of the four incoming boundary strategies.
The user must also lock a versioned, non-empty `story_contract.anchor_beats`
list before paid generation.

### C. Credit ceiling

Exit only when the user has approved one total project credit ceiling and
acknowledged that no exact provider quote will be used. Optional arithmetic is
reference-only and comes from recent matching actual jobs. An execution-profile
change invalidates that arithmetic but does not silently raise or remove the
user's total ceiling.

### D. Assets

Exit only when required character, location, prop, product, and graphic assets
have passed internal review and explicit user review, plus the **first shot's
start frame only** — later start frames are composed just-in-time during
generation (chained shots inherit the previous boundary frame; cuts and resets
compose a new one from the locked references and current story state).
Korean-text assets also require OCR evidence. Final video consumes only
versioned `LOCKED_FOR_VIDEO` assets.

### E. Shot board

Exit per shot only after boundary strategy, the single start image (plus end
image only for a motivated transition), prompt, duration, model, audio plan,
continuity handoff, and provider-compiled cinematography grammar are approved
and locked. Board a shot only when its start image exists — for chained shots
that means after the previous shot is accepted. Board approval is version-specific. Any grammar change
returns the board to `DRAFT`, increments the generation version, and resets QC.
Store the approved provider call and its generated fingerprint as
`generation.execution = {"mode":"model|workflow","argv":[...],"fingerprint":"sha256:..."}`.

### F. Generation

Generate one dependent shot at a time. Record the exact job ID, arguments,
model contract snapshot, result path, and actual credits. Inspect before the
next shot that depends on its end state: compare the rendered first frame to
the submitted start image, score eight boundary candidates from the final half
second, record the selected frame and semantic observations, and bind the next
shot to that analysis before compiling. Schema v6 blocks out-of-order dependent
generation and stale or pre-produced cut/reset start images.

### G. QC and finish

Exit only after technical, transcript, lip-sync/manual, visual, cinematography,
continuity, and user review checks are passed or explicitly not applicable. For
visible dialogue, preserve the accepted native production track and do not add
creative stems by default. Apply external audio only to its authorized
post-only route or an approved repair exception, then grade and probe the export.

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
correct flags and record the reason. Do not silently switch model.

### Submission returned a job ID but waiting failed

Use `higgsfield generate get <job_id>` or `wait <job_id>`. Treat a retry as a
new paid job and ask again if it could exceed the remaining ceiling.

### Media fails internal QC

Record which check failed and preserve the rejected version. For visible
dialogue audio failures, simplify the sound brief and regenerate the affected
shot before proposing an exceptional external replacement. For post-only
routes, prefer authorized local finishing repairs. Regenerate only the affected
shot or bridge and increment its version.

### Credits are exhausted or reference arithmetic exceeds capacity

Stop before submission. Offer a shorter scope, lower resolution, fewer
candidates, a renewed project ceiling, or delayed paid generation. Never translate credits
to cash unless Higgsfield provides an authoritative price for that account.

## Deliverables

- Final encoded video and `ffprobe` evidence.
- Timecoded script and shot ledger.
- Approved asset/version list.
- Model/workflow/job ledger and schema snapshot.
- Reference-only arithmetic, approved ceiling, and actual credits.
- QC ledger with automated evidence and manual gaps separated.
- Production dashboard and split JSON state.
