# QA Standard Operating Procedure (SOP)

**AI-assisted testing with mandatory manual QA review**

| | |
|---|---|
| Company | Main Fast Trade Technologies |
| Reference project | FTT DMS (Odoo 19 Enterprise, Project app) |
| System | QAFlow (the QA management system described by this SOP) |
| Version | 1.0 (draft, pending management approval) |

> This file is the source of truth for QAFlow. If code and this SOP disagree, this SOP wins. If this SOP is silent on something, make it configurable and record the question in `docs/OPEN_QUESTIONS.md` instead of guessing. Items marked **PROPOSED** need management approval.

---

## 1. Purpose

Establish a structured QA process that combines AI-powered test generation and execution (GrokBot) with mandatory manual QA review, integrated with the existing Odoo task system.

Goals:

1. Reduce dependency on individuals.
2. Save time on repetitive test case writing and execution.
3. Standardise testing and its documentation.
4. Make every testing cycle traceable through Odoo.
5. Ensure no software change is deployed without proper validation.

## 2. Scope

- All development tasks managed in the Odoo Project app, starting with the FTT DMS project.
- Beta testing before release, and production verification after release (section 5, S11).
- Each task normally belongs to one module. The rare multi-module task is not handled specially.

## 3. Roles

| Role | Responsibility |
|---|---|
| **QA Tester** | Reviews every AI-generated test case, validates every AI result, performs manual testing, adds missing scenarios, and gives final QA approval. The final validation authority. |
| **Requirement provider** | Developer, project manager or other team member who explains what was built. The explanation is recorded. |
| **Transcriber** | A human who transcribes the recording, using an external API tool, and submits the transcript. |
| **QA Lead / Manager** | Can override task priority order (with a reason), views accountability reports, resolves review flags. |
| **Developer** | Builds the change, deploys it to beta, and fixes tasks that fail QA. |
| **GrokBot** | External AI executor. Connects to QAFlow through its REST API and MCP server. Executes approved test cases only. Cannot approve, edit cases, see drafts or change the master repository. |
| **QAFlow** | The system. Orchestrates the workflow, stores data, enforces the rules, syncs with Odoo. |
| **Admin** | Configures users, templates, Odoo mapping and settings. |

## 4. Core Rules (non-negotiable)

| ID | Rule |
|---|---|
| R1 | Everything AI produces (user stories, requirements, test cases, results) is a **draft** until a human acts on it. AI output is never automatically approved. |
| R2 | Manual review of AI-generated test cases is **mandatory**. The reviewer is accountable for the quality and completeness of what they approve. |
| R3 | No test case reaches GrokBot until every case in the set has an explicit human decision and the set is approved. |
| R4 | The tester validates GrokBot's results. They are labelled "AI result" until the tester confirms or overrides each one. |
| R5 | Master test cases are cumulative. They are never replaced or hard-deleted. Changes create versions; removal means retire. |
| R6 | Only the tester gives final QA approval. |
| R7 | Requirements must be documented (recording and transcript) before test cases are generated. |
| R8 | Task order follows Odoo priority, delivery timeline and urgency. The tester does not choose the order. |
| R9 | Every testing cycle is traceable through Odoo (stage, QA fields, attached report, chatter). |
| R10 | No task is promoted to live without final QA approval. |
| R11 | AI must use the predefined templates for user stories, requirements, test cases, results and reports. |
| R12 | Values owned by Odoo (priority, deadline, stage, assignee, hours, Task Sub Status) are read-only in QAFlow. QAFlow writes only the fields listed in section 8. |
| R13 | Every state change is recorded in the audit log, with who and when. |

## 5. Process

```
Odoo task (stage: Deployed on Beta and Pending For Testing)
  -> S1  Priority order
  -> S2  Requirement recording -> human transcript
  -> S3  AI generates user stories, requirements, expected behaviour, test cases
  -> S4  Manual review of test cases            [Checkpoint 1, mandatory]
  -> S5  Approved set handed to GrokBot
  -> S6  GrokBot executes, posts results
  -> S7  Manual validation of results            [Checkpoint 2, mandatory]
  -> S8  Excel report attached to the Odoo task
  -> S9  Outcome: Pass / Rework / Retest
  -> S10 Final QA approval
  -> S11 Production verification
```

### S1. Prioritisation

- Owner: QA Lead (override only), system (ordering).
- All development tasks are managed in Odoo. QAFlow shows tasks in QA scope ordered by priority, delivery deadline and urgency, with a "Next task to test" indicator.
- The tester works in that order. Only QA Lead or Admin can change the order, with a mandatory reason that is audited.
- A task with no description or no checkbox action points is flagged "Not ready for QA". The flag informs the tester; it does not block automatically.

