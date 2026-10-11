import os, sys; os.environ["DATABASE_URL"] = "sqlite://"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import datetime
from types import SimpleNamespace as Q
from fastapi.testclient import TestClient
import main

def login(c, email, password="secret1"):
    return {"Authorization": "Bearer " + c.post("/auth/login", json={"email": email, "password": password}).json()["token"]}

def test_grade_pass_and_fail():
    qs = [Q(id=1, correct=0), Q(id=2, correct=1)]
    assert main.grade(qs, {"1": 0, "2": 1}, 70)[:2] == (100, True)
    score, passed, res = main.grade(qs, {"1": 0, "2": 0}, 70)
    assert (score, passed) == (50, False) and res[1]["correct"] is False

def test_cert_number_deterministic():
    assert main.cert_number(1, 2) == main.cert_number(1, 2) != main.cert_number(2, 1)

def test_full_flow():
    c = TestClient(main.app)
    c.post("/auth/register", json={"email": "a@x.com", "name": "Admin", "password": "secret1"})
    c.post("/auth/register", json={"email": "u@x.com", "name": "Uma", "password": "secret1"})
    A, U = login(c, "a@x.com"), login(c, "u@x.com")
    cid = c.post("/courses", json={"title": "Safety"}, headers=A).json()["id"]
    mids = [c.post(f"/courses/{cid}/modules", json={"title": f"M{i}"}, headers=A).json()["id"] for i in (1, 2)]
    for m in mids:
        c.post(f"/modules/{m}/quiz", headers=A, json={"passing_score": 100, "questions": [{"text": "?", "options": ["a", "b"], "correct": 1}]})
    assert c.post("/courses", json={"title": "x"}, headers=U).status_code == 403   # RBAC
    assert c.get(f"/modules/{mids[0]}", headers=U).status_code == 403              # not enrolled
    c.post(f"/courses/{cid}/enroll", headers=U)
    assert c.get(f"/modules/{mids[1]}", headers=U).status_code == 403              # no skipping
    q = c.get(f"/modules/{mids[0]}", headers=U).json()["questions"][0]
    assert "correct" not in q
    assert not c.post(f"/modules/{mids[0]}/quiz/submit", json={"answers": {str(q["id"]): 0}}, headers=U).json()["passed"]
    assert c.post(f"/courses/{cid}/certificate", headers=U).status_code == 400    # incomplete
    for m in mids:  # retry until pass
        qid = c.get(f"/modules/{m}", headers=U).json()["questions"][0]["id"]
        assert c.post(f"/modules/{m}/quiz/submit", json={"answers": {str(qid): 1}}, headers=U).json()["passed"]
    cert = c.post(f"/courses/{cid}/certificate", headers=U).json()
    assert cert == c.post(f"/courses/{cid}/certificate", headers=U).json()
    assert "Uma" in c.get(f"/certificates/{cert['number']}").text
    assert c.get("/admin/dashboard", headers=A).json()["stats"]["certified"] == 1

def test_user_management():
    c = TestClient(main.app)
    c.post("/auth/register", json={"email": "a@x.com", "name": "Admin", "password": "secret1"})
    A = login(c, "a@x.com")
    body = {"email": "new@x.com", "name": "New", "password": "secret1"}
    r = c.post("/users", headers=A, json=body)
    assert r.status_code == 201
    assert c.post("/users", headers=A, json=body).status_code == 409
    assert c.delete(f"/users/{r.json()['id']}", headers=A).status_code == 204
    me = next(u for u in c.get("/users", headers=A).json() if u["email"] == "a@x.com")
    assert c.delete(f"/users/{me['id']}", headers=A).status_code == 400

def test_module_management():
    c = TestClient(main.app)
    c.post("/auth/register", json={"email": "a@x.com", "name": "Admin", "password": "secret1"})
    A = login(c, "a@x.com")
    cid = c.post("/courses", json={"title": "Mgmt"}, headers=A).json()["id"]
    mid = c.post(f"/courses/{cid}/modules", json={"title": "M1"}, headers=A).json()["id"]
    c.post(f"/modules/{mid}/quiz", headers=A, json={"passing_score": 60, "questions": [{"text": "?", "options": ["a", "b"], "correct": 0}]})
    listing = c.get(f"/admin/courses/{cid}/modules", headers=A).json()
    assert listing[0]["questions"][0]["correct"] == 0 and listing[0]["passing_score"] == 60
    assert c.put(f"/modules/{mid}", headers=A, json={"title": "Renamed"}).status_code == 200
    assert c.get(f"/admin/courses/{cid}/modules", headers=A).json()[0]["title"] == "Renamed"
    assert c.delete(f"/modules/{mid}", headers=A).status_code == 204
    assert c.get(f"/admin/courses/{cid}/modules", headers=A).json() == []

def test_assign_with_deadline_and_reminders():
    c = TestClient(main.app)
    c.post("/auth/register", json={"email": "a@x.com", "name": "Admin", "password": "secret1"})
    c.post("/auth/register", json={"email": "d@x.com", "name": "Dee", "password": "secret1"})
    A = login(c, "a@x.com")
    uid = next(u["id"] for u in c.get("/users", headers=A).json() if u["email"] == "d@x.com")
    cid = c.post("/courses", json={"title": "Due"}, headers=A).json()["id"]
    soon = str(datetime.date.today() + datetime.timedelta(days=1))
    assert c.post(f"/courses/{cid}/assign", headers=A, json={"user_ids": [uid], "due_date": soon}).json()["assigned"] == 1
    assert c.post("/admin/send-reminders", headers=A).json()["reminders"] >= 1
    row = [r for r in c.get("/admin/dashboard", headers=A).json()["enrollments"] if r["course"] == "Due"][0]
    assert row["due_date"] == soon

def test_google_login_creates_user(monkeypatch):
    from google.oauth2 import id_token
    monkeypatch.setattr(id_token, "verify_oauth2_token",
                        lambda *a, **k: {"email": "g@x.com", "email_verified": True, "name": "Gina"})
    c = TestClient(main.app)
    r = c.post("/auth/google", json={"credential": "fake"})
    assert r.status_code == 200 and r.json()["name"] == "Gina"
    assert c.get("/courses", headers={"Authorization": "Bearer " + r.json()["token"]}).status_code == 200
    def bad(*a, **k): raise ValueError("bad token")
    monkeypatch.setattr(id_token, "verify_oauth2_token", bad)
    assert c.post("/auth/google", json={"credential": "x"}).status_code == 401