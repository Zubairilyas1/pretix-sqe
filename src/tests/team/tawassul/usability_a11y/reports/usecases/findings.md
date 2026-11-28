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
