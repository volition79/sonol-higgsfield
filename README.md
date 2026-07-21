# Sonol Higgsfield

[English](README.md) | [한국어](README.ko.md)

Turn a video idea into a controlled, reviewable Higgsfield production—not a pile
of disconnected generation attempts.

Sonol Higgsfield is an agent skill for Codex CLI, Claude Code, and compatible
Agent Skills hosts. It gives your agent a production workflow for multi-shot
films, ads, stories, campaigns, and narrated videos: requirements, storyboard,
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
- An ElevenLabs API key and approved voice IDs when visible dialogue or external
  narration is required
- Optional Higgsfield MCP access; the skill treats the live CLI schema as the
  canonical execution contract and does not require MCP

Official setup references:

- [Higgsfield CLI](https://higgsfield.ai/cli)
- [Higgsfield CLI source and platform-specific install options](https://github.com/higgsfield-ai/cli)
- [Skills CLI](https://github.com/vercel-labs/skills)

## Why use it?

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

### Keep Seedance 2.0 disciplined

The default is one controlled action and one primary camera movement per short
prototype. Experimental timecoded multi-shot generation is available only when
you accept whole-clip regeneration risk.

Each paid clip receives one start image. The first clip is composed up front;
later clips either inherit an accepted boundary frame or compose a fresh frame
just in time at a director-selected cut. Start-only is the default. One
essential image reference is allowed only after a recorded failure and a
one-variable A/B test; an end image is reserved for simple motivated transitions
where exact arrival matters. FFmpeg persists eight candidates from the final
0.5 seconds and recommends the least blurred, while the director may select a
better narrative frame with a recorded reason. Schema v7 requires start-image
preflight, first-frame QC, boundary analysis, locked story anchors, and previous
user acceptance before dependent generation.

### Resume long productions safely

A local production directory and dashboard preserve requirements, versions,
approvals, jobs, costs, QC state, and history. A later session can resume from
the recorded state instead of reconstructing the project from chat memory.

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
track is preserved without creative post-production overdubs. Off-screen
narration and no-dialogue post-only shots keep their separate finishing routes.

## Production flow

1. Interview and lock the requirements.
2. Create the persistent production state and dashboard.
3. Write a timecoded script, scenes, assets, and shot plan.
4. Choose and validate film grammar for each shot.
5. Inspect the live Higgsfield schema and credits, then approve a project ceiling.
6. Approve animatics and references.
7. Generate one bounded shot at a time.
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

Re-run the same automatic install command. Then start a new agent session:

<!-- markdownlint-disable MD013 -->

```bash
npx --yes skills@latest add volition79/sonol-higgsfield --skill sonol-higgsfield --global --agent codex --agent claude-code --copy --yes
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
