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
| **7** | 2026-11-25 | Sami | Claude Opus 5.5 / Claude Code | Read project brief and team docs; analyse pretix API source (`api/urls.py`, `serializers/{item,cart,order}.py`, `views/{item,cart,order}.py`); write Area 2 master plan. | `SAMI_MASTER_EXECUTION_PLAN.md`; finding that the planned `cart/add/` and `order/create/` routes do not exist. | Automated: spec paths resolved against pretix URL conf (`test_openapi_spec.py`). **Pending Sami review:** route table and EP/BVA input table against the source. |
| **8** | 2026-11-25 | Sami | Claude Opus 5.5 / Claude Code | Write OpenAPI 3.0 spec for the 19 tested operations from the serializer source. | `openapi/pretix_orders_api.yaml` | Automated: spec validator, examples validated against schemas, all paths resolve. First test run exposed 6 spec errors (nullable/required fields) that were corrected. **Pending Sami review:** every constraint and its source line. |
| **9** | 2026-11-25 | Sami | Claude Opus 5.5 / Claude Code | Build generator that reads the spec and emits EP classes and 3-point BVA; unit tests; regeneration demo. | `generator/generate_test_data.py`, `test_generator.py`, `regeneration_demo/` | Automated: 31 generator/spec tests; demo `--verify` confirms the predicted failure. A generator bug (type classes on the synthetic quantity field) was found by the API run and fixed. **Pending Sami review:** be able to explain each derivation rule (viva). |
| **10** | 2026-11-25 | Sami | Claude Opus 5.5 / Claude Code | Write API tests (EP/BVA, Rule 1-3, transitions, idempotency, auth, cross-workflow, coverage) and triage failures. | `api/*.py`, `endpoint_weaknesses.md` (W-01 to W-08) | Automated: 243 passed, 17 strict xfail. The 58 first-run failures were each classified (own test error / spec error / real weakness) and the reasoning recorded in `SAMI_TASK_TRACKER.md`. **Pending Sami review:** reproduce each weakness and confirm severity before filing GitHub Issues. |

---

## 🔒 Academic Integrity Declaration
We certify that all AI interactions have been strictly disclosed above. Every piece of code and test assertion generated was manually reviewed, verified against the Pretix domain specifications, executed locally, and tested in the project repository.
