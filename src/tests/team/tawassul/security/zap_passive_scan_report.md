# OWASP ZAP Passive Scan Report (W1 and W2)

| | |
| :--- | :--- |
| **Date** | 2026-11-26 |
| **Tool** | OWASP ZAP 2.17.0 (`zaproxy/zap-stable`, daemon mode, passive scan only; no attack traffic) |
| **Driver** | `zap_scan.py`: Playwright (Chromium) with ZAP as its HTTP proxy |
| **Target** | production-like perf server `http://localhost:8000` (`DEBUG=false`, compressed assets; see `../performance/perf_server.py`) |
| **Traffic** | W2: shop → add to cart → checkout (information, payment, review). W1: organizer login → item editor → quota list. |
| **Raw evidence** | `evidence/zap_alerts.json` (every alert instance), `evidence/zap_report.html` (ZAP's own report) |
| **Result** | **156 alert instances, 13 distinct rules: 0 High, 4 Medium, 4 Low, 5 Informational** |

The browser reached the review page, but the final confirmation did not reach the order page through the proxy within 90 s. All checkout pages up to and including the review page were scanned. The order page itself is covered by the header tests in `test_security_headers.py`.

## Triage of every Medium and Low alert

Each alert was checked against the evidence and the pretix source before classification.

| ZAP rule | Risk | URLs | What ZAP saw | Verdict | Reason |
| :--- | :-: | :-: | :--- | :-: | :--- |
| 10003 Vulnerable JS Library | Medium | 2 | Bootstrap **v3.4.1** in the presale and control JS bundles | **Confirmed: A3-D05** | Two advisories affect 3.4.1 and **have no patched 3.x version**: CVE-2024-6485 (XSS via `data-*` attributes, CVSS 6.4) and CVE-2025-1647 (XSS in popover/tooltip, CVSS 5.6). Bootstrap 3 is end-of-life. Exploitation needs attacker-controlled `data-*` or popover content; pretix escapes user content in templates, so the practical risk is lower than the score. |
| 10055 CSP: directive with no fallback | Medium | 10 | CSP defines `default-src`, `script-src`, `form-action` and others, but **no `frame-ancestors`** | **Partly mitigated** | `frame-ancestors` does not fall back to `default-src`. Framing is blocked by `X-Frame-Options: DENY` (verified by `test_clickjacking_protection`), and the shop deliberately allows embedding through the widget. Low practical risk. |
| 10098 Cross-Domain Misconfiguration | Medium | 16 | `Access-Control-Allow-Origin: *` on `/static/…`, fonts, `theme.css` and `jsi18n` | **By design** | 15 of the 16 URLs are public, credential-free static assets (CSS, JS, fonts, `theme.css`) that the embeddable shop widget loads from other sites. The 16th, `/control/login/bad_origin`, is pretix's **anti-phishing beacon** (`pretix/control/views/auth.py:167-184`). The login page's JavaScript POSTs there if the page is served from a foreign origin, such as a phishing clone. It must accept cross-origin POSTs, returns an empty body and only logs. No authenticated data is exposed with `*`. |
| 10202 Absence of Anti-CSRF Tokens | Medium | 7 | `<form method="dialog">` | **False positive** | `method="dialog"` forms only close a `<dialog>` element in the browser and never send a request. Every POST form checked carries `csrfmiddlewaretoken`. |
| 10021 X-Content-Type-Options missing | Low | 26 | no `nosniff` on pages and assets | **Confirmed: A3-D02** | pretix's own `SecurityMiddleware` (`pretix/base/middleware.py:341`) sets CSP and P3P only. Django's `SecurityMiddleware`, which would add `nosniff` and `Referrer-Policy`, is not in `MIDDLEWARE`. Also asserted by `test_no_mime_sniffing` (strict xfail). |
| 10010 Cookie No HttpOnly Flag | Low | 7 | `pretix_csrftoken` | **By design** | The CSRF cookie must be readable by JavaScript, because pretix's AJAX calls send it back in a header. The session cookie `pretix_session` **is** HttpOnly (`test_session_cookie_is_httponly`). |
| 10054 Cookie without SameSite | Low | 11 | `pretix_csrftoken`, `pretix_session` | **Accepted risk (documented design)** | `pretix/helpers/cookies.py` deliberately sends no SameSite over HTTP and `SameSite=None; Secure; Partitioned` over HTTPS so the shop works inside third-party iframes (widget), relying on CSRF tokens instead. Characterised by `test_cookies_samesite_design_over_http`. |
| 10096 Timestamp Disclosure | Low | 4 | 10-digit numbers such as `1795710980` | **False positive** | These are the cart-reservation expiry times shown to the customer by the countdown. They are not secrets. |

**Informational** (no action): 10027 suspicious comments in a bundled JS library, 10031 `require_cookie` reflected into an attribute (escaped, no XSS), 10109 modern web app, 10111 authentication request identified (the login form), 10112 session management identified.

## Headers and cookies (summary)

| Check | Shop | Back office | Test |
| :--- | :-: | :-: | :--- |
| `Content-Security-Policy` | ✅ | ✅ | `test_content_security_policy_present` |
| `X-Frame-Options: DENY` (clickjacking) | ✅ | ✅ | `test_clickjacking_protection` |
| `X-Content-Type-Options: nosniff` | ❌ | ❌ | `test_no_mime_sniffing` (xfail A3-D02) |
| `Referrer-Policy` (protects the order secret in URLs) | ❌ | ❌ | `test_referrer_policy_protects_order_secret` (xfail A3-D02). ZAP does not flag it. |
| `Strict-Transport-Security` | n/a | n/a | only meaningful over HTTPS (test runs on HTTP) |
| Session cookie `HttpOnly` | ✅ | ✅ | `test_session_cookie_is_httponly` |
| Session cookie `SameSite` | design: none on HTTP, `None; Secure; Partitioned` on HTTPS | | `test_cookies_samesite_design_over_http` |
| Session cookie `Secure` | not set on HTTP (expected); set when HTTPS | | — |
| Back-office session pinned to User-Agent | ✅ | | observed in `pretix/helpers/security.py:97` (see `../usability_a11y/a11y_findings.md`) |

## Defects raised
- **A3-D02 (Minor):** missing `X-Content-Type-Options` and `Referrer-Policy`.
  - **Fix:** add `django.middleware.security.SecurityMiddleware` (defaults `nosniff` and `same-origin`), or `add_header` in the nginx config from the pretix install guide.
- **A3-D05 (Minor):** Bootstrap 3.4.1 (end-of-life) with two unpatched XSS advisories.
  - **Fix:** migrate to Bootstrap 5. Short term, audit that no user-controlled data reaches `data-*` attributes or popover options.

## How to reproduce
```bash
cd src
../.venv/Scripts/python tests/team/tawassul/performance/perf_server.py      # in a second terminal
../.venv/Scripts/python tests/team/tawassul/security/zap_scan.py
```


## Open item (27 Nov 2026)
The final order confirmation of W2 still has not passed through the ZAP proxy (see above). A re-run was prepared
(perf instance rebuilt, `seed_perf_event.py`) but the ZAP image could not be pulled: Docker Desktop could not reach
Docker Hub from its VM ("no HTTPS proxy"), and Docker was later stopped. The order page's security headers and
cookies are verified by `test_security_headers.py` instead, so the residual gap is only the passive-scan rule set on
that one page. To close it: start the perf server and run `python tests/team/tawassul/security/zap_scan.py`.
