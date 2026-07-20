# Approval, state, and cost policy

## Authority

The agent may draft, inspect, estimate, and pass internal QC. Only the user may:

- lock the consolidated requirements;
- approve a cost scenario and maximum credits;
- approve or lock an asset version;
- approve or lock a shot-board version;
- pass `user_review` QC.

Silence, previous approval, dashboard display, generated output, and inferred
preferences are not approval.

## Requirement gate

All fourteen required fields must be `CONFIRMED`. Locking records actor, time,
and version. Any later change unlocks requirements and invalidates cost
approval, because scope and price may have changed.

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

Generation cannot queue until requirements and cost are approved, the shot
board is locked, every required asset is locked, and all eight continuity
fields are filled.

## Generation and QC gate

`PLANNED -> READY -> QUEUED -> GENERATING -> GENERATED`

Failures return to `READY` with retry count. A shot reaches `FINAL_COMPLETE`
only after technical, transcript, lip-sync/manual, visual, continuity, and user
review checks are `PASSED` or `NOT_APPLICABLE`. Korean pronunciation remains a
separate recorded check when relevant.

## Cost policy

- Quote economy, recommended, and highest-quality using exact live arguments.
- Show per-shot and total credits, provider/model, duration, resolution, and
  any media that a quote would upload.
- Store approved scenario and maximum credits separately from estimates.
- Bind approval to the normalized per-shot execution fingerprint and reject
  quote/execution drift before any provider submission.
- Requote after model, duration, resolution, mode, or reference changes.
- Seek renewed approval when a fallback can exceed the ceiling.
- Record job IDs and actual credits after each job.
- Reject recording actual cost that would exceed the approved ceiling; stop and
  reconcile provider transactions with the user.
- Never invent cash conversion for unknown, free, or promotional credits.

## Dashboard action safety

Interactive approval actions bind to `127.0.0.1`, require the random URL token,
and include the asset/shot version. The server rejects stale versions. Static
HTML snapshots are read-only and cannot mutate state.

## Secrets and privacy

Do not place OAuth tokens, authorization headers, cookies, email, credentials,
unredacted private URLs, or private media in dashboard state or schema files.
Ask before uploading any local media to a remote quote or generation command.
