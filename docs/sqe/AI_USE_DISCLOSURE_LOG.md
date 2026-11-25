# SE3002 SQE: Generative AI Use Disclosure Record

**Course Requirement (Page 7):**  
*"AI tools are allowed only if you check every output and disclose it in an AI-use record (tool, purpose, output, what you checked or changed). Keep your prompts."*

---

## 📋 Comprehensive AI Usage Log

| # | Date | Team Member | AI Tool & Model | Exact Purpose & Prompt Summary | AI Generated Content | Human Verification & Modifications Made |
| :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| **1** | 2026-11-25 | Zubair | Gemini 2.5 Pro / Antigravity | Analyze `pretix/models/items.py` for Quota boundary edge conditions. | Initial outline of Quota model fields (`size`, `closed`) and helper methods. | Verified against live Django ORM model; identified that `availability()` returns tuple `(status, count)` and requires `scope(organizer=...)`. |
| **2** | 2026-11-25 | Zubair | Claude 3.5 Sonnet / Antigravity | Construct complete 16-row MCC truth table for Business Rule 2 (Item purchasability). | Boolean truth table of 16 combinations for $A \land B \land C \land D$. | Verified truth table against Pretix's `is_available()` and `check_quotas()`. Formulated formal MC/DC independence pairs for conditions A, B, C, D. |
| **3** | 2026-11-25 | Zubair | GPT-4o / Cursor | Draft Pytest fixtures for Pretix transactional test database. | Basic fixtures for Organizer and Event. | Added `with scope(organizer=...)` context managers to prevent `ScopeError`, and added `make_order` and `make_cart_position` factory helpers. |
| **4** | 2026-11-25 | Zubair | Gemini 2.5 Pro / Antigravity | Formulate Custom Mutation Operators for AST in Python. | AST `NodeTransformer` snippet for comparison replacement. | Customized into two distinct domain mutators: `QuotaBoundaryInversionMutator` (operator 1) and `OrderStateMachineBypassMutator` (operator 2). |
| **5** | 2026-11-25 | Zubair | Claude 3.5 Sonnet / Antigravity | Draft GitHub Actions CI workflow for pytest and mutation gate. | Standard GitHub Actions workflow with pip install. | Replaced standard pip with high-speed `uv` setup, added matrix concurrency, and removed any potential `continue-on-error` escape hatches. |
| **6** | 2026-11-25 | Zubair | Gemini 2.5 Pro / Antigravity | Categorize 15 surviving mutants into Equivalent, Missing Test, and Weak Assertion. | Initial list of mutant code lines and classifications. | Audited each mutant against runtime bytecode; added targeted unit tests to kill 10 mutants and defended the 5 truly equivalent ones. |

---

## 🔒 Academic Integrity Declaration
We certify that all AI interactions have been strictly disclosed above. Every piece of code and test assertion generated was manually reviewed, verified against the Pretix domain specifications, executed locally, and tested in the project repository.
