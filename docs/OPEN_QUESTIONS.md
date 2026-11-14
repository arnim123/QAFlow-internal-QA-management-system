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
7. The existing test case format, so the default template can match it. No template is seeded.

## Added for bootstrap

8. How a person signs in, and how the roles in SOP section 3 are assigned (tester, requirement provider, transcriber, QA lead, developer, admin). No authentication is implemented.
9. Technical Odoo field names and stage database ids. SOP section 8 gives labels only. Settings exist and default to empty strings. No `x_*` names are guessed. Stage labels default to the SOP names so the UI can show them later:
   - Deployed on Beta and Pending For Testing
   - Tested on Beta & Ready for Live
   - Deployed on Production and Pending for Testing
   - Work In Progress
   - Cancelled/Merged Tasks
10. Which LLM provider and model generate drafts. `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY` are empty. The integration client is a stub.
11. Whether the existing reverse proxy exposes one host or separate hosts for the UI and the API. Default: one host. Frontend nginx and the Vite dev server proxy `/health`, `/ready`, and `/api/` to the API. Set `VITE_API_BASE_URL` if the proxy splits them.
12. How QAFlow authenticates GrokBot on the REST API (and later the MCP server). `GROKBOT_BASE_URL` and `GROKBOT_AUTH_SCHEME` are empty. No token format is assumed.

## Added with the domain schema

13. SOP section 3 also names Transcriber and Developer. The `roles` table has the six codes `admin`, `qa_lead`, `tester`, `requirement_provider`, `viewer`, and `executor_bot`. A user has one `role_id`. Transcriber and Developer are not separate codes, and a person cannot hold two roles.
14. `qa_cycles.status` and `executions.status` have no vocabulary in the SOP, so they are strings without a check constraint.
15. `master_test_cases.type` and `master_test_cases.priority` have no vocabulary in the SOP, so they are strings without a check constraint.
16. How a person signs in is still open (item 8). `users` has no password column. Machine clients use `api_keys.key_hash`; the plaintext key is not stored.
