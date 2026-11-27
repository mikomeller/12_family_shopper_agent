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
  return { productName, productUrl: link?.[2] || null, priceEur };
}

function FormattedReply({ content, memberName, onMockPurchase }) {
  const [purchaseStates, setPurchaseStates] = useState({});
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
  async function recordFromRow(row, rowIndex) {
    const product = getProductFromRow(row);
    if (!product || !memberName || !onMockPurchase) return;
    setPurchaseStates((current) => ({ ...current, [rowIndex]: { status: "pending" } }));
    try {
      const result = await onMockPurchase({ ...product, memberName });
      setPurchaseStates((current) => ({ ...current, [rowIndex]: { status: "done", message: result?.purchase?.pendingApproval ? "Waiting for parent approval" : "" } }));
    } catch (error) {
      setPurchaseStates((current) => ({ ...current, [rowIndex]: { status: "error", message: error.message } }));
    }
  }
  return <div className="formatted-reply">{blocks.map((block, index) => {
    if (block.type === "table") {
      const [header, ...rows] = block.rows;
      const pricedRows = rows.map((row, rowIndex) => ({ rowIndex, product: getProductFromRow(row) })).filter(({ product }) => product);
      const cheapestRowIndex = pricedRows.length > 1 ? pricedRows.reduce((lowest, current) => current.product.priceEur < lowest.product.priceEur ? current : lowest, pricedRows[0]).rowIndex : null;
      const sameProductOffers = new Set(pricedRows.map(({ product }) => product.productName.toLocaleLowerCase("de-DE"))).size === 1;
      const cheapestLabel = sameProductOffers ? "Cheapest shop" : "Lowest price";
      return <div className="reply-table-wrap" key={index}><table className="reply-table"><thead><tr>{header.map((cell, cellIndex) => <th key={cellIndex}><InlineText text={cell} /></th>)}{memberName && <th>MOCK BUY</th>}</tr></thead><tbody>{rows.map((row, rowIndex) => {
        const product = getProductFromRow(row);
        const state = purchaseStates[`${index}-${rowIndex}`];
        const isCheapest = rowIndex === cheapestRowIndex;
        return <tr key={rowIndex} className={isCheapest ? "cheapest-option" : ""}>{header.map((_, cellIndex) => <td key={cellIndex}>{cellIndex === 0 ? <><InlineText text={row[cellIndex] || "—"} />{isCheapest && <span className="cheapest-tag">{cheapestLabel}</span>}</> : <InlineText text={row[cellIndex] || "—"} />}</td>)}{memberName && <td className="reply-action-cell">{product ? <><button className="mock-buy-button" type="button" disabled={state?.status === "pending" || state?.status === "done"} aria-label={`Record a mock purchase of ${product.productName} for ${memberName}`} onClick={() => recordFromRow(row, `${index}-${rowIndex}`)}>{state?.status === "pending" ? "Adding…" : state?.status === "done" ? (state.message ? "Requested" : "Added") : "Buy (mock)"}</button>{state?.status === "done" && state.message && <span className="mock-buy-error">{state.message}</span>}{state?.status === "error" && <span className="mock-buy-error" role="alert">{state.message}</span>}</> : "—"}</td>}</tr>;
      })}</tbody></table></div>;
    }
    if (block.type === "list") return <ul key={index}>{block.items.map((item, itemIndex) => <li key={itemIndex}><InlineText text={item} /></li>)}</ul>;
    return <p key={index}><InlineText text={block.text} /></p>;
  })}</div>;
}

function MemberCard({ member }) {
  const spent = Number(member.spentEur || 0);
  const hasCap = member.spendingLimitEur != null;
  const limit = hasCap ? Number(member.spendingLimitEur) : Number(member.familyCapEur || 0);
  const percent = limit ? Math.min(100, (spent / limit) * 100) : 0;
  return (
    <article className="member-card">
      <div className="member-card-top">
        <div className="avatar">{member.name?.slice(0, 1).toUpperCase()}</div>
        <div className="member-name">{member.name}<span>{member.role}{hasCap ? "" : " · family cap only"}</span></div>
        <span className="card-menu">•••</span>
      </div>
      <div className="balance-label">WALLET BUDGET REMAINING</div>
      <div className="balance-amount">{money(member.remainingEur)}</div>
      <div className="progress-track"><div className="progress-value" style={{ width: `${percent}%` }} /></div>
      <div className="budget-foot"><span>{money(spent)} used</span><span>{hasCap ? `of ${money(limit)}` : `family ${money(member.familyRemainingEur)} left`}</span></div>
    </article>
  );
}

