#!/usr/bin/env node

import http from "node:http";

function parseArgs(argv) {
  const result = { command: argv[2] || "status", port: 9222, rest: [] };
  for (let index = 3; index < argv.length; index += 1) {
    if (argv[index] === "--port") {
      result.port = Number(argv[index + 1]);
      index += 1;
    } else {
      result.rest.push(argv[index]);
    }
  }
  return result;
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (response) => {
      let body = "";
      response.on("data", (chunk) => { body += chunk; });
      response.on("end", () => {
        if ((response.statusCode || 500) >= 400) {
          reject(new Error(
            `CDP endpoint returned HTTP ${response.statusCode}; run web_ui_runtime.py launch first`,
          ));
          return;
        }
        try { resolve(JSON.parse(body)); } catch (error) {
          reject(new Error(`CDP endpoint returned invalid JSON: ${error.message}`));
        }
      });
    }).on("error", reject);
  });
}

async function connect(port) {
  const targets = await getJson(`http://127.0.0.1:${port}/json/list`);
  const target = targets.find((item) => item.type === "page" && item.url.includes("higgsfield.ai"));
  if (!target) throw new Error("No Higgsfield browser tab is attached; run web_ui_runtime.py launch first");
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
  let nextId = 1;
  const pending = new Map();
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data.toString());
    if (!message.id || !pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result || {});
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = nextId;
    nextId += 1;
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
  return { target, socket, send };
}

async function evaluate(send, expression) {
  const response = await send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (response.exceptionDetails) {
    throw new Error(response.exceptionDetails.text || "Browser evaluation failed");
  }
  return response.result?.value;
}

const LOGIN_STATUS = `(() => {
  const body = document.body?.innerText || "";
  const accountMenu = Boolean(document.querySelector('button[aria-label="Account menu"]'));
  const signIn = [...document.querySelectorAll('button,a')].some((node) =>
    /^(sign in|log in|login)$/i.test((node.innerText || "").trim())
  );
  return {
    url: location.href,
    title: document.title,
    account_menu_visible: accountMenu,
    sign_in_visible: signIn,
    logged_in: accountMenu && !signIn,
    login_required: !accountMenu || signIn,
    page_mentions_generation: /Cinema Studio|My generations|Projects/i.test(body),
  };
})()`;

const CINEMA_INSPECT = `(() => {
  const section = document.querySelector('section[aria-label*="video generation"]');
  if (!section) return { ready: false, reason: "video composer not visible", url: location.href };
  const prompt = section.querySelector('[contenteditable="true"][role="textbox"]');
  const attachments = [...section.querySelectorAll('[data-reorder-item]')].map((item) => {
    const image = item.querySelector('img');
    const match = (image?.src || "").match(/[0-9a-f]{8}-[0-9a-f-]{27,}/i);
    const label = (item.innerText || "").trim();
    return { id: match ? match[0] : null, role: label || "Reference" };
  });
  const buttonText = [...document.querySelectorAll('button')].map((button) =>
    (button.innerText || "").trim()
  ).filter(Boolean);
  const generate = [...section.querySelectorAll('button')].find((button) =>
    (button.innerText || "").includes("GENERATE")
  );
  return {
    ready: true,
    url: location.href,
    model: section.getAttribute('aria-label'),
    prompt: prompt?.innerText || "",
    prompt_words: (prompt?.innerText || "").trim().split(/\\s+/).filter(Boolean).length,
    attachments,
    genre: buttonText.find((text) => text.startsWith("Genre:")) || null,
    style: buttonText.find((text) => text.startsWith("Style:")) || null,
    camera: buttonText.find((text) => text.startsWith("Camera:")) || null,
    composer_summary: (section.innerText || "").replace(/\\n+/g, " | "),
    generate_disabled: generate ? generate.disabled : null,
    displayed_cost: generate ? (generate.innerText || "").replace(/\\n+/g, " ") : null,
  };
})()`;

