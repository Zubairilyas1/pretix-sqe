# Usability and Accessibility Findings (WCAG 2.1 AA)

**Tools:**
- axe-core via `axe-playwright-python` (`test_axe_scan.py`, tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`)
- Google Lighthouse 12 (`lighthouse_run.py`, desktop preset)
- Playwright keyboard-only test (`test_keyboard_nav.py`)

**Screens:**

| Screen | Workflow | URL |
| :--- | :-: | :--- |
| Customer shop page | W2 | `/{org}/{event}/` |
| Customer checkout, "Your information" | W2 | `/{org}/{event}/checkout/questions/` |
| Organizer "Create a new product" (logged in) | W1 | `/control/event/{org}/{event}/items/add` |

## 1. Keyboard navigation (`test_keyboard_nav.py`, 3 tests, all pass)
- The whole purchase can be completed with Tab, Shift+Tab, Enter and Space plus typing the email address. The order is stored in the database.
- The email field has autofocus. The optional invoice address is a `<details>` element that opens with **Enter**, and its fields are then reached in visual order (given name, family name, street, ZIP, city, country).
- Bank transfer is selected with **Space**.
- **2.4.7 Focus Visible:** the focused *Add to cart* button shows an outline or box shadow.
- **2.4.1 Bypass Blocks:** the first Tab stop on the shop is a "skip to content" link.

## 2. axe-core results before remediation

| Screen | Rules violated | Elements | Evidence |
| :--- | :-: | :-: | :--- |
| Customer shop page | **0** | 0 | `reports/axe_shop_before.json` |
| Customer checkout | **0** | 0 | `reports/axe_checkout_questions_before.json` |
| Organizer item creation | **5** | **11** | `reports/axe_control_item_add_before.json` |

The customer screens are clean. Every finding is on the organizer back office (W1).

## 3. Findings on the organizer screen (de-duplicated)

| # | axe rule | Impact | WCAG 2.1 criterion | Affected element(s) | User impact | Suggested fix | Status |
| :-: | :--- | :-: | :--- | :--- | :--- | :--- | :-: |
| F1 | `html-has-lang` | serious | 3.1.1 Language of Page (A) | `<html>` | Screen reader may read the page with the wrong language and voice. | `lang="{{ LANGUAGE_CODE }}"` | **fixed** |
| F2 | `image-alt` | critical | 1.1.1 Non-text Content (A) | `.navbar-brand > img` | Logo announced by its file name. | `alt=""` (decorative) | **fixed** |
| F3 | `link-name` | serious | 2.4.4 Link Purpose (A), 4.1.2 Name, Role, Value (A) | 6 × `a.arrow[href="#"]` (sidebar sub-menu toggles) | Six links announced as "link" with no purpose; the sub-menus cannot be found by screen-reader users. | `aria-label` naming the sub-menu | **fixed** |
| F4 | `color-contrast` | serious | 1.4.3 Contrast (Minimum) (AA) | `.context-meta` (event date under the name), `.select2-selection__placeholder` | Low-vision users cannot read the event date or the "No category" placeholder. | Darken the text colour to a ratio of at least 4.5:1. | open (design decision) |
| F5 | `aria-input-field-name` | serious | 4.1.2 Name, Role, Value (A) | `#select2-id_category-container` | The category combobox has no accessible name. | Pass `aria-labelledby` to select2, or label the container. | open (third-party widget) |

F1–F3 come from the shared back-office template, so they affect **every** organizer page. They are recorded together as defect **A3-D03**.

## 4. Before/after remediation (measured)

See `screen_remediation/README.md` for the change: 4 lines in `pretixcontrol/base.html`.

| Measure (organizer "Create a new product" page) | Before | After | Evidence |
| :--- | :-: | :-: | :--- |
| **Lighthouse Accessibility** | **81** | **93** | `reports/lighthouse_control_item_add_{before,after}.report.html` |
| Lighthouse Best Practices | 100 | 100 | same |
| Lighthouse failed accessibility audits | 5 | 2 | `reports/lighthouse_scores_{before,after}.json` |
| axe rules violated | 5 | 2 | `reports/axe_control_item_add_before.json` → `reports/axe_control_item_add.json` |
| axe `html-has-lang` / `image-alt` / `link-name` elements | 1 / 1 / 6 | **0 / 0 / 0** | `test_remediated_rule_stays_fixed_on_organizer_page` (3 cases, pass) |
| Customer shop page, Lighthouse Accessibility | 100 | 100 | `reports/lighthouse_shop_{before,after}.report.html` |

The two remaining audits are F4 (`color-contrast`) and F5 (`aria-input-field-name`), which were deliberately left open (section 3).

## 5. How Lighthouse was run (and a pitfall found)
- Lighthouse 12 runs on the production-like perf server (`DEBUG=false`, compressed assets). The organizer page needs a logged-in session.
- **pretix pins every back-office session to the browser's User-Agent** (`pretix/helpers/security.py:97`) and logs the user out if it changes. This is a good security control against stolen session cookies.
- The first attempts therefore silently audited the **login page**:
  - Lighthouse's desktop preset changes the User-Agent.
  - `--emulatedUserAgent=false` is sent literally as the User-Agent `"false"`. The pretix server log showed `terminated due to user agent change. New agent: "false"`.
- `lighthouse_run.py` therefore:
  - logs in with Chromium's exact User-Agent,
  - passes the cookie and that same User-Agent to Lighthouse,
  - **rejects any report whose final URL is not the intended screen.**
- The invalid early reports were deleted, and only verified reports are kept.


## 6. Usability task tests (one per workflow) - `test_usability_tasks.py` (3 tests, pass)
| Test | Workflow | What is checked |
| :--- | :-: | :--- |
| `test_task_w1_create_quota_reject_then_correct` | W1 | Quota screen opens; size **-5** is refused and the message says *"Value must be greater than or equal to 0."* (explains the correction); nothing is stored; size 25 then shows *"The new quota has been created"* and the quota is in the database |
| `test_task_w1_keyboard_only_quota_form` | W1 | Keyboard only: focus goes name -> size -> product checkbox -> **Save** in that order; Space ticks the product; **Enter submits**; confirmation shown, quota stored |
| `test_task_w2_buy_tickets_reject_then_correct` | W2 | 3 tickets with a limit of 2 per order are refused with *"You cannot select more than 2 items of the product ..."* (names the limit); nothing reserved; 2 tickets complete the checkout, *"Your order has been placed successfully"* is shown, the order has 2 positions and the quota read-back is 2 lower |

Together with `test_keyboard_nav.py` (W2 checkout by keyboard) both workflows are covered by keyboard tests.

## 7. Lighthouse (accessibility, best practices, **SEO**) and axe on the key screen of every use case
Run on the production-like perf server with real sessions (`lighthouse_usecases.py`; organizer logged in, customer
with a real cart). Every report is checked to have audited the intended URL. Raw reports:
`reports/usecases/lighthouse_uc*.report.{html,json}`, `reports/usecases/axe_uc*.json`, `reports/usecases/summary.json`.

An issue reported by both tools for the same rule and element is **counted once** (Lighthouse's accessibility audits
are axe rules; the element is matched on its last selector).

| # | Rule / audit | Element | Screens | Found by | User impact | Proposed fix |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `aria-input-field-name` | `#select2-id_category-container` | uc1 | **both** (counted once) | serious: ARIA input fields must have an accessible name | Give the combobox an accessible name (aria-labelledby pointing at the visible label). |
| 2 | `color-contrast` | `.context-meta` | uc1, uc2 | **both** (counted once) | serious: Elements must meet minimum color contrast ratio thresholds | Darken the text/foreground colour to reach a contrast ratio of at least 4.5:1 (3:1 for large text). |
| 3 | `color-contrast` | `.select2-selection__placeholder` | uc1 | **both** (counted once) | serious: Elements must meet minimum color contrast ratio thresholds | Darken the text/foreground colour to reach a contrast ratio of at least 4.5:1 (3:1 for large text). |
| 4 | `crawlable-anchors` | `div.lb-outerContainer > div.lb-container > div.lb-loader > a.lb-cancel` | uc1, uc2 | Lighthouse (seo) | seo: Links are not crawlable | Use real hrefs on anchors (not '#' or javascript:). |
| 5 | `is-crawlable` | `(page)` | uc4, uc6 | Lighthouse (seo) | seo: Page is blocked from indexing | Intended: back-office and personal order pages are noindex on purpose (no fix). |
| 6 | `is-crawlable` | `http://localhost:8000/robots.txt` | uc1, uc2, uc3, uc6 | Lighthouse (seo) | seo: Page is blocked from indexing | Intended: back-office and personal order pages are noindex on purpose (no fix). |
| 7 | `meta-description` | `(page)` | uc1, uc2, uc3, uc4, uc5, uc6 | Lighthouse (seo) | seo: Document does not have a meta description | Add a <meta name=description> with a summary of the page. |

| Screen | Use case | Accessibility | Best practices | SEO | axe rules / elements |
| :--- | :--- | :-: | :-: | :-: | :-: |
| uc1: Create a new product | UC-1 configure item and quota | 93 | 100 | 50 | 2 / 3 |
| uc2: Shop status (go live) | UC-2 publish event / sales window | 96 | 100 | 50 | 1 / 1 |
| uc3: Checkout - your information | UC-3 checkout | 100 | 100 | 54 | 0 / 0 |
| uc4: Voucher redemption | UC-4 apply voucher | 100 | 100 | 54 | 0 / 0 |
| uc5: Shop page with a sold-out product | UC-5 sold-out category | 100 | 100 | 91 | 0 / 0 |
| uc6: Cancel order | UC-6 cancel pending order | 100 | 100 | 54 | 0 / 0 |

**Reading.** The customer screens (UC-3..UC-6) have no accessibility violation. The two organizer screens keep the two
issues that were deliberately left open (F4 contrast, F5 select2 name; risk PR-A11Y-02). SEO scores are low by design on
back-office and personal order pages (`noindex`, robots.txt); the real SEO gap is the missing `meta description`, which
affects the public shop page (UC-5, SEO 91) as well - proposed fix: render the event's short description as
`<meta name="description">` in the presale base template.
