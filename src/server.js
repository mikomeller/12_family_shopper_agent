import "dotenv/config";
import OpenAI from "openai";
import express from "express";
import { readFile, writeFile, rename } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { beginIdealoConnection, connectIdealoTools, finishIdealoAuthorization, getIdealoAuthStatus, resetIdealoConnection } from "./idealo-oauth.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const familyPath = path.join(root, "data", "family.json");
const skillPath = path.join(root, "skills", "family-shopper", "SKILL.md");
const model = process.env.OPENAI_MODEL || "gpt-6.2-sol";
const app = express();
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || "missing-api-key" });
app.use(express.json({ limit: "64kb" }));

const euro = (amount) => new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(amount);
const readFamily = async () => JSON.parse(await readFile(familyPath, "utf8"));
const remaining = (member) => Math.max(0, Number(member.spendingLimitEur) - Number(member.spentEur));

async function recordMockPurchase({ memberName, productName, priceEur, productUrl }) {
  const family = await readFamily();
  const member = family.members.find((item) => item.name.toLowerCase() === memberName.trim().toLowerCase());
  if (!member) return { ok: false, message: `I couldn't find a family profile named ${memberName}.` };
  const price = Number(priceEur);
  if (!Number.isFinite(price) || price <= 0) return { ok: false, message: "The purchase price must be a positive euro amount." };
  if (price > remaining(member)) {
    return { ok: false, message: `Not recorded: ${euro(price)} is over ${member.name}'s remaining demo budget of ${euro(remaining(member))}.` };
  }
  member.spentEur = Math.round((Number(member.spentEur) + price) * 100) / 100;
  const purchase = {
    id: `mock-${Date.now()}`,
    member: member.name,
    productName: String(productName).trim(),
    priceEur: Math.round(price * 100) / 100,
    productUrl: productUrl || null,
    recordedAt: new Date().toISOString(),
    simulated: true,
  };
  family.mockPurchases.push(purchase);
  const tempPath = `${familyPath}.tmp`;
  await writeFile(tempPath, `${JSON.stringify(family, null, 2)}\n`, { mode: 0o600 });
  await rename(tempPath, familyPath);
  return { ok: true, message: `Mock purchase recorded for ${member.name}: ${purchase.productName} at ${euro(purchase.priceEur)}. ${euro(remaining(member))} remains. No real order was placed.`, purchase };
}

const purchaseTool = {
  type: "function",
  name: "record_mock_purchase",
  description: "Record a pretend purchase in the local family demo budget. Never places a real order. Call only when the user explicitly asks to record a mock purchase and the member, chosen product, and price are clear.",
  strict: true,
  parameters: {
    type: "object",
    properties: {
      memberName: { type: "string" },
      productName: { type: "string" },
      priceEur: { type: "number" },
      productUrl: { type: ["string", "null"] },
    },
    required: ["memberName", "productName", "priceEur", "productUrl"],
    additionalProperties: false,
  },
};

const normalizeName = (value) => String(value).toLocaleLowerCase("de-DE").replace(/[^\p{L}\p{N}]+/gu, " ").trim();

async function getInstructions(messages) {
  const [skill, family] = await Promise.all([readFile(skillPath, "utf8"), readFamily()]);
  const profiles = family.members.map((member) => ({
    name: member.name,
    spendingLimitEur: member.spendingLimitEur,
    spentEur: member.spentEur,
    remainingEur: remaining(member),
  }));
  const userMessages = messages.filter((message) => message.role === "user");
  const resolveMember = (message) => {
    const content = ` ${normalizeName(message?.content)} `;
    return family.members.filter((member) => content.includes(` ${normalizeName(member.name)} `));
  };
  const latestMatches = resolveMember(userMessages.at(-1));
  let selectedMember = latestMatches.length === 1 ? latestMatches[0] : null;
  if (!latestMatches.length) {
    for (let i = userMessages.length - 2; i >= 0 && !selectedMember; i -= 1) {
      const matches = resolveMember(userMessages[i]);
      if (matches.length === 1) selectedMember = matches[0];
    }
  }
  const memberContext = selectedMember
    ? `\n\nResolved shopping member: ${selectedMember.name}. Remaining demo budget: ${euro(remaining(selectedMember))}. The user has already named this member; do not ask who the request is for. Read the latest message as the shopping request and proceed with idealo search when it names a product or category. Ask a follow-up only if a genuinely necessary product detail is missing.`
    : "";
  return {
    instructions: `${skill}\n\nCurrent family demo budgets (source of truth):\n${JSON.stringify(profiles, null, 2)}${memberContext}\n\nFor live shopping use only the idealo MCP tools listed in the tool allowlist. For any mock purchase, call record_mock_purchase; never represent a tool call as a real order.`,
    memberName: selectedMember?.name || null,
  };
}

