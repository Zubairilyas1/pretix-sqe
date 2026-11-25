# SE3002 SQE Final Project: Team Work Partitioning & AI Agent Master Guide

**Project:** Automated Testing of Open-Source MIS — `pretix`  
**Total Marks:** 120 Marks | **Target System:** `pretix` (Python / Django)  
**Upstream Repository:** `https://github.com/pretix/pretix.git`  
**Baseline Commit Hash:** `c0d887738b6cd97f724b926718c55e2ae87c9901`  
**License:** GNU AGPL v3.0 (with pretix commercial exceptions)  
**Team Members & Roles:**
1. **Zubair (User / Member 1):** Area 1 — Static Analysis, White-Box Unit Testing, Mutation Testing, CI/CD Quality Gate
2. **Sami (Member 2):** Area 2 — OpenAPI Specification, Automated Test Data Generator, API & Integration Testing
3. **Tawassul (Member 3):** Area 3 — Use Case Specification & Playwright E2E Automation, Usability/Accessibility, Defensive Security, Performance & Recovery Testing
- **Shared across All 3 Members:** Test Management (Test Plan, 3-Point Estimation, 5×5 Risk Register, Traceability Matrix, Defect Tracking with 5 Whys + Fishbone, Pareto Analysis, GQM Weekly Progress, Test Completion Report).

---

## 🤖 UNIVERSAL AI AGENT SYSTEM PROMPT (COPY-PASTE FOR AGENTS)

> **Instructions for the Team:** When you open ChatGPT, Claude, Cursor, Copilot, or Antigravity, **copy and paste the block below into your first prompt** along with your name. The AI agent will immediately understand your exact assignment, the codebase, and all rules!

```markdown
You are acting as an expert Senior Software Quality Engineer assisting me with my SE3002 Software Quality Engineering Final Project.
Our team is testing the open-source event management system "pretix" (Python/Django) located in this repository.
Here are the critical constraints and project guidelines set by our instructor:
1. TARGET REPOSITORY: pretix (upstream: https://github.com/pretix/pretix.git, commit: c0d887738b6cd97f724b926718c55e2ae87c9901).
2. ISOLATION RULE: Upstream tests earn 0 marks! All our team test suites, scripts, and generators MUST reside in a custom directory: `tests/team/` (or `pretix/src/tests/team/`).
3. SELECTED WORKFLOWS (Core Module: Event Ticketing & Order Management):
   - Workflow 1 (Organizer): Ticket Item & Quota Creation (`Quota.size`, `Item.default_price`, capacity limits).
   - Workflow 2 (Customer): Presale Cart Reservation & Order Checkout (`Order`, `OrderPosition`, `Quota.availability()`).
   - Shared Value/Record: `Quota.size` & `Quota.availability()` — Workflow 1 sets capacity; Workflow 2 checks and decrements it.
4. BUSINESS RULES:
   - Rule 1 (Boundary/Limit): Order quantity between 1 and max_per_order; Quota capacity cannot be oversold.
   - Rule 2 (Boolean Decision): Ticket is purchasable IFF (Item.active == True) AND (available_from <= now <= available_until) AND (Quota.available > 0).
   - Rule 3 (State Transition): Order lifecycle: PENDING -> PAID, PENDING -> CANCELED, PAID -> REFUNDED. Invalid: CANCELED -> PAID.
   - Rule 4 (Domain Rule): Cart expiration timeout returns reserved quota back to the pool after 30 minutes.
5. ROLES:
   - Role A: Event Organizer / Admin (Access to `/control/` dashboard, manage items/quotas).
   - Role B: Customer / Attendee (Access to `/presale/` store, checkout, order secret link; strictly denied `/control/`).
6. MY ASSIGNED IDENTITY: [INSERT MY NAME: Zubair OR Sami OR Tawassul]

Please read my designated partition in the project guidelines below, examine the codebase, and generate production-grade, reproducible code, tests, and documentation adhering to the course rubric and academic integrity policy.
```

---

## 🌿 GIT BRANCHING STRATEGY & COLLABORATION RULES

### Why This is Strictly Graded
> **Instructor Rule (Page 5 & 7 of Project Spec):**  
> *"Every member commits their own work; commit history is checked in the viva."*  
> *"Submissions are compared across all groups and sections, against upstream and online sources, and against commit history. Any component you cannot explain in the viva is treated as not your work."*

