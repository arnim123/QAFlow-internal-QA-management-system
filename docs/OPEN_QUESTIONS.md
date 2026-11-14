# Open questions

The SOP is silent on these, or it marks them as needing management approval. Behaviour that depends on an answer is configurable. Do not invent a value in code.

Defaults listed here are operational fallbacks for bootstrap, not decisions about the QA process.

## From the SOP (section 12)

1. Which stage a failed task returns to, and whether QAFlow or the tester moves the stage. Default label, used only as configuration: *Work In Progress*. Stage id is empty until an admin sets it. Write-back is off.
2. Whether QA Cycles should show 0 or 1 after a clean first pass. Default until management decides: do not write the field. The setting `ODOO_QA_CYCLES_ON_FIRST_PASS` is unset.
3. Approval of the definition of finished and the new Odoo stage (SOP section 10). Until that stage exists, a future release will record `production_verified_at` and post a chatter note. Not implemented.
4. Handling of the existing production-pending backlog (about 539 tasks). They are not auto-queued. Cutoff date and manual opt-in are unset.
5. GrokBot environments: beta URL, test accounts, and the production smoke-test limits. All empty. Production data-changing tests stay disallowed as a proposed rule, not as an implemented policy.
6. Who creates the Odoo API user and key for QAFlow. Credentials are empty.
7. The existing test case format, so the default template can match the company's current files. Version 1 of each template type is seeded and stays active until an admin activates a newer version. The seeded test case leaves `type` and `priority` as free text (see item 15). Preconditions, test data, and each evidence item are strings. The SOP does not define those shapes; publish a new template version when the existing format is known.

## Added for bootstrap

8. How a person signs in, and how the roles in SOP section 3 are assigned. Answered: email and password, stored as a bcrypt hash, with a JWT in the httpOnly cookie `qaflow_session`. An admin assigns one role through `POST /api/users`. The first admin is seeded from `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `ADMIN_DISPLAY_NAME` when those are set; a later boot does not reset the password. Template changes still record the actor name sent with the request until those routes use the session. Transcriber and Developer are still not role codes (item 13).
9. Technical Odoo field names and stage database ids. SOP section 8 gives labels only. Settings exist and default to empty strings. No `x_*` names are guessed. Stage labels default to the SOP names so the UI can show them later:
   - Deployed on Beta and Pending For Testing
   - Tested on Beta & Ready for Live
   - Deployed on Production and Pending for Testing
   - Work In Progress
   - Cancelled/Merged Tasks
10. Which LLM provider and model generate drafts. `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY` are empty. The integration client is a stub.
11. Whether the existing reverse proxy exposes one host or separate hosts for the UI and the API. Default: one host. Frontend nginx and the Vite dev server proxy `/health`, `/ready`, and `/api/` to the API. Set `VITE_API_BASE_URL` if the proxy splits them.
12. How QAFlow authenticates GrokBot on the REST API. Answered: an admin creates an `executor_bot` user and a bearer API key. The plaintext key is returned once. QAFlow stores the SHA-256 hash, can revoke the key, and records `last_used_at`. The key only authorizes executor calls. `GROKBOT_BASE_URL` is still empty; QAFlow does not call GrokBot. The MCP server is not built.

## Added with the domain schema

13. SOP section 3 also names Transcriber and Developer. The `roles` table has the six codes `admin`, `qa_lead`, `tester`, `requirement_provider`, `viewer`, and `executor_bot`. A user has one `role_id`. Transcriber and Developer are not separate codes, and a person cannot hold two roles.
14. `qa_cycles.status` and `executions.status` have no vocabulary in the SOP, so they are strings without a check constraint.
15. `master_test_cases.type` and `master_test_cases.priority` have no vocabulary in the SOP, so they are strings without a check constraint.
16. Answered by item 8. `users.password_hash` stores a bcrypt hash and is null for `executor_bot`. Machine clients use `api_keys.key_hash`.

## Added with the foundation

17. A worker that dies after claiming a job leaves that job `running`. There is no lock timeout. Do not invent one until operations chooses how long a claim may last.
