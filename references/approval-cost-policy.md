# Approval, state, and cost policy

## Authority

The agent may draft, inspect, estimate, and pass internal QC. Only the user may:

- lock the consolidated requirements;
- approve one project credit ceiling and acknowledge execution without exact live quotes;
- approve or lock an asset version;
- approve or lock a shot-board version;
- pass `user_review` QC.

Silence, previous approval, dashboard display, generated output, and inferred
preferences are not approval.

## Requirement gate

All fourteen required fields must be `CONFIRMED`. Locking records actor, time,
and version. A later change unlocks requirements and invalidates reference-only
arithmetic. The approved project ceiling remains a total limit; generation is
still blocked while requirements are unlocked.

## Asset gate

Valid forward flow:

`DRAFT -> INTERNAL_QC_PASSED -> USER_REVIEW -> USER_APPROVED -> LOCKED_FOR_VIDEO`

Revision returns through `REVISION_REQUESTED -> DRAFT` and increments version.
Changing content or production metadata after review also invalidates approval.
An asset containing Korean text cannot lock until OCR is `PASSED`; visual review
is still required.

## Shot-board gate

The board uses the same approval flow and a version number. A planning change
invalidates approval, clears provider job/result fields, resets QC, and removes
the version from the final timeline.

Generation cannot queue until requirements and the project ceiling are
approved, the shot board is locked, every required asset is locked, and all
eight continuity fields, boundary strategy, and audio route are resolved.

## Generation and QC gate

Normal provider lifecycle:

`PLANNED -> READY -> SUBMITTING -> SUBMITTED -> QUEUED/RUNNING -> PROVIDER_COMPLETED -> GENERATED`

`SUBMISSION_AMBIGUOUS` represents an unknown create outcome with no trusted job
ID. `REMOTE_UNKNOWN` represents a known job whose latest observation failed.
Neither state permits an automatic duplicate submission. Submission and waiting
are separate operations, and the job ID is persisted before any long wait.

Pre-submit gates run only when creating the durable `SUBMITTING` attempt. Once a
provider call may have happened, contract drift, changed plans, an unlocked
requirement, or a new ceiling cannot block provider observations, completed
media, or actual-cost records. Ambiguity may be closed as `NOT_SUBMITTED` with
evidence, or as `ABANDONED_RISK_ACCEPTED` only by the user with a recorded reason.

Confirmed remote failures may return to `READY` with retry count. A shot reaches `FINAL_COMPLETE`
only after technical, transcript, lip-sync/manual, visual, continuity, and user
review checks are `PASSED` or `NOT_APPLICABLE`. Korean pronunciation remains a
separate recorded check when relevant.

## Credit policy

- Never call `higgsfield generate cost`; remove three-scenario and whole-project live quoting.
- Ask the user to approve one total project credit ceiling after requirements lock.
- Explain that without a live quote a single submitted job can exceed the
  remaining ceiling; the ceiling is a preflight stop, not a provider-side cap.
- Optionally calculate a reference value from recent matching actual jobs only:
  mean observed credits per second times duration times planned attempts.
- Match provider, model/workflow mode, resolution, and generated-audio flag.
  Report `UNAVAILABLE` when no matching sample exists; do not invent coefficients.
- Label arithmetic as `REFERENCE_ONLY`, never a quote, exact price, or guarantee.
- Check current account credits and remaining approved ceiling before every job.
- Stop for renewed approval when the ceiling is exhausted or the user raises it.
- Record job IDs, execution profile, and actual credits after each job so later
  arithmetic can use evidence.
- Always record provider-reported actual cost, including an amount above the
  approved ceiling. Set `ceiling_breach=true` separately and stop new jobs.
- If a terminal response has no credit field, keep a pending reconciliation.
  An account-balance delta is evidence, not an automatic exact charge when
  concurrent jobs or account adjustments may exist.
- Pending cost reconciliation pauses new jobs by default but is not a permanent
  lock: `--acknowledge-pending-costs` records explicit risk acceptance on the
  next submission attempt. A ceiling breach remains a hard pre-submit stop.
- Never invent cash conversion for unknown, free, or promotional credits.

## Dashboard action safety

Interactive approval actions bind to `127.0.0.1`, require the random URL token,
and include the asset/shot version. The server rejects stale versions. Static
HTML snapshots are read-only and cannot mutate state.

## Secrets and privacy

Do not place OAuth tokens, authorization headers, cookies, email, credentials,
unredacted private URLs, or private media in dashboard state or schema files.
Ask before uploading any local media to a remote generation command.