async function main() {
  const args = parseArgs(process.argv);
  if (!Number.isInteger(args.port) || args.port < 1 || args.port > 65535) {
    throw new Error("--port must be a valid TCP port");
  }
  const { target, socket, send } = await connect(args.port);
  try {
    let result;
    if (args.command === "status") {
      result = { url: target.url, title: target.title };
    } else if (args.command === "login-status") {
      result = await evaluate(send, LOGIN_STATUS);
    } else if (args.command === "inspect-cinema") {
      result = await evaluate(send, CINEMA_INSPECT);
    } else if (args.command === "evaluate") {
      if (!args.rest[0]) throw new Error("evaluate requires a JavaScript expression");
      result = await evaluate(send, args.rest[0]);
    } else if (args.command === "insert-text") {
      const text = args.rest[0] || "";
      await evaluate(send, `(() => {
        const editor = document.querySelector('[contenteditable="true"][data-lexical-editor="true"]');
        if (!editor) throw new Error('prompt editor not found');
        editor.focus();
        const selection = window.getSelection();
        selection.removeAllRanges();
        const range = document.createRange();
        range.selectNodeContents(editor);
        selection.addRange(range);
        return true;
      })()`);
      await send("Input.insertText", { text });
      result = await evaluate(send, `(() => {
        const editor = document.querySelector('[contenteditable="true"][data-lexical-editor="true"]');
        return { prompt: editor?.innerText || "" };
      })()`);
    } else if (args.command === "set-start-role") {
      const imageId = args.rest[0];
      if (!imageId) throw new Error("set-start-role requires an image job id");
      result = await evaluate(send, `(async () => {
        const waitFor = async (finder, timeout = 5000) => {
          const started = Date.now();
          while (Date.now() - started < timeout) {
            const found = finder();
            if (found) return found;
            await new Promise((resolve) => setTimeout(resolve, 100));
          }
          throw new Error('timed out waiting for browser control');
        };
        const image = await waitFor(() => [...document.images].find((item) =>
          (item.src || '').includes(${JSON.stringify(imageId)})
        ));
        const item = image.closest('[data-reorder-item]');
        if (!item) throw new Error('attached image item not found');
        if ((item.innerText || '').trim() === 'Start') return { changed: false, role: 'Start' };
        const menu = item.querySelector('button[data-context-menu-trigger]');
        if (!menu) throw new Error('attachment role menu not found');
        menu.click();
        const dialog = await waitFor(() => [...document.querySelectorAll('[role="dialog"]')]
          .find((node) => (node.innerText || '').includes('Start Frame')));
        const start = [...dialog.querySelectorAll('button')].find((button) =>
          (button.innerText || '').trim().includes('Start Frame')
        );
        if (!start) throw new Error('Start Frame action not found');
        start.click();
        await waitFor(() => (item.innerText || '').trim() === 'Start');
        return { changed: true, role: 'Start' };
      })()`);
    } else if (args.command === "submit-paid") {
      if (args.rest[0] !== "I_APPROVE_THIS_PAID_GENERATION") {
        throw new Error("submit-paid requires the exact confirmation phrase");
      }
      result = await evaluate(send, `(() => {
        if (window.__sonolPaidSubmissionAt) {
          return { clicked: false, reason: 'already submitted', at: window.__sonolPaidSubmissionAt };
        }
        const section = document.querySelector('section[aria-label*="video generation"]');
        const hasStart = [...(section?.querySelectorAll('[data-reorder-item]') || [])]
          .some((item) => (item.innerText || '').trim() === 'Start');
        if (!hasStart) throw new Error('paid submission blocked: no explicit Start attachment');
        const button = [...section.querySelectorAll('button')].find((item) =>
          (item.innerText || '').includes('GENERATE')
        );
        if (!button || button.disabled) throw new Error('paid Generate button is unavailable');
        window.__sonolPaidSubmissionAt = new Date().toISOString();
        button.click();
        return { clicked: true, at: window.__sonolPaidSubmissionAt };
      })()`);
    } else {
      throw new Error(`Unknown command: ${args.command}`);
    }
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } finally {
    socket.close();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exit(2);
});
