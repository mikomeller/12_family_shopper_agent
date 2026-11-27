import { randomUUID } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { Client, StreamableHTTPClientTransport, UnauthorizedError } from "@modelcontextprotocol/client";

const oauthPath = path.resolve(".data/idealo-oauth.json");
const serverUrl = process.env.IDEALO_MCP_URL || "https://mcp.idealo.com/mcp";
const callbackUrl = "http://localhost:6274/oauth/callback";
let store = { clients: {}, tokens: {}, lastIssuer: null, verifier: null, discovery: null, state: null };
let loaded = false;
let pendingTransport;
let toolsVerified = false;
let connectionIssue = null;

function describeConnectionIssue(error) {
  const message = String(error?.message || error || "Connection could not be verified.");
  if (error?.status === 403 || /\b403\b|Forbidden/i.test(message)) {
    return "idealo returned 403 Forbidden. Sign-in was saved, but this account cannot access the idealo MCP tools yet. Contact mcp@idealo.de and include this message.";
  }
  return `idealo sign-in could not be verified: ${message}`;
}

async function persist() {
  await mkdir(path.dirname(oauthPath), { recursive: true, mode: 0o700 });
  await writeFile(oauthPath, `${JSON.stringify(store, null, 2)}\n`, { mode: 0o600 });
}

async function load() {
  if (loaded) return;
  loaded = true;
  try { store = { ...store, ...JSON.parse(await readFile(oauthPath, "utf8")) }; }
  catch (error) { if (error.code !== "ENOENT") throw error; }
}

class IdealoOAuthProvider {
  constructor() { this.authorizationUrl = null; }
  get redirectUrl() { return callbackUrl; }
  get clientMetadata() {
    return {
      client_name: "Family Shopper",
      redirect_uris: [callbackUrl],
      grant_types: ["authorization_code", "refresh_token"],
      response_types: ["code"],
      token_endpoint_auth_method: "none",
      application_type: "native",
    };
  }
  async state() { await load(); store.state = randomUUID(); await persist(); return store.state; }
  async clientInformation(context) { await load(); return store.clients[context?.issuer || "default"]; }
  async saveClientInformation(info, context) {
    await load();
    store.clients[context?.issuer || info.issuer || "default"] = info;
    await persist();
  }
  async tokens(context) {
    await load();
    return store.tokens[context?.issuer || store.lastIssuer || "default"];
  }
  async saveTokens(tokens, context) {
    await load();
    const issuer = context?.issuer || tokens.issuer || store.lastIssuer || "default";
    store.tokens[issuer] = tokens;
    store.lastIssuer = issuer;
    await persist();
  }
  async saveCodeVerifier(verifier) { await load(); store.verifier = verifier; await persist(); }
  async codeVerifier() { await load(); if (!store.verifier) throw new Error("Missing OAuth verification value."); return store.verifier; }
  async saveDiscoveryState(discovery) { await load(); store.discovery = discovery; await persist(); }
  async discoveryState() { await load(); return store.discovery || undefined; }
  async redirectToAuthorization(url) { this.authorizationUrl = url.href; }
}

export const idealoAuthProvider = new IdealoOAuthProvider();

export async function getIdealoAuthStatus() {
  await load();
  const tokens = store.tokens[store.lastIssuer || "default"];
  return {
    connected: Boolean(tokens?.access_token && toolsVerified),
    credentialsSaved: Boolean(tokens?.access_token),
    account: toolsVerified ? "Connected to idealo" : null,
    error: connectionIssue,
  };
}

export async function beginIdealoConnection() {
  await load();
  idealoAuthProvider.authorizationUrl = null;
  const client = new Client({ name: "family-shopper", version: "0.1.0" });
  const transport = new StreamableHTTPClientTransport(new URL(serverUrl), { authProvider: idealoAuthProvider });
  try {
    await client.connect(transport);
    await client.listTools();
    toolsVerified = true;
    connectionIssue = null;
    await client.close();
    return { connected: true };
  } catch (error) {
    toolsVerified = false;
    if (!(error instanceof UnauthorizedError)) connectionIssue = describeConnectionIssue(error);
    if (!(error instanceof UnauthorizedError)) {
      await transport.close().catch(() => {});
      throw new Error(connectionIssue);
    }
    pendingTransport = transport;
    if (!idealoAuthProvider.authorizationUrl) throw new Error("idealo did not provide a sign-in link.");
    return { connected: false, authorizationUrl: idealoAuthProvider.authorizationUrl };
  }
}

export async function finishIdealoAuthorization(params) {
  await load();
  if (!pendingTransport || params.get("state") !== store.state) {
    throw new Error("That sign-in link is no longer valid. Return to Family Shopper and try Connect again.");
  }
  try {
    await pendingTransport.finishAuth(params);
    await pendingTransport.close().catch(() => {});
    pendingTransport = undefined;
    const client = new Client({ name: "family-shopper", version: "0.1.0" });
    const transport = new StreamableHTTPClientTransport(new URL(serverUrl), { authProvider: idealoAuthProvider });
    try {
      await client.connect(transport);
      await client.listTools();
      toolsVerified = true;
      connectionIssue = null;
    } finally {
      await client.close().catch(() => {});
    }
  } catch (error) {
    toolsVerified = false;
    connectionIssue = describeConnectionIssue(error);
    throw new Error(connectionIssue);
  }
}

export async function connectIdealoTools() {
  await load();
  const client = new Client({ name: "family-shopper", version: "0.1.0" });
  const transport = new StreamableHTTPClientTransport(new URL(serverUrl), { authProvider: idealoAuthProvider });
  try {
    await client.connect(transport);
    const { tools } = await client.listTools();
    toolsVerified = true;
    connectionIssue = null;
    return { client, transport, tools: tools.filter((tool) => ["search_products", "get_product_details", "get_product_offers", "get_product_price_history"].includes(tool.name)) };
  } catch (error) {
    toolsVerified = false;
    connectionIssue = describeConnectionIssue(error);
    await client.close().catch(() => {});
    throw new Error(connectionIssue);
  }
}

export { UnauthorizedError };