### S2. Requirement capture

- Owner: Requirement provider, Transcriber.
- Before testing begins, the person who knows the change explains what was developed and the expected behaviour. The explanation is recorded.
- A human transcribes the recording using an API tool and submits the transcript to QAFlow (paste, upload, or API). QAFlow does not do speech-to-text.
- The Odoo task description and its checkbox action points are treated as acceptance criteria and are used together with the transcript.
- Gate: a cycle cannot proceed to AI generation without a transcript.

### S3. AI generation

- Owner: AI (draft), system.
- Using the predefined templates, AI generates from the transcript, description and action points:
  - User stories
  - Functional requirements
  - Expected behaviour
  - New test cases
- AI also proposes relevant existing master test cases as regression candidates, and avoids duplicating existing cases.
- Each generated case should reference the requirement or action point it covers. Action points with no covering case are shown to the reviewer as gaps.
- Output is saved as draft (R1).

### S4. Manual review of test cases (Checkpoint 1)

- Owner: QA Tester.
- The tester reviews every generated case and makes an explicit decision per case: **Approve**, **Modify** or **Remove** (with a reason). The tester can add new cases.
- The tester checks that the cases cover the actual business requirements and identifies missing scenarios.
- Submission requires a decision on every case and a reviewer declaration. There is no approve-all without per-case decisions.
- QAFlow records reviewer, time and a diff of each modification.
- Gate: only an approved set can go to execution (R3).

### S5. Approval and handoff

- On submission the set becomes approved and is visible to GrokBot.
- Approved new and modified cases are added to the module's master repository (section 6). Removed cases never reach GrokBot.

### S6. AI execution (GrokBot)

- Owner: GrokBot.
- GrokBot retrieves the approved set through the REST API or the MCP server, executes the cases against the application, and validates actual behaviour against expected results.
- It submits results in the predefined result format: **Passed**, **Failed**, **Blocked** or **Error** (unexpected behaviour), with actual behaviour and evidence.
- Submissions are idempotent. Results for cases outside the approved set are rejected.

### S7. Manual validation of results (Checkpoint 2)

- Owner: QA Tester. This stage is mandatory.
- The tester reviews GrokBot's results and decides per result: **Confirm** or **Override** (own result and notes).
- Failed cases are manually reproduced wherever necessary.
- The tester performs additional manual testing for business logic and scenarios the AI may miss, and records those results.
- Missing scenarios are proposed to the master repository (approved ones are added, never replacing anything).
- Gate: the cycle outcome cannot be chosen while any result is unvalidated.

### S8. Reporting

- A task-wise Excel report is generated (section 7B) and attached to the Odoo task, with a short chatter summary.
- Regenerated reports are versioned (v2, v3). They do not create duplicate posts.

### S9. Outcome

- **Pass:** go to final approval (S10).
- **Rework:** the task failed and goes back to the developer. The reason and failed cases are recorded; QA Cycles increases by 1 in Odoo; the task returns to the configured stage (default Work In Progress).
- **Retest:** when the developer redeploys to beta, the task returns to *Deployed on Beta and Pending For Testing* and the next QA cycle starts automatically, reusing the previously approved set plus new changes. Earlier cycle history is kept.

### S10. Final QA approval

- Owner: QA Tester only (R6).
- Requires a confirmation and a short note. Records who and when.
- In Odoo: **QA Passed** is ticked and the task moves to *Tested on Beta & Ready for Live*.
- No task moves to production without this approval (R10).

### S11. Production verification

- After deployment, a task in *Deployed on Production and Pending for Testing* can be queued for a production check.
- Production checks are **smoke scope**: read-only, non-destructive checks, executed by GrokBot and validated by the tester in the same way as S6 and S7. **PROPOSED:** GrokBot never runs data-changing tests on production.
- On pass, the task is verified on production and is finished according to section 10.

## 6. Master Test Case Repository (module-wise)

- Every module has a permanent master test case repository. Example: the Inventory module.
- Creation is primarily a one-time activity per module, followed by continuous additions.
- Flow: AI generates cases, the tester reviews and adds scenarios, other team members may contribute more, and approved cases become part of the module's master repository.
- When a change is introduced, AI generates cases for the change, the tester reviews them, and approved new cases are added to the existing repository.
- Existing cases are retained, not replaced. A case can be modified (new version) or retired; it is never hard-deleted.
- The repository drives regression testing: relevant existing cases are proposed again for later changes.
- Each case has a version history: who changed it, when, and why.

## 7. Documentation

**A. Master test case files (permanent, per module)**

- Module overview
- Functional areas
- Master test cases with expected results
- Test scenarios
- Additional cases added over time (with change history)

