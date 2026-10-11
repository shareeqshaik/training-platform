import { useState } from "react";
export default function Modules({ call, courses }) {
  const [cid, setCid] = useState(""); const [list, setList] = useState([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const load = id => { setCid(id); setErr(""); if (!id) return setList([]);
    call(`/admin/courses/${id}/modules`).then(setList).catch(e => setErr(e.message)); };
  const edit = async m => {
    const title = window.prompt("Module title", m.title); if (title === null || !title.trim()) return;
    const content = window.prompt("Text content", m.content || ""); if (content === null) return;
    const video = window.prompt("Video URL (blank for none)", m.video_url || ""); if (video === null) return;
    try { await call(`/modules/${m.id}`, "PUT", { title, content, video_url: video || null }); setMsg("Module updated"); load(cid); }
    catch (x) { setErr(x.message); } };
  const del = async m => {
    if (!window.confirm(`Delete module "${m.title}" and its quiz?`)) return;
    try { await call(`/modules/${m.id}`, "DELETE"); setMsg("Module deleted"); load(cid); } catch (x) { setErr(x.message); } };
  return (<div>
    <h3>Manage modules and quizzes</h3>
    {msg && <p style={{ color: "green" }}>{msg}</p>}{err && <p role="alert">{err}</p>}
    <select value={cid} onChange={e => load(e.target.value)}><option value="">Choose course</option>
      {courses.map(c => <option key={c.id} value={c.id}>#{c.id} {c.title}</option>)}</select>
    <ul>{list.map(m => <li key={m.id}><b>Module id {m.id}: {m.title}</b>{" "}
      <button type="button" onClick={() => edit(m)}>Edit</button>{" "}
      <button type="button" onClick={() => del(m)} style={{ background: "#dc2626", color: "#fff" }}>Delete</button>
      <div>{m.questions.length ? `Quiz: pass ${m.passing_score}%, ${m.questions.length} question(s)${m.max_attempts ? `, max ${m.max_attempts} attempts` : ""}` : "No quiz yet"}</div>
      {m.questions.map((q, i) => <div key={i} style={{ fontSize: 13 }}>{i + 1}. {q.text} (answer: {q.options[q.correct]})</div>)}
    </li>)}</ul>
  </div>);
}