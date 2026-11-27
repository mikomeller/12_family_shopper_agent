// Author:    mikomeller
// Version:   0.1.0
// Filename:  wallet-client.js
// Pathname:  src/wallet-client.js
// Purpose:   Node client for the Family Wallet MCP: one stdio server process per member (signed token), callWallet(memberId, tool, args)
import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// Secret stays in memory (or in the user's .env); it is never written anywhere by this code.
const secret = process.env.WALLET_TOKEN_SECRET || randomBytes(32).toString("hex");
const baseEnv = { ...process.env, PYTHONPATH: path.join(root, "src"), WALLET_TOKEN_SECRET: secret };
delete baseEnv.WALLET_MEMBER_TOKEN;
const uvBin = process.env.UV_BIN || "uv";

let tokens = null;
const clients = new Map();

function loadTokens() {
  if (!tokens) {
    const out = execFileSync(uvBin, ["run", "python", "scripts/wallet_tokens.py"], { cwd: root, env: baseEnv, encoding: "utf8" });
    tokens = JSON.parse(out);
  }
  return tokens;
}

export function walletMemberIds() { return Object.keys(loadTokens()); }

async function clientFor(memberId) {
  const token = loadTokens()[memberId];
  if (!token) throw new Error(`Unknown wallet member: ${memberId}`);
  if (!clients.has(memberId)) {
    clients.set(memberId, (async () => {
      const transport = new StdioClientTransport({
        command: uvBin,
        args: ["run", "python", "-m", "family_shopper.wallet.server"],
        cwd: root,
        env: { ...baseEnv, WALLET_MEMBER_TOKEN: token },
        stderr: "ignore",
      });
      const client = new Client({ name: "family-shopper-ui", version: "0.1.0" });
      await client.connect(transport);
      return client;
    })().catch((error) => { clients.delete(memberId); throw error; }));
  }
  return clients.get(memberId);
}

export async function callWallet(memberId, toolName, args = {}) {
  const client = await clientFor(memberId);
  const result = await client.callTool({ name: toolName, arguments: args });
  if (result.structuredContent) return result.structuredContent;
  const text = (result.content || []).find((part) => part.type === "text")?.text;
  try { return JSON.parse(text); } catch { return { ok: false, error_code: "tool_error", reason: text || "Wallet tool failed." }; }
}

export async function closeWallet() {
  const open = [...clients.values()];
  clients.clear();
  await Promise.all(open.map((p) => p.then((c) => c.close()).catch(() => {})));
}

for (const signal of ["SIGINT", "SIGTERM"]) process.once(signal, () => closeWallet().finally(() => process.exit(0)));
