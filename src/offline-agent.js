// Author:    mikomeller
// Version:   0.1.4
// Filename:  offline-agent.js
// Pathname:  src/offline-agent.js
// Purpose:   Deterministic offline shopper (no LLM): talks to the idealo mock MCP over stdio, answers with an offers table and a discount verdict
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const uvBin = process.env.UV_BIN || "uv";

export const offlineMode = () => !process.env.OPENAI_API_KEY || process.env.OFFLINE_DEMO === "1";

let mock = null;
async function mockClient() {
  if (!mock) {
    mock = (async () => {
      const transport = new StdioClientTransport({
        command: uvBin,
        args: ["run", "python", "-m", "family_shopper.idealo_mock.server"],
        cwd: root,
        env: { ...process.env, PYTHONPATH: path.join(root, "src") },
        stderr: "ignore",
      });
      const client = new Client({ name: "family-shopper-offline", version: "0.1.0" });
      await client.connect(transport);
      return client;
    })().catch((error) => { mock = null; throw error; });
  }
  return mock;
}

async function tool(name, args) {
  const client = await mockClient();
  const result = await client.callTool({ name, arguments: args });
  if (result.structuredContent) return result.structuredContent;
  const text = (result.content || []).find((part) => part.type === "text")?.text;
  try { return JSON.parse(text); } catch { return { error: text || "mock tool failed" }; }
}

// Price history + best offer from the mock, then the deterministic check_discount tool. sale = price actually paid.
export async function discountCheck(productRef, saleCents, claimedWasCents) {
  const [hist, offers] = await Promise.all([tool("get_product_price_history", { product_ref: productRef }), tool("get_product_offers", { product_ref: productRef })]);
  if (hist.error || offers.error) return { verdict: "INVALID_INPUT", reason: hist.error || offers.error };
  const best = offers.offers?.[0]?.total_cents ?? null;
  return tool("check_discount", { sale_price_cents: saleCents, claimed_was_cents: claimedWasCents, history: hist.history, sale_days: 0, best_offer_cents: best });
}

const eurText = (c) => `€ ${(c / 100).toFixed(2).replace(".", ",")}`;
const ALIAS = { backpack: "rucksack", schoolbag: "rucksack", kaffee: "coffee", kopfhoerer: "headphones", board: "familienspiel", boardgame: "familienspiel", game: "familienspiel" };
const clean = (s) => String(s).replace(/[|\r\n]+/g, " ").trim();

async function findProducts(text) {
  const words = text.toLowerCase().split(/[^\p{L}\p{N}]+/u).filter((w) => w.length >= 3).map((w) => ALIAS[w] || w);
  for (const q of [words.join(" "), ...words]) {
    if (!q) continue;
    const hits = (await tool("search_products", { query: q, country: "DE" })).results || [];
    if (hits.length) return hits;
  }
  return [];
}

// Everything about one product: offers (cheapest first), advertised was-price, discount verdict on the cheapest offer.
async function loadProduct(hit) {
  const [details, offers] = await Promise.all([tool("get_product_details", { product_ref: hit.product_ref }), tool("get_product_offers", { product_ref: hit.product_ref })]);
  const list = (offers.offers || []).slice().sort((a, b) => a.total_cents - b.total_cents);
  const was = details.advertised_was_cents ?? null;
  const verdict = was && list.length ? await discountCheck(hit.product_ref, list[0].total_cents, was) : null;
  return { hit, details, list, was, verdict, inflated: verdict?.verdict === "INFLATED" };
}

