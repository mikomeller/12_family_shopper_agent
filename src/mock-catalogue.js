// Author:    mikomeller
// Version:   0.1.1
// Filename:  mock-catalogue.js
// Pathname:  src/mock-catalogue.js
// Purpose:   Gives a live LLM the idealo MOCK tools (stdio MCP) when idealo OAuth is not connected
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// Returns { tools (Responses-style), callTool(name,args), close() }.
export async function connectMockTools() {
  const client = new Client({ name: "family-shopper-llm", version: "0.1.0" });
  await client.connect(new StdioClientTransport({
    command: process.env.UV_BIN || "uv",
    args: ["run", "python", "-m", "family_shopper.idealo_mock.server"],
    cwd: root,
    env: { ...process.env, PYTHONPATH: path.join(root, "src") },
    stderr: "ignore",
  }));
  const listed = (await client.listTools()).tools;
  const names = new Set(listed.map((t) => t.name));
  return {
    tools: listed.map((t) => ({ type: "function", name: t.name, description: t.description || `Call the mock idealo ${t.name} tool.`, parameters: t.inputSchema || { type: "object", properties: {}, additionalProperties: true } })),
    async callTool(name, args) {
      if (!names.has(name)) return { error: true, message: "Unknown tool." };
      const r = await client.callTool({ name, arguments: args });
      return r.isError ? { error: true, content: r.content } : (r.structuredContent ?? r.content);
    },
    close: () => client.close().catch(() => {}),
  };
}

// Shared lazy stdio client for server-side verification of purchases (the server, not the client, names the price).
let shared = null;
export async function mockCatalogueCall(name, args) {
  if (!shared) shared = connectMockTools().catch((error) => { shared = null; throw error; });
  const conn = await shared;
  return conn.callTool(name, args); // a tool error comes back as { error: true, ... }; a broken connection throws
}
