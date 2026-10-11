"""Training platform API (FastAPI + SQLAlchemy + PostgreSQL). Run: python -m uvicorn main:app --reload
Decisions: business rules live in grade()/statuses()/issue_certificate() (plain functions, easy to test);
routes are thin. Modules unlock one after another via statuses(). Certificate number = hash(user, course),
so it is deterministic. Emails are sent as background tasks (notify.py). The first registered user becomes admin."""
import os, io, random, hashlib, datetime as dt, jwt
from datetime import date
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import (create_engine, event, func, Column, Integer, String, Boolean, Text, Date,
                        ForeignKey, DateTime, JSON, UniqueConstraint)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from notify import send_email
from sqlalchemy.engine import URL as _SAURL
try:
    from local_settings import DB_PASSWORD as _DB_PASSWORD
except ImportError:
    _DB_PASSWORD = "postgres"
URL = os.getenv("DATABASE_URL") or _SAURL.create(
    "postgresql+psycopg", username="postgres", password=_DB_PASSWORD,
    host="localhost", port=5432, database="training").render_as_string(hide_password=False)
SECRET = os.getenv("JWT_SECRET", "dev-secret")
kw = dict(connect_args={"check_same_thread": False}, poolclass=StaticPool) if URL.startswith("sqlite") else {}
engine = create_engine(URL, **kw); Session = sessionmaker(engine); Base = declarative_base()
if URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _fk_on(conn, rec): conn.execute("PRAGMA foreign_keys=ON")
now = dt.datetime.utcnow

class User(Base):
    __tablename__ = "users"; id = Column(Integer, primary_key=True); email = Column(String, unique=True)
    name = Column(String); pw = Column(String); role = Column(String, default="user")
class Course(Base):
    __tablename__ = "courses"; id = Column(Integer, primary_key=True); title = Column(String)
    description = Column(Text, default=""); category = Column(String, default="")
class Module(Base):
    __tablename__ = "modules"; id = Column(Integer, primary_key=True)
    course_id = Column(ForeignKey("courses.id", ondelete="CASCADE")); position = Column(Integer)
    title = Column(String); content = Column(Text, default=""); video_url = Column(String)
class Quiz(Base):
    __tablename__ = "quizzes"; id = Column(Integer, primary_key=True)
    module_id = Column(ForeignKey("modules.id", ondelete="CASCADE"), unique=True)
    passing_score = Column(Integer); max_attempts = Column(Integer)
class Question(Base):
    __tablename__ = "questions"; id = Column(Integer, primary_key=True)
    quiz_id = Column(ForeignKey("quizzes.id", ondelete="CASCADE")); text = Column(Text)
    options = Column(JSON); correct = Column(Integer)
class Enrollment(Base):
    __tablename__ = "enrollments"; id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE")); course_id = Column(ForeignKey("courses.id", ondelete="CASCADE"))
    created = Column(DateTime, default=now); due_date = Column(Date)
    __table_args__ = (UniqueConstraint("user_id", "course_id"),)
class Attempt(Base):
    __tablename__ = "attempts"; id = Column(Integer, primary_key=True)
    enrollment_id = Column(ForeignKey("enrollments.id", ondelete="CASCADE")); module_id = Column(ForeignKey("modules.id", ondelete="CASCADE"))
    score = Column(Integer); passed = Column(Boolean); created = Column(DateTime, default=now)
class Certificate(Base):
    __tablename__ = "certificates"; id = Column(Integer, primary_key=True)
    enrollment_id = Column(ForeignKey("enrollments.id", ondelete="CASCADE"), unique=True)
    number = Column(String, unique=True); score = Column(Integer); issued = Column(DateTime, default=now)

# ---------- business logic ----------
def hp(p): return hashlib.pbkdf2_hmac("sha256", p.encode(), b"salt", 100_000).hex()

def grade(questions, answers, passing):
    """answers: {question_id(str): chosen_index}. Returns (score%, passed, per-question results)."""
    res, right = [], 0
    for q in questions:
        ok = answers.get(str(q.id)) == q.correct; right += ok
        res.append({"question_id": q.id, "correct": ok, "correct_index": q.correct})
    score = round(100 * right / len(questions)) if questions else 0
    return score, score >= passing, res

