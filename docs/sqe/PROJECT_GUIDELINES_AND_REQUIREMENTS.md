# SE3002: Software Quality Engineering — Final Project Master Guide & Rules

**Course:** SE3002 – Software Quality Engineering  
**Project:** Automated Testing of an Open-Source Management Information System (MIS)  
**Weightage:** 120 Marks | **Submission:** One final package (PDF Report + Git Repository ZIP)  
**Team Size:** 2 to 3 students (no 4-member groups allowed)  
**Target MIS in Workspace:** `pretix` (Django/Python based open-source event ticketing & management system)

---

## 1. Project Overview & Scope Definition (5 Marks — CLO3)

### Core Scope Requirements
1. **Target MIS Selection:**
   - Must be an open-source, web-based MIS from GitHub with persistent storage, usable browser UI, HTTP API, and accessible source code.
   - Record and commit:
     - Upstream repository URL
     - Exact commit hash (the baseline)
     - License
   - Save baseline version in Git. Upstream tests earn **0 marks**; all your team tests must reside in a dedicated folder (e.g., `tests/team/`).
2. **Workflows & Shared State:**
   - Choose **two related workflows in one module**.
   - For each workflow, document:
     - Starting condition / Preconditions
     - User action
     - Expected outcome / Postconditions
   - **Crucial Requirement:** Identify **at least one record or value that one workflow changes and the other uses** (cross-workflow dependency).
3. **Requirements & Business Rules:**
   - At least **8 functional requirements** across both workflows (minimum 3 per workflow).
   - Document **4 business rules**, which must explicitly include:
     1. A boundary or numerical limit.
     2. A decision with at least two Boolean conditions ($A \land B$ or $A \lor B$).
     3. A rule governing a change of state.
     4. Another domain-specific business rule.
   - Document **2 user roles** with distinct permissions (e.g., Event Organizer/Admin vs. Customer/Attendee).
   - State expected behavior using repository documentation or justified assumptions recorded in the test basis.
4. **Reproducibility:**
   - Provide exact, reproducible shell commands for:
     - Environment installation
     - Starting the application
     - Seeding synthetic test data
     - Resetting application state between test runs

---

## 2. Test Plan, Test Management & Defect Analysis (19 Marks Total)

### A. Test Plan & Estimation (7 Marks — CLO3)
- **Living Test Plan:** Scope, testing approach driven by risk level, roles/responsibilities, test environment, test data strategy, schedule/milestones, entry, exit, suspension, and resumption criteria.
- **Three-Point Estimation:** ($O$ = Optimistic, $M$ = Most Likely, $P$ = Pessimistic, Expected $E = \frac{O + 4M + P}{6}$) per testing area, compared against actual recorded effort at completion.
- **Traceability Matrix:** Full forward/backward mapping from Functional Requirements $\rightarrow$ Business Rules $\rightarrow$ Test Cases $\rightarrow$ Automated Test Scripts $\rightarrow$ Test Results.

### B. Risk Register & Exit Criteria (5 Marks — CLO3)
- **Risk Register:**
  - Minimum **8 product risks** (software defects, performance bottlenecks, security flaws, UI breakage).
  - Minimum **2 project risks** (schedule slippage, environment instability, API breaking changes).
  - Risk scoring: $\text{Likelihood (1–5)} \times \text{Impact (1–5)}$ mapped onto a $5 \times 5$ Risk Matrix.
  - Risk level directly dictates testing technique and depth of coverage.
- **Exit Criteria:**
  - At least **3 measurable criteria** (e.g., functional branch coverage $\ge 100\%$, p95 latency $\le 500\text{ms}$ under 5 VUs, 0 critical accessibility violations).
  - At least **2 exit criteria must be strictly tied to the highest-scoring risks**.

### C. Defect Management & Root Cause Analysis (7 Marks — CLO3)
- **Defect Tracking:** Log real/injected defects in GitHub Issues with severity, priority, lifecycle status, and triage decision.
- **Root Cause Analysis (RCA):**
  - Conduct for at least **2 major defects**.
  - Must include **5 Whys Analysis** + **Fishbone (Ishikawa) Diagram**.
  - Formulate concrete corrective actions (immediate fix) and preventive actions (process/regression guard).
