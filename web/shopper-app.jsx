import { useEffect, useRef, useState } from "react";

function money(value) {
  return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(value || 0);
}

function memberForReply(message, messages, index, members) {
  if (message.memberName) return message.memberName;
  for (let i = index - 1; i >= 0; i -= 1) {
    if (messages[i].role !== "user") continue;
    const text = ` ${messages[i].content.toLocaleLowerCase("de-DE").replace(/[^\p{L}\p{N}]+/gu, " ").trim()} `;
    const matches = members.filter((member) => text.includes(` ${member.name.toLocaleLowerCase("de-DE").replace(/[^\p{L}\p{N}]+/gu, " ").trim()} `));
    if (matches.length === 1) return matches[0].name;
    if (matches.length > 1) return null;
  }
  return null;
}

function Icon({ name, size = 20 }) {
  const shared = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
  if (name === "spark") return <svg {...shared}><path d="m12 3 1.5 6.5L20 12l-6.5 1.5L12 20l-1.5-6.5L4 12l6.5-2.5L12 3Z"/><path d="m19 3 .7 2.3L22 6l-2.3.7L19 9l-.7-2.3L16 6l2.3-.7L19 3Z"/></svg>;
  if (name === "arrow") return <svg {...shared}><path d="M5 12h14M13 6l6 6-6 6"/></svg>;
  if (name === "bag") return <svg {...shared}><path d="M5 8h14l1 13H4L5 8Z"/><path d="M9 9V6a3 3 0 0 1 6 0v3"/></svg>;
  if (name === "wallet") return <svg {...shared}><path d="M4 6.5A2.5 2.5 0 0 1 6.5 4H20v16H6.5A2.5 2.5 0 0 1 4 17.5v-11Z"/><path d="M4 7h16M15 13h2"/></svg>;
  if (name === "check") return <svg {...shared}><circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.8 2.8L16.5 9.5"/></svg>;
  if (name === "clock") return <svg {...shared}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
  if (name === "stop") return <svg {...shared}><circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/></svg>;
  if (name === "plus") return <svg {...shared}><path d="M12 5v14M5 12h14"/></svg>;
  return <svg {...shared}><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>;
}

function AppMark() {
  return <div className="brand-mark"><Icon name="spark" size={23} /></div>;
}

function InlineText({ text }) {
  const parts = String(text).split(/(\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g).filter(Boolean);
  return parts.map((part, index) => {
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    if (link) return <a key={index} href={link[2]} target="_blank" rel="noreferrer">{link[1]}</a>;
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*")) return <em key={index}>{part.slice(1, -1)}</em>;
    return part;
  });
}

function getProductFromRow(row) {
  const firstCell = row[0] || "";
  const link = firstCell.match(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/);
  const productName = (link?.[1] || firstCell.replace(/\*\*/g, "").trim());
  const priceCell = row.find((cell) => /€\s*[\d.,]+/.test(cell)) || "";
  const match = priceCell.match(/€\s*([\d.,]+)/);
  if (!productName || !match) return null;
  const normalizedPrice = match[1].includes(",")
    ? match[1].replace(/\./g, "").replace(",", ".")
    : match[1];
  const priceEur = Number(normalizedPrice);
  if (!Number.isFinite(priceEur) || priceEur <= 0) return null;
  const frag = new URLSearchParams((link?.[2] || "").split("#")[1] || "");
  const productRef = frag.get("ref") || undefined;
  const claimedWasEur = frag.get("was") ? Number(frag.get("was")) / 100 : undefined;
  return { productName, productUrl: link?.[2] || null, priceEur, productRef, claimedWasEur };
}

const STATUS = {
  ordered: { label: "Ordered", icon: "check" },
  waiting: { label: "Waiting for parent approval", icon: "clock" },
  refused: { label: "Refused: over the monthly limit", icon: "stop" },
  blocked: { label: "Blocked: discount is not real", icon: "stop" },
  rejected: { label: "Rejected by parent", icon: "stop" },
  error: { label: "Not recorded", icon: "stop" },
};
function errorKind(message) {
  const m = String(message || "");
  if (/discount/i.test(m) || /^Blocked/i.test(m)) return "blocked";
  if (/limit|budget|cap\b|exceed|remain/i.test(m)) return "refused";
  if (/reject/i.test(m)) return "rejected";
  return "error";
}
function StatusCard({ kind, text, verdict }) {
  const st = STATUS[kind] || STATUS.error;
  return <div className={`status-card status-${kind}`} role={kind === "ordered" || kind === "waiting" ? "status" : "alert"}><Icon name={st.icon} size={18} /><div><strong>{st.label}{verdict ? ` · verdict ${verdict}` : ""}</strong><span>{text}</span></div></div>;
}
function VerdictBadge({ verdict }) {
  const good = verdict === "GENUINE" || verdict === "REAL";
  const bad = verdict === "INFLATED";
  return <span className={`verdict-badge ${bad ? "verdict-bad" : good ? "verdict-good" : "verdict-warn"}`}>{bad ? "✕" : good ? "✓" : "!"} Discount {verdict}</span>;
}
const ROLE_INFO = {
  parent: { label: "Parent", rule: "Approves requests. No personal limit.", color: "var(--role-parent)" },
  teen: { label: "Teen", rule: "Orders alone up to the personal monthly limit.", color: "var(--role-teen)" },
  child: { label: "Child", rule: "Every order needs a parent.", color: "var(--role-child)" },
};

function PurchaseModal({ conf, busy, budget, onConfirm, onCancel }) {
  const confirmRef = useRef(null);
  useEffect(() => { confirmRef.current?.focus(); }, []);
  useEffect(() => { const h = (e) => { if (e.key === "Escape") onCancel(); }; window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h); });
  const child = budget?.role === "child";
  const p = conf.product;
  return <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
    <section className="purchase-confirm-modal" role="alertdialog" aria-modal="true" aria-labelledby="pc-title" aria-describedby="pc-note">
      <h2 id="pc-title">{child ? "Ask a parent?" : "Order this?"}</h2>
      <p>{p.productName}{p.shopName ? ` from ${p.shopName}` : ""}</p>
      <dl className="pc-summary">
        <div><dt>Price incl. shipping</dt><dd>{money(p.priceEur)}</dd></div>
        {budget?.meLeft != null && <div><dt>Your budget now</dt><dd>{money(budget.meLeft)}</dd></div>}
        {budget?.familyLeft != null && <div><dt>Family budget now</dt><dd>{money(budget.familyLeft)}</dd></div>}
      </dl>
      <div className="purchase-confirm-note" id="pc-note">{child ? "A parent has to approve this before anything is ordered. " : ""}Simulated: no real order or payment.</div>
      {conf.error && <div className="modal-error" role="alert">{conf.error} Check the offer or pick a cheaper one, then retry.</div>}
      <div className="modal-actions"><button type="button" className="modal-cancel" onClick={onCancel} disabled={busy}>Cancel</button><button ref={confirmRef} type="button" className="modal-save" onClick={onConfirm} disabled={busy}>{busy ? "Sending…" : conf.error ? "Retry" : child ? "Send request to parent" : "Order now"}</button></div>
    </section>
  </div>;
}