def statuses(db, enr):
    mods = db.query(Module).filter_by(course_id=enr.course_id).order_by(Module.position, Module.id).all()
    passed = {a.module_id for a in db.query(Attempt).filter_by(enrollment_id=enr.id, passed=True)}
    out, prev = [], True
    for m in mods:
        quiz = db.query(Quiz).filter_by(module_id=m.id).first()
        done = m.id in passed or quiz is None
        out.append(dict(module=m, quiz=quiz, done=done, unlocked=prev)); prev = prev and done
    return out

def cert_number(user_id, course_id):
    return "CERT-" + hashlib.sha256(f"{user_id}:{course_id}".encode()).hexdigest()[:12].upper()

def issue_certificate(db, enr):
    if (c := db.query(Certificate).filter_by(enrollment_id=enr.id).first()): return c
    st = statuses(db, enr)
    if not st or not all(s["done"] for s in st): raise HTTPException(400, "Course not complete")
    best = [max(a.score for a in db.query(Attempt).filter_by(enrollment_id=enr.id, module_id=s["module"].id, passed=True))
            for s in st if s["quiz"]]
    c = Certificate(enrollment_id=enr.id, number=cert_number(enr.user_id, enr.course_id),
                    score=round(sum(best) / len(best)) if best else 100)
    db.add(c); db.commit(); return c

# ---------- API ----------
app = FastAPI(title="Training Platform")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(engine)
bearer = HTTPBearer()

def get_db():
    db = Session()
    try: yield db
    finally: db.close()
def user(creds=Depends(bearer), db=Depends(get_db)):
    try: u = db.get(User, jwt.decode(creds.credentials, SECRET, ["HS256"])["sub"])
    except Exception: u = None
    if not u: raise HTTPException(401, "Invalid token")
    return u
def admin(u=Depends(user)):
    if u.role != "admin": raise HTTPException(403, "Admin only")
    return u
def get_or_404(db, model, id):
    o = db.get(model, id)
    if not o: raise HTTPException(404, f"{model.__name__} not found")
    return o

class Reg(BaseModel): email: str; name: str; password: str = Field(min_length=6)
class Login(BaseModel): email: str; password: str
class CourseIn(BaseModel): title: str = Field(min_length=1); description: str = ""; category: str = ""
class ModuleIn(BaseModel): title: str = Field(min_length=1); content: str = ""; video_url: Optional[str] = None; position: Optional[int] = None
class ModuleEdit(BaseModel): title: str = Field(min_length=1); content: str = ""; video_url: Optional[str] = None
class QIn(BaseModel): text: str; options: list[str] = Field(min_length=2); correct: int
class QuizIn(BaseModel): passing_score: int = Field(ge=1, le=100); max_attempts: Optional[int] = Field(None, ge=1); questions: list[QIn] = Field(min_length=1)
class Assign(BaseModel): user_ids: list[int]; due_date: Optional[date] = None
class Submit(BaseModel): answers: dict[str, int]
class NewUser(BaseModel): email: str; name: str; password: str = Field(min_length=6); role: str = Field("user", pattern="^(admin|user)$")

@app.post("/auth/register")
def register(b: Reg, db=Depends(get_db)):
    if db.query(User).filter_by(email=b.email).first(): raise HTTPException(409, "Email taken")
    u = User(email=b.email, name=b.name, pw=hp(b.password), role="admin" if db.query(User).count() == 0 else "user")
    db.add(u); db.commit(); return {"id": u.id, "role": u.role}

@app.post("/auth/login")
def login(b: Login, db=Depends(get_db)):
    u = db.query(User).filter_by(email=b.email).first()
    if not u or u.pw != hp(b.password): raise HTTPException(401, "Bad credentials")
    return {"token": jwt.encode({"sub": str(u.id)}, SECRET, "HS256"), "role": u.role, "name": u.name}

