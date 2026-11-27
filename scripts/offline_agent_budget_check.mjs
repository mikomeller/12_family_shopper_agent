// Author:    mikomeller
// Version:   0.1.1
// Filename:  offline_agent_budget_check.mjs
// Pathname:  scripts/offline_agent_budget_check.mjs
// Purpose:   Checks that the offline responder only offers what the wallet says fits the signed-in member (no HTTP server needed)
import { execFileSync } from "node:child_process";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const tmp = process.env.BUDGET_CHECK_TMP || os.tmpdir();
process.env.WALLET_DB = path.join(tmp, `budget_check_${Date.now()}.sqlite`);
process.env.PYTHONPATH = path.join(root, "src");
process.env.WALLET_TOKEN_SECRET ||= "budget-check-secret";
execFileSync(process.env.UV_BIN || "uv", ["run", "python", "scripts/seed_wallet.py"], { cwd: root, env: process.env, stdio: "ignore" });

const { offlineReply, closeOffline } = await import("../src/offline-agent.js");
const { callWallet, closeWallet } = await import("../src/wallet-client.js");

let failed = false;
const check = (name, ok, detail = "") => { console.log(`${ok ? "PASS" : "FAIL"} ${name}${detail ? ` - ${detail}` : ""}`); if (!ok) failed = true; };
const ask = async (member, text) => (await offlineReply([{ role: "user", content: text }], member, callWallet)).reply;
const hasRow = (r, name = "") => new RegExp(`^\\|\\s*\\[[^\\]]*${name}[^\\]]*\\]\\(https?:\\/\\/[^)]+\\)\\s*\\|`, "m").test(r);
const NOFIT = /fits your budget.*left this month/s;

try {
  for (const m of ["child", "teen"]) {
    const r = await ask(m, "headphones");
    check(`${m} + headphones: no row, no 299 price cell, budget sentence`, !hasRow(r, "SoundMax") && !/\|\s*€\s*299/.test(r) && NOFIT.test(r), r.split("\n")[0]);
  }
  const p = await ask("parent", "headphones");
  check("parent + headphones: INFLATED verdict, no buyable row", /INFLATED/.test(p) && !hasRow(p, "SoundMax") && /not offered: the advertised discount is not real/.test(p));
  const t = await ask("teen", "Der Hobbit");
  check("teen + Der Hobbit: table with 10,99", hasRow(t) && /€ 10,99/.test(t));
  const c = await ask("child", "Der Hobbit");
  check("child + Der Hobbit: table with 10,99 and approval line", hasRow(c) && /€ 10,99/.test(c) && /A parent has to approve this before anything is ordered\./.test(c));
  // reduce teen's remaining budget with real orders
  for (let i = 0; i < 20; i++) {
    const b = await callWallet("teen", "check_budget");
    if (!b.ok || b.remaining_personal_cents < 1099) break;
    const amt = Math.min(b.remaining_personal_cents - 1000, 2000);
    if (amt < 100) break;
    await callWallet("teen", "place_order", { product_name: "Budget filler", shop: "test", deep_link: "https://example.com/filler", price_cents: amt });
  }
  const b = await callWallet("teen", "check_budget");
  const t2 = await ask("teen", "Der Hobbit");
  check("teen after orders (left " + b.remaining_personal_cents + " cents) + Der Hobbit: no table", b.remaining_personal_cents < 1099 && !hasRow(t2) && NOFIT.test(t2), t2.split("\n")[0]);
} catch (e) {
  check("script ran without error", false, String(e?.message || e));
} finally {
  await closeOffline();
  await closeWallet();
}
process.exit(failed ? 1 : 0);