- **Pareto Analysis:** Group defects by category/root cause and show Pareto distribution ($80/20$ rule chart).
- **Linkage:** All weaknesses and defects must link directly to items in the Risk Register.

---

## 3. Static Analysis & White-Box Testing (21 Marks Total)

### A. Static Code Analysis & Metrics (5 Marks — CLO3)
- Run **SonarQube** on the target MIS code.
- Report and analyze: Cyclomatic Complexity, Cognitive Complexity, Code Duplication %, Code Smells, Bugs, Security Vulnerabilities, Technical Debt (time), Quality Gate Ratings (A-E).
- **Hand Calculation:**
  - Select one core business-rule function.
  - Draw its Control Flow Graph (CFG).
  - Calculate Cyclomatic Complexity manually: $V(G) = E - N + 2P$ (or $P + 1$ decision points).
  - Compare the manual hand calculation with SonarQube's reported value and justify differences.

### B. White-Box Unit Testing (16 Marks — CLO2)
- **Coverage Goal:**
  - **100% statement coverage** and **100% branch coverage** across all server-side business logic code for the selected workflows.
  - Any uncovered lines/branches must have a formal written justification in the report.
- **Multiple Condition Coverage (MCC) & MC/DC:**
  - On the critical business-rule module/decision:
    1. Construct a complete **MCC Truth Table** ($2^n$ combinations for $n$ conditions).
    2. Extract valid **MC/DC (Modified Condition/Decision Coverage) test pairs** directly from the MCC table demonstrating each condition independently affects the outcome.
  - Ensure all 4 business rules are exhaustively exercised.

---

## 4. API Testing, Integration & Test Data Generation (17 Marks Total)

### A. Automated Test Data Generation (7 Marks — CLO2)
- Provide or write a clean **OpenAPI specification** for the tested endpoints.
- Build a custom **test data generator script** (e.g., Python script) that parses the OpenAPI spec and automatically generates:
  - Valid and invalid **Equivalence Partitioning (EP)** classes.
  - **3-point Boundary Value Analysis (BVA)** values (just below $min - 1$, exactly at boundary $min/max$, just above $max + 1$).
- **Viva Defense Requirement:** You must be able to change two constraints in the OpenAPI spec live, regenerate test cases, and demonstrate the updated output.

### B. API and Integration Testing (10 Marks — CLO2)
- API tests must consume data directly from the automated generator.
- Implement tests covering:
  - **Equivalence Partitioning:** Every valid and invalid input class (one invalid input per test).
  - **3-Point BVA:** On all numeric, length, or ranged inputs.
  - **API Coverage Criteria:** Status codes, request payloads, response bodies, headers.
  - **Negative Scenarios:** Business rule rejections, invalid state transitions, idempotency / duplicate request handling (no duplicates permitted).
  - **Cross-Workflow Verification:** Read back shared records via API after successful mutation and after rejected operations to prove database consistency.
  - Report any endpoint vulnerabilities or data leakage weaknesses discovered.

---

## 5. Use Case Testing, Usability & Accessibility (14 Marks Total)

### A. Use Case Specification (3 Marks — CLO3)
- Formulate **2 use cases per team member** based on project documentation or system requirements.
- Each use case must document: Preconditions, Main Success Scenario, at least **2 alternative flows**, at least **2 exception/error flows**, and Postconditions.

### B. Use Case Test Automation (6 Marks — CLO2)
- Automate **every single flow** (main, alternate, exception) using **Playwright with Chromium**.
- Assert both UI feedback (toast, alert, redirect) and persistent postconditions.

### C. Usability & Accessibility Evaluation (5 Marks — CLO3)
- **Automated Browser Verification:**
  - 2 automated Playwright tests (1 per workflow). Test displays expected confirmation. One test intentionally enters invalid business-rule data, asserts error messaging, corrects the value, and confirms success.
  - In one test, simulate pure **keyboard navigation (Tab, Enter, Space)**: verify focus order reaches required inputs and submit button, and keyboard can submit without a mouse.
