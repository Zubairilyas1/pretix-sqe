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
