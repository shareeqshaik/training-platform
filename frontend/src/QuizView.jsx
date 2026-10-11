import { useState } from "react";
// Props: questions [{id,text,options}], onSubmit(answers) -> Promise<{score,passed,results}>
export default function QuizView({ questions, onSubmit }) {
  const [answers, setAnswers] = useState({}); const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  const send = async () => {
    setBusy(true); setErr("");
    try { setRes(await onSubmit(answers)); } catch (e) { setErr("Submission failed. Try again."); }
    setBusy(false);
  };
  return (<div>
    {questions.map(q => (<fieldset key={q.id}><legend>{q.text}</legend>
      {q.options.map((o, i) => (<label key={i}><input type="radio" name={`q${q.id}`}
        onChange={() => setAnswers({ ...answers, [q.id]: i })} /> {o}</label>))}
      {res && <p>{res.results.find(r => r.question_id === q.id).correct ? "✓ Correct" : "✗ Incorrect"}</p>}
    </fieldset>))}
    <button onClick={send} disabled={busy}>{busy ? "Submitting…" : "Submit"}</button>
    {err && <p role="alert">{err}</p>}
    {res && <p>Score: {res.score}% — {res.passed ? "Passed!" : "Not passed, please retry."}</p>}
  </div>);
}
