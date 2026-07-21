# Director intelligence

This layer is advisory. It must preserve the approved story and must never add
new actions, silently split a shot, choose a camera, or spend credits.

## Production router

- `QUICK_CLIP`: one or two exploratory clips; use the official Higgsfield
  generation skill/CLI directly and keep Sonol state optional.
- `NATIVE_MULTISHOT`: one Seedance generation containing two to four simple,
  timecoded beats within 15 seconds. Do not use this for exact dialogue,
  precise acting, or fragile object interactions.
- `CONTROLLED_SHOT`: one core shot per generation when acting, dialogue,
  product presentation, or camera precision is load-bearing.
- `SERIAL_STORY`: multiple provider jobs, continuity, selective regeneration,
  or a production longer than 15 seconds. Use the full Sonol state machine.
- `OFFICIAL_WORKFLOW`: Marketing Studio for ads and the official
  video-explainer workflow for explainers. Sonol may add audit or QC, but must
  not replace the official workflow by default.

Approval profiles are `LIGHT`, `TARGETED`, and `FULL`. `FULL` is reserved for
high-cost, multi-job, or long-running productions. Every paid submission still
needs an explicit spend boundary or the provider's own confirmation.

## Five advisory functions

1. Performance direction converts an abstract emotion into no more than three
   observable cues from body channels visible in the actual framing.
2. Camera recommendation returns at most two alternatives: emotion-following
   and emotion-contrasting. The director or user chooses; support is soft until
   the live provider schema proves otherwise.
3. Prompt lint uses a minimum-sufficient target, not a universal short limit.
   It prioritizes the load-bearing element, warns about ambiguity and abstract
   direction, and blocks only genuine contradictions. It cannot invent detail.
4. Complexity scoring is explainable and advisory. A split recommendation must
   be approved because it changes duration, rhythm, and cost.
5. Failure diagnosis requires at least two comparable attempts and treats
   three as the first useful sample. Systematic failures change one variable;
   probable stochastic failures preserve inputs and recommend no more than two
   additional candidates, subject to the remaining credit boundary.

## Image and boundary policy

Start-only is the minimum-sufficient default. A single evidenced essential
reference may be added after a controlled start-only failure. An end image is
allowed only when the exact arrival composition is load-bearing and the added
constraint is worth the adherence tradeoff. Previous boundary-frame inheritance
is required only for a true continuous match; a motivated transition may start
from a new just-in-time keyframe instead.