function FormattedReply({ content, memberName, onMockPurchase, budget }) {
  const [purchaseStates, setPurchaseStates] = useState({});
  const [purchaseConfirmation, setPurchaseConfirmation] = useState(null);
  const [purchaseConfirming, setPurchaseConfirming] = useState(false);
  const lines = String(content).split(/\r?\n/);
  const blocks = [];
  let paragraph = [];
  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ type: "paragraph", text: paragraph.join(" ") });
    paragraph = [];
  };
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].trim();
    if (!line) { flushParagraph(); continue; }
    if (line.startsWith("|") && line.endsWith("|")) {
      flushParagraph();
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|") && lines[i].trim().endsWith("|")) {
        const cells = lines[i].trim().slice(1, -1).split("|").map((cell) => cell.trim());
        if (!cells.every((cell) => /^:?-{3,}:?$/.test(cell))) rows.push(cells);
        i += 1;
      }
      i -= 1;
      if (rows.length) blocks.push({ type: "table", rows });
      continue;
    }
    const list = line.match(/^[-*]\s+(.+)/);
    if (list) {
      flushParagraph();
      const items = [list[1]];
      while (i + 1 < lines.length && /^\s*[-*]\s+/.test(lines[i + 1])) items.push(lines[++i].trim().replace(/^[-*]\s+/, ""));
      blocks.push({ type: "list", items });
      continue;
    }
    paragraph.push(line);
  }
  flushParagraph();
  async function confirmPurchase() {
    if (!purchaseConfirmation || !onMockPurchase) return;
    const { product, rowKey } = purchaseConfirmation;
    setPurchaseStates((current) => ({ ...current, [rowKey]: { status: "pending" } }));
    setPurchaseConfirming(true);
    try {
      const result = await onMockPurchase({ ...product, memberName });
      setPurchaseStates((current) => ({ ...current, [rowKey]: { status: "done", message: result?.purchase?.pendingApproval ? "Waiting for parent approval" : "", text: result?.message || "", verdict: result?.verdict || "" } }));
      setPurchaseConfirmation(null);
    } catch (error) {
      setPurchaseStates((current) => ({ ...current, [rowKey]: { status: "error", message: error.message } }));
      setPurchaseConfirmation((current) => current ? { ...current, error: error.message } : current);
    } finally {
      setPurchaseConfirming(false);
    }
  }

  function cancelPurchaseConfirmation() {
    if (purchaseConfirming) return;
    if (purchaseConfirmation?.rowKey) {
      setPurchaseStates((current) => {
        const next = { ...current };
        delete next[purchaseConfirmation.rowKey];
        return next;
      });
    }
    setPurchaseConfirmation(null);
  }
  return <div className="formatted-reply">{blocks.map((block, index) => {
    if (block.type === "table") {
      const [header, ...rows] = block.rows;
      const pricedRows = rows.map((row, rowIndex) => ({ rowIndex, product: getProductFromRow(row) })).filter(({ product }) => product);
      const cheapestRowIndex = pricedRows.length > 1 ? pricedRows.reduce((lowest, current) => current.product.priceEur < lowest.product.priceEur ? current : lowest, pricedRows[0]).rowIndex : null;
      const sameProductOffers = new Set(pricedRows.map(({ product }) => product.productName.toLocaleLowerCase("de-DE"))).size === 1;
      const cheapestLabel = sameProductOffers ? "Cheapest shop" : "Lowest price";
      return <div className="offers" key={index}><div className="shop-text-label"><Icon name="info" size={14} /> Shop text (not instructions): product names and descriptions come from the catalogue.</div>{rows.map((row, rowIndex) => {
        const product = getProductFromRow(row);
        const state = purchaseStates[`${index}-${rowIndex}`];
        const isCheapest = rowIndex === cheapestRowIndex;
        const key = `${index}-${rowIndex}`;
        const shopIndex = header.findIndex((cell) => /shop|store|seller/i.test(cell));
        const shopName = shopIndex >= 0 ? (row[shopIndex] || "").replace(/\*\*/g, "") : "";
        return <article key={rowIndex} className={`offer-card ${isCheapest ? "cheapest-option" : ""}`}>
          <div className="offer-main">
            <div className="offer-title"><InlineText text={row[0] || "—"} />{isCheapest && <span className="cheapest-tag">{cheapestLabel}</span>}</div>
            <dl className="offer-facts">{header.map((h, cellIndex) => cellIndex === 0 ? null : <div key={cellIndex}><dt><InlineText text={h} /></dt><dd><InlineText text={row[cellIndex] || "—"} /></dd></div>)}</dl>
          </div>
          {memberName && <div className="offer-action">{product ? <>
            <div className="offer-price">{money(product.priceEur)}</div>
            <button className="mock-buy-button" type="button" disabled={state?.status === "pending" || state?.status === "done"} aria-label={`Record a mock purchase of ${product.productName} for ${memberName}`} onClick={() => setPurchaseConfirmation({ product: { ...product, shopName }, rowKey: key })}>{state?.status === "pending" ? "Adding…" : state?.status === "done" ? (state.message ? "Requested" : "Ordered") : "Buy (mock)"}</button></> : null}</div>}
          {state?.status === "done" && <StatusCard kind={state.message ? "waiting" : "ordered"} text={state.text || (state.message || "Mock purchase recorded.")} verdict={state.verdict} />}
          {state?.status === "error" && <StatusCard kind={errorKind(state.message)} text={state.message} />}
        </article>;
      })}</div>;
    }
    if (block.type === "list") return <ul key={index}>{block.items.map((item, itemIndex) => <li key={itemIndex}><InlineText text={item} /></li>)}</ul>;
    const vm = block.text.match(/verdict \*\*([A-Z_]+)\*\*/);
    return <p key={index}>{vm && <VerdictBadge verdict={vm[1]} />}<InlineText text={block.text} /></p>;
  })}{purchaseConfirmation && <PurchaseModal conf={purchaseConfirmation} busy={purchaseConfirming} budget={budget} onConfirm={confirmPurchase} onCancel={cancelPurchaseConfirmation} />}</div>;
}

