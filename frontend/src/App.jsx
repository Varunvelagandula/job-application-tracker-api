import { useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

const STATUSES = ["applied", "screening", "interview", "offer", "rejected"];

function Auth({ onDone }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  async function submit(e) {
    e.preventDefault();
    setErr("");
    try {
      const r = await api(`/auth/${mode}`, { method: "POST", body: { email, password } });
      setToken(r.access_token);
      onDone();
    } catch (x) {
      setErr(x.message);
    }
  }

  return (
    <form className="card auth" onSubmit={submit}>
      <h1>Job Tracker</h1>
      <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" placeholder="Password (8+ characters)" value={password}
        onChange={(e) => setPassword(e.target.value)} />
      {err && <p className="err">{err}</p>}
      <button>{mode === "login" ? "Log in" : "Create account"}</button>
      <a href="#" onClick={(e) => { e.preventDefault(); setMode(mode === "login" ? "register" : "login"); }}>
        {mode === "login" ? "Need an account? Register" : "Have an account? Log in"}
      </a>
    </form>
  );
}

function Board({ onLogout }) {
  const [apps, setApps] = useState([]);
  const [stats, setStats] = useState(null);
  const [form, setForm] = useState({ company: "", role: "", source: "" });

  async function load() {
    try {
      const [a, s] = await Promise.all([api("/applications?limit=100"), api("/analytics/summary")]);
      setApps(a);
      setStats(s);
    } catch (e) {
      if (e.status === 401 || e.status === 403) onLogout();
    }
  }
  useEffect(() => { load(); }, []);

  async function add(e) {
    e.preventDefault();
    if (!form.company || !form.role) return;
    await api("/applications", { method: "POST", body: { ...form, source: form.source || null } });
    setForm({ company: "", role: "", source: "" });
    load();
  }
  const move = async (id, status) => { await api(`/applications/${id}`, { method: "PATCH", body: { status } }); load(); };
  const remove = async (id) => { await api(`/applications/${id}`, { method: "DELETE" }); load(); };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="wrap">
      <header>
        <h1>Job Tracker</h1>
        <button className="ghost" onClick={onLogout}>Log out</button>
      </header>

      {stats && (
        <div className="stats">
          <div><b>{stats.total}</b><span>Total</span></div>
          <div><b>{Math.round(stats.response_rate * 100)}%</b><span>Response rate</span></div>
          <div><b>{stats.by_status.interview}</b><span>Interviews</span></div>
          <div><b>{stats.by_status.offer}</b><span>Offers</span></div>
          <div><b>{stats.follow_ups_due}</b><span>Follow-ups due</span></div>
        </div>
      )}

      <form className="card add" onSubmit={add}>
        <input placeholder="Company" value={form.company} onChange={set("company")} />
        <input placeholder="Role" value={form.role} onChange={set("role")} />
        <input placeholder="Source (optional)" value={form.source} onChange={set("source")} />
        <button>Add</button>
      </form>

      <div className="board">
        {STATUSES.map((s) => (
          <section key={s} className="col">
            <h2>{s} <small>{apps.filter((a) => a.status === s).length}</small></h2>
            {apps.filter((a) => a.status === s).map((a) => (
              <div key={a.id} className="card item">
                <b>{a.company}</b>
                <span>{a.role}</span>
                {a.source && <small>via {a.source}</small>}
                <div className="row">
                  <select value={a.status} onChange={(e) => move(a.id, e.target.value)}>
                    {STATUSES.map((x) => <option key={x}>{x}</option>)}
                  </select>
                  <button className="ghost" onClick={() => remove(a.id)}>Delete</button>
                </div>
              </div>
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const logout = () => { setToken(null); setAuthed(false); };
  return authed ? <Board onLogout={logout} /> : <Auth onDone={() => setAuthed(true)} />;
}