# admin: content
@app.post("/courses", status_code=201)
def create_course(b: CourseIn, _=Depends(admin), db=Depends(get_db)):
    c = Course(**b.model_dump()); db.add(c); db.commit(); return {"id": c.id}
@app.put("/courses/{cid}")
def edit_course(cid: int, b: CourseIn, _=Depends(admin), db=Depends(get_db)):
    c = get_or_404(db, Course, cid)
    for k, v in b.model_dump().items(): setattr(c, k, v)
    db.commit(); return {"id": c.id}
@app.delete("/courses/{cid}", status_code=204)
def del_course(cid: int, _=Depends(admin), db=Depends(get_db)):
    db.delete(get_or_404(db, Course, cid)); db.commit()
@app.post("/courses/{cid}/modules", status_code=201)
def add_module(cid: int, b: ModuleIn, _=Depends(admin), db=Depends(get_db)):
    get_or_404(db, Course, cid)
    pos = b.position or (db.query(func.max(Module.position)).filter(Module.course_id == cid).scalar() or 0) + 1
    m = Module(course_id=cid, position=pos, **b.model_dump(exclude={"position"})); db.add(m); db.commit(); return {"id": m.id}
@app.get("/admin/courses/{cid}/modules")
def admin_modules(cid: int, _=Depends(admin), db=Depends(get_db)):
    out = []
    for m in db.query(Module).filter_by(course_id=cid).order_by(Module.position, Module.id):
        qz = db.query(Quiz).filter_by(module_id=m.id).first()
        qs = db.query(Question).filter_by(quiz_id=qz.id).all() if qz else []
        out.append({"id": m.id, "position": m.position, "title": m.title, "content": m.content, "video_url": m.video_url,
                    "passing_score": qz.passing_score if qz else None, "max_attempts": qz.max_attempts if qz else None,
                    "questions": [{"text": q.text, "options": q.options, "correct": q.correct} for q in qs]})
    return out
@app.put("/modules/{mid}")
def edit_module(mid: int, b: ModuleEdit, _=Depends(admin), db=Depends(get_db)):
    m = get_or_404(db, Module, mid)
    m.title, m.content, m.video_url = b.title, b.content, b.video_url or None
    db.commit(); return {"id": m.id}
@app.delete("/modules/{mid}", status_code=204)
def delete_module(mid: int, _=Depends(admin), db=Depends(get_db)):
    db.delete(get_or_404(db, Module, mid)); db.commit()
@app.post("/modules/{mid}/quiz", status_code=201)
def set_quiz(mid: int, b: QuizIn, _=Depends(admin), db=Depends(get_db)):
    get_or_404(db, Module, mid)
    if any(not 0 <= q.correct < len(q.options) for q in b.questions): raise HTTPException(422, "correct index out of range")
    if (old := db.query(Quiz).filter_by(module_id=mid).first()):
        db.query(Question).filter_by(quiz_id=old.id).delete(); db.delete(old); db.flush()
    qz = Quiz(module_id=mid, passing_score=b.passing_score, max_attempts=b.max_attempts); db.add(qz); db.flush()
    db.add_all(Question(quiz_id=qz.id, **q.model_dump()) for q in b.questions); db.commit(); return {"id": qz.id}
@app.post("/courses/{cid}/assign")
def assign(cid: int, b: Assign, bg: BackgroundTasks, _=Depends(admin), db=Depends(get_db)):
    course = get_or_404(db, Course, cid); n = 0
    for uid in b.user_ids:
        usr = db.get(User, uid)
        if usr and not db.query(Enrollment).filter_by(user_id=uid, course_id=cid).first():
            db.add(Enrollment(user_id=uid, course_id=cid, due_date=b.due_date)); n += 1
            due = f" Please finish it by {b.due_date}." if b.due_date else ""
            bg.add_task(send_email, usr.email, f"New course assigned: {course.title}",
                        f'Hello {usr.name},\n\nYou have been assigned the course "{course.title}".{due}\n\nLog in to start learning.')
    db.commit(); return {"assigned": n}