function Budget({ label, remaining, spent, limit, big }) {
  const percent = limit ? Math.min(100, (spent / limit) * 100) : 0;
  return <div className={`budget ${big ? "budget-big" : ""}`}>
    <div className="budget-label">{label}</div>
    <div className="balance-amount">{money(remaining)} <small>left</small></div>
    <div className="progress-track" role="progressbar" aria-label={`${label} used`} aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(percent)}><div className="progress-value" style={{ width: `${percent}%` }} /></div>
    <div className="budget-foot"><span>{money(spent)} used</span><span>of {money(limit)}</span></div>
  </div>;
}

function MemberCard({ member, me }) {
  const spent = Number(member.spentEur || 0);
  const hasCap = member.spendingLimitEur != null;
  const limit = hasCap ? Number(member.spendingLimitEur) : Number(member.familyCapEur || 0);
  const percent = limit ? Math.min(100, (spent / limit) * 100) : 0;
  const info = ROLE_INFO[String(member.name || "").toLowerCase()] || ROLE_INFO[member.role] || ROLE_INFO.parent;
  return (
    <article className={`member-card ${me ? "is-me" : ""}`}>
      <div className="member-card-top">
        <div className="avatar" style={{ background: info.color }}>{member.name?.slice(0, 1).toUpperCase()}</div>
        <div className="member-name">{member.name}{me && <em> (you)</em>}<span>{member.role}{hasCap ? "" : " · family cap only"}</span></div>
      </div>
      <div className="balance-label">REMAINING</div>
      <div className="balance-amount">{money(member.remainingEur)}</div>
      <div className="progress-track"><div className="progress-value" style={{ width: `${percent}%` }} /></div>
      <div className="budget-foot"><span>{money(spent)} used</span><span>{hasCap ? `of ${money(limit)}` : `family ${money(member.familyRemainingEur)} left`}</span></div>
    </article>
  );
}

function ChatMessage({ message, onMockPurchase, budget }) {
  const assistant = message.role === "assistant";
  return (
    <div className={`message-row ${assistant ? "assistant-row" : "user-row"}`}>
      {assistant && <div className="tiny-mark"><Icon name="spark" size={15} /></div>}
      <div className={`message-bubble ${assistant ? "assistant-bubble" : "user-bubble"}`}>
        {assistant && <div className="message-label">SHOPPER AGENT</div>}
        <div className="message-copy">{assistant ? <FormattedReply content={message.content} memberName={message.memberName} onMockPurchase={onMockPurchase} budget={budget} /> : message.content}</div>
      </div>
    </div>
  );
}

