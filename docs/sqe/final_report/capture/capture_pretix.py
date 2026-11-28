"""
Real screenshots of pretix for the report: W1 (organizer sets up product and quota) and W2 (customer buys), the
back office and two access-control checks. Everything is done through the real web UI with Playwright/Chromium on a
local pretix instance (DEBUG off, waitress + whitenoise, own data folder), started by this script.

    python docs/sqe/final_report/capture/capture_pretix.py        (from the repository root)
"""
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[4]
SRC = REPO / "src"
HERE = Path(__file__).resolve().parent
FIG = REPO / "docs/sqe/final_report/figures"
PY = str(REPO / ".venv/Scripts/python.exe")
BASE = "http://localhost:8001"
EV = "/control/event/sqe-org/sqe-conf"
SHOP = f"{BASE}/sqe-org/sqe-conf/"
ORDER_RE = re.compile(r"/order/(?P<code>[A-Z0-9]+)/(?P<secret>[a-z0-9]+)/")
ENV = {**os.environ, "PRETIX_CONFIG_FILE": str(HERE / "screens_pretix.cfg"), "PERF_PORT": "8001",
       "DJANGO_SETTINGS_MODULE": "pretix.settings"}


def start_server():
    data = HERE / ".screens_data"
    shutil.rmtree(data, ignore_errors=True)          # fresh instance every time
    subprocess.run([PY, "manage.py", "migrate", "-v", "0"], cwd=SRC, env=ENV, check=True)
    subprocess.run([PY, "manage.py", "shell", "-c", f"exec(open(r'{HERE / 'seed_screens.py'}').read())"],
                   cwd=SRC, env=ENV, check=True)
    srv = subprocess.Popen([PY, "tests/team/tawassul/performance/perf_server.py"], cwd=SRC, env=ENV)
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/control/login", timeout=3)
            return srv
        except Exception:
            time.sleep(1)
    srv.kill()
    raise RuntimeError("pretix did not start")


class Shots:
    def __init__(self, page):
        self.page = page
        self.n = 0

    def __call__(self, name, full=False, locator=None):
        time.sleep(0.6)
        path = str(FIG / f"pretix_{name}.png")
        if locator is not None:
            locator.screenshot(path=path)
        else:
            self.page.screenshot(path=path, full_page=full)
        print("saved", name, flush=True)


def tab(page, name):
    """pretix builds the form tabs from the fieldset legends with JavaScript."""
    page.locator(".nav-tabs a, [role=tab]").filter(has_text=re.compile(rf"^\s*{name}\s*$")).first.click()
    time.sleep(0.5)


def save(page):
    page.locator("button.btn-save").first.click()
    page.wait_for_load_state("networkidle")


def checkout(page, shot=None):
    page.get_by_role("button", name=re.compile("Proceed with checkout", re.I)).click()
    page.wait_for_url("**/checkout/questions/**")
    page.fill("input[name=email]", "customer@sqe.test")
    if shot:
        shot("w2_03_contact_details")
    page.click("main form button[type=submit].btn-primary")
    page.wait_for_url("**/checkout/payment/**")
    page.check("input[name=payment][value=banktransfer]")
    if shot:
        shot("w2_04_payment_method")
    page.click("main form button[type=submit].btn-primary")
    page.wait_for_url("**/checkout/confirm/")
    if shot:
        shot("w2_05_review_order", full=True)
    page.click("main form button[type=submit].btn-primary")
    page.wait_for_url(ORDER_RE, timeout=60_000)
    page.wait_for_load_state("networkidle")
    m = ORDER_RE.search(page.url)
    return m.group("code"), m.group("secret")


