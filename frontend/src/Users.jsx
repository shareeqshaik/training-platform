import { useState, useEffect } from "react";
const blank = { name: "", email: "", password: "", role: "user" };
export default function Users({ call }) {
  const [list, setList] = useState([]); const [f, setF] = useState(blank);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const load = () => call("/users").then(setList).catch(e => setErr(e.message));
  useEffect(() => { load(); }, []);
  const set = k => e => setF({ ...f, [k]: e.target.value });
  const add = async e => { e.preventDefault(); setErr(""); setMsg("");
    try { await call("/users", "POST", f); setMsg("User created"); setF(blank); load(); } catch (x) { setErr(x.message); } };
  const del = async u => {
    if (!window.confirm(`Delete ${u.name}? Their progress and certificates will be removed.`)) return;
    setErr(""); setMsg("");
    try { await call(`/users/${u.id}`, "DELETE"); setMsg("User deleted"); load(); } catch (x) { setErr(x.message); } };
  return (<div>
    <h3>Manage users</h3>
    {msg && <p style={{ color: "green" }}>{msg}</p>}
    {err && <p role="alert">{err}</p>}
    <form onSubmit={add}>
      <input placeholder="Name" value={f.name} onChange={set("name")} required />{" "}
      <input placeholder="Email" value={f.email} onChange={set("email")} required />{" "}
      <input type="password" placeholder="Password (6+ chars)" value={f.password} onChange={set("password")} required />{" "}
      <select value={f.role} onChange={set("role")}><option value="user">user</option><option value="admin">admin</option></select>{" "}
      <button>Add user</button>
    </form>
    <ul>{list.map(u => <li key={u.id}>{u.name} ({u.email}, {u.role}){" "}
      <button type="button" onClick={() => del(u)} style={{ background: "#dc2626", color: "#fff" }}>Delete</button></li>)}</ul>
  </div>);
}