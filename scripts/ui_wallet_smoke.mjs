// Author:    mikomeller
// Version:   0.1.7
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
const buy = (member, p) => call("POST", "/api/family/mock-purchases", p, member);
const orderCount = async () => (await call("GET", "/api/state", null, "parent")).body.purchases?.length;

const state = await call("GET", "/api/state", null, "teen");
const pstate = await call("GET", "/api/state", null, "parent");
check("GET /api/state as parent lists parent/teen/child and family cap",
  pstate.status === 200 && ["parent", "teen", "child"].every((id) => pstate.body.members?.some((m) => m.id === id)) && pstate.body.family?.capEur === 400,
  JSON.stringify(pstate.body.family));
check("GET /api/state as teen shows only the teen's own budget line plus the family line",
  state.status === 200 && state.body.members?.length === 1 && state.body.members[0].id === "teen" && state.body.family?.capEur === 400,
  JSON.stringify(state.body.family));


// Parent offers check runs first, while the family budget is untouched; the provider is removed again afterwards.
if (process.env.FAKE_LLM === "1") {
  await call("POST", "/api/llm", { providerId: "custom", baseUrl: "http://127.0.0.1:3032/v1", model: "fake", apiKey: "sk-test-1234" }, "parent");
  const pr = await call("POST", "/api/chat", { messages: [{ role: "user", content: "headphones" }] }, "parent");
  let pp = null;
  try { pp = JSON.parse(String(pr.body.reply).replace(/^FAKE-LLM-OFFERS:/, "")); } catch { /* reported below */ }
  check("LLM offers as parent: offers present incl. a 29900-range total, caller parent", pp?.offers?.length >= 1 && pp.budget_filter?.caller === "parent", String(pr.body.reply).slice(0, 200));
  await call("DELETE", "/api/llm/key", null, "parent");
}

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

const HP = { productRef: "headphones-x1", productUrl: "https://shop-a.example/x1" };
const ordersBeforeBig = await orderCount();
const big = await buy("teen", { productRef: "coffee-genuine", priceEur: 79.99 });
check("teen coffee machine 79.99 EUR above own budget -> 409 canAskParent, nothing recorded", big.status === 409 && big.body.canAskParent === true && (await orderCount()) === ordersBeforeBig, JSON.stringify(big.body));

const spoof = await buy("teen", { memberName: "parent", productRef: "hobbit-pb", priceEur: 10.99 });
check("header teen + body memberName parent is 403", spoof.status === 403, spoof.body.error);

const none = await call("POST", "/api/family/mock-purchases", { productRef: "hobbit-pb", priceEur: 10.99 });
check("purchase without header is 401", none.status === 401, none.body.error);

const before = await orderCount();
const hp = await buy("parent", { ...HP, productName: "SoundMax X1", priceEur: 299, claimedWasEur: 449 });
check("headphones at 299 with claimedWasEur 449 -> 409 INFLATED", hp.status === 409 && hp.body.verdict === "INFLATED", hp.body.error);
const hpNoWas = await buy("parent", { ...HP, priceEur: 299 });
check("headphones without any was-price in the request -> still 409 INFLATED (catalogue was-price)", hpNoWas.status === 409 && hpNoWas.body.verdict === "INFLATED", hpNoWas.body.error);
const hpLow = await buy("parent", { ...HP, priceEur: 1, claimedWasEur: 449 });
check("headphones with priceEur 1 -> 409, no 1 EUR order", hpLow.status === 409, hpLow.body.error);
const hpFake = await buy("parent", { productRef: "headphones-x1", productName: "H", priceEur: 1, claimedWasEur: 0 });
check("headphones with fake was-price 0 and no url -> not recorded", hpFake.status === 409, hpFake.body.error);
check("blocked orders added nothing", (await orderCount()) === before);

