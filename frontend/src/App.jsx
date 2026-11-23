import { useState, useEffect } from "react";
import QuizView from "./QuizView";
import Admin from "./Admin";
import CourseList from "./CourseList";
import GoogleButton from "./GoogleButton";
const API = import.meta.env.VITE_API_URL || "";
export default function App() {
  const [tok, setTok] = useState(null); const [courses, setCourses] = useState([]);
  const [prog, setProg] = useState(null); const [cid, setCid] = useState(null); const [mod, setMod] = useState(null);
  const [mid, setMid] = useState(null); const [msg, setMsg] = useState(""); const [role, setRole] = useState(""); const [name, setName] = useState("");
  const [authMode, setAuthMode] = useState("login");
  const call = async (path, method = "GET", body) => {
    const r = await fetch(API + path, { method, headers: { "Content-Type": "application/json", ...(tok && { Authorization: `Bearer ${tok}` }) },
      body: body && JSON.stringify(body) });
    const j = r.status === 204 ? {} : await r.json();
    if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : (j.detail || []).map(d => `${(d.loc || []).join(".")}: ${d.msg}`).join("; ") || "Error");
    return j;
  };
  useEffect(() => { if (tok) call("/courses").then(setCourses).catch(e => setMsg(e.message)); }, [tok]);
  const open = async id => { await call(`/courses/${id}/enroll`, "POST"); setCid(id); setProg(await call(`/courses/${id}/progress`)); setMod(null); };
  const signedIn = r => { setMsg(""); setRole(r.role); setName(r.name); setTok(r.token); };
  const login = async e => { e.preventDefault(); const f = new FormData(e.target);
    try { signedIn(await call("/auth/login", "POST", { email: f.get("email"), password: f.get("password") })); } catch (x) { setMsg(x.message); } };
  const signup = async e => { e.preventDefault(); const f = new FormData(e.target);
    try {
      await call("/auth/register", "POST", { name: f.get("name"), email: f.get("email"), password: f.get("password") });
      signedIn(await call("/auth/login", "POST", { email: f.get("email"), password: f.get("password") }));
    } catch (x) { setMsg(x.message); } };
  const googleLogin = async credential => {
    try { signedIn(await call("/auth/google", "POST", { credential })); } catch (x) { setMsg(x.message); } };
  const logout = () => { setTok(null); setRole(""); setName(""); setCourses([]); setProg(null); setCid(null); setMod(null); setMid(null); setMsg(""); };
  const certificate = async pdf => {
    try { const c = await call(`/courses/${cid}/certificate`, "POST");
      if (pdf) window.location.href = `${API}/certificates/${c.number}/pdf`; else window.open(`${API}/certificates/${c.number}`);
    } catch (x) { setMsg(x.message); } };
  if (!tok) return (<form onSubmit={authMode === "login" ? login : signup}>
    <h1>{authMode === "login" ? "Login" : "Create account"}</h1>
    {authMode === "signup" && <input name="name" placeholder="Name" autoComplete="name" required />}
    <input name="email" type="email" placeholder="Email" autoComplete="email" required />
    <input name="password" type="password" placeholder="Password" autoComplete={authMode === "login" ? "current-password" : "new-password"} minLength={authMode === "signup" ? 6 : undefined} required />
    <button>{authMode === "login" ? "Sign in" : "Sign up"}</button>
    <p>{authMode === "login" ? "Don't have an account?" : "Already have an account?"}{" "}
      <button type="button" className="auth-switch" onClick={() => { setAuthMode(authMode === "login" ? "signup" : "login"); setMsg(""); }}>
        {authMode === "login" ? "Sign up" : "Sign in"}
      </button>
    </p>
    <p>or</p><GoogleButton onCredential={googleLogin} />{msg && <p role="alert">{msg}</p>}
  </form>);
  return (<div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span>Signed in as <b>{name}</b> ({role})</span><button onClick={logout}>Logout</button>
    </div>
    <p>{msg}</p>
    {role === "admin" && <Admin call={call} />}
    <h2>Courses</h2>
    <CourseList courses={courses} onStart={open} />
    {prog && <><h2>Progress</h2>
      {prog.due_date && <p>Due date: <b>{prog.due_date}</b></p>}
      <ul>{prog.modules.map(m => <li key={m.id}>{m.done ? "✅" : m.unlocked ? "▶" : "🔒"} {m.title}{" "}
      {m.unlocked && <button onClick={async () => { setMid(m.id); setMod(await call(`/modules/${m.id}`)); }}>Open</button>}</li>)}</ul>
      {prog.complete && <><button onClick={() => certificate(false)}>View certificate</button>{" "}
        <button onClick={() => certificate(true)}>Download PDF</button></>}</>}
    {mod && <><h3>{mod.title}</h3><p>{mod.content}</p>{mod.video_url && <video src={mod.video_url} controls width="480" />}
      <QuizView key={mid} questions={mod.questions} onSubmit={async a => { const r = await call(`/modules/${mid}/quiz/submit`, "POST", { answers: a });
        setProg(await call(`/courses/${cid}/progress`)); return r; }} /></>}
  </div>);
}