### 1. Mainstream Branch
- The base branch is **`main`** (or clean tracking branch synced to commit `c0d887738b6cd97f724b926718c55e2ae87c9901`).
- Direct pushes to `main` are strictly forbidden. All additions must arrive via **Pull Request (PR)**.

### 2. Member Branches
Each member maintains their dedicated base branch:
- `member/zubair`
- `member/sami`
- `member/tawassul`

### 3. Feature Branches (Off Member Branches)
When working on a specific task, create a feature branch off your member branch or off `main`:
- **Zubair:**
  - `zubair/feat-sonarqube-metrics`
  - `zubair/feat-whitebox-mcdc`
  - `zubair/feat-mutation-mutmut`
  - `zubair/feat-github-actions-ci`
- **Sami:**
  - `sami/feat-openapi-spec`
  - `sami/feat-test-data-generator`
  - `sami/feat-api-integration-tests`
  - `sami/feat-cross-workflow-validation`
- **Tawassul:**
  - `tawassul/feat-playwright-usecases`
  - `tawassul/feat-a11y-lighthouse-fix`
  - `tawassul/feat-security-rbac-zap`
  - `tawassul/feat-k6-perf-recovery`

### 4. Git Identity Configuration (CRUCIAL)
Before making any commits on your local machine, run:
```bash
# Zubair:
git config user.name "Zubair"
git config user.email "zubair@yourdomain.edu.pk"

# Sami:
git config user.name "Sami"
git config user.email "sami@yourdomain.edu.pk"

# Tawassul:
git config user.name "Tawassul"
git config user.email "tawassul@yourdomain.edu.pk"
```

### 5. Pull Request & CI Gate Rules
- Every PR must trigger the **GitHub Actions CI Quality Gate**.
- The pipeline runs: Unit tests, Coverage check ($\ge 100\%$ on business logic), SonarQube scan, and Mutation check.
- **Escape Hatches Forbidden:** Never commit `continue-on-error: true` or `|| true`.
- Required PR Evidence:
  1. **One Blocked PR:** Create an intentional failing PR (e.g., breaking a business rule or lowering coverage) showing the CI pipeline blocking the merge.
  2. **One Passing Fix PR:** Create a PR that fixes a bug, failing before the fix and passing after.

---

## 📁 TEAM REPOSITORY DIRECTORY STRUCTURE

All custom tests and scripts must be organized in this clean structure:

```text
pretix/
├── tests/
│   └── team/                              <-- ALL YOUR CODE GOES HERE (Upstream tests are ignored)
│       ├── __init__.py
│       ├── conftest.py                    <-- Shared fixtures (test event, organizer user, customer user)
│       │
│       ├── zubair/                        <-- ZUBAIR'S AREA (Area 1)
│       │   ├── test_whitebox_rules.py     <-- 100% statement & branch coverage of business logic
│       │   ├── test_mcc_mcdc.py           <-- MCC Truth Table & MC/DC test cases
│       │   ├── mutation/
│       │   │   ├── mutmut_config.py       <-- mutmut setup & target modules
│       │   │   ├── custom_operators.py    <-- 2 custom mutation operators for business rules
│       │   │   └── surviving_mutants.md   <-- Analysis of 15 surviving mutants & kills
│       │   ├── sonarqube/
│       │   │   ├── sonar_report.md        <-- Sonar metrics analysis & technical debt
│       │   │   └── hand_calculated_cfg.pdf<-- CFG drawing and manual Cyclomatic Complexity calculation
│       │   └── ci/
│       │       └── github_actions.yml     <-- Complete blocking CI workflow (.github/workflows/)
│       │
│       ├── sami/                          <-- SAMI'S AREA (Area 2)
│       │   ├── openapi/
│       │   │   └── pretix_orders_api.yaml <-- Clean OpenAPI 3.0 specification for tested endpoints
│       │   ├── generator/
│       │   │   ├── generate_test_data.py  <-- Python script parsing OpenAPI -> EP & 3-point BVA
│       │   │   └── test_data.json         <-- Generated JSON datasets
│       │   └── api/
│       │       ├── test_api_ep_bva.py     <-- API tests using generated data
│       │       ├── test_negative_rules.py <-- Business rule rejections, invalid transitions
│       │       ├── test_cross_workflow.py <-- Shared record verification (Quota consistency)
│       │       └── endpoint_weaknesses.md <-- Identified API weaknesses and mitigations
│       │
│       ├── tawassul/                      <-- TAWASSUL'S AREA (Area 3)
│       │   ├── usecases/
│       │   │   ├── use_case_spec.md       <-- 6 Use cases (2 per member) with 2 alt & 2 exc flows
│       │   │   └── e2e_playwright.spec.ts <-- Automated Playwright tests for every flow
│       │   ├── usability_a11y/
│       │   │   ├── test_keyboard_nav.spec.ts<-- Playwright keyboard-only tab & submit navigation
│       │   │   ├── lighthouse_report_before.html
│       │   │   ├── lighthouse_report_after.html
│       │   │   ├── axe_core_scan.ts       <-- @axe-core/playwright audit script
│       │   │   └── screen_remediation/    <-- Fixed screen with before/after comparison
│       │   ├── security/
│       │   │   ├── rbac_access_matrix.md  <-- 2 roles x endpoints permissions matrix
│       │   │   ├── test_rbac_decisions.spec.ts <-- Automated Playwright checks (allowed & denied)
│       │   │   ├── zap_passive_scan_report.md <-- OWASP ZAP session cookie & header audit
│       │   │   └── dependency_audit_pip.md<-- pip-audit CVE scan report
│       │   └── performance/
│       │       ├── k6_workload.js         <-- k6 script (1 VU baseline & 5 VUs load, 60s runs)
│       │       ├── k6_metrics_report.md   <-- p95, RPS, failure rate comparisons
│       │       └── test_failure_recovery.py<-- Fault injection (network/DB failure) & recovery test
│       │
│       └── shared_management/             <-- SHARED TEST MANAGEMENT
│           ├── TEST_PLAN.md               <-- Scope, environment, schedule, entry/exit criteria
│           ├── THREE_POINT_ESTIMATION.md  <-- O, M, P hours vs actual effort per area
│           ├── RISK_REGISTER_5x5.md       <-- 8 product + 2 project risks mapped to 5x5 matrix
│           ├── RTM_TRACEABILITY_MATRIX.md <-- Requirements -> Rules -> Tests -> Scripts
│           ├── DEFECT_LOG_GITHUB.md       <-- Issues, severity, lifecycle, triage
│           ├── ROOT_CAUSE_ANALYSIS.md     <-- 5 Whys + Fishbone diagrams for 2 major bugs
│           ├── PARETO_ANALYSIS.md         <-- Defect classification chart (80/20 rule)
│           ├── GQM_WEEKLY_PROGRESS.md     <-- Weekly metrics (Defect density, coverage, reopen rate)
│           ├── TEST_COMPLETION_REPORT.md  <-- Tested vs untested, residual risks, Release/Hold decision
│           └── AI_USE_DISCLOSURE_LOG.md   <-- Mandatory transparency table for all members
```

---

## 👤 PARTITION 1: ZUBAIR (MEMBER 1) — COMPLETE EXECUTION SPECIFICATION

### Technical Ownership: Area 1
* **Marks Weightage:** 5 (Static Analysis) + 16 (White-Box) + 8 (Mutation & CI) = **29 Individual Marks** (+ shared management & viva).
* **Target CLOs:** CLO2 (Design & execute white-box tests), CLO3 (Static analysis, metrics, CI/CD).

### Detailed Tasks & Deliverables for Zubair:

#### Task 1.1: Static Analysis with SonarQube & Hand-Calculated Complexity
1. Set up SonarQube locally or via Docker (`docker run -d -p 9000:9000 sonarqube:lts-community`).
2. Run SonarScanner on `pretix/src/pretix/base` (specifically targeting items, quotas, and orders).
3. Report metrics:
   - Cyclomatic Complexity & Cognitive Complexity
   - Code Smells, Bugs, Vulnerabilities, Security Hotspots
   - Duplication percentage and Technical Debt ratio
   - Quality Gate Ratings (A through E).
4. **CFG Hand Calculation:**
   - Select the core business rule function in `pretix/base/services/orders.py` or `pretix/base/models/quota.py` (e.g., `_check_quotas()` or `availability()`).
   - Draw the formal **Control Flow Graph (CFG)** with labeled nodes (statements/predicates) and directed edges (transfers of control).
   - Calculate McCabe's Cyclomatic Complexity manually:
     $$V(G) = E - N + 2P \quad \text{or} \quad V(G) = P + 1$$
   - Compare with SonarQube's computed metric. Explain and justify any differences (e.g., how compound boolean predicates `&&`/`||` or exception handling blocks are counted).