function ChatMessage({ message, onMockPurchase }) {
  const assistant = message.role === "assistant";
  return (
    <div className={`message-row ${assistant ? "assistant-row" : "user-row"}`}>
      {assistant && <div className="tiny-mark"><Icon name="spark" size={15} /></div>}
      <div className={`message-bubble ${assistant ? "assistant-bubble" : "user-bubble"}`}>
        {assistant && <div className="message-label">SHOPPER</div>}
        <div className="message-copy">{assistant ? <FormattedReply content={message.content} memberName={message.memberName} onMockPurchase={onMockPurchase} /> : message.content}</div>
      </div>
    </div>
  );
}

export default function ShopperApp() {
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
  const [memberModalOpen, setMemberModalOpen] = useState(false);
  const [memberName, setMemberName] = useState("");
  const [memberBudget, setMemberBudget] = useState("");
  const [memberSaving, setMemberSaving] = useState(false);
  const [memberError, setMemberError] = useState("");
  const endRef = useRef(null);
  const sampleMember = members[0];
  const suggestions = sampleMember ? [
    `Find headphones for ${sampleMember.name} under ${money(Number(sampleMember.remainingEur || 0))}`,
    `Compare electric toothbrushes for ${sampleMember.name}`,
    `What’s the best value for ${sampleMember.name}’s budget?`,
  ] : [
    "Find headphones for a family member under €60",
    "Compare a few good electric toothbrushes",
    "What’s the best value for a family member’s budget?",
  ];

  async function refreshState() {
    try {
      const response = await fetch("/api/state");
      if (!response.ok) throw new Error("Could not load family budgets.");
      const state = await response.json();
      setMembers(state.members);
      setPurchases(state.purchases);
      setPendingApprovals(state.pendingApprovals || []);
      setFamily(state.family);
      const authResponse = await fetch("/api/idealo/status");
      if (authResponse.ok) {
        const authState = await authResponse.json();
        setIdealoConnected(Boolean(authState.connected));
        setIdealoCredentialsSaved(Boolean(authState.credentialsSaved));
        if (authState.error) setError(authState.error);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { refreshState(); }, []);
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
      const response = await fetch("/api/chat", {
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
    }
  }

  async function connectIdealo() {
    setConnecting(true);
    setError("");
    try {
      const response = await fetch("/api/idealo/connect", { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not start idealo sign-in.");
      if (result.connected) { setIdealoConnected(true); setIdealoCredentialsSaved(true); }
      else setAuthorizationUrl(result.authorizationUrl);
    } catch (err) { setError(err.message); }
    finally { setConnecting(false); }
  }

  async function recordMockPurchase(product) {
    const response = await fetch("/api/family/mock-purchases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(product),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not add this mock purchase.");
    setError("");
    await refreshState();
    return result;
  }

  async function approveRequest(requestId) {
    setError("");
    try {
      const response = await fetch("/api/family/approve", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ requestId }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not approve this request.");
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

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><AppMark /><span>family<span className="brand-light">shopper</span></span></div>
        <div className="nav-caption">YOUR SPACE</div>
        <button className="nav-item active"><span className="nav-dot" />Shopping assistant</button>
        <button className="nav-item" onClick={refreshState}><Icon name="wallet" size={18} />Family budgets</button>
        <div className="side-bottom">
          <div className="demo-note"><span className="demo-dot" /><div><strong>Demo mode</strong><small>Purchases are pretend only</small></div></div>
          <div className="profile"><div className="profile-avatar">F</div><div><strong>Family space</strong><small>Personal shopper</small></div><span className="profile-more">•••</span></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar"><div className="breadcrumb">Family space <span>/</span> <strong>Shopping assistant</strong></div>{idealoConnected ? <div className="live-pill"><i /> idealo tools ready</div> : <button className="connect-button" onClick={connectIdealo} disabled={connecting}>{connecting ? "Checking…" : idealoCredentialsSaved ? "Check idealo access" : "Connect idealo"}</button>}</header>
        <div className="workspace">
          <section className="chat-column">
            <div className="page-heading"><div className="eyebrow"><Icon name="spark" size={15} /> YOUR FAMILY’S PERSONAL SHOPPER</div><h1>Find the right thing.<br /><span>For the right price.</span></h1><p>Thoughtful picks, compared for your family and their budget.</p></div>

            <div className={`chat-panel ${messages.length ? "has-messages" : ""}`}>
              {messages.length === 0 ? (
                <div className="welcome-card">
                  <div className="welcome-icon"><Icon name="spark" size={21} /></div>
                  <div className="welcome-title">What are we looking for?</div>
                  <div className="welcome-subtitle">Tell me what you need and who it’s for. I’ll compare current prices and find a fit.</div>
                  <div className="suggestions">
                    {suggestions.map((suggestion) => <button key={suggestion} className="suggestion" onClick={() => sendMessage(suggestion)}>{suggestion}<Icon name="arrow" size={15} /></button>)}
                  </div>
                </div>
              ) : <div className="messages">{messages.map((message, index) => <ChatMessage key={`${index}-${message.role}`} message={message.role === "assistant" ? { ...message, memberName: memberForReply(message, messages, index, members) } : message} onMockPurchase={recordMockPurchase} />)}{busy && <div className="message-row assistant-row"><div className="tiny-mark"><Icon name="spark" size={15} /></div><div className="thinking"><i /><i /><i /><span>Comparing options</span></div></div>}<div ref={endRef} /></div>}
            </div>

            {error && <div className="error-note"><Icon name="info" size={16} />{error}</div>}
            {authorizationUrl && !idealoConnected && <div className="connect-note"><div><strong>Finish connecting idealo</strong><span>Sign in in idealo’s secure window, then return here.</span></div><a href={authorizationUrl} target="_blank" rel="noreferrer">Continue to idealo <Icon name="arrow" size={15} /></a></div>}
            <form className="composer" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}>
              <textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } }} placeholder="Ask for something your family needs…" rows="1" disabled={busy} />
              <div className="composer-bottom"><span><Icon name="info" size={14} />Prices can change. Purchases are simulated.</span><button className="send-button" type="submit" disabled={!draft.trim() || busy} aria-label="Send message"><Icon name="arrow" size={19} /></button></div>
            </form>
            <div className="footnote">Search results from idealo · Mock purchases only · Nothing is ever ordered</div>
          </section>

          <aside className="insights-column">
            <div className="section-heading"><div><span className="section-kicker">FAMILY</span><h2>Budget overview</h2></div><button className="icon-button" onClick={() => { setMemberError(""); setMemberModalOpen(true); }} aria-label="Add family member" title="Add family member"><Icon name="plus" size={17} /></button></div>
            {family && <div className="empty-card">Family budget this month: {money(family.spentEur)} of {money(family.capEur)} spent, {money(family.remainingEur)} left</div>}
            {members.map((member) => <MemberCard key={member.name} member={member} />)}
            {members.length === 0 && <div className="empty-card">Add a family member to start tracking their demo budget.</div>}

            {pendingApprovals.length > 0 && <div className="activity-card"><strong>Waiting for parent approval</strong>{pendingApprovals.map((r) => <div className="purchase-row" key={r.requestId}><div className="purchase-info"><strong>{r.productName}</strong><small>{r.member} · {money(r.priceEur)}</small></div><button className="mock-buy-button" type="button" onClick={() => approveRequest(r.requestId)}>Approve</button></div>)}</div>}

            <div className="activity-heading"><div><span className="section-kicker">LOCAL LEDGER</span><h2>Mock purchases</h2></div><span className="activity-count">{purchases.length}</span></div>
            <div className="activity-card">
              {purchases.length ? purchases.slice().reverse().slice(0, 4).map((purchase) => <div className="purchase-row" key={purchase.id}><div className="purchase-icon"><Icon name="bag" size={17} /></div><div className="purchase-info"><strong>{purchase.productName}</strong><small>{purchase.member} · pretend purchase</small></div><span className="purchase-price">−{money(purchase.priceEur)}</span></div>) : <div className="empty-activity"><div className="empty-icon"><Icon name="bag" size={19} /></div><strong>No purchases yet</strong><span>When you record a mock purchase, it’ll show up here.</span></div>}
              {purchases.length > 0 && <div className="activity-total"><span>Total simulated spend</span><strong>{money(spentTotal)}</strong></div>}
            </div>

            <div className="privacy-card"><div className="privacy-icon"><Icon name="wallet" size={17} /></div><div><strong>Your demo stays local</strong><p>Budgets and caps come from the Family Wallet; purchases are simulated.</p></div></div>
          </aside>
        </div>
      </main>
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
    </div>
  );
}
