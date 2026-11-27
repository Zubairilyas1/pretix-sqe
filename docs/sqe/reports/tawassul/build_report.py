"""
Builds TAWASSUL_AREA3_REPORT.docx (Times New Roman 12 pt, black and white).

    .venv/Scripts/python docs/sqe/reports/tawassul/build_report.py

Figures are real screenshots taken on 26 Nov 2026 and stored in ./figures.
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
OUT = HERE / "TAWASSUL_AREA3_REPORT.docx"
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
    src = HERE / "figures_print" / fname
    p.add_run().add_picture(str(src if src.exists() else FIG / fname), width=Cm(width_cm))
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


# ---------------------------------------------------------------- data
import json  # noqa: E402

SONAR = HERE.parents[3] / "src/tests/team/tawassul/static_analysis/evidence/sonar_measures.json"
sonar = json.loads(SONAR.read_text("utf-8")) if SONAR.exists() else None


PRINT = HERE / "figures_print"


def _print_copy(name):
    """Grayscale copy for the black-and-white report; console captures lose the
    window shadow and the strip of desktop under the border."""
    from PIL import Image, ImageOps
    PRINT.mkdir(exist_ok=True)
    im = Image.open(FIG / name).convert("RGB")
    if name[:2] in ("01", "02", "06"):
        w, h_ = im.size
        im = im.crop((8, 0, w - 8, h_ - 12))
    ImageOps.grayscale(im).save(PRINT / name, optimize=True)


def fig_if(name, caption, width=16.0):
    if (FIG / name).exists():
        _print_copy(name)
        figure(name, caption, width)


# ---------------------------------------------------------------- title page
for _ in range(3):
    doc.add_paragraph()
para("National University of Computer and Emerging Sciences, Islamabad", WD_ALIGN_PARAGRAPH.CENTER, 14)
para("SE3002 Software Quality Engineering, Fall 2026", WD_ALIGN_PARAGRAPH.CENTER, 13, after=36)
tp = doc.add_paragraph(style="Title")
tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
_font(tp.add_run("Final Project Report"), 22, bold=True)
para("**Area 3: Use Cases, Usability, Accessibility, Security and Performance**", WD_ALIGN_PARAGRAPH.CENTER, 16)
para("System under test: pretix (open-source event ticketing system)", WD_ALIGN_PARAGRAPH.CENTER, 13, after=48)
meta = doc.add_table(rows=0, cols=2)
meta.alignment = WD_TABLE_ALIGNMENT.CENTER
for k, v in (("Author", "Tawassul Akbar (Member 3, Area 3 owner)"),
             ("Student ID", "i243100"),
             ("Repository", "github.com/Zubairilyas1/pretix-sqe"),
             ("pretix baseline", "c0d887738b6cd97f724b926718c55e2ae87c9901"),
             ("Branches", "member/tawassul and tawassul/feat-*"),
             ("Report date", "26 November 2026")):
    c = meta.add_row().cells
    _runs(c[0].paragraphs[0], f"**{k}**")
    _runs(c[1].paragraphs[0], v)
    c[0].width, c[1].width = Cm(4.5), Cm(10)
page_break()

tc = doc.add_paragraph()
_font(tc.add_run("Table of Contents"), 14, bold=True)
_field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
page_break()
for s in doc.sections:
    s.different_first_page_header_footer = True
    fp = s.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(fp.add_run("Page "), 10)
    _field(fp, "PAGE", 10)
    hp = s.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _font(hp.add_run("SE3002 SQE Final Project | Area 3 Report (Tawassul Akbar)"), 10, italic=True)

# ---------------------------------------------------------------- 1
h("1. Executive Summary")
para("This report covers Area 3 of the team project:")
bullets(["use-case based end-to-end testing",
         "usability and accessibility",
         "defensive security",
         "performance and failure recovery",
         "static analysis with a hand-calculated control flow graph"])
para("All browser tests drive a real pretix server in Chromium with Playwright, and check both what the user "
     "sees and what is stored in the database.")
para("The final run of the Area 3 suite produced **61 passed and 4 expected failures (strict xfail)**, with "
     "flake8 reporting no findings. Six defects were found (A3-D01 to A3-D06), four of them Major.")
bullets(["The accessibility defects of the organizer back office were fixed, and the **Lighthouse accessibility "
         "score of the item editor rose from 81 to 93**.",
         "The k6 load test shows that the checkout API meets the p95 ≤ 500 ms target with one user but "
         "not with five, and that no order data is corrupted under load."])
para("Every figure in this report is a real screenshot or real tool output captured on 26 November 2026.")

# ---------------------------------------------------------------- 2
h("2. Introduction")
h("2.1 Scope", 2)
para("The brief assigns Area 3 the user-facing and non-functional qualities of the two workflows the team "
     "selected:")
bullets(["**W1:** the organizer creates items and quotas.",
         "**W2:** the customer buys tickets."])
para("Area 1 (white-box, mutation, CI) and Area 2 (API testing and data generation) are reported by my "
     "teammates.")
h("2.2 System and roles", 2)
table("Roles used in Area 3", ["Role", "Description", "Entry point"],
      [["Organizer", "back-office user in a team with event permissions", "`/control/`"],
       ["Viewer", "back-office user who may only read orders", "`/control/`"],
       ["Customer", "anonymous shop visitor; owns an order through its secret link", "`/{org}/{event}/`"]],
      [3.0, 8.0, 5.0])

# ---------------------------------------------------------------- 3
h("3. Test Environment and Tools")
table("Environment and tools", ["Item", "Value"],
      [["Operating system", "Windows 10 Pro (build 19045)"],
       ["Python / Django", "Python 3.12.10, Django 5.2.19"],
       ["Browser automation", "Playwright 1.65 (Python) with Chromium, pytest-django live server"],
       ["Accessibility", "axe-core (axe-playwright-python), Google Lighthouse 12"],
       ["Security", "OWASP ZAP 2.17.0 (Docker, passive), pip-audit, GitHub Advisory Database"],
       ["Performance", "Grafana k6 (Docker)"],
       ["Static analysis", "SonarQube Community (Docker), hand-drawn CFG"],
       ["Server for k6 / ZAP / Lighthouse", "pretix with DEBUG off and compressed assets, served by waitress + whitenoise"]],
      [5.0, 11.0])
para("Tests run against SQLite. The tools that need a long-running server use a separate production-like "
     "instance (`performance/perf_server.py`) with its own data folder. A seed script resets that data before "
     "each run.")

# ---------------------------------------------------------------- 4
h("4. Use Case Specification and Playwright End-to-End Tests")
para("`usecases/use_case_spec.md` specifies six use cases. Each has preconditions, a main success scenario, "
     "two alternative flows, two exception flows and postconditions. Every flow is one test in "
     "`test_e2e_usecases.py` (30 tests).")
table("Use cases and their flows", ["UC", "Title", "Alternative flows", "Exception flows"],
      [["UC-1", "Organizer configures item and quota", "add to existing quota; create quota on quota page",
        "negative price (**A3-D01**); quota without name"],
       ["UC-2", "Organizer publishes event and sets sales window", "take shop offline; sales not started",
        "sales period over; end before start"],
       ["UC-3", "Customer completes checkout", "two tickets; remove ticket in cart",
        "invalid email; reservation expired and seats gone"],
       ["UC-4", "Customer applies a voucher", "fixed-price voucher; code typed on shop page",
        "unknown code; voucher used up"],
       ["UC-5", "Customer tries a sold-out category", "waiting list; other category free",
        "last seat taken during checkout; quota closed"],
       ["UC-6", "Customer cancels a pending order", "cancel from order page; organizer cancels",
        "wrong secret (404); self-cancel disabled"]],
      [1.4, 4.6, 5.0, 5.0], size=10)
para("Each test asserts the UI (URL, alert text, page content) **and** the database (orders, cart positions, "
     "vouchers, quota availability). For example, the UC-3 main flow checks the thank-you page and then that:")
bullets(["one pending order with total 50.00 exists,",
         "the cart is empty,",
         "the quota dropped from 10 to 9."])
para("**Defect A3-D01:** the organizer back office saves an item with price −5.00. This has the same "
     "root cause as the API weakness W-01 in Area 2 (no minimum validator on `Item.default_price`), now shown "
     "through the web screen. The test is kept as a strict expected failure.")
fig_if("03_uc3_order_placed.png", "Final browser page of test_uc3_main_checkout_one_ticket: order placed, payment pending (real Playwright screenshot).", 12.5)

# ---------------------------------------------------------------- 5
h("5. Usability and Accessibility")
h("5.1 Keyboard-only navigation", 2)
para("`test_keyboard_nav.py` completes a purchase using only Tab, Shift+Tab, Enter and Space. It records where "
     "focus goes after every Tab, and asserts that the optional invoice section opens with Enter and that its "
     "fields are reached top to bottom.")
para("Two more tests check WCAG 2.4.7 (focus is visible) and 2.4.1 (a skip link is the first Tab stop). All "
     "three tests pass.")
h("5.2 axe-core findings", 2)
table("axe-core scan before remediation (WCAG 2.1 AA)", ["Screen", "Rules violated", "Elements"],
      [["Customer shop page", "0", "0"], ["Customer checkout", "0", "0"],
       ["Organizer item creation", "**5**", "**11**"]], [9.0, 3.5, 3.5])
table("Findings on the organizer screen", ["#", "Rule", "WCAG", "Element", "Status"],
      [["F1", "html-has-lang", "3.1.1 (A)", "`<html>`", "fixed"],
       ["F2", "image-alt", "1.1.1 (A)", "logo image", "fixed"],
       ["F3", "link-name", "2.4.4, 4.1.2 (A)", "6 sidebar submenu toggles", "fixed"],
       ["F4", "color-contrast", "1.4.3 (AA)", "event date, select placeholder", "open (design)"],
       ["F5", "aria-input-field-name", "4.1.2 (A)", "select2 category widget", "open (third party)"]],
      [1.0, 4.0, 3.2, 5.0, 2.8], size=10)
h("5.3 Remediation and before/after", 2)
para("F1 to F3 come from the shared back-office template `pretixcontrol/base.html`, so they affected every "
     "organizer page (defect A3-D03). The fix changes four lines and is a separate commit:")
bullets(["a `lang` attribute on `<html>`",
         "`alt=\"\"` on the decorative logo",
         "an `aria-label` on each submenu toggle"])
table("Measured before and after (organizer item page)", ["Measure", "Before", "After"],
      [["Lighthouse Accessibility", "**81**", "**93**"], ["Lighthouse Best Practices", "100", "100"],
       ["axe rules violated", "5", "2"], ["axe elements affected", "11", "3"],
       ["html-has-lang / image-alt / link-name", "1 / 1 / 6", "0 / 0 / 0"]], [9.0, 3.5, 3.5])
para("**A pitfall found along the way:** pretix pins every back-office session to the browser's User-Agent "
     "(`pretix/helpers/security.py:97`), so the first Lighthouse runs silently audited the login page. The "
     "runner now logs in with the exact User-Agent Lighthouse uses, and rejects any report whose final URL is "
     "not the intended screen.")
fig_if("05_lighthouse_organizer_before.png", "Lighthouse on the logged-in organizer item page before the fix: Accessibility 81 (real report).", 13.5)
fig_if("05_lighthouse_organizer_after.png", "Lighthouse on the same page after the fix: Accessibility 93 (real report).", 13.5)

# ---------------------------------------------------------------- 6
h("6. Defensive Security")
h("6.1 Role-based access control", 2)
table("Access decisions automated in test_rbac_decisions.py", ["Who", "Resource", "Expected", "Result"],
      [["Organizer", "`/control/`, item editor", "200", "pass"],
       ["Customer", "shop", "200", "pass"],
       ["Customer", "`/control/`, event back office", "redirect to login", "pass"],
       ["Customer", "other order: wrong secret / no secret / wrong code", "404", "pass"],
       ["Viewer (orders:read)", "order list", "200", "pass"],
       ["Viewer (orders:read)", "create item, cancel order", "403, DB unchanged", "pass"]],
      [3.4, 6.2, 3.6, 2.8], size=10)
para("pretix answers a wrong order secret exactly like a non-existent order (404), so order codes cannot be "
     "enumerated.")
h("6.2 OWASP ZAP passive scan", 2)
para("Playwright walked the W2 checkout and the W1 organizer pages through the ZAP proxy. ZAP reported "
     "156 alert instances in 13 rules (0 High, 4 Medium, 4 Low). Each Medium and Low alert was checked "
     "against the pretix source:")
table("Triage of ZAP alerts", ["Rule", "Risk", "Verdict"],
      [["Vulnerable JS library (Bootstrap 3.4.1)", "Medium", "**confirmed, A3-D05** (CVE-2024-6485, CVE-2025-1647; no 3.x fix)"],
       ["CSP directive without fallback", "Medium", "no `frame-ancestors`; mitigated by X-Frame-Options DENY"],
       ["Cross-domain misconfiguration", "Medium", "by design: public static assets and the anti-phishing beacon"],
       ["Absence of anti-CSRF tokens", "Medium", "false positive: `<form method=\"dialog\">`"],
       ["X-Content-Type-Options missing", "Low", "**confirmed, A3-D02**"],
       ["Cookie without HttpOnly", "Low", "by design: CSRF cookie read by JavaScript; session cookie is HttpOnly"],
       ["Cookie without SameSite", "Low", "documented design for the iframe widget (`helpers/cookies.py`)"],
       ["Timestamp disclosure", "Low", "false positive: cart expiry countdown"]],
      [5.5, 1.8, 8.7], size=10)
fig_if("07_zap_report.png", "ZAP's own HTML report of the passive scan (real report).", 14.0)
h("6.3 Dependency audit", 2)
table("pip-audit result (213 packages checked)", ["Package", "Advisory", "Severity", "Fixed in"],
      [["oauthlib 3.3.1", "CVE-2026-49272 (device-code grant token issue)", "High, CVSS 8.5", "4.0.1"],
       ["oauthlib 3.3.1", "CVE-2026-49265 (PKCE timing side channel)", "Medium, CVSS 6.8", "4.0.0"]],
      [3.2, 7.0, 3.3, 2.5], size=10)
para("pretix pins `oauthlib==3.3.*`, so the fix is a major-version upgrade (defect A3-D04). pretix does not "
     "intentionally offer the device grant, so it is unconfirmed whether the high CVE can be exploited.")

# ---------------------------------------------------------------- 7
h("7. Performance and Failure Recovery")
h("7.1 k6 workload", 2)
para("One k6 iteration is a W2 purchase through the REST API: read availability, create order, read order. "
     "The SLA is p95 ≤ 500 ms and a failure rate below 1 %. Each configuration ran twice for 60 s from "
     "identical seeded data.")
table("k6 results", ["Run", "VUs", "p95 (ms)", "Errors", "Throughput (req/s)", "SLA"],
      [["1a", "1", "472", "0 %", "4.39", "met"], ["1b", "1", "398", "0 %", "4.97", "met"],
       ["2a", "5", "1 390", "26.4 %", "7.40", "**failed**"], ["2b", "5", "1 580", "21.5 %", "6.38", "**failed**"]],
      [1.6, 1.6, 2.6, 2.6, 4.0, 3.6])
para("At 5 users, every failure is an order creation answered with HTTP 500, because SQLite allows only one "
     "writer at a time (`database is locked`). This is a limit of the test database; production pretix uses "
     "PostgreSQL.")
para("Correctness held under load. After run 2b there were exactly 74 orders, 74 positions and 74 seats "
     "taken, matching the 74 successful responses, with no half-written orders.")
fig_if("06_k6_run_1b.png", "k6 summary of run 1b (1 VU): thresholds met (real k6 output).", 14.5)
fig_if("06_k6_run_2a.png", "k6 summary of run 2a (5 VUs): thresholds crossed (real k6 output).", 14.5)
h("7.2 Failure injection and recovery", 2)
para("`test_failure_recovery.py` interrupts a real browser checkout with a simulated database failure inside "
     "`_create_order`, at two points: while cart positions are turned into order positions, and while the "
     "order transactions are booked. In both cases:")
bullets(["the customer is not sent to an order page,",
         "no order, position or payment is left behind,",
         "the quota is unchanged,",
         "a retry after the fault is removed creates exactly one order."])
para("Both tests pass.")

# ---------------------------------------------------------------- 8
h("8. Static Analysis and Cyclomatic Complexity")
if sonar:
    p_ = sonar["project"]
    table("SonarQube measures for the four W1/W2 source files",
          ["Measure", "Value"],
          [["Lines of code", p_.get("ncloc", "-")], ["Cyclomatic complexity", p_.get("complexity", "-")],
           ["Cognitive complexity", p_.get("cognitive_complexity", "-")], ["Bugs", p_.get("bugs", "-")],
           ["Vulnerabilities", p_.get("vulnerabilities", "-")], ["Security hotspots", p_.get("security_hotspots", "-")],
           ["Code smells", p_.get("code_smells", "-")], ["Duplicated lines (%)", p_.get("duplicated_lines_density", "-")]],
          [9.0, 7.0])
    para(f"SonarQube reported {len(sonar['issues'])} issues and {len(sonar['hotspots'])} security hotspots. "
         "The quality gate passed. The three bugs are one real defect, **A3-D06**: the add-on price "
         "correction in `cart.py:1056-1066` assigns each field to itself, so it never corrects anything. "
         "Details are in `static_analysis/sonar_findings.md`, and the raw export is in "
         "`evidence/sonar_measures.json`.")
    fig_if("08_sonarqube_dashboard.png", "SonarQube dashboard of the W1/W2 files (real screenshot).", 15.0)
para("For the hand calculation I chose `Quota.availability()`, the function behind the record that both "
     "workflows share. Each operand of its short-circuit `and` conditions is its own decision node.")
table("Cyclomatic complexity of Quota.availability()", ["Method", "Calculation", "V(G)"],
      [["Edges and nodes", "E − N + 2 = 16 − 12 + 2", "**6**"],
       ["Decision nodes", "5 + 1", "**6**"], ["Regions", "5 bounded + 1 outer", "**6**"]], [5.0, 8.0, 3.0])
para("Five basis paths are feasible. They are tested in `test_cfg_paths.py` and cover all 16 edges. The sixth "
     "path is infeasible, because it needs the cache to be non-empty and `None` at the same time. So V(G) is "
     "an upper bound on the number of tests, not always the number of runnable paths.")

# ---------------------------------------------------------------- 9
h("9. Test Execution Results")
table("Area 3 tests per file (final run, 26 November 2026)", ["Test file", "Tests", "Result"],
      [["usecases/test_e2e_usecases.py", "30", "29 passed, 1 xfailed (A3-D01)"],
       ["usability_a11y/test_keyboard_nav.py", "3", "3 passed"],
       ["usability_a11y/test_axe_scan.py", "6", "6 passed"],
       ["security/test_rbac_decisions.py", "10", "10 passed"],
       ["security/test_security_headers.py", "9", "6 passed, 3 xfailed (A3-D02)"],
       ["performance/test_failure_recovery.py", "2", "2 passed"],
       ["static_analysis/test_cfg_paths.py", "5", "5 passed"],
       ["**Total**", "**65**", "**61 passed, 4 xfailed**"]], [8.0, 2.0, 6.0])
fig_if("02_full_area3_run.png", "Summary of the full Area 3 run (real pytest output).")

# ---------------------------------------------------------------- 10
h("10. Defects Found")
table("Area 3 defects", ["ID", "Defect", "Severity", "Found by"],
      [["A3-D01", "Back office saves a negative item price", "Major", "Playwright UC-1"],
       ["A3-D02", "X-Content-Type-Options and Referrer-Policy not sent", "Minor", "header tests, ZAP"],
       ["A3-D03", "Back office fails WCAG 2.1 A (lang, alt, link names), fixed", "Major", "axe, Lighthouse"],
       ["A3-D04", "oauthlib 3.3.1 with CVE-2026-49272 (8.5)", "Major", "pip-audit"],
       ["A3-D05", "Bootstrap 3.4.1 end-of-life with two XSS advisories", "Minor", "ZAP"],
       ["A3-D06", "Add-on price correction in cart.py is a no-op (self-assignments)", "Major", "SonarQube"]],
      [2.0, 8.0, 2.0, 4.0], size=10)

# ---------------------------------------------------------------- 11
h("11. Configuration Management")
para("As the team guide requires, the work was built on a member branch with one feature branch per "
     "deliverable, each on top of the previous one. Every commit is authored by Tawassul Akbar.")
table("Branches", ["Branch", "Content"],
      [["member/tawassul", "Master plan"], ["tawassul/feat-playwright-usecases", "Use cases and E2E tests"],
       ["tawassul/feat-a11y-lighthouse-fix", "Template fix, keyboard, axe, Lighthouse"],
       ["tawassul/feat-security-rbac-zap", "RBAC, headers, ZAP, pip-audit"],
       ["tawassul/feat-k6-perf-recovery", "k6 runs and failure recovery"],
       ["tawassul/feat-static-cfg", "CFG, V(G), basis paths, SonarQube"],
       ["tawassul/docs-shared-management", "Shared rows, AI log, this report"]], [7.0, 9.0], size=10)
fig_if("01_git_commits_tawassul.png", "Commit history of the Area 3 branches with author Tawassul Akbar (real console screenshot).")
fig_if("09_pull_request.png", "Pull request of the Area 3 work into main (real browser screenshot).", 14.0)

# ---------------------------------------------------------------- 12
h("12. Limitations and Threats to Validity")
bullets(["SQLite was used instead of PostgreSQL, so the 5-user error rate would most likely be lower in "
         "production.",
         "k6, pretix and the browser share one laptop, and waitress replaces gunicorn and nginx.",
         "ZAP ran in passive mode only, so no active attacks were tried.",
         "Lighthouse and axe detect only part of WCAG, and a manual screen-reader check was not done.",
         "The use cases were assigned two per member as the brief requires; teammates should review theirs."])

# ---------------------------------------------------------------- 13
h("13. Use of Generative AI")
para("As required, AI use is recorded in the team's AI-use disclosure log (rows 11 to 14). Claude Code was "
     "used under my direction to probe pretix, write the tests, run the tools and draft the reports. Every "
     "output was executed, and problems the AI introduced were caught by the runs and fixed, for example:")
bullets(["a Lighthouse run that audited the login page,",
         "a cookie test that passed for the wrong reason,",
         "a k6 run whose requests were all rejected."])
para("I am reviewing every test and calculation myself before the viva.")

# ---------------------------------------------------------------- 14
h("14. Conclusion")
para("Area 3 delivered:")
bullets(["six fully specified use cases with 30 browser tests,",
         "a keyboard and accessibility evaluation with a measured fix (Lighthouse 81 to 93),",
         "ten automated access-control decisions,",
         "a triaged ZAP scan and a dependency audit,",
         "four k6 runs with a recovery test,",
         "a hand-calculated control flow graph with basis-path tests."])
para("Six defects were found. One was fixed, and each of the others has evidence and a proposed fix. The next "
     "steps are to file A3-D01, A3-D02, A3-D04, A3-D05 and A3-D06 as GitHub Issues, and to repeat the 5-user load test "
     "on PostgreSQL.")

h("Appendix A: How to Reproduce")
code(["cd pretix-sqe/src",
      "../.venv/Scripts/python -m playwright install chromium",
      "../.venv/Scripts/python -m pytest tests/team/tawassul -v",
      "../.venv/Scripts/python -m flake8 tests/team/tawassul",
      "# k6, ZAP, Lighthouse and SonarQube: see each report's How to reproduce section"])

doc.save(OUT)
print("wrote", OUT)
