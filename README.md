# Sonol Higgsfield

[English](README.md) | [한국어](README.ko.md)

Turn a video idea into a controlled, reviewable Higgsfield production—not a pile
of disconnected generation attempts.

Sonol Higgsfield is an agent skill for Codex CLI, Claude Code, and compatible
Agent Skills hosts. It routes small work to the lightest official path and gives
your agent a managed production workflow for multi-job films, stories, and campaigns: requirements, storyboard,
cinematography, references, budget approval, generation, continuity checks,
audio routing, selective repair, finishing, and delivery.

> This is a community production skill built around the official Higgsfield
> CLI. It is not an official Higgsfield product.

## Install automatically

Install globally for both Codex CLI and Claude Code:

<!-- markdownlint-disable MD013 -->

```bash
npx --yes skills@latest add volition79/sonol-higgsfield --skill sonol-higgsfield --global --agent codex --agent claude-code --copy --yes
```

Install for only one agent:

```bash
# Codex CLI
npx --yes skills@latest add volition79/sonol-higgsfield --skill sonol-higgsfield --global --agent codex --copy --yes

# Claude Code
npx --yes skills@latest add volition79/sonol-higgsfield --skill sonol-higgsfield --global --agent claude-code --copy --yes
```

<!-- markdownlint-enable MD013 -->

The repository is recognized by the Skills CLI as one valid skill named
`sonol-higgsfield`. The two-agent command has been tested in an isolated home
directory and installs copies for both hosts. Start a new Codex or Claude Code
session after installation so the agent discovers the skill.

Requirements for automatic installation:

- Node.js 18 or newer with `npx`
- Git
- Codex CLI and/or Claude Code

## Complete runtime setup

Installing the skill teaches the agent the workflow. The official Higgsfield
CLI and account authorization are separate prerequisites.

```bash
# Cross-platform Higgsfield CLI installation
npm install -g @higgsfield/cli

# Browser/device authorization
higgsfield auth login

# Select a billing workspace when required
higgsfield workspace list
higgsfield workspace set <workspace_id>

# Confirm the active account and workspace
higgsfield account status
higgsfield workspace status
```

For the complete production workflow, also provide:

- Python 3.10+; Python 3.12 is the verified development runtime
- FFmpeg and FFprobe for inspection, trimming, audio, transitions, and assembly
- Tesseract with Korean (`kor`) language data when Korean text OCR is required
- An active Higgsfield account, selected workspace, and enough credits for the
  generation you approve
- An ElevenLabs API key and approved voice IDs when the skill must generate a
  new visible-dialogue reference or external narration; not required when an
  authorized finished reference file is already supplied
- Optional Higgsfield MCP access; the skill treats the live CLI schema as the
  canonical execution contract and does not require MCP

Official setup references:

