# Higgsfield web UI runtime

Use the web UI as an audited execution surface when a required control is
web-only or a confirmed provider/CLI defect rejects a valid paid call before a
job is created. Keep the CLI for live contract discovery, account balance,
provider history, job observation, downloading, and reconciliation.

## Control order

1. Prefer a native computer-use/browser tool already exposed to the agent.
2. Otherwise prefer an available Playwright/browser MCP with a persistent,
   dedicated Higgsfield profile.
3. Otherwise use `scripts/web_ui_runtime.py` and its loopback CDP bridge.
4. If none is available, ask the user to perform the visible UI steps and then
   reconcile the exact job ID. Never pretend a manual step was automated.

Run the portable preflight:

```bash
python3 scripts/web_ui_runtime.py doctor
python3 scripts/web_ui_runtime.py launch
```

The launch command uses an isolated user profile and loopback-only Chrome
DevTools. It intentionally does not reuse or inspect the user's normal browser
profile. Do not expose the debugging port beyond `127.0.0.1`.

## Mandatory login handoff

Authentication is a user action. After opening the dedicated browser, stop and
say:

> Higgsfield 전용 브라우저에서 로그인과 2단계 인증을 직접 완료한 뒤
> 로그인했다고 알려주세요. 비밀번호나 인증 코드를 채팅에 보내지 마세요.

Do not request, paste, record, print, or inspect passwords, one-time codes,
cookies, authorization headers, OAuth tokens, or storage values. Captcha,
passkey, consent, and suspicious-login prompts also remain with the user. After
the user confirms, verify the visible account menu or run:

```bash
python3 scripts/web_ui_runtime.py login-status
```

Reuse the dedicated profile on that computer so later sessions normally remain
signed in. A different computer or deleted profile requires a new login.

## Platform compatibility

| Environment | Preferred control | CDP fallback |
|---|---|---|
| Windows Claude Code | Exposed computer-use/Playwright tool | Dedicated Chrome or Edge plus native Node.js 22+ |
| WSL Codex/Claude | Exposed browser tool controlling Windows | Windows Chrome/Edge and Windows `node.exe`; paths are translated with `wslpath` |
| macOS Claude Code | Native computer use when exposed | Dedicated Chrome/Edge/Chromium plus Node.js 22+ |
| Linux | Exposed browser tool | Chrome/Chromium/Edge plus Node.js 22+ |

`doctor` reports the detected platform, browser, Node version, profile path, and
whether the CDP fallback is ready. It installs nothing. If Node 22+ is missing,
use native computer use or ask before installing anything.

## Cinema Studio 3.5 start-frame flow

1. Open Video mode and select Cinema Studio 3.5.
2. Add the approved image from Uploads or Image Generations. Selecting an asset
   initially assigns `Reference`; that is not a start-frame binding.
3. Open the attachment menu and choose `Use as ... -> Start Frame`, or start
   from the image tile's `Turn into video` action.
4. Confirm the attachment itself displays `Start`. With the CDP fallback:

   ```bash
   python3 scripts/web_ui_runtime.py set-start-role <image_job_id>
   python3 scripts/web_ui_runtime.py inspect-cinema
   ```

5. Set the approved genre, color palette, lighting, camera moveset, camera/lens
   controls, aspect, resolution, duration, sound state, and minimum-sufficient
   prompt. Do not add an end frame or generic reference unless the shot policy
   explicitly calls for it.
6. Before clicking Generate, inspect the visible model, `Start` badge, prompt,
   settings, displayed credit amount, account balance, and remaining approved
   ceiling. A browser session is not spending approval.
7. Click Generate exactly once. The fallback command is deliberately guarded:

   ```bash
   python3 scripts/web_ui_runtime.py submit-paid \
     --confirm I_APPROVE_THIS_PAID_GENERATION
   ```

   Use it only after the same user approval required by the CLI runner. Never
   retry from a timeout or missing toast; query provider history first.

8. Confirm `Generation started`, then use `higgsfield generate list/get` to
   persist the real job ID and verify that `params.medias[].role` is
   `start_image`. Reconcile it into Sonol state:

   ```bash
   python3 scripts/run_shot.py <production> <shot_id> --reconcile \
     --job-id <job_id> --submission-surface web_ui [--credits <actual>] \
     [--result-path <downloaded-file>]
   ```

9. Download and inspect the result. Compare the submitted image with the actual
   first frame; an explicit start-frame role is strong conditioning, not a
   pixel-lock guarantee.

## Confirmed Cinema 3.5 recovery rule

On Higgsfield CLI 1.1.19, repeated Cinema 3.5 media submissions may terminate
before job creation with `IP check not finished for input media`, including
inputs that the web UI accepts. After one controlled CLI baseline and provider
history evidence of no job, stop the retry loop. Preserve the same model,
start image, prompt intent, and approved spend boundary, then route the call
through the web UI. This is a transport recovery, not permission to change the
shot or spend again.

Verified on 2026-07-21: a GPT Image job selected in Cinema Studio 3.5 was
changed from the default `Reference` role to `Start Frame`; the resulting web
job stored that exact image job under `medias` with role `start_image` and
completed normally. Treat this as versioned evidence, not a permanent promise;
reinspect the visible UI and provider job params each session.
