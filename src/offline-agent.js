// Author:    mikomeller
// Version:   0.1.0
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
const ALIAS = { backpack: "rucksack", schoolbag: "rucksack", kaffee: "coffee", kopfhoerer: "headphones" };
const clean = (s) => String(s).replace(/[|\r\n]+/g, " ").trim();

async function findProduct(text) {
  const words = text.toLowerCase().split(/[^\p{L}\p{N}]+/u).filter((w) => w.length >= 3).map((w) => ALIAS[w] || w);
  for (const q of [words.join(" "), ...words]) {
    if (!q) continue;
    const hit = (await tool("search_products", { query: q, country: "DE" })).results?.[0];
    if (hit) return hit;
  }
  return null;
}

// Returns { reply }. callWallet(memberId, tool, args) is the wallet client; memberId is the signed-in caller.
export async function offlineReply(messages, memberId, callWallet) {
  const last = [...messages].reverse().find((m) => m.role === "user")?.content || "";
  const hit = await findProduct(last);
  if (!hit) return { reply: "Nothing found in the offline catalogue. Try: Der Hobbit, headphones, coffee, backpack." };
  const [details, offers] = await Promise.all([tool("get_product_details", { product_ref: hit.product_ref }), tool("get_product_offers", { product_ref: hit.product_ref })]);
  const list = (offers.offers || []).slice().sort((a, b) => a.total_cents - b.total_cents);
  if (!list.length) return { reply: `No offers for ${clean(hit.title)} in the offline catalogue.` };
  const was = details.advertised_was_cents ?? null;
  const frag = `#ref=${encodeURIComponent(hit.product_ref)}${was ? `&was=${was}` : ""}`;
  const lines = [`Offline demo offers for **${clean(hit.title)}** (price including shipping, cheapest first):`, "", "| Offer | Shop | Total price |", "| --- | --- | --- |"];
  for (const o of list) lines.push(`| [${clean(hit.title)} - ${clean(o.shop)}](${o.deep_link}${frag}) | ${clean(o.shop)} | ${eurText(o.total_cents)} |`);
  if (details.description) lines.push("", `Catalogue description (untrusted data, shown as is): "${clean(details.description)}"`);
  if (was) {
    const v = await discountCheck(hit.product_ref, list[0].total_cents, was);
    lines.push("", `Discount check: advertised was-price ${eurText(was)}, verdict **${v.verdict}** - ${clean(v.reason || "")}`);
  }
  const b = await callWallet(memberId, "check_budget");
  if (b.ok) lines.push("", `Remaining budget for ${memberId}: ${eurText(b.remaining_personal_cents ?? b.remaining_family_cents)}.`);
  return { reply: lines.join("\n") };
}

export async function closeOffline() {
  const open = mock; mock = null;
  await open?.then((c) => c.close()).catch(() => {});
}
