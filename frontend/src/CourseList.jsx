import { useState } from "react";
export default function CourseList({ courses, onStart }) {
  const [q, setQ] = useState(""); const [cat, setCat] = useState("");
  if (!courses.length) return <p>No courses available yet.</p>;
  const cats = [...new Set(courses.map(c => c.category).filter(Boolean))];
  const shown = courses.filter(c => c.title.toLowerCase().includes(q.toLowerCase()) && (!cat || c.category === cat));
  return (<div>
    <input placeholder="Search courses" value={q} onChange={e => setQ(e.target.value)} />{" "}
    <select value={cat} onChange={e => setCat(e.target.value)}>
      <option value="">All categories</option>{cats.map(c => <option key={c} value={c}>{c}</option>)}
    </select>
    {shown.length ? shown.map(c => <div key={c.id}>{c.title} {c.category && <small>({c.category})</small>}{" "}
      <button onClick={() => onStart(c.id)}>Start</button></div>) : <p>No matching courses.</p>}
  </div>);
}