// Author:    mikomeller
// Version:   0.1.1
// Filename:  ui_wallet_smoke.mjs
// Pathname:  scripts/ui_wallet_smoke.mjs
// Purpose:   Smoke test of the Node UI server against the Family Wallet (server must run on 127.0.0.1:3001 with a fresh WALLET_DB)
const base = process.env.UI_BASE || "http://127.0.0.1:3001";
let failed = false;

async function call(method, url, body) {
  const res = await fetch(base + url, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  return { status: res.status, body: await res.json().catch(() => ({})) };
}
function check(name, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"} ${name}${detail ? ` - ${detail}` : ""}`);
  if (!ok) failed = true;
}

const state = await call("GET", "/api/state");
check("GET /api/state lists parent/teen/child and family cap",
  state.status === 200 && ["parent", "teen", "child"].every((id) => state.body.members?.some((m) => m.id === id)) && state.body.family?.capEur === 400,
  JSON.stringify(state.body.family));

const ok = await call("POST", "/api/family/mock-purchases", { memberName: "teen", productName: "Smoke Headphones", priceEur: 10.99, productUrl: "https://example.com/a" });
check("teen buys 10.99 EUR", ok.status === 201 && ok.body.ok === true, ok.body.message || ok.body.error);

const big = await call("POST", "/api/family/mock-purchases", { memberName: "teen", productName: "Smoke Laptop", priceEur: 300, productUrl: "https://example.com/b" });
check("teen 300 EUR refused (personal cap)", big.status === 400 && /monthly limit/i.test(big.body.error || ""), big.body.error);

const kid = await call("POST", "/api/family/mock-purchases", { memberName: "child", productName: "Smoke Book", priceEur: 5, productUrl: "https://example.com/c" });
check("child 5 EUR becomes approval request", kid.status === 201 && kid.body.purchase?.pendingApproval === true, kid.body.message || kid.body.error);

const after = await call("GET", "/api/state");
const req = after.body.pendingApprovals?.find((r) => r.productName === "Smoke Book");
check("open request visible in state", Boolean(req), JSON.stringify(req));

const appr = await call("POST", "/api/family/approve", { requestId: req?.requestId });
check("parent approves request", appr.status === 200 && appr.body.ok === true, appr.body.message || appr.body.error);

const add = await call("POST", "/api/family/members", { name: "Mallory", spendingLimitEur: 99999 });
check("POST /api/family/members is 403", add.status === 403, add.body.error);

process.exit(failed ? 1 : 0);