function parseOffers(reply) {
  const rows = [];
  let header = null;
  for (const raw of String(reply).split(/\r?\n/)) {
    const line = raw.trim();
    if (!(line.startsWith("|") && line.endsWith("|"))) continue;
    const cells = line.slice(1, -1).split("|").map((c) => c.trim());
    if (cells.every((c) => /^:?-{3,}:?$/.test(c))) continue;
    if (!header) { header = cells; continue; }
    const product = getProductFromRow(cells);
    if (!product) continue;
    const si = header.findIndex((c) => /shop|store|seller/i.test(c));
    rows.push({ ...product, shopName: si >= 0 ? (cells[si] || "").replace(/\*\*/g, "") : "" });
  }
  return rows.reduce((best, r) => (!best || r.priceEur < best.priceEur ? r : best), null);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const firstSentence = (t) => { const s = String(t).replace(/\|.*$/gm, "").replace(/\*\*/g, "").trim(); const m = s.match(/^[^.!?\n]*[.!?]/); return (m ? m[0] : s.split("\n")[0]).trim(); };

function Decision({ steps, finished, running, onStop, onAgain }) {
  const icon = { running: <span className="trail-spin" aria-hidden="true" />, ok: "✓", bad: "✕", wait: "⏳" };
  return <section className="panel decision-trail" aria-label="Decision trail">
    <h2>Decision trail</h2>
    <div aria-live="polite">
      <ol className="trail">{steps.map((s) => <li key={s.id} className={`trail-step trail-${s.state}`}>
        <span className="trail-dot">{icon[s.state]}</span>
        <div className="trail-body"><strong>{s.title}</strong>{s.text && <span>{s.text}</span>}{(s.subs || []).map((x, i) => <span key={i} className="trail-sub">{x}</span>)}{s.bold && <strong className="trail-bold">{s.bold}</strong>}</div>
      </li>)}</ol>
      {finished && <div className="trail-summary"><strong>{finished.ok ? "Story finished: 1 order approved by a parent, 1 purchase refused" : "Story stopped."}</strong>
        <small>TrustBoris is not connected in this demo: the gateway steps are simulated; the limits are enforced for real by the Family Wallet.</small></div>}
    </div>
    {running ? <button type="button" className="secondary-button" onClick={onStop}>Stop</button> : finished && <button type="button" className="mock-buy-button" onClick={onAgain}>Play again</button>}
    {finished && <small className="trail-note">Playing again uses the same wallet: budgets carry over.</small>}
  </section>;
}

const ACCOUNTS = ["parent", "teen", "child"];
const cap = (id) => id.charAt(0).toUpperCase() + id.slice(1);

export default function ShopperApp() {
  const [account, setAccount] = useState(() => { const asParam = new URLSearchParams(window.location.search).get("as"); if (ACCOUNTS.includes(asParam)) return asParam; try { return localStorage.getItem("familyMember") || "parent"; } catch { return "parent"; } });
  const accountRef = useRef(account);
  accountRef.current = account;
  const [offline, setOffline] = useState(false);
  const [llmMode, setLlmMode] = useState("");
  const [catalogue, setCatalogue] = useState("");
  const [llmOpen, setLlmOpen] = useState(false);
  const [llmInfo, setLlmInfo] = useState(null);
  const [llmForm, setLlmForm] = useState({ providerId: "openai", baseUrl: "", model: "", apiKey: "" });
  const [llmError, setLlmError] = useState("");
  const [llmSaving, setLlmSaving] = useState(false);
  const api = (url, options = {}) => fetch(url, { ...options, headers: { ...(options.headers || {}), "X-Family-Member": accountRef.current } });
  const switchAccount = (id) => { try { localStorage.setItem("familyMember", id); } catch { /* ignore */ } setAccount(id); setError(""); };
  const [members, setMembers] = useState([]);
  const [purchases, setPurchases] = useState([]);
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [family, setFamily] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [idealoConnected, setIdealoConnected] = useState(false);
  const [idealoCredentialsSaved, setIdealoCredentialsSaved] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [authorizationUrl, setAuthorizationUrl] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [mineOpen, setMineOpen] = useState(true);
  const [memberModalOpen, setMemberModalOpen] = useState(false);
  const [memberName, setMemberName] = useState("");
  const [memberBudget, setMemberBudget] = useState("");
  const [memberSaving, setMemberSaving] = useState(false);
  const [memberError, setMemberError] = useState("");
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const lastState = useRef(null);
  useEffect(() => { refreshState(); }, [account]);
  useEffect(() => { const q = new URLSearchParams(window.location.search).get("q"); if (q) sendMessage(q); }, []);
  const [story, setStory] = useState({ running: false, steps: [], finished: null });
  const storyAbort = useRef(false);
  useEffect(() => { if (new URLSearchParams(window.location.search).get("story") === "1") setTimeout(() => playStory(), 600); }, []);
  const stepSet = (id, patch, title) => setStory((st) => {
    const exists = st.steps.some((s) => s.id === id);
    const steps = exists ? st.steps.map((s) => (s.id === id ? { ...s, ...patch } : s)) : [...st.steps, { id, title, state: "running", ...patch }];
    return { ...st, steps };
  });
  async function playStory() {
    if (story.running || busy) return;
    storyAbort.current = false;
    setStory({ running: true, steps: [], finished: null });
    const T = { s1: "1 · Child asks", s2: "2 · idealo price comparison", s3: "3 · Child asks to buy", s4: "4 · Trust layer decides", s5: "5 · Parent decides", s6: "6 · Child asks", s7: "7 · idealo price comparison", s8: "8 · Child tries to buy anyway", s9: "9 · Trust layer decides" };
    let current = null;
    const begin = (id, text) => { current = id; stepSet(id, { state: "running", text }, T[id]); };
    const pause = async () => { await sleep(1500); if (storyAbort.current) throw new Error("__stopped__"); };
    const as = async (id) => { accountRef.current = id; try { localStorage.setItem("familyMember", id); } catch { /* ignore */ } setAccount(id); setError(""); await sleep(300); };
    const post = async (url, body) => {
      const response = await api(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const result = await response.json().catch(() => ({}));
      return { ok: response.ok, status: response.status, result };
    };
    const conv = [];
    const ask = async (text) => {
      conv.push({ role: "user", content: text });
      setMessages([...conv]);
      setBusy(true);
      try {
        const r = await post("/api/chat", { messages: conv, scripted: true });
        if (!r.ok) throw new Error(r.result.error || "The shopper could not answer.");
        conv.push({ role: "assistant", content: r.result.reply });
        setMessages([...conv]);
        return r.result.reply;
      } finally { setBusy(false); }
    };
    const stateNow = async () => { await refreshState(); return lastState.current; };
    const childLeft = () => lastState.current?.members?.find((m) => String(m.name).toLowerCase() === "child")?.remainingEur;
    try {
      setMessages([]);
      await as("child"); await refreshState();
      // Scene 1
      begin("s1", 'Child: "I\'d like Der Hobbit."'); await ask("Der Hobbit"); stepSet("s1", { state: "ok" }); await pause();
      begin("s2", "Comparing offers on idealo…");
      const reply1 = conv[conv.length - 1].content; const best = parseOffers(reply1);
      stepSet("s2", { state: "ok", text: `Compared offers on idealo — best offer highlighted${best ? `: ${best.shopName ? best.shopName + ", " : ""}${money(best.priceEur)}` : ""}` }); await pause();
      begin("s3", "Sending the purchase request…");
      const body = { productRef: "hobbit-pb" }; if (best?.productUrl) body.productUrl = best.productUrl;
      const buy = await post("/api/family/mock-purchases", body);
      if (!buy.ok) throw new Error(buy.result.error || `Purchase failed (${buy.status})`);
      stepSet("s3", { state: "ok", text: "Request sent for Der Hobbit." }); await refreshState(); await pause();
      begin("s4", "");
      stepSet("s4", { subs: ["Identity: Child (demo sign-in — TrustBoris Agent Gateway in production)"] }); await pause();
      stepSet("s4", { subs: ["Identity: Child (demo sign-in — TrustBoris Agent Gateway in production)", "Tool gating: a child may only ask — place_order is not available"] }); await pause();
      stepSet("s4", { state: "wait", text: "Waiting for a parent", subs: ["Identity: Child (demo sign-in — TrustBoris Agent Gateway in production)", "Tool gating: a child may only ask — place_order is not available", `Family Wallet: ${buy.result.message || "Request recorded."}`] }); await pause();
      begin("s5", "Switching to Parent…");
      await as("parent");
      const st = await stateNow();
      const req = (st?.pendingApprovals || [])[0];
      if (!req?.requestId) throw new Error("No pending approval found for the parent.");
      const ap = await post("/api/family/approve", { requestId: req.requestId });
      if (!ap.ok) throw new Error(ap.result.error || `Approval failed (${ap.status})`);
      await refreshState();
      stepSet("s4", { state: "ok", text: "Passed to a parent" });
      stepSet("s5", { state: "ok", text: `${ap.result.message || "Approved."} Ordered — counts against the child's limit and the family limit` }); await pause();
      // Scene 2
      await as("child"); await refreshState(); await pause();
      begin("s6", 'Child: "I want the headphones."'); await ask("headphones"); stepSet("s6", { state: "ok" }); await pause();
      begin("s7", "Comparing offers on idealo…");
      stepSet("s7", { state: "ok", text: firstSentence(conv[conv.length - 1].content) }); await pause();
      begin("s8", "Trying to buy anyway…");
      const bad = await post("/api/family/mock-purchases", { productRef: "headphones-x1" });
      if (bad.ok) throw new Error("Unexpected: the headphones purchase was not refused.");
      if (bad.status !== 409 && bad.status !== 400) throw new Error(bad.result.error || `Unexpected status ${bad.status}`);
      const errText = bad.result.error || bad.result.message || "Refused.";
      stepSet("s8", { state: "bad", text: `Refused — ${errText}` }); await refreshState(); await pause();
      begin("s9", "");
      const verdict = bad.result.verdict || bad.result.reason;
      const subs = [`Family Wallet: only ${money(childLeft())} left this month`];
      if (verdict) subs.push(`Discount check: ${verdict}`);
      stepSet("s9", { state: "bad", text: "", subs, bold: "Every refusal says why and how much is left." });
      setStory((s) => ({ ...s, running: false, finished: { ok: true } }));
    } catch (err) {
      const stopped = err.message === "__stopped__";
      if (current && !stopped) stepSet(current, { state: "bad", text: err.message });
      if (!stopped) setError(err.message);
      setBusy(false);
      setStory((s) => ({ ...s, running: false, finished: { ok: false } }));
    }
  }
  const sampleMember = members[0];
  const suggestions = ["Der Hobbit", "headphones", "coffee machine", "school backpack"];

  async function refreshState() {
    try {
      const response = await api("/api/state");
      if (!response.ok) throw new Error("Could not load family budgets.");
      const state = await response.json();
      setMembers(state.members);
      setPurchases(state.purchases);
      setPendingApprovals(state.pendingApprovals || []);
      setFamily(state.family);
      lastState.current = state;
      const authResponse = await fetch("/api/idealo/status");
      if (authResponse.ok) {
        const authState = await authResponse.json();
        setIdealoConnected(Boolean(authState.connected));
        setOffline(authState.mode === "offline-mock");
        setLlmMode(authState.mode || "");
        setCatalogue(authState.catalogue || "");
        setIdealoCredentialsSaved(Boolean(authState.credentialsSaved));
        if (authState.error) setError(authState.error);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (!authorizationUrl || idealoConnected) return undefined;
    const timer = setInterval(async () => {
      const response = await fetch("/api/idealo/status");
      if (response.ok) {
        const state = await response.json();
        setIdealoConnected(Boolean(state.connected));
        setIdealoCredentialsSaved(Boolean(state.credentialsSaved));
        if (state.connected || state.error) {
          setAuthorizationUrl("");
          setError(state.error || "");
          await refreshState();
        }
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [authorizationUrl, idealoConnected]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages, busy]);

  async function sendMessage(text = draft) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    const next = [...messages, { role: "user", content: trimmed }];
    setMessages(next);
    setDraft("");
    setBusy(true);
    setError("");
    try {
      const response = await api("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "The shopper could not answer just now.");
      setMessages((current) => [...current, { role: "assistant", content: result.reply, memberName: result.memberName }]);
      await refreshState();
    } catch (err) {
      setError(err.message);
      setMessages((current) => [...current, { role: "assistant", content: "I couldn’t connect just now. Check the local setup and try again." }]);
    } finally {
      setBusy(false);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }

  function fillLlmForm(info, providerId) {
    const p = info.providers.find((x) => x.id === providerId) || info.providers[0];
    const same = info.active.providerId === p.id;
    setLlmForm({ providerId: p.id, baseUrl: same ? info.active.baseUrl : p.baseUrl, model: same ? info.active.model : p.defaultModel, apiKey: "" });
  }
  async function openLlmDialog() {
    setLlmError("");
    try {
      const response = await api("/api/llm");
      const info = await response.json();
      if (!response.ok) throw new Error(info.error || "Could not load the model provider.");
      setLlmInfo(info);
      fillLlmForm(info, info.active.providerId);
      setLlmOpen(true);
    } catch (err) { setError(err.message); }
  }
  async function saveLlm(event) {
    event.preventDefault();
    setLlmSaving(true); setLlmError("");
    try {
      const response = await api("/api/llm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(llmForm) });
      const info = await response.json();
      if (!response.ok) throw new Error(info.error || "Could not save the provider.");
      setLlmInfo(info); setLlmForm((f) => ({ ...f, apiKey: "" })); refreshState();
    } catch (err) { setLlmError(err.message); } finally { setLlmSaving(false); }
  }
  async function forgetLlmKey() {
    setLlmSaving(true); setLlmError("");
    try {
      const response = await api("/api/llm/key", { method: "DELETE" });
      const info = await response.json();
      if (!response.ok) throw new Error(info.error || "Could not forget the key.");
      setLlmInfo(info); refreshState();
    } catch (err) { setLlmError(err.message); } finally { setLlmSaving(false); }
  }

  async function connectIdealo(forceReconnect = false) {
    setConnecting(true);
    setError("");
    setAuthorizationUrl("");
    try {
      const endpoint = forceReconnect ? "/api/idealo/reconnect" : "/api/idealo/connect";
      const response = await fetch(endpoint, { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not start idealo sign-in.");
      setIdealoConnected(Boolean(result.connected));
      setIdealoCredentialsSaved(Boolean(result.connected));
      if (!result.connected) setAuthorizationUrl(result.authorizationUrl);
    } catch (err) { setError(err.message); }
    finally { setConnecting(false); }
  }

  async function recordMockPurchase(product) {
    const response = await api("/api/family/mock-purchases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...product, memberName: undefined }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not add this mock purchase. Pick a cheaper offer or ask a parent.");
    setError("");
    await refreshState();
    const left = lastState.current?.members?.find((m) => String(m.name).toLowerCase() === accountRef.current)?.remainingEur;
    setNotice(result?.purchase?.pendingApproval ? "Sent. A parent has to approve it." : `Done. ${money(left)} left this month.`);
    return result;
  }

  async function approveRequest(requestId, action = "approve") {
    setError(""); setNotice("");
    try {
      const response = await api(`/api/family/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ requestId }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not approve this request.");
      setNotice(action === "reject" ? "Rejected. Nothing was spent." : "Approved. The order was placed (simulated).");
      await refreshState();
    } catch (err) { setError(err.message); }
  }

  async function addFamilyMember(event) {
    event.preventDefault();
    setMemberSaving(true);
    setMemberError("");
    try {
      const response = await fetch("/api/family/members", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: memberName, spendingLimitEur: memberBudget }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not add family member.");
      setMembers((current) => [...current, result.member]);
      setMemberName("");
      setMemberBudget("");
      setMemberModalOpen(false);
    } catch (err) { setMemberError(err.message); }
    finally { setMemberSaving(false); }
  }

  const spentTotal = members.reduce((sum, member) => sum + Number(member.spentEur || 0), 0);
  const me = members.find((m) => String(m.name).toLowerCase() === account);
  const info = ROLE_INFO[account];
  const isParent = account === "parent";
  const teenLimit = members.find((m) => String(m.name).toLowerCase() === "teen")?.spendingLimitEur;
  const rule = account === "teen" && teenLimit != null ? `Orders alone up to ${money(Number(teenLimit))} / month; above that a parent decides.` : info.rule;

  return (
    <div className={`app-shell ${story.running ? "story-running" : ""}`}>
      <header className="topbar">
        <div className="brand"><AppMark /><span>Family Shopper</span></div>
        <div className="role-switch" role="radiogroup" aria-label="Signed in as (demo sign-in)">
          {ACCOUNTS.map((id) => <button key={id} type="button" role="radio" aria-checked={account === id} className={`role-btn ${account === id ? "active" : ""}`} onClick={() => switchAccount(id)}><span className="role-avatar" style={{ background: ROLE_INFO[id].color }}>{cap(id).slice(0, 1)}</span>{cap(id)}{id === "parent" && pendingApprovals.length > 0 && <span className="role-badge">{pendingApprovals.length} waiting</span>}</button>)}
        </div>
        <div className="top-actions">
          <button className="ghost-button" type="button" onClick={playStory} disabled={story.running || busy}>▶ Play the story</button>
          <button className="ghost-button" onClick={openLlmDialog} disabled={!isParent} title={isParent ? "" : "Only a parent can change this"}>Model provider</button>
          {idealoConnected ? <span className="live-pill"><i /> idealo tools ready</span> : <button className="ghost-button" onClick={() => connectIdealo(false)} disabled={connecting}>{connecting ? "Checking…" : idealoCredentialsSaved ? "Check idealo access" : "Connect idealo"}</button>}
          <button className="ghost-button" type="button" onClick={() => connectIdealo(true)} disabled={connecting}>Reconnect idealo</button>
        </div>
      </header>
      {offline ? <div className="offline-banner">Offline demo: idealo mock, no LLM</div> : llmMode && <div className="offline-banner">Model: {llmMode.replace("llm:", "")} · catalogue: {catalogue === "live" ? "live idealo" : "idealo mock"}</div>}
      <div className="toast-area" aria-live="polite">{notice && <div className="toast">{notice}</div>}</div>
      <div className="who-bar" style={{ "--who": info.color }}>
        <div className="who-text"><span className="who-label">Signed in as</span><strong>{info.label}</strong><span className="who-rule">{rule}</span></div>
        {me && <div className="who-money"><span>Your budget left</span><strong>{money(me.remainingEur)}</strong></div>}
        {family && <div className="who-money"><span>Family budget left</span><strong>{money(family.remainingEur)}</strong></div>}
      </div>
      <main className="workspace">
        <section className="chat-column" aria-label="Chat with the shopping agent">
          <div className={`chat-panel ${messages.length ? "has-messages" : ""}`}>
            {messages.length === 0 ? (
              <div className="welcome-card">
                <div className="welcome-title">What are we looking for?</div>
                <div className="welcome-subtitle">Ask for a product. The agent compares offers and the family wallet decides whether you may buy.</div>
                <ol className="steps"><li>Choose who you are</li><li>Ask for a product</li><li>Order within your budget</li></ol>
                <div className="suggestions">
                  {suggestions.map((suggestion) => <button key={suggestion} type="button" className="suggestion" onClick={() => sendMessage(suggestion)}>{suggestion}<Icon name="arrow" size={15} /></button>)}
                </div>
              </div>
            ) : <div className="messages">{messages.map((message, index) => <ChatMessage key={`${index}-${message.role}`} message={message.role === "assistant" ? { ...message, memberName: cap(account) } : message} onMockPurchase={recordMockPurchase} budget={{ role: account, meLeft: me?.remainingEur, familyLeft: family?.remainingEur }} />)}{busy && <div className="message-row assistant-row" role="status"><div className="thinking"><i /><i /><i /><span>Agent is comparing offers…</span></div></div>}<div ref={endRef} /></div>}
          </div>

          <div className="status-area" aria-live="polite">
            {error && <div className="error-note" role="alert"><Icon name="info" size={16} />{error}</div>}
          </div>
          {authorizationUrl && !idealoConnected && <div className="connect-note"><div><strong>Finish connecting idealo</strong><span>Sign in in idealo’s secure window, then return here.</span></div><a href={authorizationUrl} target="_blank" rel="noreferrer">Continue to idealo <Icon name="arrow" size={15} /></a></div>}
          <form className="composer" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}>
            <label htmlFor="chat-input" className="composer-label">Message to the shopping agent</label>
            <textarea id="chat-input" ref={inputRef} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } }} placeholder="e.g. Der Hobbit, headphones…" rows="2" readOnly={busy || story.running} />
            <div className="composer-bottom"><span>Prices can change. Purchases are simulated.</span><button className="send-button" type="submit" disabled={!draft.trim() || busy || story.running}>{busy ? "Sending…" : "Send"} <Icon name="arrow" size={17} /></button></div>
          </form>
        </section>

        <aside className="insights-column">
          {(story.running || story.steps.length > 0) && <Decision steps={story.steps} finished={story.finished} running={story.running} onStop={() => { storyAbort.current = true; }} onAgain={playStory} />}
          <details className="panel" open={mineOpen} onToggle={(e) => setMineOpen(e.currentTarget.open)}>
            <summary><h2>Budgets</h2></summary>
            {family && <Budget big label="Family budget this month" remaining={family.remainingEur} spent={family.spentEur} limit={family.capEur} />}
            {members.map((member) => <MemberCard key={member.name} member={member} me={String(member.name).toLowerCase() === account} />)}
            {members.length === 0 && <div className="empty-card">No budgets loaded yet.</div>}
          </details>

          <section className={`panel ${isParent && pendingApprovals.length ? "panel-first" : ""}`}>
            <h2>Waiting for parent approval {pendingApprovals.length > 0 && <span className="activity-count">{pendingApprovals.length}</span>}</h2>
            {pendingApprovals.length === 0 && <div className="empty-card">No requests waiting.</div>}
            {pendingApprovals.map((r) => <div className="approval" key={r.requestId}><div className="purchase-info"><strong>{r.productName}</strong><small>{r.member} · {money(r.priceEur)}</small></div>
              {isParent ? <div className="approval-actions"><button className="mock-buy-button" type="button" onClick={() => approveRequest(r.requestId)}>Approve</button><button className="secondary-button" type="button" onClick={() => approveRequest(r.requestId, "reject")}>Reject</button></div> : <small className="readonly-note">Read-only: only a parent can decide.</small>}</div>)}
          </section>

          <section className="panel">
            <h2>Recent purchases <span className="activity-count">{purchases.length}</span></h2>
            {purchases.length ? purchases.slice().reverse().slice(0, 4).map((purchase) => <div className="purchase-row" key={purchase.id}><div className="purchase-icon"><Icon name="bag" size={17} /></div><div className="purchase-info"><strong>{purchase.productName}</strong><small>{purchase.member} · simulated</small></div><span className="purchase-price">−{money(purchase.priceEur)}</span></div>) : <div className="empty-card">No purchases yet.</div>}
            {purchases.length > 0 && <div className="activity-total"><span>Total simulated spend</span><strong>{money(spentTotal)}</strong></div>}
          </section>
        </aside>
      </main>
      <footer className="footnote">Purchases are simulated; no real order is placed.<br />Demo sign-in: accounts are simulated; in production the caller identity comes from TrustBoris.</footer>
      {memberModalOpen && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !memberSaving) setMemberModalOpen(false); }}>
        <section className="member-modal" role="dialog" aria-modal="true" aria-labelledby="member-modal-title">
          <button className="modal-close" type="button" onClick={() => setMemberModalOpen(false)} disabled={memberSaving} aria-label="Close">×</button>
          <div className="modal-eyebrow">FAMILY BUDGET</div>
          <h2 id="member-modal-title">Add family member</h2>
          <p>Set a name and demo spending limit to start tracking their budget.</p>
          <form onSubmit={addFamilyMember}>
            <label htmlFor="member-name">Name</label>
            <input id="member-name" autoFocus autoComplete="off" maxLength={60} value={memberName} onChange={(event) => setMemberName(event.target.value)} placeholder="e.g. Alex" required />
            <label htmlFor="member-budget">Spending limit</label>
            <div className="budget-input"><span>€</span><input id="member-budget" type="number" min="0" max="1000000" step="0.01" value={memberBudget} onChange={(event) => setMemberBudget(event.target.value)} placeholder="60.00" required /></div>
            {memberError && <div className="modal-error" role="alert">{memberError}</div>}
            <div className="modal-actions"><button type="button" className="modal-cancel" onClick={() => setMemberModalOpen(false)} disabled={memberSaving}>Cancel</button><button type="submit" className="modal-save" disabled={memberSaving}>{memberSaving ? "Adding…" : "Add member"}</button></div>
          </form>
        </section>
      </div>}
      {llmOpen && llmInfo && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !llmSaving) setLlmOpen(false); }}>
        <section className="member-modal" role="dialog" aria-modal="true" aria-labelledby="llm-modal-title">
          <button className="modal-close" type="button" onClick={() => setLlmOpen(false)} disabled={llmSaving} aria-label="Close">×</button>
          <div className="modal-eyebrow">MODEL PROVIDER</div>
          <h2 id="llm-modal-title">Bring your own model</h2>
          <p>Active: {llmInfo.providers.find((p) => p.id === llmInfo.active.providerId)?.label} · {llmInfo.active.model || "no model"} · {llmInfo.active.hasKey ? `key ends in ••••${llmInfo.active.keyLast4}` : "no key (offline demo)"}</p>
          <form onSubmit={saveLlm}>
            <label htmlFor="llm-provider">Provider</label>
            <select id="llm-provider" value={llmForm.providerId} onChange={(event) => fillLlmForm(llmInfo, event.target.value)}>{llmInfo.providers.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}</select>
            {(() => { const p = llmInfo.providers.find((x) => x.id === llmForm.providerId); return <>
              <label htmlFor="llm-url">Base URL</label>
              <input id="llm-url" autoComplete="off" value={llmForm.baseUrl} readOnly={!p?.editableBaseUrl} onChange={(event) => setLlmForm({ ...llmForm, baseUrl: event.target.value })} placeholder="https://…/v1" required />
              {p?.unverified && <small>Unverified: check the base URL in your Nebius console.</small>}
              {p?.note && <small>{p.note}</small>}
            </>; })()}
            <label htmlFor="llm-model">Model</label>
            <input id="llm-model" autoComplete="off" value={llmForm.model} onChange={(event) => setLlmForm({ ...llmForm, model: event.target.value })} required />
            <label htmlFor="llm-key">API key</label>
            <input id="llm-key" type="password" autoComplete="off" value={llmForm.apiKey} onChange={(event) => setLlmForm({ ...llmForm, apiKey: event.target.value })} placeholder={llmInfo.active.hasKey ? "leave empty to keep the current key" : "paste your key"} />
            <small>The key stays in this server's memory only; it is not saved to disk and is gone after a restart. Use a key you can revoke.</small>
            {llmError && <div className="modal-error" role="alert">{llmError}</div>}
            <div className="modal-actions"><button type="button" className="modal-cancel" onClick={forgetLlmKey} disabled={llmSaving || !llmInfo.active.hasKey}>Forget key</button><button type="submit" className="modal-save" disabled={llmSaving}>{llmSaving ? "Saving…" : "Save"}</button></div>
          </form>
        </section>
      </div>}
    </div>
  );
}
