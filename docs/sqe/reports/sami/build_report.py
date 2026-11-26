"""
Builds SAMI_AREA2_REPORT.docx (Times New Roman 12 pt, black and white).

    .venv/Scripts/python docs/sqe/reports/sami/build_report.py

Figures are real screenshots taken on 26 Nov 2026 and stored in ./figures.
"""
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
OUT = HERE / "SAMI_AREA2_REPORT.docx"
FONT = "Times New Roman"
BLACK = RGBColor(0, 0, 0)

doc = Document()
_fig = [0]
_tab = [0]


# ---------------------------------------------------------------- styles
def _font(style_or_run, size=None, bold=None, italic=None, name=FONT):
    f = style_or_run.font
    f.name = name
    f.color.rgb = BLACK
    if size:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    el = style_or_run.element if hasattr(style_or_run, "element") else style_or_run._element
    rpr = el.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(a), name)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rfonts.get(qn(a)) is not None:
            del rfonts.attrib[qn(a)]


st = doc.styles
_font(st["Normal"], 12)
st["Normal"].paragraph_format.space_after = Pt(6)
st["Normal"].paragraph_format.line_spacing = 1.15
for name, size, before, after in (("Title", 20, 0, 12), ("Heading 1", 14, 18, 8),
                                  ("Heading 2", 12, 12, 6), ("Heading 3", 12, 10, 4)):
    s = st[name]
    _font(s, size, bold=True, italic=False)
    pf = s.paragraph_format
    pf.space_before, pf.space_after, pf.keep_with_next = Pt(before), Pt(after), True
for name in ("List Bullet", "List Number", "Caption"):
    _font(st[name], 12)
_font(st["Caption"], 11, bold=False, italic=True)

sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Cm(2.54))


# ---------------------------------------------------------------- helpers
def _runs(p, text, size=None):
    """Write text with **bold** and `code` spans."""
    import re
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**"):
            r = p.add_run(part[2:-2])
            _font(r, size, bold=True)
        elif part.startswith("`"):
            r = p.add_run(part[1:-1])
            _font(r, (size or 12) - 1.5, name="Courier New")
        else:
            r = p.add_run(part)
            _font(r, size)
    return p


def para(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=None, after=None):
    """Body paragraph."""
    p = doc.add_paragraph()
    p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return _runs(p, text, size)


def bullets(items, style="List Bullet"):
    for it in items:
        p = doc.add_paragraph(style=style)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(3)
        _runs(p, it)


def h(text, level=1):
    p = doc.add_heading(level=level)
    r = p.add_run(text)
    _font(r, None, bold=True)
    return p


def code(lines):
    for i, ln in enumerate(lines):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.space_after = Pt(6 if i == len(lines) - 1 else 0)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(ln)
        _font(r, 10, name="Courier New")