async function answer(messages) {
  const { instructions, memberName } = await getInstructions(messages);
  const connection = await connectIdealoTools();
  try {
    const toolMap = new Map(connection.tools.map((tool) => [tool.name, tool]));
    const tools = [
      ...connection.tools.map((tool) => ({
        type: "function",
        name: tool.name,
        description: tool.description || `Call the idealo ${tool.name} tool.`,
        parameters: tool.inputSchema || { type: "object", properties: {}, additionalProperties: true },
      })),
      purchaseTool,
    ];
    let response = await client.responses.create({ model, instructions, input: messages, tools });
    for (let turn = 0; turn < 6; turn += 1) {
      const calls = response.output.filter((item) => item.type === "function_call");
      if (!calls.length) return { reply: response.output_text || "I couldn't prepare a response. Please try again.", memberName };
      const outputs = [];
      for (const call of calls) {
        let result;
        try {
          if (call.name === "record_mock_purchase") {
            result = await recordMockPurchase(JSON.parse(call.arguments));
          } else if (toolMap.has(call.name)) {
            const toolResult = await connection.client.callTool({ name: call.name, arguments: JSON.parse(call.arguments) });
            result = toolResult.isError ? { error: true, content: toolResult.content } : (toolResult.structuredContent ?? toolResult.content);
          } else result = { error: true, message: "Unknown tool." };
        } catch (error) { result = { error: true, message: error.message }; }
        outputs.push({ type: "function_call_output", call_id: call.call_id, output: JSON.stringify(result) });
      }
      response = await client.responses.create({ model, instructions, input: [...response.output, ...outputs], tools });
    }
    return { reply: response.output_text || "I hit the tool-call limit. Please try again.", memberName };
  } finally {
    await connection.client.close().catch(() => {});
  }
}

app.get("/api/state", async (_request, response) => {
  try {
    const family = await readFamily();
    response.json({ members: family.members, purchases: family.mockPurchases || [] });
  } catch (error) { response.status(500).json({ error: error.message }); }
});

app.post("/api/family/members", async (request, response) => {
  const name = typeof request.body?.name === "string" ? request.body.name.trim() : "";
  const spendingLimitEur = Number(request.body?.spendingLimitEur);
  if (!name || name.length > 60) return response.status(400).json({ error: "Enter a name up to 60 characters." });
  if (!Number.isFinite(spendingLimitEur) || spendingLimitEur < 0 || spendingLimitEur > 1000000) {
    return response.status(400).json({ error: "Enter a budget between €0 and €1,000,000." });
  }
  try {
    const family = await readFamily();
    if (family.members.some((member) => member.name.trim().toLowerCase() === name.toLowerCase())) {
      return response.status(409).json({ error: "That family member already exists." });
    }
    const member = { name, spendingLimitEur: Math.round(spendingLimitEur * 100) / 100, spentEur: 0 };
    family.members.push(member);
    const tempPath = `${familyPath}.tmp`;
    await writeFile(tempPath, `${JSON.stringify(family, null, 2)}\n`, { mode: 0o600 });
    await rename(tempPath, familyPath);
    response.status(201).json({ member });
  } catch (error) { response.status(500).json({ error: error.message || "Could not save the family member." }); }
});

