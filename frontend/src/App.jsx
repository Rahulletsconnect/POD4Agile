import React, { useState } from 'react'

function useSignerFields(initial) {
  const [signers, setSigners] = useState(initial)
  const update = (i, field, value) =>
    setSigners((s) => s.map((row, idx) => (idx === i ? { ...row, [field]: value } : row)))
  const add = () => setSigners((s) => [...s, { name: '', email: '' }])
  const remove = (i) => setSigners((s) => s.filter((_, idx) => idx !== i))
  return { signers, update, add, remove }
}

export default function App() {
  const [accountNumber, setAccountNumber] = useState('')
  const { signers, update, add, remove } = useSignerFields([{ name: '', email: '' }])
  const [account, setAccount] = useState(null)
  const [notifications, setNotifications] = useState([])
  const [auditLog, setAuditLog] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function createAccount() {
    setError('')
    const cleanSigners = signers.filter((s) => s.name && s.email)
    if (!accountNumber || !cleanSigners.length) return setError('Enter an account number and at least one signer.')
    setBusy(true)
    try {
      const r = await fetch('/api/accounts', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_number: accountNumber, signers: cleanSigners }),
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || 'Failed to create account')
      setAccount(data); setNotifications([]); setAuditLog([])
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function closeAccount() {
    setError(''); setBusy(true)
    try {
      const r = await fetch(`/api/accounts/${account.id}/close`, { method: 'POST' })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || 'Failed to close account')
      setAccount(data)
      const [n, a] = await Promise.all([
        fetch(`/api/accounts/${account.id}/notifications`).then((r) => r.json()),
        fetch(`/api/audit-log?account_id=${account.id}`).then((r) => r.json()),
      ])
      setNotifications(n); setAuditLog(a)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="page">
      <h1>Account Closure Notifications</h1>
      <p className="lead">REQ-1003 — notify every signer when an account closes, and keep a 7-year audit trail.</p>

      {!account ? (
        <section className="card">
          <h2>1. Open an account</h2>
          <label>Account number</label>
          <input value={accountNumber} onChange={(e) => setAccountNumber(e.target.value)} placeholder="e.g. 1234567890" />
          <label>Signers</label>
          {signers.map((s, i) => (
            <div className="signer-row" key={i}>
              <input placeholder="Name" value={s.name} onChange={(e) => update(i, 'name', e.target.value)} />
              <input placeholder="Email" value={s.email} onChange={(e) => update(i, 'email', e.target.value)} />
              {signers.length > 1 && <button className="link" onClick={() => remove(i)}>Remove</button>}
            </div>
          ))}
          <button className="link" onClick={add}>+ Add another signer</button>
          <div className="actions"><button className="primary" disabled={busy} onClick={createAccount}>Create account</button></div>
        </section>
      ) : (
        <section className="card">
          <h2>Account {account.account_number}</h2>
          <p>Status: <b>{account.status}</b>{account.closed_at && <> — closed at {account.closed_at}</>}</p>
          <p>Signers: {account.signers.map((s) => `${s.name} <${s.email}>`).join(', ')}</p>
          {account.status === 'open' && (
            <div className="actions"><button className="primary" disabled={busy} onClick={closeAccount}>Close account</button></div>
          )}
        </section>
      )}

      {error && <div className="alert err">{error}</div>}

      {notifications.length > 0 && (
        <section className="card">
          <h2>2. Notifications sent</h2>
          <table><thead><tr><th>Recipient</th><th>Channel</th><th>Status</th><th>Retries</th><th>Sent at</th></tr></thead>
            <tbody>{notifications.map((n) => (
              <tr key={n.id}><td>{n.recipient}</td><td>{n.channel}</td><td>{n.status}</td><td>{n.retry_count}</td><td>{n.sent_at}</td></tr>
            ))}</tbody>
          </table>
        </section>
      )}

      {auditLog.length > 0 && (
        <section className="card">
          <h2>3. Audit log (retained 7 years)</h2>
          <ul className="audit-list">{auditLog.map((e) => (
            <li key={e.id}><b>{e.action}</b> — {e.details} <small>({e.recorded_at})</small></li>
          ))}</ul>
        </section>
      )}
    </div>
  )
}