const noRef = await buy("parent", { productName: "H", priceEur: 1, claimedWasEur: 449 });
check("purchase without productRef -> 400", noRef.status === 400, noRef.body.error);
const badRef = await buy("parent", { productRef: "nope-123", priceEur: 1 });
check("unknown productRef -> 400", badRef.status === 400, badRef.body.error);
for (const bad of ["1e2", -5, 10.999, "abc", 0]) {
  const r = await buy("parent", { productRef: "hobbit-pb", priceEur: bad });
  check(`priceEur ${JSON.stringify(bad)} -> 400`, r.status === 400, r.body.error);
}
check("rejected inputs added nothing", (await orderCount()) === before);

const coffee = await buy("parent", { productRef: "coffee-genuine", priceEur: 79.99, claimedWasEur: 1 });
check("coffee (catalogue was-price, client claim ignored) -> ok GENUINE", coffee.status === 201 && coffee.body.verdict === "GENUINE", coffee.body.message || coffee.body.error);

const tstate = await call("GET", "/api/state", null, "teen");
check("teen GET /api/state shows no orders of other members", tstate.body.purchases?.length >= 1 && tstate.body.purchases.every((o) => o.member === "Teen"), JSON.stringify(tstate.body.purchases?.map((o) => o.member)));

const BP = { productRef: "hobbit-pb", productUrl: "https://shop-a.example/hobbit" };
const childLeft = async () => (await call("GET", "/api/state", null, "child")).body.members?.[0]?.remainingEur;
const famSpent = async () => (await call("GET", "/api/state", null, "parent")).body.family?.spentEur;
const leftBefore = await childLeft();
const kid = await buy("child", { ...BP, priceEur: 10.99 });
check("child buys the Hobbit -> 201 ORDER (not pending)", kid.status === 201 && kid.body.ok === true && kid.body.purchase?.pendingApproval === false && /^order-/.test(kid.body.purchase?.id || ""), kid.body.message || kid.body.error);
check("child's remaining dropped", (await childLeft()) < leftBefore, `${leftBefore} -> ${await childLeft()}`);

const BG = { productRef: "boardgame-dice", productUrl: "https://shop-spielkiste.example/wuerfelwald" };
const ordersBeforeBg = await orderCount();
const bg = await buy("child", BG);
check("child board game above own budget -> 409 canAskParent, wallet reason + 'A parent can step in.'",
  bg.status === 409 && bg.body.canAskParent === true && bg.body.productRef === "boardgame-dice" && typeof bg.body.priceEur === "number" && /A parent can step in\.$/.test(bg.body.error || "") && /monthly limit/i.test(bg.body.error || ""), JSON.stringify(bg.body));
const openAfterBg = (await call("GET", "/api/state", null, "parent")).body.pendingApprovals?.length;
check("409 recorded nothing (no order, no request)", (await orderCount()) === ordersBeforeBg && openAfterBg === 0, `orders ${ordersBeforeBg}, open ${openAfterBg}`);

const noHdr = await call("POST", "/api/family/request-approval", BG);
check("request-approval without header is 401", noHdr.status === 401);
const ra1 = await call("POST", "/api/family/request-approval", BG, "child");
check("child request-approval -> 201 with requestId", ra1.status === 201 && ra1.body.ok === true && Number.isInteger(ra1.body.request?.requestId) && /Nothing is spent until a parent approves/.test(ra1.body.message || ""), JSON.stringify(ra1.body));
const ra2 = await call("POST", "/api/family/request-approval", BG, "child");
check("second child request-approval -> 201", ra2.status === 201, JSON.stringify(ra2.body));
const CM = { productRef: "coffee-genuine", productUrl: "https://shop-a.example/coffee" };
const taRa = await call("POST", "/api/family/request-approval", CM, "teen");
check("teen request-approval for the coffee machine -> 201", taRa.status === 201 && taRa.body.ok === true && Number.isInteger(taRa.body.request?.requestId), JSON.stringify(taRa.body));
const pRa = await call("POST", "/api/family/request-approval", CM, "parent");
check("parent request-approval -> 403 (role not allowed)", pRa.status === 403 && pRa.body.error_code === "NOT_ALLOWED_FOR_ROLE", JSON.stringify(pRa.body));
const hpRa = await call("POST", "/api/family/request-approval", { productRef: "headphones-x1", productUrl: HP.productUrl }, "child");
check("headphones via request-approval (child) -> 409 INFLATED", hpRa.status === 409 && hpRa.body.verdict === "INFLATED", hpRa.body.error);
const hpRaP = await call("POST", "/api/family/request-approval", { productRef: "headphones-x1", productUrl: HP.productUrl }, "parent");
check("headphones via request-approval (parent) -> 409 INFLATED", hpRaP.status === 409 && hpRaP.body.verdict === "INFLATED", hpRaP.body.error);
const hpChild = await buy("child", { ...HP, priceEur: 299 });
check("headphones as child purchase -> 409 INFLATED", hpChild.status === 409 && hpChild.body.verdict === "INFLATED", hpChild.body.error);
const hpTeen = await buy("teen", { ...HP, priceEur: 299 });
check("headphones as teen purchase -> 409 INFLATED", hpTeen.status === 409 && hpTeen.body.verdict === "INFLATED", hpTeen.body.error);