app.post("/api/family/mock-purchases", async (request, response) => {
  const { memberName, productName, priceEur, productUrl } = request.body || {};
  if (typeof memberName !== "string" || !memberName.trim() || typeof productName !== "string" || !productName.trim()) {
    return response.status(400).json({ error: "This product is missing its family member or name." });
  }
  if (productUrl !== null && productUrl !== undefined && (typeof productUrl !== "string" || !/^https?:\/\//i.test(productUrl))) {
    return response.status(400).json({ error: "This product link is invalid." });
  }
  const result = await recordMockPurchase({ memberName, productName, priceEur, productUrl: productUrl || null });
  if (!result.ok) return response.status(400).json({ error: result.message });
  response.status(201).json(result);
});


app.get("/api/idealo/status", async (_request, response) => {
  try { response.json(await getIdealoAuthStatus()); }
  catch (error) { response.status(500).json({ error: error.message }); }
});

app.post("/api/idealo/connect", async (_request, response) => {
  try { response.json(await beginIdealoConnection()); }
  catch (error) { response.status(502).json({ error: error.message || "Could not connect to idealo." }); }
});

app.post("/api/idealo/reconnect", async (_request, response) => {
  try {
    await resetIdealoConnection();
    response.json(await beginIdealoConnection());
  } catch (error) { response.status(502).json({ error: error.message || "Could not reconnect to idealo." }); }
});

app.get("/oauth/callback", async (request, response) => {
  const params = new URL(request.originalUrl, "http://127.0.0.1:3001").searchParams;
  try {
    await finishIdealoAuthorization(params);
    response.type("html").send("<!doctype html><html><meta charset='utf-8'><title>Connected</title><body style='font:16px system-ui;max-width:520px;margin:15vh auto;padding:24px;color:#34483f'><h1>idealo connected</h1><p>You can close this tab and return to Family Shopper.</p></body></html>");
  } catch {
    const issue = (await getIdealoAuthStatus()).error;
    if (issue?.includes("403")) {
      response.status(403).type("html").send("<!doctype html><html><meta charset='utf-8'><title>idealo access denied</title><body style='font:16px system-ui;max-width:520px;margin:15vh auto;padding:24px;color:#34483f'><h1>Sign-in saved, but idealo denied tool access</h1><p>Family Shopper received a valid sign-in, but idealo returned 403 Forbidden for its MCP tools. Contact mcp@idealo.de and ask them to check access for your MCP account.</p><p>Return to Family Shopper to see the current connection status.</p></body></html>");
      return;
    }
    response.status(400).type("html").send("<!doctype html><html><meta charset='utf-8'><title>Connection issue</title><body style='font:16px system-ui;max-width:520px;margin:15vh auto;padding:24px;color:#34483f'><h1>Could not finish sign-in</h1><p>Return to Family Shopper and try connecting again.</p></body></html>");
  }
});

app.post("/api/chat", async (request, response) => {
  const messages = request.body?.messages;
  if (!Array.isArray(messages) || !messages.length || messages.length > 24 || messages.some((message) => !["user", "assistant"].includes(message.role) || typeof message.content !== "string")) {
    return response.status(400).json({ error: "Send a short chat as user and assistant messages." });
  }
  if (!process.env.OPENAI_API_KEY) return response.status(503).json({ error: "Add OPENAI_API_KEY to your .env file, then restart the app." });
  try {
    const result = await answer(messages.map(({ role, content }) => ({ role, content })));
    response.json(result);
  } catch (error) {
    if (error?.name === "UnauthorizedError") return response.status(409).json({ authRequired: true, error: "Connect idealo to search products." });
    response.status(502).json({ error: error.message || "The shopper could not connect to its services." });
  }
});

const port = Number(process.env.PORT || 3001);
app.listen(port, "127.0.0.1", () => console.log(`Family Shopper server is ready at http://127.0.0.1:${port}`));
