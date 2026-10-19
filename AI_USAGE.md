# AI Usage Summary

This document discloses how AI tools were used on this project, as required by the challenge rules.

## Tools used

| Tool | Used for |
|------|----------|
| Claude | Backend API and database, frontend UI, certificates, email notifications, Google sign-in, debugging, and documentation |
| Prompt Cowboy | Improving and structuring my prompts before sending them to Claude |

## How AI was used

- **Backend (FastAPI, SQLAlchemy, PostgreSQL):** Claude helped build the API routes, the data model (users, courses, modules, quizzes, questions, enrollments, attempts, certificates) and the business rules in `grade()`, `statuses()` and `issue_certificate()`. _Add one line on what you decided or wrote yourself._
- **Frontend (React):** Claude helped build the admin and learner screens. _Add one line on what you decided or changed yourself._
- **Certificates, emails and Google sign-in:** Claude helped with the certificate web page and PDF, the background email notifications, and Google single sign-on. _Add one line on what you decided or changed yourself._
- **Debugging:** I pasted errors and unexpected behaviour into Claude and used its suggestions to find the cause. _Add one real example below._
- **Documentation:** Claude helped draft the README, ER diagram, this file and the Declaration of Originality, which I reviewed and edited.
- **Prompt Cowboy:** I used it to improve my prompts before sending them to Claude.

## What I reviewed and changed myself

_Write two or three real examples, one or two sentences each. Good examples: a bug you found and how it was fixed, a Claude suggestion you rejected or simplified, a design decision you made and why (for example, requiring modules to be completed in order, or limiting quiz attempts)._

1. _example 1_
2. _example 2_
3. _example 3_

## Prompt history

| Tool | Link or file |
|------|--------------|
| Claude conversation(s) | _shared link, or the exported file in `docs/prompt-history/`_ |
| Prompt Cowboy | _the improved prompts or screenshots, saved in `docs/prompt-history/`_ |

## Ownership

I can explain every part of this codebase, including the grading logic (`grade()`), module unlocking (`statuses()`), certificate issuing (`issue_certificate()`), authentication, and the database schema, and I can make changes to it live.