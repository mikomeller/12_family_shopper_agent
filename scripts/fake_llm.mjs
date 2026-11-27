// Author:    mikomeller
// Version:   0.1.1
// Filename:  fake_llm.mjs
// Pathname:  scripts/fake_llm.mjs
// Purpose:   Tiny local OpenAI-compatible server (127.0.0.1:3032) for testing the bring-your-own-model path without a real key
import http from "node:http";

const seen = [];
http.createServer((req, res) => {
  const send = (code, obj) => { res.writeHead(code, { "Content-Type": "application/json" }); res.end(JSON.stringify(obj)); };
  if (req.method === "GET" && req.url === "/seen") return send(200, { authorization: seen });
  if (req.method !== "POST" || req.url !== "/v1/chat/completions") return send(404, { error: "not found" });
  let raw = "";
  req.on("data", (c) => { raw += c; });
  req.on("end", () => {
    seen.push(req.headers.authorization || "");
    const body = JSON.parse(raw || "{}");
    const tool = [...(body.messages || [])].reverse().find((m) => m.role === "tool");
    const lastUser = [...(body.messages || [])].reverse().find((m) => m.role === "user")?.content || "";
    if (/headphones/i.test(String(lastUser))) {
      if (!tool) return send(200, { choices: [{ message: { role: "assistant", content: null, tool_calls: [{ id: "call_h", type: "function", function: { name: "get_product_offers", arguments: JSON.stringify({ product_ref: "headphones-x1" }) } }] } }] });
      return send(200, { choices: [{ message: { role: "assistant", content: `FAKE-LLM-OFFERS:${tool.content}` } }] });
    }
    if (!tool) {
      return send(200, { choices: [{ message: { role: "assistant", content: null, tool_calls: [{ id: "call_1", type: "function", function: { name: "search_products", arguments: JSON.stringify({ query: "Der Hobbit", country: "DE" }) } }] } }] });
    }
    const title = /"title"\s*:\s*"([^"]+)"/.exec(tool.content)?.[1] || "(no title)";
    send(200, { choices: [{ message: { role: "assistant", content: `FAKE-LLM-OK first product: ${title}` } }] });
  });
}).listen(3032, "127.0.0.1", () => console.log("fake LLM on http://127.0.0.1:3032/v1"));
