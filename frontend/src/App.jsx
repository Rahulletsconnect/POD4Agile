import React, { useEffect, useState } from 'react'

export default function App() {
  const [beneficiaries, setBeneficiaries] = useState([])
  const [schedules, setSchedules] = useState([])
  const [name, setName] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [form, setForm] = useState({ beneficiary_id: '', amount: '', frequency: 'monthly',
    start_date: '', end_date: '', two_factor_confirmed: false })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState(null)
  const [payments, setPayments] = useState([])
  const [audit, setAudit] = useState([])

  const refreshSchedules = () => fetch('/api/schedules').then((r) => r.json()).then(setSchedules)
  useEffect(() => { fetch('/api/beneficiaries').then((r) => r.json()).then(setBeneficiaries); refreshSchedules() }, [])

  async function addBeneficiary() {
    setError('')
    if (!name || !accountNumber) return setError('Enter a name and account number.')
    const r = await fetch('/api/beneficiaries', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, account_number: accountNumber }) })
    const data = await r.json()
    if (!r.ok) return setError(data.detail || 'Failed')
    setBeneficiaries((b) => [...b, data]); setName(''); setAccountNumber('')
  }

  async function createSchedule() {
    setError(''); setBusy(true)
    try {
      const r = await fetch('/api/schedules', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, amount: Number(form.amount), end_date: form.end_date || null }) })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || 'Failed to create schedule')
      await refreshSchedules()
      setForm({ beneficiary_id: '', amount: '', frequency: 'monthly', start_date: '', end_date: '', two_factor_confirmed: false })
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function act(id, action) {
    await fetch(`/api/schedules/${id}/${action}`, { method: 'POST' })
    await refreshSchedules()
    if (selected === id) await openDetail(id)
  }

  async function simulatePayment(id, sufficientFunds) {
    await fetch(`/api/schedules/${id}/process-due-payment?sufficient_funds=${sufficientFunds}`, { method: 'POST' })
    await refreshSchedules()
    await openDetail(id)
  }

  async function openDetail(id) {
    setSelected(id)
    const [p, a] = await Promise.all([
      fetch(`/api/schedules/${id}/payments`).then((r) => r.json()),
      fetch(`/api/schedules/${id}/audit-log`).then((r) => r.json()),
    ])
    setPayments(p); setAudit(a)
  }

  const beneficiaryName = (id) => beneficiaries.find((b) => b.id === id)?.name || id

  return (
    <div className="page">
      <h1>Recurring Payments</h1>
      <p className="lead">REQ-1005 — schedule a recurring payment with a 24-hour reminder before each run.</p>

      <section className="card">
        <h2>1. Beneficiaries</h2>
        <div className="signer-row">
          <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="Account number" value={accountNumber} onChange={(e) => setAccountNumber(e.target.value)} />
          <button className="link" onClick={addBeneficiary}>+ Add</button>
        </div>
        <ul className="audit-list">{beneficiaries.map((b) => <li key={b.id}>{b.name} — {b.account_number}</li>)}</ul>
      </section>

      <section className="card">
        <h2>2. Create a recurring payment</h2>
        <label>Beneficiary</label>
        <select value={form.beneficiary_id} onChange={(e) => setForm((f) => ({ ...f, beneficiary_id: e.target.value }))}>
          <option value="">Select…</option>
          {beneficiaries.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
        <label>Amount</label>
        <input type="number" value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} />
        <label>Frequency</label>
        <select value={form.frequency} onChange={(e) => setForm((f) => ({ ...f, frequency: e.target.value }))}>
          <option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option>
        </select>
        <label>Start date</label>
        <input type="date" value={form.start_date} onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))} />
        <label>End date (optional)</label>
        <input type="date" value={form.end_date} onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))} />
        {Number(form.amount) > 10000 && (
          <label className="sens-checkbox">
            <input type="checkbox" checked={form.two_factor_confirmed}
              onChange={(e) => setForm((f) => ({ ...f, two_factor_confirmed: e.target.checked }))} />
            Confirm second-factor for this payment (required above 10,000)
          </label>
        )}
        <div className="actions"><button className="primary" disabled={busy || !form.beneficiary_id} onClick={createSchedule}>Create schedule</button></div>
      </section>

      {error && <div className="alert err">{error}</div>}

      <section className="card">
        <h2>3. Schedules</h2>
        <table><thead><tr><th>Beneficiary</th><th>Amount</th><th>Frequency</th><th>Next payment</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>{schedules.map((s) => (
            <tr key={s.id}>
              <td>{beneficiaryName(s.beneficiary_id)}</td><td>{s.amount}</td><td>{s.frequency}</td>
              <td>{s.next_payment_date}</td><td>{s.status}</td>
              <td className="row-actions">
                <button className="link" onClick={() => openDetail(s.id)}>Details</button>
                {s.status === 'active' && <>
                  <button className="link" onClick={() => simulatePayment(s.id, true)}>Simulate payment</button>
                  <button className="link" onClick={() => simulatePayment(s.id, false)}>Simulate insufficient funds</button>
                  <button className="link" onClick={() => act(s.id, 'pause')}>Pause</button>
                  <button className="link" onClick={() => act(s.id, 'cancel')}>Cancel</button>
                </>}
                {s.status === 'paused' && <button className="link" onClick={() => act(s.id, 'resume')}>Resume</button>}
              </td>
            </tr>
          ))}</tbody>
        </table>
      </section>

      {selected && (
        <section className="card">
          <h2>Schedule detail</h2>
          <h3>Payment attempts</h3>
          <table><thead><tr><th>Scheduled for</th><th>Status</th><th>Attempted at</th></tr></thead>
            <tbody>{payments.map((p) => <tr key={p.id}><td>{p.scheduled_for}</td><td>{p.status}</td><td>{p.attempted_at}</td></tr>)}</tbody>
          </table>
          <h3>Audit log</h3>
          <ul className="audit-list">{audit.map((e) => <li key={e.id}><b>{e.action}</b> — {e.details} <small>({e.recorded_at})</small></li>)}</ul>
        </section>
      )}
    </div>
  )
}