#### Task 1.2: 100% Statement & Branch Coverage White-Box Testing
1. Target the server-side business logic handling ticket quota reservation and order processing:
   - `pretix.base.models.quota.Quota`
   - `pretix.base.services.orders.perform_order()` and `Order.can_be_paid()`
2. Write unit tests in `tests/team/zubair/test_whitebox_rules.py` using `pytest` and `coverage.py`.
3. Achieve **100% Statement Coverage** and **100% Branch Coverage** on all designated business rule functions.
4. If any defensive code or unhandled exception branch cannot be hit, write a documented defense justifying why it is unreachable in the test environment.

#### Task 1.3: Multiple Condition Coverage (MCC) & MC/DC Pairs
1. Identify the critical decision containing $\ge 2$ boolean conditions (Business Rule 2: Item Availability & Quota).
   Example Decision:
   $$D = (\text{active}) \land (\text{valid\_time}) \land (\text{quota\_avail}) \land (\neg \text{hide\_sold\_out})$$
2. Construct the full **MCC Truth Table** with all $2^n$ combinations ($2^4 = 16$ rows).
3. Derive **MC/DC Test Pairs** directly from the MCC table:
   - For each independent condition $C_i$, identify two test cases where $C_i$ flips between True and False, all other conditions remain fixed, and the overall decision outcome $D$ flips.
4. Implement executable pytest cases in `tests/team/zubair/test_mcc_mcdc.py` verifying each identified MC/DC pair.

#### Task 1.4: Mutation Testing (`mutmut`) & Custom Mutation Operators
1. Configure `mutmut` targeting the business rule module.
2. Run mutation testing and record the baseline mutation score:
   $$\text{Mutation Score} = \frac{\text{Killed Mutants}}{\text{Total Mutants}} \times 100\%$$
3. **Implement at least 2 Custom Mutation Operators:**
   - Operator 1 (Quota Boundary Flip): Mutate `remaining_quota < requested_quantity` into `remaining_quota <= requested_quantity`.
   - Operator 2 (State Machine Inversion): Mutate `Order.STATUS_PENDING` check into `Order.STATUS_PAID`.
4. **Surviving Mutants Analysis:**
   - Deep-dive analyze at least **15 surviving mutants**.
   - Categorize each as: (a) *Equivalent Mutant* (semantically identical, cannot be killed), (b) *Missing Test Case*, or (c) *Weak Assertion*.
   - Write new targeted unit tests to kill all killable surviving mutants.

#### Task 1.5: GitHub Actions CI Quality Gate
1. Create `.github/workflows/sqe_quality_gate.yml`.
2. Configure steps on every Pull Request:
   - Checkout code $\rightarrow$ Setup Python $\rightarrow$ Install dependencies.
   - Run `pytest --cov --cov-fail-under=100` on team business logic.
   - Run SonarQube Scanner $\rightarrow$ enforce Quality Gate status.
   - Run `mutmut` $\rightarrow$ fail if mutation score drops below threshold.
3. **Strict Constraints:** Zero escape hatches (`continue-on-error: true` or `|| true` are strictly banned).
4. Deliver **PR #1 (Blocked PR)** showing pipeline failure, and **PR #2 (Passing Bugfix PR)** showing successful merge after fixing the code.

---

## 👤 PARTITION 2: SAMI (MEMBER 2) — COMPLETE EXECUTION SPECIFICATION

### Technical Ownership: Area 2
* **Marks Weightage:** 7 (Data Generator) + 10 (API & Integration) = **17 Individual Marks** (+ shared management & viva).
* **Target CLOs:** CLO2 (API testing, Equivalence Partitioning, Boundary Value Analysis, Automated test data generation).

### Detailed Tasks & Deliverables for Sami:

#### Task 2.1: OpenAPI 3.0 Specification
1. Document the REST API endpoints in `tests/team/sami/openapi/pretix_orders_api.yaml` for both selected workflows:
   - Organizer Endpoint: `POST /api/v1/organizers/{org}/events/{event}/items/` & `POST .../quotas/`
   - Customer Endpoints: `POST /api/v1/organizers/{org}/events/{event}/cart/add/` & `POST .../order/create/`
   - Status & Order Query: `GET /api/v1/organizers/{org}/events/{event}/orders/{code}/`
2. Define exact schemas, data types, required fields, enum states, numeric constraints (`minimum: 1`, `maximum: 10`, `format: int32`), and HTTP status codes (200, 201, 400, 403, 409).

