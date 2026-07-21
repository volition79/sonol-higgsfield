# Production workflow and recovery

## Contents

- Phase exits
- Resume protocol
- Failure recovery
- Deliverables

## Phase exits

### A. Requirements

For `FULL`, exit only when all required requirement fields are `CONFIRMED`, the user has
reviewed the consolidated specification, and `requirements_lock.status` is
`LOCKED`. A later requirement change unlocks it and invalidates reference-only
arithmetic. `TARGETED` and `LIGHT` skip this phase exit and resolve only their
load-bearing inputs.

### B. Script and plan

For `FULL`, exit only when the timecoded script fits the approved duration, every scene and
shot has a stable ID, shot durations sum to the target, and each shot has all
eight continuity fields. Keep one camera purpose, one primary action, and one
primary camera movement per shot. Produce one to three intent-first grammar
recommendations, record the selected `shot_grammar` and rationale, compile it
for the live provider contract, and require full grammar validation. Record
planned edit points and one of the four incoming boundary strategies.
The user must also lock a versioned, non-empty `story_contract.anchor_beats`
list before paid generation. `TARGETED` and `LIGHT` use only the applicable
subset and may choose routed native multi-shot instead of separate shots.

### C. Credit ceiling

Exit only when the user has approved one total project credit ceiling and
acknowledged that no exact provider quote will be used. Optional arithmetic is
reference-only and comes from recent matching actual jobs. An execution-profile
change invalidates that arithmetic but does not silently raise or remove the
user's total ceiling.

### D. Assets

In `FULL`, exit only when required character, location, prop, product, and graphic assets
have passed internal review and explicit user review, plus the **first shot's
start frame only** — later start frames are composed just-in-time during
generation (true continuous chains inherit the previous boundary frame; cuts and resets
compose a new one from the locked references and current story state).
Korean-text assets also require OCR evidence. Final video consumes only
versioned `LOCKED_FOR_VIDEO` assets.

### E. Shot board

In `TARGETED` or `FULL`, exit per load-bearing shot only after boundary strategy, the reviewed start image, selected
image-input profile (start-only by default; one evidenced essential reference
or motivated-transition end image only as an exception), prompt, duration, model, audio plan,
continuity handoff, a complete compact brief for native production sound, and
provider-compiled cinematography grammar are approved
and locked. Board a shot only when its start image exists — for chained shots
that means after the previous shot is accepted. Board approval is version-specific. Any grammar change
returns the board to `DRAFT`, increments the generation version, and resets QC.
Store the approved provider call and its generated fingerprint as
`generation.execution = {"mode":"model|workflow","argv":[...],"fingerprint":"sha256:..."}`.

### F. Generation

Generate one dependent provider job at a time; that job may contain one
controlled shot or a routed native multi-shot sequence. Persist a submission attempt before the
provider call, submit without waiting, and store the exact job ID immediately.
Observe that known job in a separate reconcile command. Record the arguments,
model contract snapshot, result path, provider observations, and actual credits. Inspect before the
next shot that depends on its end state: compare the rendered first frame to
the submitted start image, score eight boundary candidates from the final half
second, record the director-selected frame and semantic observations, and bind
the next shot to that analysis only when the frame is inherited. Schema v9 also
blocks paid generation without start-image preparation review. Cut/reset shots
need accepted prior footage and a JIT start image, but not boundary analysis.

### G. QC and finish

Exit only after technical, transcript, lip-sync/manual, visual, cinematography,
continuity, and user review checks are passed or explicitly not applicable. For
native sound, preserve the accepted production track and do not add creative
stems by default. Apply external audio only to off-screen narration, a
user-approved post-only route, or an approved repair exception, then grade and
probe the export.

## Resume protocol

1. Run `sonol_higgsfield.py validate <production>`.
   If it reports an older schema version, run `sonol_higgsfield.py migrate <production>`
   explicitly, inspect the new draft grammars, and do not assume old approvals carry over.
2. Read `data/project.json`, then the newest events in `data/history.json`.
3. Refresh the live schema if the previous snapshot is from another session or
   the CLI version changed.
4. Reconcile active attempts by job ID. With no ID, allow automatic binding only
   when provider history has one fingerprint/time-window match; otherwise use
   manual `--job-id`. Do not resubmit merely because a local process stopped.
5. Resume from the earliest failed gate, not the latest-looking media file.
6. Refresh `dashboard/project-data.js` after reconciliation.

## Failure recovery

### Submission ended without a recognized job ID

The attempt stays `SUBMISSION_AMBIGUOUS`. Search provider history using the
stored provider, prompt hash, stable arguments, and submission time. Bind one
unambiguous match; if several match, require an exact `--job-id`. Return to a
retryable state only after evidence confirms `NOT_SUBMITTED`, or after the user
explicitly accepts abandonment and possible duplicate-charge risk.

### Submission returned a job ID but observation failed

Keep the ID and set `REMOTE_UNKNOWN`. Use `run_shot.py --reconcile`, optionally
with `--wait`, against that same ID. Queue duration is not a local failure and
does not justify a new paid submission.

### Provider completed after plans or gates changed

Record `PROVIDER_COMPLETED`, the result, and any actual cost without re-running
mutable pre-submit gates. The ceiling and board policy control new submissions;
they cannot rewrite or conceal provider truth that already occurred.

### Provider response omitted actual credits

Keep the result usable and add a pending ledger entry. Account balance before
and after the attempt may be shown as a candidate only, because concurrent jobs,
free credits, or adjustments can contaminate the delta. Record confirmed credits
with `--credits`. Pending entries pause new submissions by default, but the user
may explicitly continue with `--acknowledge-pending-costs`; that decision is
persisted on the new attempt rather than creating a permanent deadlock.

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
