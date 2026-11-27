import "dotenv/config";
import OpenAI from "openai";
import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import { readFile, writeFile, rename } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const familyPath = path.join(root, "data", "family.json");
const skillPath = path.join(root, "skills", "family-shopper", "SKILL.md");
const model = process.env.OPENAI_MODEL || "gpt-6.2-sol";
const idealoUrl = process.env.IDEALO_MCP_URL || "https://mcp.idealo.com/mcp";
const allowedIdealoTools = [
  "search_products",
  "get_product_details",
  "get_product_offers",
  "get_product_price_history",
];

function euro(value) {
  return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(value);
}

async function readFamily() {
  return JSON.parse(await readFile(familyPath, "utf8"));
}

function getMember(family, name) {
  return family.members.find((member) => member.name.toLowerCase() === name.trim().toLowerCase());
}

function remaining(member) {
  return Math.max(0, Number(member.spendingLimitEur) - Number(member.spentEur));
}

function showBudgets(family) {
  for (const member of family.members) {
    console.log(`${member.name}: ${euro(member.spentEur)} spent of ${euro(member.spendingLimitEur)}; ${euro(remaining(member))} left`);
  }
}

async function saveFamily(family) {
  const tempPath = `${familyPath}.tmp`;
  await writeFile(tempPath, `${JSON.stringify(family, null, 2)}\n`, { mode: 0o600 });
  await rename(tempPath, familyPath);
}

async function recordMockPurchase({ memberName, productName, priceEur, productUrl }) {
  const family = await readFamily();
  const member = getMember(family, memberName);
  if (!member) {
    return { ok: false, message: `I couldn't find a family profile named ${memberName}.` };
  }
  const price = Number(priceEur);
  if (!Number.isFinite(price) || price <= 0) {
    return { ok: false, message: "The purchase price must be a positive euro amount." };
  }
  if (price > remaining(member)) {
    return {
      ok: false,
      message: `Not recorded: ${euro(price)} is over ${member.name}'s remaining demo budget of ${euro(remaining(member))}.`,
    };
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
  await saveFamily(family);
  return {
    ok: true,
    message: `Mock purchase recorded for ${member.name}: ${purchase.productName} at ${euro(purchase.priceEur)}. ${euro(remaining(member))} remains. No real order was placed.`,
    purchase,
  };
}

const purchaseTool = {
  type: "function",
  name: "record_mock_purchase",
  description: "Record a pretend purchase in the local family demo budget. Never places a real order. Call only when the user explicitly asks to record a mock purchase and the member, chosen product, and price are clear.",
  strict: true,
  parameters: {
    type: "object",
    properties: {
      memberName: { type: "string", description: "Family member profile name." },
      productName: { type: "string", description: "The product the user chose." },
      priceEur: { type: "number", description: "The chosen product's price in euros." },
      productUrl: { type: ["string", "null"], description: "Product or offer link, or null if unavailable." },
    },
    required: ["memberName", "productName", "priceEur", "productUrl"],
    additionalProperties: false,
  },
};

async function respond(client, skill, userText) {
  const family = await readFamily();
  const profiles = family.members.map((m) => ({
    name: m.name,
    spendingLimitEur: m.spendingLimitEur,
    spentEur: m.spentEur,
    remainingEur: remaining(m),
  }));
  const instructions = `${skill}\n\nCurrent family demo budgets (source of truth):\n${JSON.stringify(profiles, null, 2)}\n\nFor live shopping use only the idealo MCP tools listed in the tool allowlist. For any mock purchase, call record_mock_purchase; never represent a tool call as a real order.`;
  const tools = [
    {
      type: "mcp",
      server_label: "idealo",
      server_url: idealoUrl,
      authorization: process.env.IDEALO_MCP_ACCESS_TOKEN,
      require_approval: { never: { tool_names: allowedIdealoTools } },
    },
    purchaseTool,
  ];

  let response = await client.responses.create({ model, instructions, input: userText, tools });
  for (let turn = 0; turn < 6; turn += 1) {
    const calls = response.output.filter((item) => item.type === "function_call");
    if (calls.length === 0) return response.output_text || "I couldn't prepare a response. Please try again.";

    const outputs = [];
    for (const call of calls) {
      if (call.name !== "record_mock_purchase") continue;
      let result;
      try {
        result = await recordMockPurchase(JSON.parse(call.arguments));
      } catch (error) {
        result = { ok: false, message: `The mock purchase could not be saved: ${error.message}` };
      }
      outputs.push({ type: "function_call_output", call_id: call.call_id, output: JSON.stringify(result) });
    }
    if (outputs.length === 0) return response.output_text || "I couldn't complete that request.";
    response = await client.responses.create({
      model,
      instructions,
      input: [...response.output, ...outputs],
      tools,
    });
  }
  return response.output_text || "I hit the tool-call limit for this request. Please try a shorter request.";
}

function printHelp() {
  console.log("Ask for a product search, for example: Find headphones for Member 1 under €60.");
  console.log("Commands: /budgets, /help, /quit");
  console.log("You can ask to record a mock purchase after choosing a product; no real order can be placed.");
}

async function main() {
  if (!process.env.OPENAI_API_KEY) {
    console.error("Add OPENAI_API_KEY to your .env file. See README.md for setup.");
    process.exitCode = 1;
    return;
  }
  if (!process.env.IDEALO_MCP_ACCESS_TOKEN) {
    console.error("Add IDEALO_MCP_ACCESS_TOKEN to your .env file. See README.md for setup.");
    process.exitCode = 1;
    return;
  }
  const [skill] = await Promise.all([
    readFile(skillPath, "utf8"),
    readFamily(),
  ]);
  const client = new OpenAI();
  const rl = readline.createInterface({ input, output, prompt: "shopper> " });
  console.log("Family Shopper — searches are live; purchases are pretend only. Type /help for help.");
  rl.prompt();
  for await (const raw of rl) {
    const text = raw.trim();
    if (!text) { rl.prompt(); continue; }
    const command = text.toLowerCase();
    if (command === "/quit" || command === "/exit") break;
    if (command === "/help") printHelp();
    else if (command === "/budgets") showBudgets(await readFamily());
    else {
      try {
        console.log(`\n${await respond(client, skill, text)}\n`);
      } catch (error) {
        console.error(`\nRequest failed: ${error.message}\n`);
      }
    }
    rl.prompt();
  }
  rl.close();
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
