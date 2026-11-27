# Screen remediation: organizer back office (`pretixcontrol/base.html`)

**Screen:** Organizer → Products → *Create a new product* (`/control/event/{org}/{event}/items/add`), the W1 entry screen.
**Why this screen:** it is where W1 starts. The customer checkout screens had **0** axe violations, while this screen had **5 rules / 11 elements** (`../reports/axe_control_item_add_before.json`).

The three defects below are in the shared layout template `src/pretix/control/templates/pretixcontrol/base.html`, so the fix applies to **every** back-office page, not only this one.

| # | axe rule | WCAG 2.1 | Element | Problem for users | Fix |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | `html-has-lang` | 3.1.1 Language of Page (A) | `<html>` | Screen readers guess the language and may read English text with the wrong voice and pronunciation. | `<html lang="{{ LANGUAGE_CODE }}">` |
| 2 | `image-alt` | 1.1.1 Non-text Content (A) | `.navbar-brand > img` (pretix logo) | The image is announced by its file name. The link next to it already has the instance name as text, so the image is decorative. | `alt=""` (decorative; the link text names the target) |
| 3 | `link-name` | 2.4.4 Link Purpose, 4.1.2 Name, Role, Value (A) | 6 × `a.arrow[href="#"]` in the sidebar | Screen readers announce "link" with no name, so users cannot tell that the arrow expands the *Products*, *Orders* and other sub-menus. | `aria-label="{% blocktrans %}Show/hide {{ label }} submenu{% endblocktrans %}"` plus `aria-hidden="true"` on the icon |

Not fixed here, and reported in `../a11y_findings.md`:
- `color-contrast` on `.context-meta` and the select2 placeholder. This needs a design-colour decision.
- `aria-input-field-name` on the select2 widget. This is in third-party JavaScript.

**Verification:**
- axe before/after: `../reports/axe_control_item_add_before.json` → `../reports/axe_control_item_add.json`
- Lighthouse before/after: `../reports/lighthouse_*_{before,after}.report.html`
- Regression test: `test_axe_scan.py::test_remediated_rule_stays_fixed_on_organizer_page` (one case per rule)

The template change itself is in a separate commit ("fix(a11y): …") so its diff can be reviewed on its own.
