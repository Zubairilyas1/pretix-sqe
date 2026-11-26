# Dependency Vulnerability Audit (pip-audit)

| | |
| :--- | :--- |
| **Date** | 2026-11-26 |
| **Tool** | `pip-audit` (PyPI advisory database and OSV), JSON output |
| **Command** | `.venv/Scripts/python -m pip_audit --format json --progress-spinner off` |
| **Scope** | The environment `pip install -e ".[dev]"` installed for pretix at baseline `c0d887738b6c` |
| **Raw evidence** | `evidence/pip_audit_2026-11-26.json` |
| **Packages checked** | 213. Skipped: 1 (`pretix` itself, installed in editable mode and not on PyPI). |
| **Result** | **3 advisories, all in 1 package: `oauthlib 3.3.1`** |

CVSS v3 scores and severities were taken from the GitHub Advisory Database (`gh api advisories/<GHSA id>`).

## Findings

| # | Package | Installed | Advisory | CVE | Severity (CVSS v3) | Fixed in |
| :-: | :--- | :-: | :--- | :--- | :-: | :-: |
| 1 | oauthlib | 3.3.1 | GHSA-3jp2-3mrg-2vxc | CVE-2026-49272 | **High (8.5)** | 4.0.1 |
| 2 | oauthlib | 3.3.1 | GHSA-xpv3-w29h-x7cv / PYSEC-2026-4114 | CVE-2026-49265 | Medium (6.8) | 4.0.0 |

pip-audit lists finding 2 twice, once under the PyPA id and once under the GHSA alias. Together that is the 3 advisories it reports.

### 1. CVE-2026-49272: bearer token issued for a bogus device code
- **What:** a call to the token endpoint with grant type `urn:ietf:params:oauth:grant-type:device_code` and an invalid `device_code` can obtain a bearer token if the client knows a valid client id.
- **Relevance to pretix:** pretix is an OAuth provider (`django-oauth-toolkit`, `OAUTH2_PROVIDER` in `settings.py:890`). Its configuration supports only the authorization-code response type (`OIDC_RESPONSE_TYPES_SUPPORTED = ["code"]`), so the device grant is **not intentionally offered**. Whether the token endpoint still accepts the device grant type was not tested. Exploitability is therefore **unconfirmed**, but the potential impact (API token theft) is high.
- **Action:** upgrade to oauthlib ≥ 4.0.1. Until then, add a test that posts `grant_type=urn:ietf:params:oauth:grant-type:device_code` to `/api/v1/oauth/token` and expects a rejection.

### 2. CVE-2026-49265: timing side channel in PKCE verifier comparison
- **What:** the PKCE `code_verifier` is compared in non-constant time (CWE-208).
- **Relevance to pretix:** PKCE is supported but optional (`PKCE_REQUIRED: False`; `code_challenge` fields exist since migration `api/0009`). An attacker would need an intercepted authorization code plus many timed requests. **Medium.**
- **Action:** fixed by the same upgrade.

## Upgrade path
- pretix pins `oauthlib==3.3.*` in `pyproject.toml:70`. The fix needs a **major version** change (3.x to 4.0.1), so it cannot be applied by a patch-level update.
- Steps:
  1. Change the pin to `oauthlib>=4.0.1,<5`.
  2. Check that `django-oauth-toolkit` supports oauthlib 4.
  3. Run pretix's OAuth tests (`tests/api/test_oauth.py`).
  4. Run this team's API suite.
- Until upgraded, the risk is recorded in the shared risk register (proposed id **PR-SEC-01**, likelihood 2 × impact 4 = 8).

## Packages with no known vulnerabilities
The other 212 packages had no known advisories on the audit date, including Django 5.2.19, djangorestframework, celery, Pillow, cryptography and requests. This is a point-in-time result: re-run the command before release.
