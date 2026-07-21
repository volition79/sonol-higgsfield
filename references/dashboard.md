# Dashboard contract

## Source of truth

`data/*.json` is authoritative. `dashboard/project-data.js` is a generated
read-only snapshot for opening the dashboard without a server. Never edit the
snapshot manually.

Split state files:

- `project.json`: project summary, stage, requirement lock, cost approval.
- `requirements.json`: field value, state, source, confirmer.
- `assets.json`: versioned images, characters, products, props, locations.
- `scenes.json`: ordered scene plan.
- `shots.json`: board, structured cinematography grammar, continuity, generation,
  provider-attempt observations, audio, and QC state.
- `costs.json`: reference-only arithmetic, actual-credit ledger, pending
  reconciliation, and ceiling-breach truth.
- `history.json`: append-only mutation events.

Atomic writes preserve a one-generation `.bak` file for recovery. The dashboard
does not contain credentials or OAuth state.

## Required views

- Project identity and final completion gauge.
- Total/grammar-ready/generated/QC/final shot metrics.
- Approval queue appropriate to the selected profile: requirements only in
  `FULL`, plus the project ceiling and applicable assets/shot boards.
- Active interlocks and recoverable blockers, including ambiguous submissions
  and known jobs whose remote status is temporarily unknown.
- Shot table with board, grammar and generation state, model, QC count, version.
- Per-shot grammar cards with intent, core camera choices, rationale, provider,
  support level, and the five compact director-intelligence summaries.
- Asset version/lock/OCR state.
- Reference-only arithmetic coverage, actual credits, pending reconciliation,
  approved project ceiling, and independent ceiling-breach status.
- Reverse chronological history.

## Running

Static review:

```bash
python3 scripts/sonol_higgsfield.py dashboard <production>
```

Interactive local review:

```bash
python3 scripts/dashboard_server.py <production> --port 8765
```

Open the exact printed URL including `?token=...`. The server binds only to
loopback. Use `--port 0` in tests or when an automatically selected free port is
preferred.

## Action behavior

The browser may submit only user-authority actions. Asset and shot actions carry
their displayed version; the server rejects stale approvals after a concurrent
edit. All accepted actions pass through `project_state.py`, append history, and
refresh the snapshot.

## Design direction

The bundled template follows an industrial production-control aesthetic: light
chassis panels, dark rails, safety orange/red, tactile buttons, status LEDs,
monospace instrumentation, strong hierarchy, and responsive single-column
collapse. Preserve accessibility, keyboard-native buttons, readable contrast,
mobile layout, and escaped state content when extending it.