#### Task 2.2: Automated Test Data Generator Script
1. Develop a Python script `tests/team/sami/generator/generate_test_data.py` using `pyyaml` or `openapi-schema-validator`.
2. The script must parse the OpenAPI YAML specification and automatically generate:
   - **Equivalence Partitioning (EP) Classes:**
     - Valid partition (e.g., ticket quantity $\in [1, 10]$).
     - Invalid sub-boundary partition (e.g., quantity $\le 0$).
     - Invalid super-boundary partition (e.g., quantity $> 10$).
     - Invalid type / malformed string (e.g., quantity = `"abc"` or `None`).
   - **3-Point Boundary Value Analysis (BVA) Values:**
     - For lower boundary ($min = 1$): test at $0$ (just below), $1$ (exact), and $2$ (just above).
     - For upper boundary ($max = 10$): test at $9$ (just below), $10$ (exact), and $11$ (just above).
3. Export generated test cases to `tests/team/sami/generator/test_data.json`.
4. **Viva Requirement:** Sami must be able to change 2 constraints in the OpenAPI YAML live (e.g., change `maximum: 10` to `maximum: 5`), re-run the generator, and show updated BVA test values.

#### Task 2.3: API & Integration Testing
1. Write pytest test suites in `tests/team/sami/api/test_api_ep_bva.py` that dynamically load and execute against the generator's output using Django REST Framework's `APIClient` or `requests`.
2. Verify all API coverage criteria: HTTP status codes, headers, response JSON schema, and validation error payloads.
3. Test **Negative Scenarios & Rejections:**
   - Attempting to purchase tickets exceeding quota capacity (expect HTTP 400 / 409).
   - Attempting illegal state transitions via API (e.g., triggering payment on a canceled order).
   - Duplicate / Idempotency tests: Resend the exact same order submission token repeatedly and verify no duplicate orders or double quota deductions occur.

#### Task 2.4: Cross-Workflow Shared State Verification
1. Implement `tests/team/sami/api/test_cross_workflow.py`:
   - Step 1: Workflow 1 (Organizer API) creates a quota with size = 5.
   - Step 2: Read back `Quota.availability()` -> assert capacity is 5.
   - Step 3: Workflow 2 (Customer API) orders 3 tickets -> assert order succeeds (HTTP 201).
   - Step 4: Read back `Quota.availability()` -> assert remaining capacity is now 2.
   - Step 5: Customer API attempts to order 3 more tickets -> assert rejection (HTTP 400).
   - Step 6: Read back `Quota.availability()` -> assert remaining capacity is **still exactly 2** (no corrupted or partially decremented state).
2. Author `endpoint_weaknesses.md` detailing any discovered rate-limiting gaps, improper HTTP status codes, or leaky error responses.

---

## 👤 PARTITION 3: TAWASSUL (MEMBER 3) — COMPLETE EXECUTION SPECIFICATION

### Technical Ownership: Area 3
* **Marks Weightage:** 3 (Use Case Spec) + 6 (Playwright E2E) + 5 (Usability & A11y) + 6 (Security) + 5 (Perf & Recovery) = **25 Individual Marks** (+ shared management & viva).
* **Target CLOs:** CLO2 (Playwright automation, Security testing, Performance testing), CLO3 (Usability, Accessibility, Use case engineering).

### Detailed Tasks & Deliverables for Tawassul:

#### Task 3.1: Use Case Specification & Playwright End-to-End Automation
1. Specify **6 formal Use Cases** (2 per member across the team) in `tests/team/tawassul/usecases/use_case_spec.md`:
   - UC-1: Organizer configures ticket categories, items, and quotas.
   - UC-2: Organizer publishes event and defines ticket sales window.
   - UC-3: Customer selects tickets, inputs attendee details, and completes checkout.
   - UC-4: Customer applies discount voucher code during cart checkout.
   - UC-5: Customer attempts to purchase tickets for a sold-out category.
   - UC-6: Customer cancels an unconfirmed/pending order before expiration.
   - **Mandatory Flow Requirements:** Each use case must have Preconditions, Main Success Scenario, $\ge 2$ Alternative Flows, $\ge 2$ Exception Flows, and Postconditions.
2. Automate **all flows** using **Playwright with Chromium** in TypeScript/JavaScript or Python (`@playwright/test`).
3. Assert both UI element confirmations (toast banners, modal alerts, page URL redirects) and underlying database state changes.