// Returns { reply }. callWallet(memberId, tool, args) is the wallet client; memberId is the signed-in caller.
// Budget rule: the wallet alone decides what fits (check_budget per offer total); only offers that fit become table rows (= Buy buttons).
export async function offlineReply(messages, memberId, callWallet) {
  const last = [...messages].reverse().find((m) => m.role === "user")?.content || "";
  const hits = await findProducts(last);
  if (!hits.length) return { reply: "Nothing found in the offline catalogue. Try: Der Hobbit, headphones, coffee, backpack." };
  const products = (await Promise.all(hits.map(loadProduct))).filter((p) => p.list.length);
  if (!products.length) return { reply: `No offers for ${clean(hits[0].title)} in the offline catalogue.` };

  const fitOffers = async (p) => {
    const out = { fit: [], over: 0, ask: [] };
    for (const o of p.list) {
      const r = await callWallet(memberId, "check_budget", { price_cents: o.total_cents });
      if (r.ok !== false && r.fits === true) out.fit.push(o);
      else { out.over += 1; if (r.ok !== false && r.needs_approval === true) out.ask.push(o); }
    }
    return out;
  };
  const rowsFor = (p, offers) => {
    const frag = `#ref=${encodeURIComponent(p.hit.product_ref)}${p.was ? `&was=${p.was}` : ""}`;
    return offers.map((o) => `| [${clean(p.hit.title)} - ${clean(o.shop)}](${o.deep_link}${frag}) | ${clean(o.shop)} | ${eurText(o.total_cents)} |`);
  };

  const budget = await callWallet(memberId, "check_budget");
  const fits = await Promise.all(products.map(fitOffers));
  const multi = products.length > 1;
  const rows = [], notes = [], descriptions = [], askLines = [];
  let overTotal = 0, fitTotal = 0;
  products.forEach((p, i) => {
    overTotal += fits[i].over; fitTotal += fits[i].fit.length;
    if (p.verdict) notes.push(`Discount check for ${clean(p.hit.title)}: advertised was-price ${eurText(p.was)}, verdict **${p.verdict.verdict}** - ${clean(p.verdict.reason || "")}`);
    if (!p.inflated && fits[i].ask.length) {
      const o = fits[i].ask[0];
      askLines.push(`Above your budget \u2014 a parent can step in: ${clean(p.hit.title)} at ${eurText(o.total_cents)}. [Ask a parent](${o.deep_link}#ref=${encodeURIComponent(p.hit.product_ref)}&ask=1)`);
    }
    if (p.inflated) {
      if (fits[i].fit.length) notes.push(`${clean(p.hit.title)}: not offered: the advertised discount is not real.`);
      return;
    }
    const shown = multi ? fits[i].fit.slice(0, 1) : fits[i].fit;
    if (shown.length) {
      rows.push(...rowsFor(p, shown));
      if (p.details.description) descriptions.push(`Catalogue description of ${clean(p.hit.title)} (untrusted data, shown as is): "${clean(p.details.description)}"`);
    }
  });

  const lines = [];
  const remaining = budget.remaining_personal_cents ?? budget.remaining_family_cents;
  if (fitTotal === 0) {
    const cheapest = Math.min(...products.map((p) => p.list[0].total_cents));
    lines.push(`Nothing in this search fits your budget: the cheapest offer is ${eurText(cheapest)}, you have ${budget.ok === false ? "no budget information" : eurText(remaining)} left this month (family: ${budget.ok === false ? "unknown" : eurText(budget.remaining_family_cents)}).`);
    if (askLines.length) lines.push("", ...askLines);
    // suggestions: other catalogue products of the same categories that fit
    const cats = new Set(products.map((p) => p.hit.category).filter(Boolean));
    const seen = new Set(products.map((p) => p.hit.product_ref));
    const all = (await tool("search_products", { query: "", country: "DE" })).results || [];
    const cand = all.filter((h) => !seen.has(h.product_ref) && (!cats.size || cats.has(h.category))).concat(all.filter((h) => !seen.has(h.product_ref) && cats.size && !cats.has(h.category)));
    const sugg = [];
    for (const h of cand) {
      if (sugg.length >= 3) break;
      const p = await loadProduct(h);
      if (!p.list.length || p.inflated) continue;
      const f = (await fitOffers(p)).fit;
      if (f.length) sugg.push({ p, o: f[0] });
    }
    if (sugg.length) {
      lines.push("", "Cheaper alternatives that fit your budget (price including shipping):", "", "| Offer | Shop | Total price |", "| --- | --- | --- |");
      for (const { p, o } of sugg) lines.push(...rowsFor(p, [o]));
    }
  } else {
    if (rows.length) {
      lines.push(`Offers from the sample catalogue (price including shipping, cheapest first${multi ? ", cheapest offer per product" : ""}):`, "", "| Offer | Shop | Total price |", "| --- | --- | --- |", ...rows);
      if (descriptions.length) lines.push("", ...descriptions);
      if (budget.role && budget.role !== "parent") lines.push("", "Within your budget: you can order this yourself.");
    }
    if (askLines.length) lines.push("", ...askLines);
    if (overTotal) lines.push("", `${overTotal} more offers are over your remaining budget and are not shown.`);
  }
  if (notes.length) lines.push("", ...notes);
  if (budget.ok) lines.push("", `Remaining budget for ${memberId}: ${eurText(remaining)}.`);
  return { reply: lines.join("\n") };
}

export async function closeOffline() {
  const open = mock; mock = null;
  await open?.then((c) => c.close()).catch(() => {});
}