- **Lighthouse & axe-core Audits:**
  - Run Google Lighthouse (Accessibility, Best Practices, SEO) logged in.
  - Run full axe-core scan via `@axe-core/playwright`.
  - Deduplicate findings found in both tools. For each issue report: DOM element, user impact, and proposed remediation.
- **Screen Improvement / Remediation:**
  - Fix one screen (in the MIS code or an isolated representative HTML page).
  - Rerun Lighthouse and axe-core; provide **before-and-after** audit comparison showing measured improvement.

---

## 6. Defensive Security Assessment (6 Marks — CLO2)

1. **Role-Based Access Control (RBAC) Matrix:**
   - Map routes, endpoints, and data across the two chosen roles.
   - Automate verification with Playwright for at least **4 access decisions** across the two roles (including at least 1 allowed and 1 forbidden/denied action).
   - Log role, action, expected status, observed status, and artifact evidence (screenshots, response code).
2. **OWASP ZAP Passive Scan:**
   - Route Playwright test execution traffic through OWASP ZAP in passive scanner mode.
   - Review at least **2 key security controls** (e.g., Session cookie attributes like `HttpOnly`, `SameSite`, `Secure`; CSRF tokens; security headers).
   - Corroborate observations with source code and server configuration.
3. **Open-Source Dependency Vulnerability Audit:**
   - Run `pip-audit` or `OWASP Dependency-Check`.
   - List all checked dependencies and versions.
   - For any CVEs or warnings: document component, CVE ID, severity, affected version, evidence, impact, and upgrade recommendation. Documenting clean, verified controls also receives credit.

---

## 7. Performance & Recovery Testing (5 Marks — CLO2)

1. **Target Metrics & Limits:**
   - Select 1 high-impact state-changing operation from either workflow.
   - Define and justify a baseline SLA: **p95 latency threshold** (e.g., $\le 500\text{ms}$) and **error rate limit** (e.g., $< 1\%$).
2. **Grafana k6 OSS Workload Testing:**
   - Baseline Run: 1 simulated user (VU).
   - Concurrency Run: At least 5 simulated users (VUs) simultaneously.
   - **Protocol:** Run each configuration **twice**; collect metrics for at least **60 seconds per run** after steady state is reached. Keep machine, build, and initial database identical.
   - Report: p95 response time (ms), requests per second (RPS), unexpected failure rate (%). Compare against defined limits.
3. **Automated Failure-and-Recovery Testing:**
   - Automate 1 controlled fault injection on a state-changing operation (e.g., database connection drop or mock dependency failure before write completes).
   - Assert system state after failure (no orphaned/corrupted records), restore service, retry operation, and verify successful final state without duplicate creation.

---

## 8. Mutation Testing & CI Quality Gate (8 Marks — CLO3)

1. **Mutation Testing:**
   - Execute a mutation testing framework (e.g., `mutmut` / `Cosmic Ray` for Python).
   - Report baseline mutation score ($\frac{\text{Killed Mutants}}{\text{Total Mutants}} \times 100\%$).
   - **Implement at least 2 custom mutation operators** tailored specifically to the project's business rules.
   - Analyze at least **15 surviving mutants**: classify each as *equivalent mutant*, *missing test case*, or *weak assertion*, and kill all killable mutants.
2. **GitHub Actions CI Quality Gate:**
   - Configure a CI pipeline on every Pull Request executing: SonarQube analysis, full unit/integration test suites, and mutation testing.
   - **Strict Blocking Rule:** Merge and deployment must be automatically blocked if tests fail or if code falls below justified coverage/Sonar/mutation thresholds.
   - **Zero Escape Hatches:** Prohibited to use `continue-on-error: true` or `|| true`.
   - **Pull Request Evidence:**
     - Include 1 documented PR that was **blocked** by the gate.
     - Include 1 documented PR with a bug fix that **failed before and passed after**.

---

## 9. Monitoring, Completion Report & Final Decision (5 Marks — CLO3)

1. **Weekly Progress Reports:**
   - Document weekly progress against schedule with control actions taken when deviations occurred.
   - Measure Goal-Question-Metric (GQM) indicators: Defect Density, Requirements Coverage %, Reopen Rate %.