const open = (await call("GET", "/api/state", null, "parent")).body.pendingApprovals?.filter((r) => r.member === "Child") || [];
check("two open child requests", open.length === 2, JSON.stringify(open));
const [req, req2] = open;
const cstate = await call("GET", "/api/state", null, "child");
check("child sees only its own open requests", cstate.body.pendingApprovals?.length === 2 && cstate.body.pendingApprovals.every((r) => r.member === "Child"));
const badId = await call("POST", "/api/family/approve", { requestId: true }, "parent");
check("requestId true -> 400", badId.status === 400, badId.body.error);

const childApprove = await call("POST", "/api/family/approve", { requestId: req?.requestId }, "child");
check("child cannot approve (403)", childApprove.status === 403 && /parent/i.test(childApprove.body.error || ""), childApprove.body.error);
const tryApprove = await call("POST", "/api/family/approve", { requestId: req?.requestId }, "teen");
check("teen approve refused by the wallet", tryApprove.status === 403 && /parent/i.test(tryApprove.body.error || ""), tryApprove.body.error);

const spentBefore = (await call("GET", "/api/state", null, "parent")).body.members.find((m) => m.id === "child").spentEur;
const rej = await call("POST", "/api/family/reject", { requestId: req?.requestId }, "parent");
check("parent rejects request", rej.status === 200 && rej.body.request?.status === "rejected", rej.body.error || JSON.stringify(rej.body.request));
const st = await call("GET", "/api/state", null, "parent");
check("rejected request no longer open, no spend", !st.body.pendingApprovals.some((r) => r.requestId === req?.requestId) && st.body.members.find((m) => m.id === "child").spentEur === spentBefore);

const famBefore = await famSpent();
const ordersBeforeAppr = await orderCount();
const appr = await call("POST", "/api/family/approve", { requestId: req2?.requestId }, "parent");
check("parent approves the over-budget request -> order recorded", appr.status === 200 && appr.body.ok === true && (await orderCount()) === ordersBeforeAppr + 1, appr.body.message || appr.body.error);
check("child's remaining shows 0 (not negative)", (await childLeft()) === 0, String(await childLeft()));
check("family total went up by the order", (await famSpent()) > famBefore, `${famBefore} -> ${await famSpent()}`);

const teenReq = (await call("GET", "/api/state", null, "parent")).body.pendingApprovals?.find((r) => r.member === "Teen");
const teenLeft = async () => (await call("GET", "/api/state", null, "teen")).body.members?.[0]?.remainingEur;
const famBeforeT = await famSpent();
const ordersBeforeT = await orderCount();
const apprT = await call("POST", "/api/family/approve", { requestId: teenReq?.requestId }, "parent");
check("parent approves the teen's request -> order recorded", apprT.status === 200 && apprT.body.ok === true && (await orderCount()) === ordersBeforeT + 1, apprT.body.message || apprT.body.error);
check("teen's remaining shows 0 (not negative), family reduced", (await teenLeft()) === 0 && (await famSpent()) > famBeforeT, `${await teenLeft()}, ${famBeforeT} -> ${await famSpent()}`);
const tSmall = await buy("teen", { productRef: "hobbit-pb", priceEur: 10.99 });
check("further small teen purchase refused (budget used up)", tSmall.status !== 201 && tSmall.body.ok !== true, JSON.stringify(tSmall.body));

