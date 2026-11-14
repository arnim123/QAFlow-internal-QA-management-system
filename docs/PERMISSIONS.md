# Permissions

QAFlow has six roles. A user has one role. Transcriber and Developer are not separate role codes; see `docs/OPEN_QUESTIONS.md`.

The source of truth in code is `backend/app/core/permissions.py`. This document matches that table. Domain permissions are declared now and enforced when those routes exist.

People sign in with email and password. The session is a JWT in the httpOnly cookie `qaflow_session`. `GET /api/me` is available to every signed-in human role. `executor_bot` receives 403.

`executor_bot` does not use a password. An admin creates a bearer API key for that user. The key is shown once, stored as a SHA-256 hash, and can be revoked. It can call only executor endpoints.

## Matrix

| Permission | admin | qa_lead | tester | requirement_provider | viewer | executor_bot |
|---|---|---|---|---|---|---|
| `users.read` | yes | | | | | |
| `users.manage` | yes | | | | | |
| `api_keys.manage` | yes | | | | | |
| `settings.read` | yes | yes | | | | |
| `settings.write` | yes | | | | | |
| `audit.read` | yes | yes | | | | |
| `jobs.read` | yes | | | | | |
| `jobs.retry` | yes | | | | | |
| `templates.read` | yes | | | | | |
| `templates.manage` | yes | | | | | |
| `priority.override` | yes | yes | | | | |
| `review_flags.read` | yes | yes | | | | |
| `review_flags.resolve` | yes | yes | | | | |
| `cycles.read` | yes | yes | yes | | yes | |
| `cases.read` | yes | yes | yes | | yes | |
| `cases.review` | | yes | yes | | | |
| `cases.add` | | | yes | | | |
| `cases.final_approve` | | | yes | | | |
| `results.validate` | | | yes | | | |
| `results.record_manual` | | | yes | | | |
| `requirements.read` | yes | yes | yes | | yes | |
| `requirements.upload` | | | | yes | | |
| `reports.read` | yes | yes | yes | | yes | |
| `executor.read_approved_set` | | | | | | yes |
| `executor.submit_results` | | | | | | yes |

## Rules this encodes

- Only the tester and the QA lead can review cases (approve, modify, or remove).
- Only the tester gives final QA approval (SOP R6) and validates or overrides AI results.
- Only the tester adds a case during review.
- Only the QA lead and an admin can override task priority, and the reason is audited.
- The audit log is read-only, and only an admin or the QA lead can read it.
- The requirement provider can only upload requirement sources.
- A viewer can read cycles, cases, requirements, and reports, and cannot change them.
- GrokBot cannot approve, edit cases, see drafts, or change the master repository. It can read an approved set and submit results.
- An admin configures users, API keys, templates, jobs, and settings, including the Odoo field mapping. An admin does not approve cases or give final QA approval.
- Secrets (`ODOO_API_KEY`, `LLM_API_KEY`, `JWT_SECRET`, database URLs, and the write-back switch) stay in the environment. They are not settings.