@app.post("/admin/send-reminders")
def send_reminders(bg: BackgroundTasks, _=Depends(admin), db=Depends(get_db)):
    """Emails every learner whose deadline is overdue or within 3 days and who has no certificate yet."""
    soon, n = date.today() + dt.timedelta(days=3), 0
    for e in db.query(Enrollment).filter(Enrollment.due_date.isnot(None), Enrollment.due_date <= soon):
        if db.query(Certificate).filter_by(enrollment_id=e.id).first(): continue
        usr, course = db.get(User, e.user_id), db.get(Course, e.course_id)
        status = "is overdue" if e.due_date < date.today() else f"is due on {e.due_date}"
        bg.add_task(send_email, usr.email, f"Deadline reminder: {course.title}",
                    f'Hello {usr.name},\n\nYour course "{course.title}" {status}. Please complete it soon.')
        n += 1
    return {"reminders": n}
@app.get("/admin/dashboard")
def dashboard(_=Depends(admin), db=Depends(get_db)):
    rows = []
    for e in db.query(Enrollment).all():
        st = statuses(db, e); cert = db.query(Certificate).filter_by(enrollment_id=e.id).first()
        rows.append({"user": db.get(User, e.user_id).email, "course": db.get(Course, e.course_id).title,
                     "completed_modules": sum(s["done"] for s in st), "total_modules": len(st),
                     "due_date": str(e.due_date) if e.due_date else None,
                     "certified": bool(cert), "attempts": [{"module_id": a.module_id, "score": a.score, "passed": a.passed}
                      for a in db.query(Attempt).filter_by(enrollment_id=e.id)]})
    return {"courses": [{"id": c.id, "title": c.title, "category": c.category} for c in db.query(Course)],
            "enrollments": rows, "stats": {"enrollments": len(rows), "certified": sum(r["certified"] for r in rows)}}

# admin: users
@app.get("/users")
def list_users(_=Depends(admin), db=Depends(get_db)):
    return [{"id": u.id, "name": u.name, "email": u.email, "role": u.role} for u in db.query(User)]
@app.post("/users", status_code=201)
def create_user(b: NewUser, _=Depends(admin), db=Depends(get_db)):
    if db.query(User).filter_by(email=b.email).first(): raise HTTPException(409, "Email taken")
    u = User(email=b.email, name=b.name, pw=hp(b.password), role=b.role); db.add(u); db.commit(); return {"id": u.id}
@app.delete("/users/{uid}", status_code=204)
def delete_user(uid: int, me=Depends(admin), db=Depends(get_db)):
    if uid == me.id: raise HTTPException(400, "You cannot delete your own account")
    db.delete(get_or_404(db, User, uid)); db.commit()

# learner
@app.get("/courses")
def courses(q: str = "", _=Depends(user), db=Depends(get_db)):
    qs = db.query(Course).filter(Course.title.ilike(f"%{q}%"))
    return [{"id": c.id, "title": c.title, "description": c.description, "category": c.category} for c in qs]
@app.post("/courses/{cid}/enroll", status_code=201)
def enroll(cid: int, u=Depends(user), db=Depends(get_db)):
    get_or_404(db, Course, cid)
    if not db.query(Enrollment).filter_by(user_id=u.id, course_id=cid).first():
        db.add(Enrollment(user_id=u.id, course_id=cid)); db.commit()
    return {"ok": True}
def my_enr(db, u, cid):
    e = db.query(Enrollment).filter_by(user_id=u.id, course_id=cid).first()
    if not e: raise HTTPException(403, "Not enrolled")
    return e
@app.get("/courses/{cid}/progress")
def progress(cid: int, u=Depends(user), db=Depends(get_db)):
    e = my_enr(db, u, cid); st = statuses(db, e); cert = db.query(Certificate).filter_by(enrollment_id=e.id).first()
    return {"modules": [{"id": s["module"].id, "title": s["module"].title, "done": s["done"], "unlocked": s["unlocked"]} for s in st],
            "complete": bool(st) and all(s["done"] for s in st), "certificate": cert.number if cert else None,
            "due_date": str(e.due_date) if e.due_date else None}
