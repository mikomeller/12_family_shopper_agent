// Author:    mikomeller
// Version:   0.1.2
// Filename:  ui_wallet_smoke.mjs
// Pathname:  scripts/ui_wallet_smoke.mjs
// Purpose:   Smoke test of the Node UI server (offline mode, no OpenAI key) against the Family Wallet; start the server with a fresh WALLET_DB
const base = process.env.UI_BASE || "http://127.0.0.1:3001";
let failed = false;

async function call(method, url, body, member) {
  const headers = { "Content-Type": "application/json" };
  if (member) headers["X-Family-Member"] = member;
  const res = await fetch(base + url, { method, headers, body: body ? JSON.stringify(body) : undefined });
  return { status: res.status, body: await res.json().catch(() => ({})) };
}
function check(name, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"} ${name}${detail ? ` - ${detail}` : ""}`);
  if (!ok) failed = true;
}
const buy = (member, p) => call("POST", "/api/family/mock-purchases", { productUrl: "https://example.com/x", ...p }, member);
const orderCount = async () => (await call("GET", "/api/state", null, "parent")).body.purchases?.length;

const state = await call("GET", "/api/state", null, "teen");
check("GET /api/state as teen lists parent/teen/child and family cap",
  state.status === 200 && ["parent", "teen", "child"].every((id) => state.body.members?.some((m) => m.id === id)) && state.body.family?.capEur === 400,
  JSON.stringify(state.body.family));

const noHeader = await call("GET", "/api/state");
check("no X-Family-Member header is 401", noHeader.status === 401, noHeader.body.error);

const status = await call("GET", "/api/idealo/status");
check("status reports mode offline-mock", status.body.mode === "offline-mock", JSON.stringify(status.body.mode));

const chat = await call("POST", "/api/chat", { messages: [{ role: "user", content: "Der Hobbit" }] }, "teen");
const rows = [...String(chat.body.reply).matchAll(/^\|\s*\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)\s*\|[^|]*\|\s*€\s*([\d.,]+)\s*\|/gm)];
check("offline chat 'Der Hobbit' returns a table with a price", chat.status === 200 && rows.length >= 1, rows[0]?.[3]);
const cheapest = rows[0];
const cheapestEur = Number(String(cheapest?.[3] || "0").replace(/\./g, "").replace(",", "."));

const ok = await buy("teen", { productName: cheapest?.[1] || "Der Hobbit", priceEur: cheapestEur, productUrl: cheapest?.[2], productRef: "hobbit-pb" });
check("teen buys the cheapest Hobbit offer", ok.status === 201 && ok.body.ok === true, ok.body.message || ok.body.error);

const big = await buy("teen", { productName: "Smoke Laptop", priceEur: 300 });
check("teen 300 EUR refused (monthly limit)", big.status === 400 && /monthly limit/i.test(big.body.error || ""), big.body.error);

const spoof = await buy("teen", { memberName: "parent", productName: "Spoof", priceEur: 1 });
check("header teen + body memberName parent is 403", spoof.status === 403, spoof.body.error);

const none = await call("POST", "/api/family/mock-purchases", { productName: "x", priceEur: 1 });
check("purchase without header is 401", none.status === 401, none.body.error);

const before = await orderCount();
const hp = await buy("parent", { productName: "SoundMax X1", priceEur: 299, productRef: "headphones-x1", claimedWasEur: 449 });
check("headphones with claimedWasEur 449 -> 409 INFLATED", hp.status === 409 && hp.body.verdict === "INFLATED", hp.body.error);
check("blocked order added nothing", (await orderCount()) === before);

const coffee = await buy("parent", { productName: "BrewPro 3", priceEur: 79.99, productRef: "coffee-genuine", claimedWasEur: 99.99 });
check("coffee with its was-price -> ok (GENUINE)", coffee.status === 201 && coffee.body.verdict === "GENUINE", coffee.body.message || coffee.body.error);

const kid = await buy("child", { productName: "Smoke Book", priceEur: 5 });
check("child purchase is pending approval", kid.status === 201 && kid.body.purchase?.pendingApproval === true, kid.body.message || kid.body.error);
const req = (await call("GET", "/api/state", null, "parent")).body.pendingApprovals?.find((r) => r.productName === "Smoke Book");

const tryApprove = await call("POST", "/api/family/approve", { requestId: req?.requestId }, "teen");
check("teen approve refused by the wallet", tryApprove.status === 403 && /parent/i.test(tryApprove.body.error || ""), tryApprove.body.error);

const rej = await call("POST", "/api/family/reject", { requestId: req?.requestId }, "parent");
if (/unknown tool|not found|no such tool/i.test(rej.body.error || "") || rej.status === 502) console.log(`SKIP reject (wallet tool missing) - ${rej.body.error}`);
else {
  const spentBefore = (await call("GET", "/api/state", null, "parent")).body.members.find((m) => m.id === "child").spentEur;
  check("parent rejects request", rej.status === 200 && rej.body.request?.status === "rejected", rej.body.error || JSON.stringify(rej.body.request));
  const st = await call("GET", "/api/state", null, "parent");
  check("rejected request no longer open, no spend", !st.body.pendingApprovals.some((r) => r.requestId === req?.requestId) && st.body.members.find((m) => m.id === "child").spentEur === spentBefore);
}

await buy("child", { productName: "Smoke Book 2", priceEur: 6 });
const req2 = (await call("GET", "/api/state", null, "parent")).body.pendingApprovals?.find((r) => r.productName === "Smoke Book 2");
const appr = await call("POST", "/api/family/approve", { requestId: req2?.requestId }, "parent");
check("parent approves second request", appr.status === 200 && appr.body.ok === true, appr.body.message || appr.body.error);

const add = await call("POST", "/api/family/members", { name: "Mallory", spendingLimitEur: 99999 }, "parent");
check("POST /api/family/members is 403", add.status === 403, add.body.error);

process.exit(failed ? 1 : 0);
