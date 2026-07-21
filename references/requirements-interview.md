# Requirements interview

Extract facts already present in the conversation or supplied documents before
asking questions. Mark extracted but unconfirmed facts `INFERRED`; never mark
them `CONFIRMED` on the user's behalf.

## Required fields

| Field | Resolve |
|---|---|
| `purpose` | Film, ad, explainer, campaign, music-led piece, or other outcome |
| `core_message` | The single takeaway or action |
| `target_audience` | Who must understand or act |
| `target_platform` | Placement and delivery constraints |
| `duration_seconds` | Exact target and allowed tolerance |
| `aspect_ratio` | 16:9, 9:16, 1:1, or explicit custom target |
| `resolution` | Planning and final output resolution |
| `frame_rate` | Timeline and delivery fps |
| `language` | Spoken, caption, and on-screen languages |
| `story_direction` | Narrative arc, tone, pace, visual style |
| `characters_products_brands` | Identity, product, logo, and brand constraints |
| `copyright_constraints` | Ownership, licenses, likeness, music, and references |
| `approval_method` | Dashboard/chat review, responsible approver, milestones |
| `quality_cost_priority` | Economy, balance, or highest quality and tradeoffs |

## High-value conditional questions

- Is visible dialogue required, or can the narration remain off-screen?
- Must one real person's identity remain consistent? If yes, is Soul training
  already available and authorized, or should approved image references be used?
- Which Korean words, logos, labels, numbers, or legal lines must appear exactly?
- Which supplied media may be uploaded to Higgsfield and which must remain local?
- Which shots have visible dialogue, which have off-screen narration, and which
  need only post-produced ambience/effects/music?
- What may never change between shots: face, costume, product, location, color,
  logo, prop state, direction of motion, or camera axis?
- Who can approve requirements, costs, assets, shot boards, and final output?

## Interview conduct

Ask one unresolved decision at a time unless the user asks for a worksheet.
Explain why a decision affects quality, cost, or feasibility. Offer a proposed
default only when it is reversible, and retain it as `INFERRED` until confirmed.

When requirements conflict, record `CONFLICT`, cite both sources in `source`,
and ask the user to choose. Do not erase the conflict by guessing.

Before locking, present a compact specification containing all required fields,
upload scope, selected identity strategy, audio strategy, approval checkpoints,
and known limitations. Only an explicit user response can lock it.

## Example state writes

```bash
python3 scripts/sonol_higgsfield.py set-requirement ./production \
  duration_seconds 30 --status CONFIRMED --actor user --source "chat approval"

python3 scripts/sonol_higgsfield.py set-requirement ./production \
  aspect_ratio '"9:16"' --status INFERRED --source "TikTok placement"
```