@app.get("/modules/{mid}")
def view_module(mid: int, u=Depends(user), db=Depends(get_db)):
    m = get_or_404(db, Module, mid); e = my_enr(db, u, m.course_id)
    s = next(s for s in statuses(db, e) if s["module"].id == mid)
    if not s["unlocked"]: raise HTTPException(403, "Complete previous modules first")
    qs = db.query(Question).filter_by(quiz_id=s["quiz"].id).all() if s["quiz"] else []
    random.shuffle(qs)  # randomized question order on every visit
    return {"title": m.title, "content": m.content, "video_url": m.video_url,
            "passing_score": s["quiz"].passing_score if s["quiz"] else None,
            "questions": [{"id": q.id, "text": q.text, "options": q.options} for q in qs]}  # no answers leaked
@app.post("/modules/{mid}/quiz/submit")
def submit(mid: int, b: Submit, bg: BackgroundTasks, u=Depends(user), db=Depends(get_db)):
    m = get_or_404(db, Module, mid); e = my_enr(db, u, m.course_id)
    s = next(s for s in statuses(db, e) if s["module"].id == mid)
    if not s["unlocked"]: raise HTTPException(403, "Module locked")
    if not s["quiz"]: raise HTTPException(400, "No quiz for module")
    n = db.query(Attempt).filter_by(enrollment_id=e.id, module_id=mid).count()
    if s["quiz"].max_attempts and n >= s["quiz"].max_attempts and not s["done"]: raise HTTPException(403, "Max attempts reached")
    qs = db.query(Question).filter_by(quiz_id=s["quiz"].id).all()
    score, passed, res = grade(qs, b.answers, s["quiz"].passing_score)
    db.add(Attempt(enrollment_id=e.id, module_id=mid, score=score, passed=passed)); db.commit()
    verdict = "PASSED" if passed else "not passed yet, please retry"
    bg.add_task(send_email, u.email, f"Quiz result: {m.title}",
                f'Hello {u.name},\n\nYou scored {score}% on "{m.title}" (pass mark {s["quiz"].passing_score}%). Result: {verdict}.')
    return {"score": score, "passed": passed, "passing_score": s["quiz"].passing_score, "results": res}
@app.post("/courses/{cid}/certificate")
def certificate(cid: int, bg: BackgroundTasks, u=Depends(user), db=Depends(get_db)):
    e = my_enr(db, u, cid)
    had = db.query(Certificate).filter_by(enrollment_id=e.id).first() is not None
    c = issue_certificate(db, e)
    if not had:
        bg.add_task(send_email, u.email, "Your certificate is ready",
                    f"Hello {u.name},\n\nCongratulations! Your certificate number is {c.number} (final score {c.score}%).\n"
                    f"Download it: http://localhost:8000/certificates/{c.number}/pdf")
    return {"number": c.number, "score": c.score}
