// Author:    mikomeller
// Version:   0.1.1
// Filename:  story_replay.mjs
// Pathname:  scripts/story_replay.mjs
// Purpose:   Replays the guided story in headless Chrome over the DevTools protocol: clicks "Play the story",
//            confirms the demo reset when the wallet is used, waits for "Story finished". Exit 0 only if it finished.
// Usage:     node scripts/story_replay.mjs http://localhost:6274/ [output-dir]   (needs Google Chrome; ALLOW_DEMO_RESET=1 on the server;
//            for another page origin start the server with a matching APP_ORIGINS, e.g. APP_ORIGINS=http://localhost:6280)
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
const url = process.argv[2] || "http://localhost:6274/", out = process.argv[3] || (await import("node:os")).tmpdir();
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new", "--disable-gpu", "--remote-debugging-port=9377", "--window-size=1440,1000", `--user-data-dir=${out}/profile`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pending = new Map();
const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJs = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result?.result?.value;
const shot = async (name) => { const r = await send("Page.captureScreenshot", { format: "png" }); writeFileSync(`${out}/${name}.png`, Buffer.from(r.result.data, "base64")); };
const clickText = (t) => evalJs(`(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim().includes(${JSON.stringify(t)}) && !x.disabled); if(!b) return false; b.click(); return true; })()`);
const text = () => evalJs("document.body.innerText");
let code = 1;
try {
  let target; for (let i = 0; i < 40 && !target; i++) { await sleep(250); try { target = (await (await fetch("http://127.0.0.1:9377/json")).json()).find((t) => t.type === "page"); } catch {} }
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => (ws.onopen = r));
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
  await send("Page.enable"); await send("Runtime.enable");
  await send("Page.navigate", { url }); await sleep(3500);
  console.log("click Play the story:", await clickText("Play the story")); await sleep(1500);
  const t1 = await text();
  const hasDialog = /Reset the demo wallet and play again\?/.test(t1);
  console.log("reset dialog shown:", hasDialog); await shot("1_start");
  if (hasDialog) console.log("click Reset and play:", await clickText("Reset and play"));
  let done = false, stopped = false;
  for (let i = 0; i < 90 && !done && !stopped; i++) { await sleep(1000); const t = await text(); done = /Story finished/.test(t); stopped = /Story stopped/.test(t); if (i === 12) await shot("2_mid"); }
  console.log("story finished:", done, "story stopped:", stopped); await shot("3_end");
  const t2 = await text();
  console.log("summary line:", (t2.match(/Budgets after the story:[^\n]*/) || ["(none)"])[0]);
  code = done && !stopped ? 0 : 1;
} catch (e) { console.log("driver error:", e.message); }
chrome.kill(); process.exit(code);
