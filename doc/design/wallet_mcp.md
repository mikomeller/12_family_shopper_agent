<!--
Author:    mikomeller
Version:   0.1.0
Filename:  wallet_mcp.md
Pathname:  doc/design/wallet_mcp.md
Purpose:   Tool contract of the Family Wallet MCP (story #6): tools, errors, roles, schema, identity, concurrency, eval mapping
-->
# Family Wallet MCP — tool contract

**Purpose.** The Family Wallet MCP records simulated orders (record + shop deep link, no payment) and enforces the
personal and family monthly caps and the role rules itself, independent of Boris. This spec is what `wallet-dev`
implements and what L1-01…L1-13 and L2-01…L2-09 in `doc/evals/eval_plan.md` test. Diagram: `doc/diagrams/wallet_contract.mmd`.

## Code layout (fixed)
| File | Content |
|---|---|
| `src/family_shopper/wallet/db.py` | `connect(path)`, schema DDL, `init_db(conn, config)` (seeds members/family only when tables are empty) |
| `src/family_shopper/wallet/identity.py` | `Member`, `IdentityResolver` protocol, `TokenResolver`, `mint_token()` |
| `src/family_shopper/wallet/service.py` | `WalletService(db_path, resolver, clock)`; one method per tool; no MCP imports; returns Pydantic results |
| `src/family_shopper/wallet/server.py` | FastMCP server; each tool = one line calling the service and returning `result.model_dump()` |

Config: `config/family_budget.yaml`, else `config/family_budget.example.yaml`; euros × 100 → cents via `Decimal` (never float).
DB: env `WALLET_DB`, default `data/wallet.sqlite`. Clock: `clock: Callable[[], datetime]` (tz-aware), default
`lambda: datetime.now(timezone.utc)`. Month key = `clock().astimezone(ZoneInfo("Europe/Berlin")).strftime("%Y-%m")`.

## Result envelope
Every tool returns a dict; no exception crosses the tool boundary (unexpected errors → `INTERNAL_ERROR`, transaction rolled back).
- Success: `{"ok": true, ...tool fields}`
- Refusal: `{"ok": false, "error_code": str, "reason": str, "remaining_personal_cents": int|null, "remaining_family_cents": int|null}`
  Remaining fields are filled whenever the caller is known (null before identity is resolved; personal is null for a member without a cap).
  Remaining values are never negative (`max(0, cap - spent)`).

### Error codes (final list) and reason texts
`{x}` = formatted euros, e.g. `25.00 €` (`f"{c//100}.{c%100:02d} €"`).
| Code | Reason text |
|---|---|
| `IDENTITY_MISSING` | `No caller identity was provided.` |
| `IDENTITY_INVALID` | `The caller identity is invalid or expired.` |
| `INVALID_INPUT` | `Invalid input: {field} {problem}.` (missing, wrong type, empty string) |
| `INVALID_AMOUNT` | `The amount must be a whole number of cents greater than zero.` |
| `NOT_ALLOWED_FOR_ROLE` | place_order by child: `Orders by {member} need a parent's approval; use request_approval.` · request_approval by parent/teen: `{member} can order directly; use place_order.` |
| `NOT_A_PARENT` | `Only a parent can {action}.` (action = `approve requests` / `set budgets`) |
| `PERSONAL_CAP_EXCEEDED` | `This exceeds {member}'s monthly limit; {remaining} left this month.` |
| `FAMILY_CAP_EXCEEDED` | `This exceeds the family's monthly limit; {remaining} left this month.` |
| `REQUEST_NOT_FOUND` | `Approval request {id} does not exist.` |
| `REQUEST_NOT_OPEN` | `Approval request {id} is already {status}.` |
| `MEMBER_NOT_FOUND` | `Member {id} does not exist.` (set_budget target) |
| `INTERNAL_ERROR` | `The wallet could not complete the request; nothing was changed.` |

Check order (fixed, so tests are decidable): identity → input/amount → role → (in transaction) request state → personal cap → family cap.

## Tools
No tool has a `member`/`caller` argument; the caller is always `resolver.resolve()`. `price_cents` must be a Python `int`
(not `bool`, not float, not str) and `> 0`, else `INVALID_AMOUNT`. Strings must be non-empty, ≤ 500 chars, else `INVALID_INPUT`.

| Tool | Inputs | Success fields (besides `ok`) | Error codes (besides identity, `INVALID_INPUT`, `INTERNAL_ERROR`) |
|---|---|---|---|
| `check_budget` | `price_cents: int \| None = None` | `member_id, role, month, personal_cap_cents\|null, personal_spent_cents, remaining_personal_cents\|null, family_cap_cents, family_spent_cents, remaining_family_cents, needs_approval: bool, fits: bool\|null` (null when no price) | `INVALID_AMOUNT` |
| `place_order` | `product_name: str, shop: str, deep_link: str, price_cents: int` | `order_id, member_id, product_name, shop, deep_link, price_cents, month, remaining_personal_cents\|null, remaining_family_cents` | `INVALID_AMOUNT, NOT_ALLOWED_FOR_ROLE, PERSONAL_CAP_EXCEEDED, FAMILY_CAP_EXCEEDED` |
| `request_approval` | `product_name: str, shop: str, deep_link: str, price_cents: int` | `request_id, status="open", member_id, price_cents, remaining_personal_cents, remaining_family_cents` | `INVALID_AMOUNT, NOT_ALLOWED_FOR_ROLE` |
| `approve_request` | `request_id: int` | same fields as `place_order` (member = the child) + `request_id, approved_by` | `NOT_A_PARENT, REQUEST_NOT_FOUND, REQUEST_NOT_OPEN, PERSONAL_CAP_EXCEEDED, FAMILY_CAP_EXCEEDED` |
| `set_budget` | `target: str` (`"family"` or a member id), `cap_cents: int \| None` | `target, cap_cents` | `NOT_A_PARENT, MEMBER_NOT_FOUND, INVALID_AMOUNT` (cap must be int ≥ 0; `None` only for a parent member) |
| `list_orders` | `month: str \| None = None` (`YYYY-MM`, default current) | `month, orders: [{order_id, member_id, placed_by, product_name, shop, deep_link, price_cents, created_at, request_id\|null}]` | — |
| `list_requests` | `status: "open" \| "approved" \| None = "open"` | `requests: [{request_id, member_id, product_name, shop, deep_link, price_cents, status, created_at}]` | — |

Notes:
- `request_approval` creates no order and no spend; it does not check caps (the check happens at approval time).
- `approve_request` that fails a cap rolls back: the request stays `open`, no order (L1-07). Cap checked = the **child's** personal cap and the family cap (A1). `placed_by` = approving parent.
- `list_orders` / `list_requests`: parent sees all members; teen and child see only their own rows (L2-08).
- `set_budget` may set a cap below the current spend; it only blocks further orders.
- **Extra tool `list_requests`** (7th tool): S-08 "Approve Mia's request" needs the request id, which the parent cannot get otherwise.
- Reject/expire of requests is not in scope (no eval case).

## Role / tool matrix
"Wallet" = enforced by the wallet (authoritative). "Boris" = proposed tool visibility via Boris gating (unverified until the identity spike).
| Tool | Parent wallet / Boris | Teen wallet / Boris | Child wallet / Boris |
|---|---|---|---|
| `check_budget` | yes / visible | yes / visible | yes / visible |
| `place_order` | yes / visible | yes (within caps) / visible | **no** `NOT_ALLOWED_FOR_ROLE` / hidden |
| `request_approval` | no `NOT_ALLOWED_FOR_ROLE` / hidden | no `NOT_ALLOWED_FOR_ROLE` / hidden | yes / visible |
| `approve_request` | yes / visible | no `NOT_A_PARENT` / hidden | no `NOT_A_PARENT` / hidden |
| `set_budget` | yes / visible | no `NOT_A_PARENT` / hidden | no `NOT_A_PARENT` / hidden |
| `list_orders` | all / visible | own / visible | own / visible |
| `list_requests` | all / visible | own / hidden | own / visible |

Role rules come from the `members.role` column: `parent` = can approve + set budgets; `child` = needs approval.

## SQL schema (`db.py`)
```sql
PRAGMA foreign_keys = ON;  PRAGMA journal_mode = WAL;  PRAGMA busy_timeout = 5000;
CREATE TABLE IF NOT EXISTS family (
  id               INTEGER PRIMARY KEY CHECK (id = 1),
  family_cap_cents INTEGER NOT NULL CHECK (family_cap_cents >= 0));
CREATE TABLE IF NOT EXISTS members (
  id                 TEXT PRIMARY KEY CHECK (id GLOB '[a-z0-9_-]*' AND length(id) BETWEEN 1 AND 32),
  role               TEXT NOT NULL CHECK (role IN ('parent','teen','child')),
  personal_cap_cents INTEGER CHECK (personal_cap_cents IS NULL OR personal_cap_cents >= 0));
CREATE TABLE IF NOT EXISTS approval_requests (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  member_id    TEXT NOT NULL REFERENCES members(id),
  product_name TEXT NOT NULL, shop TEXT NOT NULL, deep_link TEXT NOT NULL,
  price_cents  INTEGER NOT NULL CHECK (typeof(price_cents) = 'integer' AND price_cents > 0),
  status       TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','approved')),
  created_at   TEXT NOT NULL, decided_at TEXT, decided_by TEXT REFERENCES members(id));
CREATE TABLE IF NOT EXISTS orders (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  member_id    TEXT NOT NULL REFERENCES members(id),   -- whose cap it counts against
  placed_by    TEXT NOT NULL REFERENCES members(id),   -- caller (parent for approved child orders)
  request_id   INTEGER UNIQUE REFERENCES approval_requests(id),
  product_name TEXT NOT NULL, shop TEXT NOT NULL, deep_link TEXT NOT NULL,
  price_cents  INTEGER NOT NULL CHECK (typeof(price_cents) = 'integer' AND price_cents > 0),
  month        TEXT NOT NULL CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'),
  created_at   TEXT NOT NULL);                           -- ISO-8601 UTC from the injected clock
CREATE INDEX IF NOT EXISTS ix_orders_month_member ON orders(month, member_id);
```
Spend is always derived: `SELECT COALESCE(SUM(price_cents),0) FROM orders WHERE month=? [AND member_id=?]`.
No stored counters, so a new month starts at zero by construction (L1-09). Caps live in the DB after seeding;
`set_budget` writes there; the YAML is only the initial seed.

## Identity
- `Member` = `(id: str, role: Literal["parent","teen","child"])`, loaded from `members`.
- `class IdentityResolver(Protocol): def resolve(self) -> Member` — raises `IdentityMissing` / `IdentityInvalid`,
  which the service maps to `IDENTITY_MISSING` / `IDENTITY_INVALID`. Tests pass a fake resolver in-process.
- **Default `TokenResolver`**: token `member_id.expiry.signature`; `expiry` = Unix seconds (int);
  `signature` = hex `HMAC-SHA256(key=WALLET_TOKEN_SECRET, msg=f"{member_id}.{expiry}")`; compare with `hmac.compare_digest`.
  Missing/empty token → `IDENTITY_MISSING`. Wrong part count, bad signature, `expiry <= clock()`, member not in DB,
  or `WALLET_TOKEN_SECRET` unset/empty → `IDENTITY_INVALID` (fail closed). `mint_token(member_id, ttl_s, secret, clock)` for scripts/tests.
- **How the token reaches the server (chosen):** env `WALLET_MEMBER_TOKEN`, read by `TokenResolver` on every call,
  set per server process. With stdio this is **one wallet access point per role/member** (the agent/Boris config starts
  `wallet-server` with that member's token). Why: the LLM never sees or writes the token, so a prompt cannot change the
  member (L2-05), and it works whether or not Boris forwards identity. Rejected: a `member_token` tool argument
  (the token passes through the LLM context and can be replayed or swapped). When the Boris spike shows identity
  forwarding, a `BorisResolver` replaces `TokenResolver` — only `identity.py` changes.
- A `member`/`member_id` argument sent by a caller is not declared on any tool and is never read (L2-05).
  Whether FastMCP drops or rejects undeclared arguments is unverified; either outcome passes L2-05.

## Concurrency (L1-10)
`service.py` opens one connection per call (`sqlite3.connect(path, isolation_level=None, timeout=5)`).
`place_order` and `approve_request` run exactly: `BEGIN IMMEDIATE` → (approve: `SELECT` request, check open) →
personal `SUM` → family `SUM` → compare → `INSERT orders` (+ `UPDATE approval_requests SET status='approved', decided_at, decided_by
WHERE id=? AND status='open'`) → `COMMIT`; any refusal or exception → `ROLLBACK`. `BEGIN IMMEDIATE` takes the write lock
before the reads, so a second writer waits and then sees the first order. `set_budget` and `request_approval` also use
`BEGIN IMMEDIATE`. Reads (`check_budget`, lists) need no explicit transaction. Test: two threads, own connections, teen with
€0 spent each ordering 3000 cents → exactly one `ok`, one `PERSONAL_CAP_EXCEEDED`.

## Eval mapping
| ID | Rule that satisfies it |
|---|---|
| L1-01 | place_order, teen, 2500 ≤ 5000 → ok, `remaining_personal_cents=2500` |
| L1-02 | personal check `2500+3000 > 5000` → `PERSONAL_CAP_EXCEEDED`, remaining 2500 |
| L1-03 | parent has no personal cap; family `39000+2000 > 40000` → `FAMILY_CAP_EXCEEDED`, remaining 1000 |
| L1-04 | comparison is `≤`: `39000+1000 = 40000` → ok, `remaining_family_cents=0` |
| L1-05 | request_approval by child → request `open`, no `orders` row, spend unchanged |
| L1-06 | approve_request → order with `member_id=child`, counts in child + family SUMs (A1) |
| L1-07 | approve fails cap → ROLLBACK, request stays `open`, error with remaining amounts |
| L1-08 | approve_request by teen → `NOT_A_PARENT` |
| L1-09 | spend = SUM over `month` of the injected clock; new month → 0 |
| L1-10 | cap check + insert inside one `BEGIN IMMEDIATE` transaction |
| L1-11 | `price_cents` not int / bool / ≤ 0 → `INVALID_AMOUNT`, no write |
| L1-12 | `≤` comparison: 5000 at cap 5000 → ok |
| L1-13 | integer cents: 5001 > 5000 → `PERSONAL_CAP_EXCEEDED` |
| L2-01 | success fields per Tools table; Pydantic result models in `service.py` are the schema |
| L2-02 | validation before any transaction → `INVALID_INPUT`/`INVALID_AMOUNT`, no state change (see open question 3) |
| L2-03 | no `WALLET_MEMBER_TOKEN` → `IDENTITY_MISSING` |
| L2-04 | bad signature / expired / unknown member → `IDENTITY_INVALID` |
| L2-05 | no member argument exists; resolver alone decides the member |
| L2-06 | place_order checks role in the wallet: child → `NOT_ALLOWED_FOR_ROLE` |
| L2-07 | set_budget / approve_request check `role='parent'` → `NOT_A_PARENT` |
| L2-08 | list_orders filters `member_id = caller` unless parent |
| L2-09 | place_order success has `order_id, price_cents, shop, deep_link, remaining_personal_cents, remaining_family_cents` |

## Decisions
| Decision | Rejected alternative | Reason |
|---|---|---|
| Token via env per server process | `member_token` tool argument | token never in LLM context; simplest for stdio |
| Spend derived from `orders` by month | stored monthly counters + reset job | no reset logic, cannot drift |
| Caps in DB, YAML only seeds | read caps from YAML on every call | `set_budget` must persist |
| Request approval checks caps at approval, not at request | reserve budget at request time | matches L1-05 (no spend) and L1-07 |
| Child cannot `place_order` even within cap | allow small child orders | config says `needs_approval: true` for every child order |
| Add `list_requests` | parent guesses request ids | S-08 needs it |

## Open questions (for the owner)
1. Should `eval_plan.md` A1 be marked confirmed (owner decision taken in the story brief)?
2. Should a parent be able to reject a request? Not specified; no tool now.
3. FastMCP may reject wrong-typed arguments itself (schema validation) before our code runs; is an MCP error result
   acceptable for L2-02 at the MCP layer, with structured `INVALID_*` asserted at the service layer? (unverified)
4. Month boundary in `Europe/Berlin` — OK?
