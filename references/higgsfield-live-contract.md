# Higgsfield live contract

## Authority order

1. Current authenticated CLI `model get` / `workflow get` output.
2. Current official Higgsfield skill routing guidance.
3. This reference, which is a capability map and may drift.

Never send a paid request solely from remembered flags or examples here.

## Session preflight

Run `inspect_live_schema.py`. It captures the CLI version, redacted account and
selected workspace state, complete model/workflow lists, selected contracts,
available credits, stable per-contract/schema fingerprints, and MCP URL health.
It deliberately removes email and secret fields. Compile paid shots only from a
snapshot no older than 24 hours. A successful preflight does not approve
spending.

## Observed contract snapshot (2026-07-20)

The authenticated CLI was version `1.1.19`. It listed 66 models and 18
workflows. The selected free workspace exposed 10 credits. These are evidence
from that date, not fixed values.

Relevant current job types included:

- Video: `seedance_2_0`, `seedance_2_0_mini`, `veo3_1`, `kling3_0`,
  `video_deflicker`, `video_upscale`, `topaz_video`.
- Image: `gpt_image_2`, `nano_banana_flash`, `nano_banana_2_lite`,
  `nano_banana_pro`, `text2image_soul_v2`, `z_image`.
- Audio/data: `seed_audio`, `text2speech_v2`, `inworld_text_to_speech`,
  `speech2text`, `clip_transcriber`.
- Workflows included `voice_change`, `dubbing`, `draw_to_video`, `reframe`,
  `cinematic_studio_image`, `cinematic_studio_3_0`, and
  `cinematic_studio_video_3_5`.

The observed Cinema Studio Video 3.5 contract exposed structured
`camera_style`, `light_scheme`, and `color_grading` enums. These are style
families, not the full 64-control web preset list. Cinema Studio 3.0 exposed
`speedramp`; Cinema Studio Image exposed camera/lens/focal/aperture ID fields,
but their valid IDs require a live options source. The compiler validates every
emitted structured value against the captured contract and otherwise keeps the
technique at prompt-soft or blocked status.

The current Seedance 2.0 contract accepted start and end images plus image,
video, and audio references. The observed limits were nine images including
start/end, three videos, three audios, twelve total references, duration 4–15
seconds, and 480p/720p/1080p/4K. Fast mode was restricted to at most 720p.
Reinspect these constraints before every live production session.
Its observed `generate_audio` default was `true`; always emit an explicit
boolean from the shot audio plan.

The current `voice_change` workflow required `input_video`, `voice_id`, and a
`voice_type` of `preset` or `element`; cost depended on duration. Its public
schema did not identify the downstream provider, so do not label it ElevenLabs.

No live `explainer_video` workflow was present in the observed workflow list.
Do not make it a dependency. The separate official explainer skill is intended
for non-photoreal narrated ten-second blocks, not arbitrary photoreal films.

## MCP boundary

The official streamable HTTP endpoint is expected at
`https://mcp.higgsfield.ai/mcp`. A root URL without `/mcp` is invalid for the
current endpoint. Treat MCP as usable only after an authenticated handshake and
visible tool input schemas. MCP availability never expands the product's model
contract, bypasses billing, or replaces explicit project-ceiling approval.

If MCP is unavailable or its schema cannot be inspected in the current session,
use the CLI and record `MCP_UNAVAILABLE`. Never claim that MCP has a feature
merely because the CLI has it.

The official Camera Controls page lists 64 named motion controls plus `General`
in the verified snapshot. They remain `web_only` unless a current CLI workflow or MCP tool input
schema exposes the corresponding field or preset ID.

## What is not proven automatic

- Dialogue/background separation: no observed dedicated separation contract.
- Objective lip-sync score: no observed scoring contract.
- Cross-shot face, costume, prop, or camera continuity scoring: manual review or
  separately integrated vision tooling is required.
- Exact Korean typography quality: OCR only checks text evidence.
- Voice-provider identity behind `voice_change`: not disclosed by the schema.
