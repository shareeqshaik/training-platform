import { useState, useEffect } from "react";
import Users from "./Users";
import Modules from "./Modules";
export default function Admin({ call }) {
  const [d, setD] = useState(null); const [cl, setCl] = useState([]); const [err, setErr] = useState(""); const [ok, setOk] = useState("");
  const [title, setTitle] = useState(""); const [desc, setDesc] = useState(""); const [cat, setCat] = useState("");
  const [mc, setMc] = useState(""); const [mt, setMt] = useState(""); const [mb, setMb] = useState(""); const [mv, setMv] = useState("");
  const [qm, setQm] = useState(""); const [qp, setQp] = useState(70); const [qa, setQa] = useState(""); const [qt, setQt] = useState("");
  const [users, setUsers] = useState([]); const [ac, setAc] = useState(""); const [au, setAu] = useState([]); const [due, setDue] = useState("");
  const load = () => {
    call("/admin/dashboard").then(setD).catch(e => setErr(e.message));
    call("/courses").then(setCl).catch(() => {});
    call("/users").then(setUsers).catch(() => {});
  };
  useEffect(() => { load(); }, []);
  const run = async (fn, msg) => { setErr(""); setOk(""); try { const r = await fn(); setOk(msg(r)); load(); return true; } catch (x) { setErr(x.message); return false; } };
  const create = async e => { e.preventDefault();
    if (await run(() => call("/courses", "POST", { title, description: desc, category: cat }), r => `Course created (id ${r.id})`)) { setTitle(""); setDesc(""); setCat(""); } };
  const edit = c => {
    const t = window.prompt("Course title", c.title); if (t === null || !t.trim()) return;
    const k = window.prompt("Category", c.category || ""); if (k === null) return;
    run(() => call(`/courses/${c.id}`, "PUT", { title: t, description: c.description || "", category: k }), () => "Course updated");
  };
  const del = c => {
    if (!window.confirm(`Delete "${c.title}" with all its modules, quizzes and results? This cannot be undone.`)) return;
    run(() => call(`/courses/${c.id}`, "DELETE"), () => "Course deleted");
  };
  const addModule = async e => { e.preventDefault();
    if (await run(() => call(`/courses/${mc}/modules`, "POST", { title: mt, content: mb, video_url: mv || null }), r => `Module created (id ${r.id})`)) { setMt(""); setMb(""); setMv(""); } };
  const addQuiz = async e => { e.preventDefault();
    const questions = qt.split("\n").filter(l => l.trim()).map(l => {
      const [q, o, c] = l.split("|").map(s => s.trim());
      return { text: q, options: (o || "").split(";").map(s => s.trim()).filter(Boolean), correct: Number(c) - 1 };
    });
    if (await run(() => call(`/modules/${qm}/quiz`, "POST", { passing_score: Number(qp), max_attempts: qa ? Number(qa) : null, questions }), r => `Quiz saved (id ${r.id})`)) setQt(""); };
  const toggle = id => setAu(au.includes(id) ? au.filter(x => x !== id) : [...au, id]);
  const assign = async e => { e.preventDefault();
    if (!au.length) { setErr("Select at least one user"); return; }
    if (await run(() => call(`/courses/${ac}/assign`, "POST", { user_ids: au, due_date: due || null }), r => `Assigned to ${r.assigned} new user(s)`)) { setAu([]); setDue(""); } };
  const remind = () => run(() => call("/admin/send-reminders", "POST"), r => `Deadline reminders queued for ${r.reminders} learner(s)`);
  if (!d) return <p>{err || "Loading dashboard…"}</p>;
  return (<div style={{ border: "1px solid #888", padding: 12, marginBottom: 16 }}>
    <h2>Admin Dashboard</h2>
    <p>Courses: {d.courses.length} | Enrollments: {d.stats.enrollments} | Certificates: {d.stats.certified}</p>
    {ok && <p style={{ color: "green" }}>{ok}</p>}
    {err && <p role="alert" style={{ color: "red" }}>{err}</p>}
    <h3>Create course</h3>
    <form onSubmit={create}>
      <input placeholder="Title" value={title} onChange={e => setTitle(e.target.value)} required />{" "}
      <input placeholder="Description" value={desc} onChange={e => setDesc(e.target.value)} />{" "}
      <input placeholder="Category" value={cat} onChange={e => setCat(e.target.value)} />{" "}
      <button>Create</button>
    </form>
    <h3>Add module</h3>
    <form onSubmit={addModule}>
      <select value={mc} onChange={e => setMc(e.target.value)} required>
        <option value="">Choose course</option>
        {d.courses.map(c => <option key={c.id} value={c.id}>#{c.id} {c.title}</option>)}
      </select>{" "}
      <input placeholder="Module title" value={mt} onChange={e => setMt(e.target.value)} required />{" "}
      <input placeholder="Text content" value={mb} onChange={e => setMb(e.target.value)} />{" "}
      <input placeholder="Video URL (optional)" value={mv} onChange={e => setMv(e.target.value)} />{" "}
      <button>Add module</button>
    </form>
    <h3>Add quiz to a module</h3>
    <p style={{ fontSize: 13 }}>One question per line: <code>Question | option A ; option B ; option C | correct option number</code><br />
      Example: <code>Is fire hot? | No ; Yes | 2</code></p>
    <form onSubmit={addQuiz}>
      <input type="number" placeholder="Module id" value={qm} onChange={e => setQm(e.target.value)} required style={{ width: 90 }} />{" "}
      <input type="number" min="1" max="100" placeholder="Pass %" value={qp} onChange={e => setQp(e.target.value)} required style={{ width: 80 }} />{" "}
      <input type="number" min="1" placeholder="Max attempts (optional)" value={qa} onChange={e => setQa(e.target.value)} style={{ width: 170 }} />
      <br /><textarea rows="4" cols="70" placeholder="Questions, one per line" value={qt} onChange={e => setQt(e.target.value)} required />
      <br /><button>Save quiz</button>
    </form>
    <h3>Assign course to users</h3>
    <form onSubmit={assign}>
      <select value={ac} onChange={e => setAc(e.target.value)} required>
        <option value="">Choose course</option>
        {d.courses.map(c => <option key={c.id} value={c.id}>#{c.id} {c.title}</option>)}
      </select>{" "}
      <label>Due date (optional): <input type="date" value={due} onChange={e => setDue(e.target.value)} /></label>
      <div>{users.map(u => <label key={u.id} style={{ display: "block" }}>
        <input type="checkbox" checked={au.includes(u.id)} onChange={() => toggle(u.id)} /> {u.name} ({u.email}, {u.role})
      </label>)}</div>
      <button>Assign</button>
    </form>
    <Users call={call} />
    <Modules call={call} courses={d.courses} />
    <h3>Courses</h3>
    <ul>{cl.map(c => <li key={c.id}>#{c.id} {c.title} ({c.category || "no category"}){" "}
      <button type="button" onClick={() => edit(c)}>Edit</button>{" "}
      <button type="button" onClick={() => del(c)} style={{ background: "#dc2626", color: "#fff" }}>Delete</button></li>)}</ul>
    <h3>Enrollments</h3>
    <button type="button" onClick={remind}>Send deadline reminders</button>
    <table border="1" cellPadding="6"><thead><tr><th>User</th><th>Course</th><th>Due</th><th>Progress</th><th>Quiz scores</th><th>Certified</th></tr></thead>
    <tbody>{d.enrollments.map((e, i) => <tr key={i}><td>{e.user}</td><td>{e.course}</td><td>{e.due_date || "-"}</td>
      <td>{e.completed_modules}/{e.total_modules}</td>
      <td>{e.attempts.map(a => `${a.score}%${a.passed ? "✓" : "✗"}`).join(", ") || "-"}</td>
      <td>{e.certified ? "Yes" : "No"}</td></tr>)}</tbody></table>
  </div>);
}