#### Task 3.2: Usability, Keyboard Navigation & Accessibility Evaluation
1. **Automated Keyboard Navigation Test:**
   - In `test_keyboard_nav.spec.ts`, write a Playwright test that uses *only* keyboard events (`page.keyboard.press('Tab')`, `press('Enter')`, `press('Space')`).
   - Assert that keyboard focus moves sequentially through all required form inputs, checkboxes, and the submit button in logical tab order, and successfully submits the order.
2. **Lighthouse & axe-core Audits:**
   - Run Google Lighthouse on key screens (Organizer Item Creation page and Customer Checkout page) while logged in.
   - Run automated WCAG 2.1 AA scan via `@axe-core/playwright`.
   - Deduplicate overlapping findings. Report for each issue: Affected DOM element, WCAG criteria violated, user impact, and suggested fix.
3. **Screen Remediation (Before & After):**
   - Fix accessibility defects on one key screen (e.g., missing form labels, invalid ARIA roles, color contrast issues).
   - Re-run Lighthouse and axe-core. Document the verified **Before-and-After score comparison** (e.g., Accessibility score improved from 74 $\rightarrow$ 98).

#### Task 3.3: Defensive Security Assessment
1. **Role-Based Access Control (RBAC) Matrix:**
   - Map routes (`/control/...` vs `/presale/...`) across Organizer Role and Attendee Role.
   - Automate verification with Playwright for at least **4 access decisions**:
     - Organizer accessing `/control/` (Allowed $\rightarrow$ HTTP 200).
     - Customer accessing `/presale/` (Allowed $\rightarrow$ HTTP 200).
     - Customer attempting to access `/control/` (Denied $\rightarrow$ HTTP 403 / Redirect to Login).
     - Customer attempting to view another customer's order without secret token (Denied $\rightarrow$ HTTP 404/403).
2. **OWASP ZAP Passive Scan:**
   - Configure Playwright to route browser traffic through OWASP ZAP proxy in passive scanning mode.
   - Verify security headers (`Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`) and session cookie attributes (`HttpOnly`, `SameSite=Lax/Strict`, `Secure`).
3. **Dependency Vulnerability Audit:**
   - Run `pip-audit` on `pretix` requirements.
   - Report checked packages, CVE identifiers, CVSS severity scores, and upgrade paths.

#### Task 3.4: Performance Testing (k6) & Failure Recovery
1. **Grafana k6 OSS Workload Testing:**
   - Define SLA target: $\text{p95} \le 500\text{ms}$, failure rate $< 1\%$.
   - Test script `k6_workload.js` simulating ticket checkout.
   - **Execution Protocol:**
     - Run 1: Baseline run with 1 Virtual User (VU) for 60 seconds steady state.
     - Run 2: Concurrency run with $\ge 5$ concurrent VUs for 60 seconds steady state.
     - Repeat each run **twice** using identical starting test data.
   - Report p95 response time (ms), throughput (requests/sec), and HTTP error percentage.
2. **Automated Failure-and-Recovery Testing:**
   - In `test_failure_recovery.py`, inject a simulated failure (e.g., mock a database connection timeout or Redis cache outage right before order commit).
   - Assert system handles failure gracefully (no orphaned order positions or unreturned quota).
   - Restore the dependency, retry the transaction, and assert successful order completion without duplicate records.

---

## 🤝 SHARED RESPONSIBILITIES (ALL 3 MEMBERS TOGETHER)

All members contribute equally to Test Management. These files reside in `tests/team/shared_management/`:

| Component | Marks | Owner | Key Deliverables |
| :--- | :---: | :---: | :--- |
| **System Scope & Baseline** | 5 | All | Upstream URL, commit hash `c0d887738b6cd97f724b926718c55e2ae87c9901`, 8 functional reqs, 4 business rules, 2 roles. |
| **Test Plan & 3-Point Estimation** | 7 | All | Scope, environment, schedule, entry/exit criteria, $E = \frac{O + 4M + P}{6}$ vs actual effort table. |
| **Risk Register & Exit Criteria** | 5 | All | 8 product + 2 project risks on $5 \times 5$ matrix; 3 measurable exit criteria tied to top risks. |
| **Requirements Traceability Matrix** | Incl. | All | Forward/backward traceability mapping Reqs $\rightarrow$ Rules $\rightarrow$ Tests $\rightarrow$ Automated Scripts. |
| **Defect Tracking & RCA** | 7 | All | GitHub Issues, **5 Whys Analysis** + **Fishbone Diagrams** for 2 major bugs, Pareto chart ($80/20$). |
| **GQM Monitoring & Test Completion** | 5 | All | Weekly reports against plan, defect density, reopen rate, final **Release / Hold** decision. |
| **AI-Use Disclosure Log** | Mandatory| All | Complete table logging tool, prompt, output, human check. |
| **Viva & Live Task** | 20 | All | Individual defense of assigned technical partition and live test adaptation. |

