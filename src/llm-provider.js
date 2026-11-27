// Author:    mikomeller
// Version:   0.1.0
// Filename:  llm-provider.js
// Pathname:  src/llm-provider.js
// Purpose:   Bring-your-own model provider: preset registry, in-memory key store (never on disk, never returned), Chat Completions tool loop
const PRESETS = [
  { id: "openai", label: "OpenAI / Codex API key", baseUrl: "https://api.openai.com/v1", defaultModel: process.env.OPENAI_MODEL || "gpt-6.2-sol", api: "responses", editableBaseUrl: false },
  // Base URL confirmed on docs.tokenfactory.nebius.com (2026-11-27). The default model is a guess: pick one from your Nebius console.
  { id: "nebius", label: "Nebius Token Factory", baseUrl: "https://api.tokenfactory.nebius.com/v1", defaultModel: "meta-llama/Llama-3.3-70B-Instruct", api: "chat-completions", editableBaseUrl: true, unverified: false, modelUnverified: true, note: "Base URL taken from Nebius' documentation; check the model name in your Nebius console." },
  { id: "custom", label: "Any OpenAI-compatible endpoint", baseUrl: "", defaultModel: "", api: "chat-completions", editableBaseUrl: true },
];
export const presets = () => PRESETS.map((p) => ({ ...p }));
const preset = (id) => PRESETS.find((p) => p.id === id);

export function validateBaseUrl(value) {
  let url;
  try { url = new URL(String(value || "").trim()); } catch { return "The base URL is not a valid URL."; }
  if (url.username || url.password) return "The base URL must not contain credentials.";
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (url.protocol !== "https:" && !(url.protocol === "http:" && local)) return "The base URL must start with https:// (http:// only for localhost).";
  return null;
}

let config = initialConfig();
function initialConfig() {
  const e = process.env;
  const providerId = preset(e.LLM_PROVIDER) ? e.LLM_PROVIDER : (!e.LLM_API_KEY && e.OPENAI_API_KEY ? "openai" : (e.LLM_API_KEY ? "custom" : "openai"));
  const p = preset(providerId);
  const apiKey = e.LLM_API_KEY || (providerId === "openai" ? e.OPENAI_API_KEY : "") || "";
  const baseUrl = e.LLM_BASE_URL && !validateBaseUrl(e.LLM_BASE_URL) ? e.LLM_BASE_URL.trim() : p.baseUrl;
  return { providerId, baseUrl, model: e.LLM_MODEL || p.defaultModel, apiKey };
}

export const hasKey = () => Boolean(config.apiKey);
export const activeConfig = () => ({ ...config });
export const activeApi = () => preset(config.providerId).api;
export const mode = () => (hasKey() && process.env.OFFLINE_DEMO !== "1" ? `llm:${config.providerId}` : "offline-mock");

// Public view: never contains the key, only whether one exists and its last 4 characters.
export function publicState() {
  return {
    providers: presets(),
    active: { providerId: config.providerId, baseUrl: config.baseUrl, model: config.model, hasKey: hasKey(), keyLast4: hasKey() ? config.apiKey.slice(-4) : null },
    mode: mode(),
  };
}

// Returns an error string or null. Omitted apiKey keeps the current key when the provider stays the same.
export function setConfig({ providerId, baseUrl, model, apiKey }) {
  const p = preset(providerId);
  if (!p) return "Unknown provider.";
  const url = String(p.editableBaseUrl ? (baseUrl || p.baseUrl) : p.baseUrl).trim();
  const problem = validateBaseUrl(url);
  if (problem) return problem;
  const chosenModel = String(model || p.defaultModel || "").trim().slice(0, 200);
  if (!chosenModel) return "Enter a model name.";
  let key = config.providerId === providerId ? config.apiKey : "";
  if (typeof apiKey === "string" && apiKey.trim()) key = apiKey.trim().slice(0, 500);
  config = { providerId, baseUrl: url.replace(/\/+$/, ""), model: chosenModel, apiKey: key };
  return null;
}
export const forgetKey = () => { config = { ...config, apiKey: "" }; };

// Responses-style tool definitions -> Chat Completions format.
export const toChatTools = (tools) => tools.map((t) => ({ type: "function", function: { name: t.name, description: t.description, parameters: t.parameters } }));

// Chat Completions tool loop (up to 6 turns). callTool(name, args) returns a JSON-able result; errors are fed back to the model.
export async function chatCompletionsLoop({ system, messages, tools, callTool, maxTurns = 6 }) {
  const { baseUrl, model, apiKey } = config;
  const convo = [{ role: "system", content: system }, ...messages];
  const chatTools = toChatTools(tools);
  for (let turn = 0; turn < maxTurns; turn += 1) {
    const res = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({ model, messages: convo, tools: chatTools }),
    });
    if (!res.ok) {
      const detail = (await res.text().catch(() => "")).replace(/\s+/g, " ").slice(0, 200);
      throw new Error(`The model provider answered ${res.status}.${res.status === 401 || res.status === 403 ? " Check the API key." : ""} ${detail.split(apiKey).join("***")}`.trim());
    }
    const msg = (await res.json()).choices?.[0]?.message;
    if (!msg) throw new Error("The model provider returned no message.");
    const calls = msg.tool_calls || [];
    if (!calls.length) return msg.content || "I couldn't prepare a response. Please try again.";
    convo.push({ role: "assistant", content: msg.content ?? null, tool_calls: calls });
    for (const call of calls) {
      let result;
      try { result = await callTool(call.function?.name, JSON.parse(call.function?.arguments || "{}")); }
      catch (error) { result = { error: true, message: error.message }; }
      convo.push({ role: "tool", tool_call_id: call.id, content: JSON.stringify(result) });
    }
  }
  return "I hit the tool-call limit. Please try again.";
}
