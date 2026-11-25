# pretix-sqe: Software Quality Engineering Final Project (Fall 2026)

[![Course](https://img.shields.io/badge/Course-SE3002%20SQE-blue.svg)](https://github.com/Zubairilyas1/pretix-sqe)
[![Base Commit](https://img.shields.io/badge/Pretix%20Baseline-c0d887738-green.svg)](https://github.com/pretix/pretix/commit/c0d887738b6cd97f724b926718c55e2ae87c9901)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-orange.svg)](LICENSE)

This repository serves as the official submission and automated testing workspace for the **Software Quality Engineering (SE3002)** Final Project.

---

## 👥 Team Roster & Area Partitioning

| Student Name | Assigned Technical Area | Key Deliverables |
| :--- | :--- | :--- |
| **Zubair** *(Lead / Member 1)* | **Area 1:** Static Analysis, White-Box Testing, Mutation Testing & CI/CD | SonarQube metrics, CFG hand calculation, 100% statement & branch coverage on business rules, MCC Truth Tables & MC/DC pairs, `mutmut` mutation tests with 2 custom operators, and GitHub Actions CI quality gate. |
| **Sami** *(Member 2)* | **Area 2:** OpenAPI Spec, Automated Test Data Generation & API Testing | OpenAPI 3.0 specification, custom automated data generator script (`EP` & 3-point `BVA`), API & integration tests, negative rule rejections, cross-workflow `Quota` consistency verification. |
| **Tawassul** *(Member 3)* | **Area 3:** Use Case Engineering, Playwright E2E, A11y, Security & Performance | 6 use cases (2 per member), Playwright flow automation, keyboard-only navigation test, Lighthouse CI + axe-core accessibility audit & screen remediation, RBAC matrix, OWASP ZAP passive audit, `pip-audit`, and Grafana k6 performance testing. |
| **All Members** | **Shared Test Management & Viva Defense** | Living Test Plan, 3-Point Estimation, $5 \times 5$ Risk Register, Traceability Matrix (RTM), GitHub Issues defect tracking, Root Cause Analysis (5 Whys + Fishbone), Pareto Chart, GQM Weekly Progress, Test Completion Report (Release/Hold), and AI-Use Disclosure Log. |

---

## 📌 Upstream Reference & Baseline

- **Target System:** [pretix](https://github.com/pretix/pretix) — Open-source ticketing & event management system.
- **Upstream Repository:** `https://github.com/pretix/pretix.git`
- **Baseline Commit Hash:** `c0d887738b6cd97f724b926718c55e2ae87c9901`
- **Upstream License:** GNU Affero General Public License v3.0 (with pretix exceptions)
- **Isolation Rule:** All team tests, scripts, and documentation are strictly isolated inside `src/tests/team/` and `docs/sqe/`. Upstream tests are kept untouched.

---

## 🎯 Selected Workflows & Core Business Rules

- **Target Module:** Event Ticketing & Order Management (`src/pretix/base/`, `src/pretix/control/`, `src/pretix/presale/`).
- **Workflow 1 (Organizer/Admin):** Ticket Item & Quota Configuration (`Quota.size`, pricing, capacity definition).
- **Workflow 2 (Customer/Attendee):** Ticket Reservation & Order Checkout (`Order`, `OrderPosition`, `Quota.availability()`).
- **Shared Invariant Record:** `pretix.base.models.Quota` (`Quota.size` & `Quota.availability()`). Workflow 1 establishes capacity; Workflow 2 checks and decrements it.
- **4 Core Business Rules:**
  1. *Boundary / Numerical Limit:* Ticket purchase quantity restricted to $1 \le \text{qty} \le \text{max\_per\_order}$; Quota capacity cannot be oversold.
  2. *Multi-Condition Boolean Decision:* Item purchasable $\iff (\text{active} == \text{True}) \land (\text{from} \le \text{now} \le \text{until}) \land (\text{quota} > 0)$.
  3. *State Machine Transition:* Order transitions: $\text{PENDING} \rightarrow \text{PAID}$, $\text{PENDING} \rightarrow \text{CANCELED}$. Invalid: $\text{CANCELED} \centernot\rightarrow \text{PAID}$.
  4. *Domain Cart Expiration:* Cart positions expire after timeout (30 min), releasing reserved slots back to available quota.

---

## 📁 Repository Directory Structure

```text
pretix/
├── docs/
│   └── sqe/
│       ├── PROJECT_GUIDELINES_AND_REQUIREMENTS.md  # Master syllabus & rubric instructions
│       ├── TEAM_PARTITIONING_AND_AGENT_INSTRUCTIONS.md # AI agent prompt & individual blueprints
│       ├── SQE_Team_Work_Partitioning_Guide.pdf    # Complete formatted reference guide
│       └── SQE_Final_Project Fall 2026.pdf         # Original course assignment specification
│
├── src/
│   ├── pretix/                                     # Target application source code
│   └── tests/
│       └── team/                                   # ALL SQE TEAM TESTS (Isolated)
│           ├── zubair/                             # Area 1: White-box, MCC/MCDC, mutation, CI
│           ├── sami/                               # Area 2: OpenAPI, generator, API tests
│           ├── tawassul/                           # Area 3: Playwright E2E, a11y, security, k6
│           └── shared_management/                  # Test plan, risk register, RCA, RTM, AI log
```

---

## 🌿 Git Workflow & Branch Strategy

- **Mainline Branch (`main`):** Protected baseline. Code enters through Pull Requests only.
- **Member Branches:** `member/zubair`, `member/sami`, `member/tawassul`
- **Feature Branches:** `zubair/feat-...`, `sami/feat-...`, `tawassul/feat-...`
- **CI Quality Gate:** GitHub Actions enforces test suite pass, 100% white-box coverage, SonarQube quality gate, and mutation score thresholds before PR merge.