def _shade(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def _repeat_header(row):
    trpr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trpr.append(el)


def table(caption, header, rows, widths, size=10.5):
    _tab[0] += 1
    cp = doc.add_paragraph(style="Caption")
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp.paragraph_format.keep_with_next = True
    cp.paragraph_format.space_before = Pt(6)
    _font(cp.add_run(f"Table {_tab[0]}: {caption}"), 11, italic=True)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, txt in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        _runs(c.paragraphs[0], f"**{txt}**", size)
        _shade(c, "D9D9D9")
    _repeat_header(t.rows[0])
    for row in rows:
        cells = t.add_row().cells
        for i, txt in enumerate(row):
            cells[i].text = ""
            _runs(cells[i].paragraphs[0], str(txt), size)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                p.paragraph_format.keep_with_next = row is not t.rows[-1]
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.0
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return _tab[0]


def figure(fname, caption, width_cm=16.0):
    _fig[0] += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIG / fname), width=Cm(width_cm))
    cp = doc.add_paragraph(style="Caption")
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(cp.add_run(f"Figure {_fig[0]}: {caption}"), 11, italic=True)
    return _fig[0]


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def _field(paragraph, instr, size=11):
    r = paragraph.add_run()
    _font(r, size)
    for kind, text in (("begin", None), (None, instr), ("separate", None), (None, "1"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
            r._r.append(el)
        elif text == instr:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = f" {instr} "
            r._r.append(el)
        else:
            el = OxmlElement("w:t")
            el.text = text
            r._r.append(el)


# ---------------------------------------------------------------- title page
for _ in range(3):
    doc.add_paragraph()
para("National University of Computer and Emerging Sciences, Islamabad", WD_ALIGN_PARAGRAPH.CENTER, 14)
para("SE3002 Software Quality Engineering, Fall 2026", WD_ALIGN_PARAGRAPH.CENTER, 13, after=36)
tp = doc.add_paragraph(style="Title")
tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
_font(tp.add_run("Final Project Report"), 22, bold=True)
para("**Area 2: API Testing and Test Data Generation**", WD_ALIGN_PARAGRAPH.CENTER, 16)
para("System under test: pretix (open-source event ticketing system)", WD_ALIGN_PARAGRAPH.CENTER, 13, after=48)

meta = doc.add_table(rows=0, cols=2)
meta.alignment = WD_TABLE_ALIGNMENT.CENTER
for k, v in (("Author", "Sami (Member 2, Area 2 owner)"),
             ("Student ID", "i243070"),
             ("Repository", "github.com/Zubairilyas1/pretix-sqe"),
             ("pretix baseline", "c0d887738b6cd97f724b926718c55e2ae87c9901"),
             ("Work merged in", "Pull request #12 (member/sami into main)"),
             ("Report date", "26 November 2026")):
    c = meta.add_row().cells
    _runs(c[0].paragraphs[0], f"**{k}**")
    _runs(c[1].paragraphs[0], v)
    c[0].width, c[1].width = Cm(4.5), Cm(10)
page_break()

# ---------------------------------------------------------------- contents
tc = doc.add_paragraph()
_font(tc.add_run("Table of Contents"), 14, bold=True)
_field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
page_break()

# footer with page numbers, header with short title (from page 1 on)
for s in doc.sections:
    s.different_first_page_header_footer = True
    fp = s.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(fp.add_run("Page "), 10)
    _field(fp, "PAGE", 10)
    hp = s.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _font(hp.add_run("SE3002 SQE Final Project | Area 2 Report (Sami)"), 10, italic=True)

# ---------------------------------------------------------------- 1
h("1. Executive Summary")
para("This report covers Area 2 of the team project: API testing and test data generation for pretix. "
     "I wrote an OpenAPI 3.0 specification for the 19 API operations used by our two workflows, built a "
     "generator that turns the constraints in that specification into equivalence-partition (EP) and "
     "three-point boundary value (BVA) test cases, and executed those cases, together with business-rule, "
     "state-transition, duplicate-request, authorisation and cross-workflow tests, against the real pretix API.")
para("The final run produced **243 passed and 17 expected failures (strict xfail)**, with flake8 reporting no "
     "findings. The 17 expected failures are not test errors: each one documents a confirmed weakness in "
     "pretix. In total **eight endpoint weaknesses (W-01 to W-08)** were found, six of them rated Major. "
     "The most important are that the order API ignores the item sale window and the per-order limits "
     "(Business Rules 1 and 2), that negative prices are accepted, and that a retried order request without an "
     "idempotency key creates a second order.")
para("All work was developed on stacked feature branches and merged into `main` through pull request #12. "
     "Every figure in this report is a real screenshot taken on 26 November 2026 from the actual runs.")

# ---------------------------------------------------------------- 2
h("2. Introduction")
h("2.1 Purpose and scope", 2)
para("The project brief asks the team to test two related workflows of an open-source information system "
     "across three areas. Area 2 (my area) covers API testing and data generation: an API specification, "
     "a data generator driven by that specification, API and integration tests, and checks on the state that "
     "the two workflows share. Static analysis, white-box and mutation testing (Area 1) and usability, "
     "accessibility, security and performance (Area 3) are reported by my teammates.")
h("2.2 System under test", 2)
para("pretix is a Django and Django REST Framework ticketing system. The team pinned upstream commit "
     "`c0d887738b6c` as the baseline. All tests run against that code using pretix's own test settings "
     "(SQLite database) and pytest-django.")
h("2.3 Workflows and the shared record", 2)
table("Workflows under test",
      ["Workflow", "Actor", "API steps", "Effect on the shared record"],
      [["W1: set up sales", "Organizer", "create item, create or patch quota", "writes `Quota.size` (capacity)"],
       ["W2: purchase", "Customer via API client", "reserve cart position, create order, change order state",
        "consumes `available_number`; cancel or expire releases it"]],
      [3.2, 3.0, 5.0, 4.8])
para("The **Quota** is the record both workflows touch. W1 decides how many seats exist; W2 takes them. "
     "Many of the tests in this report check that the quota stays consistent whatever sequence of W1 and W2 "
     "actions is applied.")
h("2.4 Business rules tested", 2)
bullets(["**Rule 1 (capacity):** an order or cart reservation is accepted only if the requested quantity is "
         "within the quota's available number, and within the item's `min_per_order` / `max_per_order`.",
         "**Rule 2 (purchasable item):** an item can be bought only if it is active, belongs to a quota and is "
         "inside its sale window (`available_from` to `available_until`).",
         "**Rule 3 (order lifecycle):** an order moves only through the allowed state changes between pending (n), "
         "paid (p), expired (e) and canceled (c), and only pending and paid orders hold a seat."])

# ---------------------------------------------------------------- 3
h("3. Test Basis and a Correction to the Plan")
para("The team's partitioning guide planned tests against `cart/add/` and `order/create/`. Reading pretix's "
     "`api/urls.py` and the item, cart and order views showed that **these routes do not exist**. The real API, "
     "under `/api/v1/organizers/{org}/events/{event}/`, uses `items/`, `quotas/`, `cartpositions/`, `orders/` "
     "and one action route per order state change. The plan was rebased on the real routes before any test "
     "was written, and the OpenAPI test `test_spec_path_exists_in_pretix_url_conf` now resolves every path "
     "in the specification against pretix's URL configuration, so this mistake cannot come back.")
para("The test basis for each constraint is the pretix source itself (model fields and serializers), with "
     "the file and line recorded in the specification and in the weakness report.")

# ---------------------------------------------------------------- 4
h("4. Test Environment and Tools")
table("Environment", ["Item", "Value"],
      [["Operating system", "Windows 10 Pro (build 19045)"],
       ["Python / Django", "Python 3.12.10, Django 5.2.19"],
       ["Test runner", "pytest 9.2.0, pytest-django 4.14.0, pytest-xdist 3.8.0 (4 workers)"],
       ["Database", "SQLite (pretix test settings, `tests.settings`)"],
       ["Spec validation", "openapi-spec-validator; response checks with `OAS30Validator`"],
       ["Lint", "flake8 (project configuration)"],
       ["Version control", "Git, GitHub (feature branches and pull requests)"],
       ["Authentication in tests", "pretix team API tokens: full-permission, read-only and anonymous clients"]],
      [4.5, 11.5])

# ---------------------------------------------------------------- 5
h("5. OpenAPI 3.0 Specification")
para("File: `src/tests/team/sami/openapi/pretix_orders_api.yaml`. pretix does not ship an OpenAPI document, so "
     "I wrote one for exactly the operations our workflows use. Each request schema carries the constraints "
     "taken from the serializer and model, and an `example` that is used as the valid baseline payload by "
     "the tests.")
ops = [("GET", "items/", "listItems"), ("POST", "items/", "createItem"), ("GET", "quotas/", "listQuotas"),
       ("POST", "quotas/", "createQuota"), ("GET", "quotas/{id}/", "getQuota"),
       ("PATCH", "quotas/{id}/", "patchQuota"), ("GET", "quotas/{id}/availability/", "getQuotaAvailability"),
       ("GET", "cartpositions/", "listCartPositions"), ("POST", "cartpositions/", "createCartPosition"),
       ("DELETE", "cartpositions/{id}/", "deleteCartPosition"), ("GET", "orders/", "listOrders"),
       ("POST", "orders/", "createOrder"), ("GET", "orders/{code}/", "getOrder"),
       ("POST", "orders/{code}/mark_paid/", "markOrderPaid"),
       ("POST", "orders/{code}/mark_canceled/", "markOrderCanceled"),
       ("POST", "orders/{code}/mark_expired/", "markOrderExpired"),
       ("POST", "orders/{code}/mark_pending/", "markOrderPending"),
       ("POST", "orders/{code}/mark_refunded/", "markOrderRefunded"),
       ("POST", "orders/{code}/reactivate/", "reactivateOrder")]
table("The 19 specified operations (paths are relative to /api/v1/organizers/{org}/events/{event}/)",
      ["#", "Method", "Path", "operationId", "Workflow"],
      [[i + 1, m, f"`{p}`", o, "W1" if p.startswith(("items", "quotas")) else "W2"]
       for i, (m, p, o) in enumerate(ops)],
      [1.0, 2.0, 6.5, 4.5, 2.0], size=10)
table("Key constraints in the specification and their source",
      ["Field", "Constraint", "Source in pretix"],
      [["Item `default_price`", "0 to 99999999999.99, `multipleOf` 0.01", "`Item.default_price` DecimalField(13,2)"],
       ["Item `name`", "1 to 255 characters (default locale)", "`Item.name` I18nCharField(max_length=255)"],
       ["Item `min_per_order` / `max_per_order`", "integer, minimum 0", "`Item` model fields"],
       ["Quota `size`", "0 to 2147483647, nullable (null = unlimited)", "`Quota.size` PositiveIntegerField"],
       ["Quota `name`", "1 to 200 characters", "`Quota.name` CharField(max_length=200)"],
       ["Order `code`", "5 to 16 characters, charset A-Z without I and O, digits", "`OrderCreateSerializer.code`"],
       ["Order `email`", "email format, at most 254 characters", "EmailField"],
       ["Order `positions`", "1 to 500 items; business limit = available seats", "`PRETIX_MAX_ORDER_SIZE` = 500"],
       ["Cart `cart_id`", "must end with `@api`, nullable", "cart position serializer"]],
      [4.2, 6.0, 5.8], size=10)
para("The specification is itself tested (17 tests): it must be valid OpenAPI 3.0, every operationId must be "
     "unique, every example must validate against its own schema, and every path must resolve in pretix's "
     "URL configuration (Figure 1).")

# ---------------------------------------------------------------- 6
h("6. EP and BVA Test Data Generator")
para("File: `src/tests/team/sami/generator/generate_test_data.py`. The generator reads the specification, "
     "inlines all `$ref` references, walks every request field and derives test cases from its keywords. "
     "It writes `test_data.json`. **No boundary value is hard-coded in any test**: the API tests only load "
     "this file, so a change to the specification flows straight into the tests.")
table("Derivation rules (specification keyword to generated cases)",
      ["Keyword", "Cases generated"],
      [["`minimum` / `maximum`", "BVA min-1, min, min+1 and max-1, max, max+1; EP below_min, valid, above_max"],
       ["`multipleOf`", "BVA step size (0.01 for prices); EP too_many_decimals"],
       ["`minLength` / `maxLength`", "BVA on string length; EP too_short, too_long"],
       ["`minItems` / `maxItems`", "BVA on list length (order positions)"],
       ["`pattern`, `format: email`, `enum`", "EP pattern_mismatch, invalid_format, one case per enum value, not_in_enum"],
       ["`type`, `nullable`, `required`", "EP wrong_type, null, missing"],
       ["`x-business-limit`", "BVA relative to the live available number: limit-1, limit, limit+1"]],
      [5.0, 11.0])
para("Each case has an identifier of the form `operation.field.technique.class` (for example "
     "`createOrder.code.BVA.len_max+1`), the value, and the expected result (accept or reject). The file "
     "also stores a SHA-256 hash of the specification it was generated from.")
table("Generated cases per operation",
      ["Operation", "EP", "BVA", "Total"],
      [["createItem", 29, 18, 47], ["createQuota", 15, 12, 27], ["patchQuota", 9, 6, 15],
       ["createCartPosition", 12, 9, 21], ["createOrder", 31, 18, 49], ["markOrderPaid", 4, 0, 4],
       ["markOrderCanceled", 4, 0, 4], ["**Total**", "**104**", "**63**", "**167**"]],
      [6.0, 3.0, 3.0, 3.0])
para("The generator has 15 unit tests of its own: each derivation rule, determinism (same specification "
     "gives the same file), `$ref` resolution, coverage of every request operation, and "
     "`test_committed_test_data_matches_spec`, which fails if someone edits the specification without "
     "regenerating the data. Figure 1 shows these tests and the specification tests passing, together with "
     "a clean flake8 run; Figure 2 shows part of the generator's own summary output.")
figure("01_spec_generator_tests.png", "Specification and generator tests: 32 passed (real console screenshot).")
figure("02_generator_summary.png", "Generator summary: BVA cases with value and expected result (real console screenshot).", 13.5)

# ---------------------------------------------------------------- 7
h("7. API Test Design")
h("7.1 EP and BVA tests (153 tests)", 2)
para("`test_api_ep_bva.py` creates one test per generated case for `createItem`, `createQuota`, `patchQuota`, "
     "`createCartPosition` and `createOrder`. The test copies the valid example payload, applies the case "
     "(set a value, remove a field, or build a list of the required length) and sends it. For an **accept** "
     "case it checks the response status and that the stored value equals the sent value. For a **reject** "
     "case it checks for HTTP 400, that the error names the field, and that **nothing was written** to the "
     "database. Where pretix accepts a value the specification says must be rejected, the case is listed in "
     "`KNOWN_DEVIATIONS` with its weakness id and marked `xfail(strict=True)`.")
h("7.2 Business rules, state transitions, duplicates and authorisation (50 tests)", 2)
para("`test_negative_rules.py` covers the rules that are not simple field constraints:")
bullets(["**Rule 1:** order quantity and cart reservations at available-1, available and available+1; "
         "`max_per_order` and `min_per_order` at the boundary (max-1, max, max+1 and min-1, min, min+1).",
         "**Rule 2:** inactive item, item without a quota, sale already ended, sale not yet started.",
         "**Rule 3:** all 9 allowed and 11 disallowed state changes (Table 7), checking both the new state and the "
         "quota afterwards, plus reactivation of a canceled order after the quota has sold out.",
         "**Duplicates:** the same order code twice is rejected; the same `X-Idempotency-Key` returns the first "
         "response; double `mark_paid` creates one payment; a retry without a key creates a second order (W-03).",
         "**Authorisation:** a read-only token can read but gets 403 on every write; anonymous requests get 401; "
         "an unknown order code gets 404."])
table("Order state changes tested (Rule 3)",
      ["From", "Allowed action (to state)", "Disallowed actions (pretix error)"],
      [["n (pending)", "mark_paid (p), mark_canceled (c), mark_expired (e)",
        "mark_refunded, mark_pending (not paid); reactivate (not allowed)"],
       ["p (paid)", "mark_pending (n), mark_canceled (c), mark_refunded (c)",
        "mark_paid (not pending or expired); mark_expired (not pending); reactivate"],
       ["e (expired)", "mark_paid (p), mark_canceled (c)", "mark_refunded (not paid); mark_expired (not pending)"],
       ["c (canceled)", "reactivate (n)", "mark_paid, mark_canceled, mark_refunded"]],
      [2.6, 6.2, 7.2], size=10)
para("Idempotency tests run with `django_db(transaction=True)` because pretix's `IdempotencyMiddleware` "
     "opens a durable transaction that cannot be nested inside the normal test transaction.")
h("7.3 API coverage (20 tests)", 2)
para("`test_api_coverage.py` keeps a `COVERED` list of operationIds that must equal the set of operations "
     "in the specification (`test_every_spec_operation_is_covered`), and calls each of the 19 operations "
     "on its success path, validating the response body against the specification's response schema. "
     "**API operation coverage is therefore 19 of 19 (100%).**")

# ---------------------------------------------------------------- 8
h("8. Cross-Workflow Integration Testing")
para("`test_cross_workflow.py` drives W1 and W2 against the same quota and checks the shared record after every "
     "step, through both the API (`quotas/{id}/availability/`) and the database. The main scenario:")
table("Main cross-workflow scenario (quota size 5)",
      ["Step", "Action", "Expected available seats", "Checked"],
      [["1", "W1 creates quota with size 5", "5", "total 5"],
       ["2", "W2 orders 3 seats (pending)", "2", "pending 3, available 2"],
       ["3", "W2 tries to order 3 more", "2 (rejected, nothing changes)", "HTTP 400, still 2"],
       ["4", "W2 reserves 1 cart position", "1", "pending 3, cart 1"],
       ["5", "Cart position deleted", "2", "reservation released"],
       ["6", "W2 cancels the order", "5", "all seats released"]],
      [1.3, 6.0, 4.7, 4.0])
para("Further tests check that shrinking the quota below the sold number blocks new orders, that a closed quota "
     "blocks W2 even with free capacity, that paid and pending orders both hold seats while expired orders do "
     "not, and that the API and the database always report the same number (Figure 3).")
figure("04_cross_workflow.png", "Cross-workflow tests: 5 passed (real console screenshot).")

# ---------------------------------------------------------------- 9
h("9. Test Execution Results")
table("Tests per file (final run, 26 November 2026)",
      ["Test file", "Tests", "Result"],
      [["openapi/test_openapi_spec.py", 17, "17 passed"],
       ["generator/test_generator.py", 15, "15 passed"],
       ["api/test_api_ep_bva.py", 153, "141 passed, 12 xfailed"],
       ["api/test_negative_rules.py", 50, "45 passed, 5 xfailed"],
       ["api/test_cross_workflow.py", 5, "5 passed"],
       ["api/test_api_coverage.py", 20, "20 passed"],
       ["**Total**", "**260**", "**243 passed, 17 xfailed**"]],
      [7.5, 2.5, 6.0])
para("Figure 4 shows the end of the full run with the reason for every expected failure. Each reason starts "
     "with the weakness id, so the run itself is the evidence for Section 10. Because the markers are strict, "
     "if pretix ever fixes one of these weaknesses the test reports XPASS and the suite fails, which forces "
     "the weakness list to be updated.")
figure("03_full_suite.png", "Full Area 2 suite: 243 passed, 17 xfailed, each xfail naming its weakness (real console screenshot).")

# ---------------------------------------------------------------- 10
h("10. Endpoint Weaknesses Found")
para("Full details (evidence test, root cause with source line, impact and fix) are in "
     "`src/tests/team/sami/api/endpoint_weaknesses.md` (Figure 5). Risk ids are proposed entries for the "
     "team's shared risk register; risk = likelihood x impact on a 1 to 5 scale.")
table("Summary of weaknesses",
      ["ID", "Weakness", "Root cause", "Severity", "Risk (LxI)"],
      [["W-01", "Negative item price accepted", "`Item.default_price` has no minimum validator", "Major", "PR-API-01 (3x4=12)"],
       ["W-02", "Negative cart-position price accepted", "cart serializer copies `price` without a bound check", "Major", "PR-API-01"],
       ["W-03", "Retry without idempotency key creates a duplicate order", "header is optional in `IdempotencyMiddleware`", "Major", "PR-API-02 (3x4=12)"],
       ["W-04", "Item name not validated (empty, missing locale, over 255)", "i18n field does not enforce length", "Minor", "PR-API-03 (3x2=6)"],
       ["W-05", "Quota size above the 32-bit range accepted", "no `max_value` on `Quota.size`", "Major", "PR-API-04 (2x4=8)"],
       ["W-06", "`with_availability` ignored on quota detail", "only `list` computes availability", "Minor", "PR-API-05 (4x2=8)"],
       ["W-07", "Order API ignores the sale window (Rule 2)", "`OrderCreateSerializer` skips `available_from/until`", "Major", "PR-API-06 (3x4=12)"],
       ["W-08", "Order API ignores min/max per order (Rule 1)", "`OrderCreateSerializer` skips per-order limits", "Major", "PR-API-06"]],
      [1.4, 4.6, 5.0, 1.8, 3.2], size=10)
h("10.1 Impact of the Major weaknesses", 2)
bullets(["**W-01 / W-02:** a misconfigured product or API client can create negative prices, so the shop pays the "
         "buyer and reports become wrong. Fix: `MinValueValidator(0)` on the field or a check in the serializer.",
         "**W-03:** a client that retries after a network timeout double-books and double-charges. Fix: make the "
         "idempotency header mandatory for `POST orders/`, or document it clearly for integrators.",
         "**W-05:** on PostgreSQL (production) the same request would fail in the database and return 500 instead "
         "of a clear 400. This was observed on SQLite only; the PostgreSQL behaviour is a stated assumption.",
         "**W-07 / W-08:** box-office and reseller integrations can sell after sales close and bypass "
         "per-customer limits (anti-scalping). The shop front end enforces both rules; the API does not. This "
         "may be intentional for trusted integrations, but it is not documented, so the triage is "
         "\"document, then decide\". Suggested fix: enforce the rules unless `force: true` is sent."])
h("10.2 Controls verified (no weakness found)", 2)
bullets(["The quota cannot be oversold through orders or cart reservations (BVA 9/10/11 on size 10).",
         "Rejected requests leave the shared record unchanged.",
         "Inactive items and items without a quota are refused.",
         "All 9 allowed and 11 disallowed order state changes behave as specified; reactivation re-checks capacity.",
         "The same idempotency key or order code never creates a duplicate; double `mark_paid` creates one payment.",
         "Read-only tokens cannot write (403); anonymous requests get 401; unknown codes get 404.",
         "Order code length and charset, and the 1 to 500 position limit, are enforced."])
figure("09_weaknesses_github.png", "The weakness report as published on GitHub in main (real browser screenshot).", 11.0)

# ---------------------------------------------------------------- 11
h("11. Specification Change and Regeneration Demonstration")
para("The brief requires showing that changed constraints regenerate the test data. "
     "`regeneration_demo/run_demo.py` copies the specification, applies two realistic business changes, "
     "regenerates the data, reports every changed case and, with `--verify`, reruns the affected API tests "
     "on the new data. The real specification is never modified.")
table("Constraint changes applied",
      ["Change", "Constraint", "Before", "After"],
      [["C1", "`OrderCreate.code.maxLength` (shorter order codes)", "16", "12"],
       ["C2", "`QuotaCreate.size.maximum` (venue capacity cap)", "2147483647", "1000"]],
      [1.8, 8.2, 3.0, 3.0])
para("Result: **exactly 9 of 167 cases change** (4 for the code length, 5 for the quota size) and no other case "
     "is affected, which shows the generator depends on each constraint field by field. When the tests are "
     "rerun on the new data, `createOrder.code.BVA.len_max+1` (now 13 characters, expected reject) **fails**, "
     "because pretix still accepts codes up to 16 characters. That failure is the expected "
     "specification-versus-implementation mismatch the exercise is meant to expose. The quota-size cases "
     "report as the already known W-05 (Figure 6).")
figure("05_regeneration_demo.png", "Regeneration demo with --verify: 9 cases changed, 1 predicted failure observed (real console screenshot).")
para("In the viva the same steps can be done by hand: edit one constraint in the YAML file, run the generator, "
     "inspect `git diff test_data.json`, and rerun the tests.")

# ---------------------------------------------------------------- 12
h("12. First-Run Defect Triage")
para("The first full run had 58 failures. Each was classified before anything was marked as a pretix weakness:")
table("Classification of the 58 first-run failures",
      ["Cause", "Count", "Action"],
      [["My test error: read availability from the quota detail endpoint", "35",
        "switched to `quotas/{id}/availability/`; the trap itself recorded as W-06"],
       ["Specification error: pretix deliberately allows the value (quota without items, null `cart_id`, `locale`, `send_email`, ...)", "6", "specification corrected"],
       ["Generator bug: type classes on the synthetic quantity field", "2", "generator fixed"],
       ["Missing fixture in my tests", "3", "fixture dependency added"],
       ["Real pretix weaknesses", "12", "W-01, W-02, W-04, W-05 (later W-07, W-08 from new tests)"]],
      [7.5, 1.5, 7.0], size=10)
para("The lesson is that a failing test is first a question about the test. Two thirds of the first failures "
     "came from my own assumptions, not from pretix.")

# ---------------------------------------------------------------- 13
h("13. Configuration Management")
para("Work was done on a member branch with one feature branch per deliverable, each built on the previous one. "
     "All branches were pushed and merged into the protected `main` through pull request #12 (Figures 7 to 9).")
table("Branches and commits",
      ["Branch", "Commit", "Content"],
      [["member/sami", "b7550d351", "Master plan and task tracker"],
       ["sami/feat-openapi-spec", "62d788f11, 8661e5022", "OpenAPI specification, then corrections"],
       ["sami/feat-test-data-generator", "566481031", "Generator and its unit tests"],
       ["sami/feat-api-ep-bva", "144d2a040", "EP/BVA API tests and coverage suite"],
       ["sami/feat-api-negative-rules", "2f5d96ef8", "Rules, transitions, duplicates, authorisation"],
       ["sami/feat-cross-workflow", "ab3c5deca", "Cross-workflow tests and weakness report"],
       ["sami/feat-regeneration-demo", "d36eee675", "Regeneration demonstration"],
       ["sami/docs-shared-management", "bbd29933a, c72af59ec", "Tracker and AI-use log"],
       ["sami/docs-area2-report", "(this report)", "This report and its figures"]],
      [5.6, 4.0, 6.4], size=10)
figure("06_git_history.png", "Commit history of member/sami and the pushed Sami branches (real console screenshot).")
figure("07_pr12_top.png", "Pull request #12 merged into main (real browser screenshot).", 13.0)
figure("08_pr12_commits.png", "The 10 commits in pull request #12 (real browser screenshot).", 13.0)

# ---------------------------------------------------------------- 14
h("14. Limitations and Threats to Validity")
bullets(["Tests run on SQLite. Behaviour that depends on the database (W-05 in particular) may differ on "
         "PostgreSQL, which pretix uses in production.",
         "The specification was written from the source code, not from an official contract; where pretix "
         "behaviour looks deliberate (W-07, W-08), the finding is a documented difference, not proof of a bug.",
         "Tests were run on Windows. A harmless `PermissionError` on a temporary log file appears at the end of "
         "each run; it does not affect results.",
         "Performance and concurrency of the API are outside Area 2 and are covered in Area 3."])

# ---------------------------------------------------------------- 15
h("15. Use of Generative AI")
para("As the brief requires, AI use is recorded in the team's AI-use disclosure log "
     "(`shared_management/AI_USE_DISCLOSURE_LOG.md`, rows 7 to 10). Claude (Claude Code) was used to read the pretix source, draft the plan, the "
     "specification, the generator, the tests, the weakness report and this report. Every output was "
     "executed: the specification, generator and tests are checked by the automated suite described above, "
     "and the 58 first-run failures were classified one by one rather than accepted. In addition, I am "
     "personally reviewing each constraint against its source line, each derivation rule and each weakness; "
     "the log marks these rows as pending that review until it is complete.")

# ---------------------------------------------------------------- 16
h("16. Conclusion")
para("Area 2 delivered a validated OpenAPI specification for all 19 operations of the two workflows, a "
     "specification-driven EP/BVA generator producing 167 cases, and 260 automated tests that cover every "
     "operation and the shared quota record. The suite found eight real weaknesses in pretix, six of them "
     "Major, each backed by a strict expected-failure test, a root cause in the source and a proposed fix. "
     "The regeneration demonstration shows that a change to one constraint changes only the affected cases "
     "and immediately exposes a mismatch with the implementation. The remaining work is to file W-01 to W-08 "
     "as GitHub issues and add the Area 2 rows to the shared risk register and traceability matrix.")

# ---------------------------------------------------------------- appendix
h("Appendix A: How to Reproduce")
code(["cd pretix-sqe",
      "python -m venv .venv",
      ".venv/Scripts/pip install -e \".[dev]\" pyyaml openapi-spec-validator",
      "cd src",
      "../.venv/Scripts/python -m pytest tests/team/sami -n 4",
      "../.venv/Scripts/python -m flake8 tests/team/sami",
      "../.venv/Scripts/python tests/team/sami/generator/generate_test_data.py --summary",
      "../.venv/Scripts/python tests/team/sami/generator/regeneration_demo/run_demo.py --verify"])
h("Appendix B: Deliverable Files")
table("Area 2 files in the repository",
      ["Path (under src/tests/team/sami/)", "Purpose"],
      [["openapi/pretix_orders_api.yaml", "OpenAPI 3.0 specification (19 operations)"],
       ["openapi/test_openapi_spec.py", "Specification validity and path resolution tests"],
       ["generator/generate_test_data.py", "EP/BVA generator"],
       ["generator/test_data.json", "Generated cases (167)"],
       ["generator/test_generator.py", "Generator unit tests"],
       ["generator/regeneration_demo/", "Constraint-change demonstration and report"],
       ["api/conftest.py", "API clients, helpers and fixtures"],
       ["api/test_api_ep_bva.py", "Generated EP/BVA API tests"],
       ["api/test_negative_rules.py", "Rules, transitions, duplicates, authorisation"],
       ["api/test_cross_workflow.py", "Shared quota integration tests"],
       ["api/test_api_coverage.py", "Operation coverage and response validation"],
       ["api/endpoint_weaknesses.md", "Weaknesses W-01 to W-08"]],
      [7.0, 9.0], size=10)

doc.save(OUT)
print("wrote", OUT)
