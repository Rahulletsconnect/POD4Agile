import React, { useEffect, useState } from 'react'

function LoginForm({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError(''); setBusy(true)
    try {
      const r = await fetch('/api/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || 'Login failed')
      onLogin(data)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="page">
      <div className="card">
        <h1>Sign in</h1>
        <p className="lead">Sample login — test account: <b>test</b> / <b>test</b></p>
        <form onSubmit={submit}>
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          {error && <div className="alert err">{error}</div>}
          <button className="primary" disabled={busy || !username || !password}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}

function BankingHome({ session, onLogout }) {
  const [account, setAccount] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      fetch(`/api/account?token=${encodeURIComponent(session.token)}`).then((r) => r.json()),
      fetch(`/api/transactions?token=${encodeURIComponent(session.token)}`).then((r) => r.json()),
    ]).then(([a, t]) => { setAccount(a); setTransactions(t) })
      .catch(() => setError('Could not load account data.'))
  }, [session.token])

  return (
    <div className="dash">
      <header className="dash-header">
        <b>Sample Bank</b>
        <div className="dash-user">Hi, {session.username} <button className="link" onClick={onLogout}>Log out</button></div>
      </header>

      <main className="dash-main">
        {error && <div className="alert err">{error}</div>}
        {account && (
          <section className="balance-card">
            <small>Account {account.account_number}</small>
            <div className="balance">{account.currency} {account.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
          </section>
        )}

        <section className="card">
          <h2>Recent transactions</h2>
          <table>
            <thead><tr><th>Date</th><th>Description</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td>{t.description}</td>
                  <td className={t.amount < 0 ? 'neg' : 'pos'} style={{ textAlign: 'right' }}>
                    {t.amount < 0 ? '-' : '+'}${Math.abs(t.amount).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  )
}

export default function App() {
  const [session, setSession] = useState(null)

  async function logout() {
    await fetch(`/api/logout?token=${encodeURIComponent(session.token)}`, { method: 'POST' })
    setSession(null)
  }

  return session
    ? <BankingHome session={session} onLogout={logout} />
    : <LoginForm onLogin={setSession} />
}