@app.get("/certificates/{number}", response_class=HTMLResponse)
def view_cert(number: str, db=Depends(get_db)):  # public, verifiable; print to PDF from browser
    import html as h
    c = db.query(Certificate).filter_by(number=number).first()
    if not c: raise HTTPException(404, "Not found")
    e = db.get(Enrollment, c.enrollment_id)
    page = """<!doctype html><html><head><meta charset="utf-8"><title>Certificate __NO__</title><style>
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;background:#000;font-family:Georgia,'Times New Roman',serif;padding:30px 12px}
.cert{max-width:900px;margin:auto;background:#0a0a0a;border:12px solid #dc2626;outline:3px solid #fff;outline-offset:-26px;padding:60px 50px 70px;text-align:center;color:#fff;box-shadow:0 0 40px rgba(220,38,38,.45)}
h1{font-size:54px;letter-spacing:8px;margin:0;color:#fff}
.sub{color:#ef4444;font-size:20px;letter-spacing:10px;margin:6px 0 18px;font-weight:bold}
.line{width:240px;height:2px;background:#dc2626;margin:0 auto 22px}
.muted{color:#aaa;font-style:italic;font-size:18px;margin:10px 0}
.name{font-size:46px;font-style:italic;font-weight:bold;color:#fff;border-bottom:2px solid #dc2626;display:inline-block;padding:0 30px 4px;margin:8px 0}
.course{font-size:32px;font-weight:bold;color:#ef4444;margin:10px 0}
.row{display:flex;justify-content:space-around;align-items:flex-end;margin-top:34px}
.sig{width:220px;border-top:1px solid #fff;padding-top:6px;font-size:14px;color:#ddd}
.seal{width:104px;height:104px;border-radius:50%;background:radial-gradient(circle,#ef4444,#991b1b);border:4px double #fff;box-shadow:0 0 0 3px #dc2626;color:#fff;display:flex;flex-direction:column;justify-content:center;font-weight:bold}
.seal b{font-size:26px}.seal small{font-size:11px;letter-spacing:2px}
.no{margin-top:26px;font-size:13px;color:#888;letter-spacing:2px}
.bar{text-align:center;margin-top:18px}.bar a,.bar button{background:#dc2626;color:#fff;border:0;padding:10px 20px;border-radius:6px;font-size:15px;text-decoration:none;cursor:pointer;margin:0 6px}
@media print{body{padding:0}.bar{display:none}.cert{box-shadow:none}}
</style></head><body>
<div class="cert"><h1>CERTIFICATE</h1><div class="sub">OF COMPLETION</div><div class="line"></div>
<div class="muted">This certificate is proudly presented to</div><div class="name">__NAME__</div>
<div class="muted">for successfully completing the course</div><div class="course">__COURSE__</div>
<div class="muted" style="font-style:normal">with a final score of __SCORE__%</div>
<div class="row"><div class="sig"><i>Training Platform</i><br>Authorized Signature</div>
<div class="seal"><small>CERTIFIED</small><b>__SCORE__%</b></div>
<div class="sig"><i>__DATE__</i><br>Date of Completion</div></div>
<div class="no">CERTIFICATE NO. __NO__</div></div>
<div class="bar"><a href="/certificates/__NO__/pdf">Download PDF</a><button onclick="window.print()">Print</button></div>
</body></html>"""
    return (page.replace("__NO__", c.number).replace("__NAME__", h.escape(db.get(User, e.user_id).name))
            .replace("__COURSE__", h.escape(db.get(Course, e.course_id).title)).replace("__SCORE__", str(c.score))
            .replace("__DATE__", f"{c.issued:%d %B %Y}"))