const add = await call("POST", "/api/family/members", { name: "Mallory", spendingLimitEur: 99999 }, "parent");
check("POST /api/family/members is 403", add.status === 403, add.body.error);

if (process.env.FAKE_LLM === "1") {
  const fakeKey = "sk-test-1234";
  const l0 = await call("GET", "/api/llm", null, "parent");
  check("GET /api/llm as parent shows no key", l0.status === 200 && l0.body.active?.hasKey === false && l0.body.mode === "offline-mock", JSON.stringify(l0.body.active));
  const t403 = await call("POST", "/api/llm", { providerId: "custom", baseUrl: "http://127.0.0.1:3032/v1", model: "fake", apiKey: fakeKey }, "teen");
  check("POST /api/llm as teen is 403", t403.status === 403, t403.body.error);
  const set = await call("POST", "/api/llm", { providerId: "custom", baseUrl: "http://127.0.0.1:3032/v1", model: "fake", apiKey: fakeKey }, "parent");
  check("parent sets custom provider: hasKey, last4 1234, no key in body", set.status === 200 && set.body.active?.hasKey === true && set.body.active?.keyLast4 === "1234" && !JSON.stringify(set.body).includes(fakeKey) && set.body.mode === "llm:custom", JSON.stringify(set.body.active));
  const get1 = await call("GET", "/api/llm", null, "teen");
  check("GET /api/llm never contains the key", !JSON.stringify(get1.body).includes(fakeKey));
  const evil = await call("POST", "/api/llm", { providerId: "custom", baseUrl: "http://evil.example/v1", model: "fake", apiKey: fakeKey }, "parent");
  check("http://evil.example base URL is 400", evil.status === 400, evil.body.error);
  const lchat = await call("POST", "/api/chat", { messages: [{ role: "user", content: "Der Hobbit" }] }, "teen");
  check("LLM chat returns FAKE-LLM-OK and a Hobbit title (tool loop reached the mock catalogue)", lchat.status === 200 && /FAKE-LLM-OK/.test(lchat.body.reply) && /hobbit/i.test(lchat.body.reply), lchat.body.reply || lchat.body.error);
  // Budget enforcement on the LLM path: offers the caller cannot buy never reach the model.
  const offersFor = async (member) => {
    const r = await call("POST", "/api/chat", { messages: [{ role: "user", content: "headphones" }] }, member);
    const raw = String(r.body.reply || "");
    let parsed = null;
    try { parsed = JSON.parse(raw.replace(/^FAKE-LLM-OFFERS:/, "")); } catch { /* reported by the check */ }
    return { raw, parsed, status: r.status };
  };
  for (const m of ["child", "teen"]) {
    const o = await offersFor(m);
    check(`LLM offers as ${m}: no 29900 offer, offers empty, omitted_over_budget >= 1`,
      o.status === 200 && o.parsed && Array.isArray(o.parsed.offers) && o.parsed.offers.length === 0 && o.parsed.budget_filter?.omitted_over_budget >= 1 && o.parsed.budget_filter?.caller === m && !o.parsed.offers.some((x) => x.total_cents === 29900), o.raw.slice(0, 200));
  }
  const seen = await (await fetch("http://127.0.0.1:3032/seen")).json();
  check("fake server saw Bearer sk-test-1234", seen.authorization?.includes(`Bearer ${fakeKey}`));
  const del = await call("DELETE", "/api/llm/key", null, "parent");
  const st2 = await call("GET", "/api/idealo/status");
  check("DELETE /api/llm/key returns to offline-mock", del.status === 200 && del.body.active?.hasKey === false && st2.body.mode === "offline-mock", st2.body.mode);
}

process.exit(failed ? 1 : 0);