---

## 📝 MANDATORY AI-USE DISCLOSURE LOG TEMPLATE

> **Strict Rule from Page 7 of Course Document:**  
> *"AI tools are allowed only if you check every output and disclose it in an AI-use record (tool, purpose, output, what you checked or changed). Keep your prompts. Undisclosed AI use gets zero marks."*

Every member must log every AI query in `tests/team/shared_management/AI_USE_DISCLOSURE_LOG.md`:

```markdown
# AI-Use Disclosure Record

| Date | Team Member | AI Tool & Model | Exact Purpose & Prompt Summary | AI Generated Output | Human Verification & Modifications Made |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-11-25 | Zubair | Claude 3.5 Sonnet / Antigravity | Generated MCC truth table for Rule 2 | Table with 16 rows and Boolean evaluations | Checked rows 5 and 7 for operator precedence; adjusted bracket grouping for Django models. |
| 2026-11-25 | Sami | GPT-4o / Cursor | Drafted OpenAPI schema for `/cart/add/` | Initial YAML specification | Added missing `max_per_order` boundary constraint and corrected 409 Conflict status. |
| 2026-11-25 | Tawassul | Gemini 1.5 Pro / Antigravity | Generated Playwright keyboard navigation test | TypeScript script using `page.keyboard.press` | Fixed selector for pretix custom dropdown widget and verified assertion timing. |
```

---

## 🎯 VIVA DEFENSE & LIVE TASK PREPARATION GUIDE

### Zubair (Member 1) Defense Strategy:
1. **Explain CFG & Cyclomatic Complexity:** Be ready to draw the CFG on a whiteboard, identify predicate nodes, and explain why SonarQube's complexity matches or differs from your formula $E - N + 2P$.
2. **Explain MC/DC Test Selection:** Show your MCC table and point out the exact pair of rows that isolates each condition.
3. **Live Task Anticipation:** The professor may say: *"Invert the boundary from `<` to `<=` in the quota check. Which tests fail?"* You must predict the failing pytest and mutation mutants, modify the code, and demonstrate the failure.

### Sami (Member 2) Defense Strategy:
1. **Explain Test Data Generation:** Walk through `generate_test_data.py`, showing how the AST/YAML parser identifies numeric boundaries and constructs $min-1, min, max, max+1$.
2. **Explain Cross-Workflow Invariant:** Explain how the Quota availability state is read before, during, and after cart checkout.
3. **Live Task Anticipation:** The professor may say: *"Change the max ticket constraint from 10 to 4 in your OpenAPI spec. Regenerate test data live."* You will run `python generate_test_data.py` and show the updated BVA values ($3, 4, 5$).

### Tawassul (Member 3) Defense Strategy:
1. **Explain Playwright Assertions:** Show how your Playwright tests verify both the visible UI banner and the persistent backend state.
2. **Explain Accessibility & Remediation:** Explain the exact WCAG failure detected by axe-core and demonstrate the before-and-after score in Lighthouse.
3. **Live Task Anticipation:** The professor may say: *"What happens if a customer role user manipulates the URL to access `/control/`?"* Run the automated RBAC Playwright test and prove that Pretix returns an HTTP 403 or redirects to login.

---

## 📦 FINAL PACKAGE SUBMISSION CHECKLIST

- [ ] Repository ZIP named `Project_RollNumber1_RollNumber2_RollNumber3_Section.zip`.
- [ ] Preserved `.git` folder inside ZIP to prove commit history for Zubair, Sami, and Tawassul.
- [ ] Comprehensive PDF Report named `Project_RollNumber1_RollNumber2_RollNumber3_Section.pdf`.
- [ ] Public GitHub repository link included in the report.
- [ ] All team tests isolated in `tests/team/`.
- [ ] CI pipeline documented with 1 blocked PR and 1 passing fix PR.
- [ ] Complete AI-Use disclosure log included.
