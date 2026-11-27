<!--
Author:    mikomeller
Version:   0.1.0
Filename:  affinidi_boris_idealo.md
Pathname:  doc/research/affinidi_boris_idealo.md
Purpose:   Research summary (2026-11-27): Affinidi, the TrustBoris hackathon challenge, the idealo MCP server,
           and the resulting design decisions for the family shopping agent
-->
# Research: Affinidi, TrustBoris and idealo MCP

## 1. Affinidi
- Temasek-founded (2020) trust-infrastructure company, HQ Singapore, hubs in Bangalore and **Berlin**. ISO 27001, GDPR/PDPA.
- Positioning: "Most gateways route traffic. Affinidi routes trust." Every agent gets a verifiable identity (DID); calls are checked against policy and audited.
- Product lines:
  - **Trust Fabric**: Agent Gateway (identity, OPA policy, audit; DIDComm v2.1, TSP, MCP, A2A, AP2, x402), Agent Stream (LLM safety, budgets, routing), Agent Pay (coming soon).
  - **Radix**: trust registries and governance (closed beta).
  - **Elements**: Vault, OID4VC issuance/verification, DIDComm messaging.
  - Open source: VTI (Apache-2.0, Rust), OpenVTC (Linux Foundation).

## 2. The challenge: "Build agents you'd confidently offer publicly"
- Platform: **TrustBoris** (trustboris.ai) — Agent Builder, Agent Gateway, LLM Gateway, MCP tool gating.
- Features: agent identity and access, MCP tool gating (blocked tools hidden), prompt/reply screening with PII masking,
  agent + model throttling, backup models and retries, response caching, bring-your-own key/model, try-before-you-switch, LLM drift monitor (Pro).
- **Trust dividend**: hand the agent one task normally kept behind a human (spending money, sending messages, personal data, risky tools).
- Judging: (1) a job worth doing, (2) trust you can see — what breaks without Boris, (3) more freedom, safely — what did it do alone, (4) only what matters — every feature justified.
- Prizes: 2 months Pro / 1 month Pro / 3 months Starter.
- Pre-kickoff: Docker running; `brew install --cask affinidi-ai/tap/boris`; `boris doctor`; `boris login --url https://trustboris.ai`; use Chrome (Safari can't connect dashboard ↔ CLI).
- No public Boris docs found — behaviour must be verified in the dashboard.

## 3. idealo MCP (official)
- Endpoint `https://mcp.idealo.com/mcp`, OAuth 2.0 + DCR + PKCE (separate from the idealo.de website account).
- Markets DE, AT, GB, FR, IT, ES (unknown country codes fall back to DE); `productRef` is market-specific.
- Tools: `search_products`, `get_product_details`, `get_product_offers` (5 per page), `get_product_price_history` (30 days).
- **No checkout/ordering.** idealo Checkout was discontinued on 31 Dec 2022.
- Trial tier: 3 req/s, burst 6, **500 calls/day**, max 10 offers per product; Amazon, eBay and Otto offers excluded. Partner tier via mcp@idealo.de.

## 4. Design decisions
| Decision | Reason |
|---|---|
| Own **Family Wallet MCP** (Python + SQLite) with `place_order` | idealo MCP is read-only; Agent Pay not yet available |
| Orders are **simulated**: recorded + shop deep link, no payment | No checkout API; safe for a public demo |
| Euro caps enforced **in the wallet** | Boris throttles calls/tokens, not money |
| Boris identity + tool gating decide **who may call which wallet tool** | Child never sees `place_order`; only parents see `set_budget` / `approve_request` |
| Response caching + throttle | Protect the 500 calls/day idealo quota |
| Screening | Block prompt injection hidden in product/offer texts |
| Defaults: parent no personal cap · teen €50 · child €20 + approval · family €400 / month | Agreed 2026-11-27 |

**Key risk (spike):** does Boris forward the verified caller identity to downstream MCP tools? Without it, the wallet can't apply personal caps.

## Sources
- https://www.affinidi.com/ · https://www.affinidi.com/trust-fabric · https://www.affinidi.com/agent-stream
- https://docs.affinidi.com/products/affinidi-trust-fabric/agent-gateway/overview/
- Hackathon brief: `ah3-brief-affinidi-trust-boris.pdf` (this folder) · https://trustboris.ai
- https://glama.ai/mcp/servers/mja2sd73so (idealo MCP server guide) · https://github.com/idealo/mcp-server-guide
- https://knowledge.plentyone.com/en-gb/manual/main/markets/idealo-setup.html (idealo Checkout discontinued)
- https://luma.com/research-to-commerce (AI Agents Berlin hackathon, 42 Berlin)