def run():
    FIG.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1366, "height": 860}, locale="en-US")
        page = ctx.new_page()
        shot = Shots(page)

        # ---------------- W1: organizer ----------------
        page.goto(f"{BASE}/control/login")
        page.fill("input[name=email]", "organizer@sqe.test")
        page.fill("input[name=password]", "Sqe-Organizer-2026!")
        shot("w1_01_login")
        page.click("button[type=submit]")
        page.wait_for_url(f"{BASE}/control/")
        shot("w1_02_control_dashboard")
        page.goto(f"{BASE}{EV}/")
        shot("w1_03_event_dashboard")

        page.goto(f"{BASE}{EV}/items/add")
        page.fill("#id_name_0", "General Admission Ticket")
        page.fill("#id_default_price", "-5.00")
        page.check("#id_quota_option_2")
        page.fill("input[name=quota_add_new_name]", "Main Stage Quota")
        page.fill("input[name=quota_add_new_size]", "10")
        shot("w1_04_create_product_form", full=True)
        save(page)
        # known defect A3-D01: the back office stores the negative price ("Your changes have been saved")
        shot("w1_05_negative_price_accepted_A3-D01")
        item_id = re.search(r"/items/(\d+)/", page.url).group(1)
        tab(page, "Price")
        page.fill("#id_default_price", "50.00")
        shot("w1_06_price_corrected_to_50")
        save(page)
        shot("w1_06b_product_saved")
        page.goto(f"{BASE}{EV}/items/")
        shot("w1_07_product_list")
        page.goto(f"{BASE}{EV}/quotas/")
        shot("w1_08_quota_list")
        page.locator("a", has_text="Main Stage Quota").first.click()
        page.wait_for_load_state("networkidle")
        quota_url = page.url.split("?")[0].rstrip("/")
        shot("w1_09_quota_detail_before_sales", full=True)
        page.goto(f"{quota_url}/change")
        page.fill("#id_size", "-5")
        save(page)
        shot("w1_10_negative_quota_size_rejected", full=True)
        page.fill("#id_size", "10")
        save(page)
        # limit tickets per order (rule used by the max-per-order screen)
        page.goto(f"{BASE}{EV}/items/{item_id}/")
        tab(page, "Availability")
        page.fill("#id_max_per_order", "4")
        save(page)

        # ---------------- W2: customer ----------------
        cust = b.new_context(viewport={"width": 1366, "height": 860}, locale="en-US")
        cp = cust.new_page()
        cshot = Shots(cp)
        cp.goto(SHOP)
        cshot("w2_01_shop_front_page", full=True)
        cp.fill(f"input[name=item_{item_id}]", "5")
        cp.click("#btn-add-to-cart")
        cp.wait_for_load_state("networkidle")
        cshot("w2_02_max_per_order_rejected")
        cp.goto(SHOP)
        cp.fill(f"input[name=item_{item_id}]", "2")
        cp.click("#btn-add-to-cart")
        cp.wait_for_load_state("networkidle")
        cshot("w2_02b_cart", full=True)
        code1, secret1 = checkout(cp, cshot)
        cshot("w2_06_order_confirmation", full=True)

        # the last VIP seat: after this purchase the VIP category is sold out
        vip_box = cp
        cp.goto(SHOP)
        vip = cp.locator("article, .item-row, .product-row").filter(has_text="VIP Ticket").first
        vip.locator("input[type=number], input[type=checkbox]").first.click()
        box = vip.locator("input[type=number]")
        if box.count():
            box.first.fill("1")
        cp.click("#btn-add-to-cart")
        cp.wait_for_load_state("networkidle")
        code2, secret2 = checkout(cp)
        cp.goto(SHOP)
        cshot("w2_07_vip_sold_out", full=True)

        # quota after the sales (shared record between W1 and W2)
        page.goto(quota_url + "/")
        shot("w1_11_quota_detail_after_sales", full=True)

        # ---------------- back office ----------------
        page.goto(f"{BASE}{EV}/orders/")
        shot("bo_01_order_list")
        page.goto(f"{BASE}{EV}/orders/{code1}/")
        shot("bo_02_order_pending", full=True)
        page.goto(f"{BASE}{EV}/orders/{code1}/transition?status=p")
        shot("bo_03_mark_paid_form")
        page.locator("form button[type=submit].btn-primary").last.click()
        page.wait_for_load_state("networkidle")
        shot("bo_04_order_paid", full=True)
        page.goto(f"{BASE}{EV}/orders/{code2}/transition?status=c")
        shot("bo_05_cancel_form", full=True)
        page.locator("form button[type=submit].btn-danger, form button[type=submit].btn-primary").last.click()
        page.wait_for_load_state("networkidle")
        shot("bo_06_order_canceled", full=True)
        cp.goto(SHOP)
        cshot("w2_08_vip_available_again_after_cancel", full=True)

        # ---------------- access control ----------------
        viewer = b.new_context(viewport={"width": 1366, "height": 860}, locale="en-US").new_page()
        vshot = Shots(viewer)
        viewer.goto(f"{BASE}/control/login")
        viewer.fill("input[name=email]", "viewer@sqe.test")
        viewer.fill("input[name=password]", "Sqe-Viewer-2026!")
        viewer.click("button[type=submit]")
        viewer.wait_for_url(f"{BASE}/control/")
        viewer.goto(f"{BASE}{EV}/orders/")
        vshot("sec_01_viewer_can_list_orders")
        resp = viewer.goto(f"{BASE}{EV}/items/add")
        print("viewer items/add status", resp.status)
        vshot("sec_02_viewer_403_create_product")
        anon = b.new_context(viewport={"width": 1366, "height": 860}, locale="en-US").new_page()
        resp = anon.goto(f"{SHOP}order/{code1}/wrongsecret0000/")
        print("wrong secret status", resp.status)
        Shots(anon)("sec_03_wrong_order_secret_404")
        resp = anon.goto(f"{BASE}{EV}/orders/")
        Shots(anon)("sec_04_anonymous_redirected_to_login")
        cp.goto(f"{SHOP}order/{code1}/{secret1}/")
        cshot("w2_09_customer_order_page_paid", full=True)
        b.close()


if __name__ == "__main__":
    srv = start_server()
    try:
        run()
    finally:
        srv.kill()