- [Higgsfield CLI](https://higgsfield.ai/cli)
- [Higgsfield CLI source and platform-specific install options](https://github.com/higgsfield-ai/cli)
- [Skills CLI](https://github.com/vercel-labs/skills)

## Why use it?

### Use only as much production system as the job needs

The router chooses a quick official clip, a native Seedance multi-shot clip, a
controlled precision shot, a serial Sonol production, or an official dedicated
workflow. Marketing Studio remains first choice for ads and the official video
explainer remains first choice for explainers. Approval depth is `LIGHT`,
`TARGETED`, or `FULL`; the full interview and board are reserved for expensive,
multi-job, or long productions.

### Make a film, not isolated clips

The skill carries story state, characters, locations, props, camera direction,
audio, and edit handoffs from shot to shot. A director boundary decision chooses
whether to inherit the accepted previous last frame, build a start/end bridge,
make an editorial cut, or reset the scene. It never forces morphing across a cut.

### Turn plain intent into film language

You can describe the result in ordinary language—“make the reveal feel uneasy”
or “follow her without losing spatial clarity.” The skill searches a catalog of
148 film techniques, proposes explainable camera and directing alternatives,
and compiles the chosen grammar for the selected live provider.

### Keep credit planning fast

The agent checks the live model contract, account credits, workspace, reference
limits, and one user-approved project ceiling. It does not make slow live cost
calls or build three quote scenarios. When matching actual jobs exist, it shows
clearly labeled reference arithmetic from observed credits per second; otherwise
it says the estimate is unavailable. Silence never counts as approval.

### Keep Seedance 2.0 adaptive

The skill chooses one controlled shot when dialogue, acting, product interaction,
or camera precision is load-bearing. Two to four simple timecoded beats may use
one native multi-shot generation when whole-clip regeneration is acceptable.
Prompts are minimum-sufficient rather than universally short: the load-bearing
instruction comes early and word ranges remain advisory.

Each paid clip receives one start image. The first clip is composed up front;
later clips inherit an accepted boundary frame only for true continuous action;
other transitions compose a fresh frame just in time. Start-only is the default. One
essential image reference is allowed only after a recorded failure and a
one-variable A/B test; an end image is reserved for simple motivated transitions
where exact arrival matters. FFmpeg persists eight candidates from the final
0.5 seconds and recommends the least blurred, while the director may select a
better narrative frame with a recorded reason. Schema v9 requires start-image
preflight for aspect, collage/labels, subject readability, first-action
compatibility, and off-frame reveal risk. Optional SSIM/PSNR comparison is
technical evidence, not automatic approval. Boundary analysis is required for
inherited continuity, not for an editorial cut or scene reset. Full serial work
also locks story anchors and prior user acceptance.
The prompt exit state remains the default; an end image constrains only a simple
exact-arrival transition and does not guarantee pixel-identical arrival.

The built-in director aids add five small advisory tools: visible acting cues,
two camera alternatives, prompt lint, explainable shot-complexity scoring, and
attempt-history failure diagnosis. They never silently invent action, split a
shot, choose a camera, or spend credits.

### Resume long productions safely

A local production directory and dashboard preserve requirements, versions,
approvals, jobs, costs, QC state, and history. A later session can resume from
the recorded state instead of reconstructing the project from chat memory.
Paid submission is separated from queue waiting: the skill saves a durable
attempt first, binds the job ID immediately, and observes the same job later.
An interrupted create becomes an explicit ambiguous attempt instead of a blind
retry; an interrupted wait keeps the known job ID. Provider completion and
actual cost are always recorded even if local policies changed afterward.
Missing credits remain reconcilable evidence, while above-ceiling actual usage
is preserved and flagged rather than rejected from the ledger.

### Repair only what failed

The workflow favors edit-point repair, J/L cuts, ambience, grading, speed
adjustment, cutaways, bridge shots, and transitions before expensive
regeneration. When regeneration is needed, it targets the affected shot rather
than restarting the entire film.

### Treat Korean text and audio as production concerns

Korean text assets can pass through OCR evidence and human visual review.
Visible dialogue starts from a clean locked ElevenLabs V3 conditioning reference.
Before generation, the agent records the intended voice, ambience, synchronized
effects, music state, and excluded sounds in one compact Seedance brief. Seedance
then generates picture and complete production sound together; a QC-passed native
track is preserved without creative post-production overdubs. This is also the
default for no-dialogue shots that need ambience, effects, or music. Post-only
sound rebuilding is a user-approved repair exception; off-screen narration keeps
its separate finishing route. An ElevenLabs V3 file is conditioning guidance,
not a promise of sample-identical timing, timbre, or fidelity.

## Production flow

1. Route the intent to quick clip, native multi-shot, controlled shot, serial production, or an official dedicated workflow.
2. For a managed route, choose `LIGHT`, `TARGETED`, or `FULL` approval depth and create state only when useful.
3. Write the minimum necessary timecoded script, scenes, assets, and shot plan.
4. Choose and validate film grammar for each shot.
5. Inspect the live Higgsfield schema and credits, then approve a project ceiling.
6. Approve animatics and references.
7. Generate one recoverable provider job at a time; a simple job may contain native multi-shot beats.
8. Review continuity, audio, text, and technical quality immediately.
9. Repair or selectively regenerate only the affected material.
10. Assemble, finish, audit, and deliver the approved versions.

## Start using it

After opening a new agent session, ask naturally:

> Use sonol-higgsfield to plan a 60-second cinematic brand film. Interview me
> first, show the storyboard and project credit ceiling, and do not run paid
> generation until I approve it.

Or:

> Resume my existing Sonol Higgsfield production, open the dashboard, and tell
> me which approval or QC gate blocks the next shot.

The agent should load `sonol-higgsfield`, inspect the live CLI contract, and
start with requirements or the recorded production state—not with a paid
generation call.

## Verify the installation

```bash
npx --yes skills@latest list --global --agent codex --agent claude-code
higgsfield --version
higgsfield account status
higgsfield workspace status
```

You can also confirm that one of these files exists:

- Codex: `~/.agents/skills/sonol-higgsfield/SKILL.md`
- Claude Code: `~/.claude/skills/sonol-higgsfield/SKILL.md`

The Skills CLI may maintain a shared canonical copy and agent-specific links or
copies. The install commands above use `--copy` for predictable behavior on
Windows and other environments where symlink permissions vary.

## Update

Use the Skills CLI update command, then start a new agent session:

<!-- markdownlint-disable MD013 -->

```bash
npx --yes skills@latest update sonol-higgsfield --global --yes
```

<!-- markdownlint-enable MD013 -->

## Manual installation

If you cannot use Node.js, clone the repository into the user skill directory
for your host:

```bash
# Codex CLI
git clone https://github.com/volition79/sonol-higgsfield.git ~/.agents/skills/sonol-higgsfield

# Claude Code
git clone https://github.com/volition79/sonol-higgsfield.git ~/.claude/skills/sonol-higgsfield
```

On Windows PowerShell, `$HOME/.agents/skills/...` and
`$HOME/.claude/skills/...` resolve inside the current Windows user profile.

## Repository layout

```text
SKILL.md       Agent workflow and non-negotiable production gates
scripts/       Production state, dashboard, cost, grammar, QC, and runner tools
references/    Film grammar, Seedance, continuity, audio, routing, and policies
assets/        Local production dashboard template
tests/         Deterministic workflow and contract tests
```

## Important limits

- Generated video models may not follow every camera or acting instruction.
- A validated prompt or film grammar improves control but cannot guarantee a
  rendered result.
- MCP capabilities are used only when their live tool schema is visible in the
  current session.
- Paid Higgsfield jobs consume credits. This skill uses a user-approved project
  ceiling but intentionally skips exact live quotes, so one submitted job can
  exceed the remaining ceiling and cannot be reversed.
- OCR, transcript, and automated checks are evidence, not substitutes for
  human visual, editorial, and continuity review.
- ElevenLabs V3 and start/end images are generative conditioning inputs; they
  improve control but do not guarantee the original waveform or exact pixels.