@app.get("/certificates/{number}/pdf")
def cert_pdf(number: str, db=Depends(get_db)):
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas
    c = db.query(Certificate).filter_by(number=number).first()
    if not c: raise HTTPException(404, "Not found")
    e = db.get(Enrollment, c.enrollment_id)
    name, course = db.get(User, e.user_id).name, db.get(Course, e.course_id).title
    BLACK, RED, DARKRED, WHITE, GREY = HexColor("#0a0a0a"), HexColor("#dc2626"), HexColor("#991b1b"), HexColor("#ffffff"), HexColor("#aaaaaa")
    buf = io.BytesIO(); w, h = landscape(A4); p = canvas.Canvas(buf, pagesize=(w, h))
    p.setFillColor(BLACK); p.rect(0, 0, w, h, fill=1, stroke=0)                       # black page
    p.setStrokeColor(WHITE); p.setLineWidth(2); p.rect(38, 38, w - 76, h - 76)        # white inner borders
    p.setStrokeColor(RED); p.setLineWidth(.8); p.rect(46, 46, w - 92, h - 92)
    p.setFillColor(RED)
    for x, y in [(38, 38), (w - 38, 38), (38, h - 38), (w - 38, h - 38)]: p.circle(x, y, 7, fill=1, stroke=0)
    p.setFillColor(WHITE); p.setFont("Times-Bold", 46); p.drawCentredString(w / 2, h - 125, "CERTIFICATE")
    p.setFillColor(RED); p.setFont("Times-Bold", 20); p.drawCentredString(w / 2, h - 155, "O F   C O M P L E T I O N")
    p.setStrokeColor(RED); p.setLineWidth(1.5); p.line(w / 2 - 120, h - 172, w / 2 + 120, h - 172)
    p.setFillColor(GREY); p.setFont("Times-Italic", 16); p.drawCentredString(w / 2, h - 205, "This certificate is proudly presented to")
    p.setFillColor(WHITE); p.setFont("Times-BoldItalic", 40); p.drawCentredString(w / 2, h - 255, name)
    half = max(p.stringWidth(name, "Times-BoldItalic", 40) / 2 + 20, 150)
    p.setStrokeColor(RED); p.setLineWidth(1.2); p.line(w / 2 - half, h - 265, w / 2 + half, h - 265)
    p.setFillColor(GREY); p.setFont("Times-Italic", 16); p.drawCentredString(w / 2, h - 295, "for successfully completing the course")
    p.setFillColor(RED); p.setFont("Times-Bold", 28); p.drawCentredString(w / 2, h - 335, course)
    p.setFillColor(GREY); p.setFont("Times-Roman", 14); p.drawCentredString(w / 2, h - 365, f"with a final score of {c.score}%")
    sx, sy = w / 2, 140                                                               # red seal with ribbon
    p.setFillColor(DARKRED)
    for dx in (-18, 18):
        t = p.beginPath(); t.moveTo(sx + dx - 12, sy - 20); t.lineTo(sx + dx + 12, sy - 20); t.lineTo(sx + dx + 12, sy - 62)
        t.lineTo(sx + dx, sy - 50); t.lineTo(sx + dx - 12, sy - 62); t.close(); p.drawPath(t, fill=1, stroke=0)
    p.setFillColor(RED); p.circle(sx, sy, 42, fill=1, stroke=0)
    p.setStrokeColor(WHITE); p.setLineWidth(1.5); p.circle(sx, sy, 36, fill=0, stroke=1); p.circle(sx, sy, 30, fill=0, stroke=1)
    p.setFillColor(WHITE); p.setFont("Times-Bold", 11); p.drawCentredString(sx, sy + 8, "CERTIFIED")
    p.setFont("Times-Bold", 20); p.drawCentredString(sx, sy - 12, f"{c.score}%")
    p.setStrokeColor(WHITE); p.setLineWidth(1)                                        # signature lines
    p.line(110, 118, 290, 118); p.line(w - 290, 118, w - 110, 118)
    p.setFillColor(WHITE); p.setFont("Times-Italic", 18); p.drawCentredString(200, 124, "Training Platform")
    p.drawCentredString(w - 200, 124, f"{c.issued:%d %B %Y}")
    p.setFillColor(GREY); p.setFont("Times-Roman", 11); p.drawCentredString(200, 103, "Authorized Signature"); p.drawCentredString(w - 200, 103, "Date of Completion")
    p.drawCentredString(w / 2, 58, f"CERTIFICATE NO. {c.number}")
    p.showPage(); p.save()
    return Response(buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{c.number}.pdf"'})

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "524566616253-gbujjrau57crtic9fcs8c4i67va6n8g7.apps.googleusercontent.com")
class GoogleLogin(BaseModel): credential: str

@app.post("/auth/google")
def google_login(b: GoogleLogin, db=Depends(get_db)):
    """Single sign-on: verify the Google ID token, then find or create the local user and return our own token."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as greq
    try:
        info = id_token.verify_oauth2_token(b.credential, greq.Request(), GOOGLE_CLIENT_ID, clock_skew_in_seconds=10)
    except Exception:
        raise HTTPException(401, "Invalid Google token")
    if not info.get("email_verified"): raise HTTPException(401, "Google email is not verified")
    email = info["email"].lower()
    u = db.query(User).filter(func.lower(User.email) == email).first()
    if not u:
        u = User(email=email, name=info.get("name") or email.split("@")[0], pw=hp(os.urandom(16).hex()),
                 role="admin" if db.query(User).count() == 0 else "user")
        db.add(u); db.commit()
    return {"token": jwt.encode({"sub": str(u.id)}, SECRET, "HS256"), "role": u.role, "name": u.name}