**B. Task-wise testing reports (per QA cycle)**

- Summary: task, module, cycle number, tester, dates, totals
- Test cases used for this task
- AI execution results
- Manual QA observations
- Final status
- Attached to the Odoo task as an Excel file

Temporary AI execution files are not kept as permanent history. The Odoo task retains its testing report as its documentation.

## 8. Odoo Integration (Odoo 19 Enterprise, Project app)

QAFlow uses what already exists in Odoo. There are no Quality, Helpdesk or QA tag modules. All QA tracking uses task stages and a few custom fields.

### Stage mapping

| Odoo stage | QAFlow meaning |
|---|---|
| In design, Assigned, Work In Progress | Development. No QA action. Work In Progress is the default return stage after a fail. |
| Deployed on Beta and Pending For Testing | **Entry point for beta QA.** Creates the QA cycle. |
| Tested on Beta & Ready for Live | Beta QA passed and approved for production. Set after final approval (S10). |
| Deployed on Production and Pending for Testing | Production verification queue (S11). Opt-in only. |
| Cancelled/Merged Tasks | Ignored. |
| Main Modules, Pending to explore | Parking stages, not part of the flow. Ignored. |

### Field mapping

| Odoo field | Type | QAFlow use |
|---|---|---|
| QA Started | Checkbox | Written: ticked when the tester starts the cycle. |
| QA Passed | Checkbox | Written: ticked on final QA approval at beta. |
| QA Cycles | Number | Written: +1 each time a failed task goes back to the developer. |
| Task Sub Status | Dropdown | Read-only. Values: TBD with web and app team, TBD with web team, TBD with app team, Documentation Required. |
| Estimated Hours, Actual Hour Taken | Number | Read-only. Used in reports and the dashboard (estimate vs actual). |
| Description, deadline, assignee, priority | Standard | Read-only. Description checkbox action points are acceptance criteria. |

Technical field names and stage ids are **configured by an admin** in QAFlow settings, never hardcoded.

### Rules

- Write-back to Odoo goes through a retrying job with a dry-run mode. Real write-back is enabled only by a setting. A failed Odoo write never loses local QAFlow state.
- Report attachment and chatter notes are idempotent.
- New tasks should have a description plus checkbox action points. QAFlow flags tasks without them.
- **Scope control:** only tasks in *Deployed on Beta and Pending For Testing* create QA cycles automatically. About 539 tasks currently sit in *Deployed on Production and Pending for Testing*. They are not auto-queued; a cutoff date and manual opt-in apply.

## 9. Accountability and Quality Control

A concern raised in discussion is that testers might approve AI output without properly reviewing it. To prevent this:

- Reviewing test cases and validating results is mandatory, with an explicit decision per item (S4, S7).
- The reviewer is accountable for the quality and completeness of what they approve. Their name, time and decisions are recorded on every approved case and validated result.
- Incomplete or incorrect reviews are treated as a process violation. QAFlow raises **review flags** as signals for management, for example: all cases approved in an unrealistically short time, no case opened or modified before approval, results confirmed with no notes while failures exist, a cycle closed with unvalidated results, or a case later found wrong.
- Flags are visible to QA Lead and Admin. Consequences are decided by management, not by the system.
- AI assists the tester. It does not replace the tester's responsibility.

## 10. Definition of Finished (PROPOSED)

Odoo currently has no stage after production testing, so a task can never be marked finished.

**PROPOSED:** a task is finished when all of these are true:

1. Final QA approval at beta was given (QA Passed ticked).
2. The task was deployed to production.
3. Production verification (S11) passed and was recorded.

**PROPOSED Odoo change:** add a final stage such as *Done / Verified on Production* after *Deployed on Production and Pending for Testing*. Until it exists, QAFlow records `production_verified_at` and posts a chatter note.

## 11. Definitions

- **Test case status:** draft, in review, approved, retired.
- **Review decision:** approve, modify, remove (reason required).
- **AI result:** Passed, Failed, Blocked, Error.
- **Tester validation:** confirmed or overridden.
- **Cycle outcome:** Pass, Rework, Retest.
- **QA Cycles (Odoo):** number of times a failed task went back to the developer. QAFlow's own cycle number is a separate internal counter.

## 12. Open Items

1. Which stage a failed task returns to (default: Work In Progress), and whether QAFlow or the tester moves stages.
2. Whether QA Cycles should show 0 or 1 after a clean first pass (default: 0).
3. Approval of the definition of finished and the new Odoo stage (section 10).
4. Handling of the existing production-pending backlog.
5. GrokBot's environments (beta URL, test accounts) and the production smoke-test limits.
6. Who creates the Odoo API user and key for QAFlow.
7. The existing test case format, to align the default template.