2. **Test Completion Report:**
   - Summarize what was tested vs. not tested, deviations from plan, open defect status, and residual risk per risk item.
   - Deliver a formal **Release or Hold recommendation** backed by actual vs. target metrics for each of the 3 predefined exit criteria.

---

## 10. Individual Work Allocation & Viva Defense (20 Marks — CLO1)

### Work Ownership Split
Each member must officially own and defend distinct technical areas:
- **Member 1 Area:** Static analysis (SonarQube, CFG, Cyclomatic complexity), White-box unit testing (100% coverage, MCC, MC/DC), Mutation testing (mutmut, custom operators, 15 surviving mutants), GitHub Actions CI pipeline gate.
- **Member 2 Area:** OpenAPI specification, Automated test data generator script (EP/BVA), API & integration testing, Cross-workflow verification.
- **Member 3 Area (or split between 2 members if in a pair):** Use case specification and Playwright automation, Usability & accessibility (Lighthouse, axe-core, keyboard nav, screen fix), Defensive security (RBAC matrix, ZAP, dependency audit), Performance & recovery (k6 runs, fault recovery).
- **Shared by All Members:** Test management (Test Plan, 3-point estimation, Risk Register, Defect tracking, Root cause analysis, GQM monitoring, Test completion report).

### Viva Rules & Live Task
- **Individual Defense:** Every student must rerun tests live and explain assertions and theoretical basis. If a student cannot explain a component in their assigned area, marks for that component are deducted (potentially to zero).
- **Live Task:** The examiner will assign a live business-rule modification or updated API schema. The student must:
  1. Predict which tests and CI gates will fail.
  2. Implement the change live.
  3. Run the suite and prove the prediction.
- **Zero Tolerance Policy:** "We did it but forgot" is strictly rejected.

---

## 11. AI Usage & Academic Integrity Policy

- **Allowed With Disclosure:** Generative AI tools are permitted **only** if every output is critically verified and documented in an **AI-Use Record Table**:
  - `Tool Name` | `Purpose/Prompt` | `AI Output Generated` | `Human Verification / Modifications Made`
  - Prompts must be preserved and recorded.
- **Strictly Prohibited:**
  - Undisclosed AI usage.
  - Fabricated or manually edited evidence/screenshots/pipeline logs.
  - Code copying or test borrowing across groups, sections, or upstream repository tests.
- **Plagiarism Checks:** Submissions are automatically checked across sections, against upstream codebases, and against individual Git commit histories. Every student must commit their own code from their own account!
- **Penalties:** Zero for the component or whole project + university disciplinary referral.

---

## 12. Final Packaging & Submission Checklist

- [ ] **Archive Format:** Single ZIP file containing Git repository (with full `.git` folder intact).
- [ ] **Report Format:** Single PDF report with active public GitHub repository link.
- [ ] **Naming Convention:**
  - Groups of 3: `Project_RollNumber1_RollNumber2_RollNumber3_Section.zip` and `.pdf`
  - Groups of 2: `Project_RollNumber1_RollNumber2_Section.zip` and `.pdf`
- [ ] **Contents in Report:**
  - System Scope & Baseline Git Commit Hash
  - Living Test Plan & 3-Point Estimation Comparison
  - 5x5 Risk Register & 3 Measurable Exit Criteria
  - Complete Traceability Matrix
  - SonarQube Metrics & CFG Cyclomatic Complexity Comparison
  - Unit Test Results (100% Coverage, MCC Table, MC/DC Pairs)
  - OpenAPI Spec & Test Data Generator Verification
  - API Test Results & Cross-Workflow Invariants
  - Playwright Use Case Automation & Keyboard Nav Results
  - Accessibility & Usability (Lighthouse + axe-core Before & After)
  - Defensive Security (RBAC Matrix, ZAP Passive Findings, pip-audit)
  - k6 Performance (1 VU vs 5 VUs, 60s runs, p95, RPS) & Recovery Test
  - Mutation Testing (Score, 2 Custom Operators, 15 Mutant Analysis)
  - GitHub Actions CI Gate (Blocked PR + Passing PR)
  - Defect Logs, 5 Whys + Fishbone RCA, Pareto Chart
  - GQM Weekly Reports & Test Completion Release/Hold Decision
  - Member Work Allocation & Verified AI-Use Record Table
