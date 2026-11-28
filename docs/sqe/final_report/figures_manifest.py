"""
Which evidence screenshot goes into which report section, with its caption.

All files are in docs/sqe/final_report/figures/ (raw_tests/ = page at the end of the named automated test, saved by
the SQE_SCREENSHOT_DIR hook in src/tests/team/tawassul/conftest.py). Images are used exactly as captured.
Console figures are real command output rendered as text (capture/capture_console.py) and are captioned as such.
"""

T = "raw_tests/"

UC_TESTS = {
    "UC-1": ["test_uc1_main_create_item_with_new_quota", "test_uc1_alt_add_item_to_existing_quota",
             "test_uc1_alt_create_quota_from_quota_page", "test_uc1_exc_negative_price_rejected_in_backoffice",
             "test_uc1_exc_quota_without_name_rejected"],
    "UC-2": ["test_uc2_main_organizer_takes_shop_live", "test_uc2_alt_take_shop_offline",
             "test_uc2_alt_sales_not_started_yet", "test_uc2_exc_sales_period_over",
             "test_uc2_exc_end_before_start_rejected"],
    "UC-3": ["test_uc3_main_checkout_one_ticket", "test_uc3_alt_two_tickets", "test_uc3_alt_remove_ticket_before_checkout",
             "test_uc3_exc_invalid_email", "test_uc3_exc_cart_expired_before_confirm"],
    "UC-4": ["test_uc4_main_percentage_voucher", "test_uc4_alt_fixed_price_voucher",
             "test_uc4_alt_voucher_entered_on_shop_page", "test_uc4_exc_unknown_voucher",
             "test_uc4_exc_voucher_already_used"],
    "UC-5": ["test_uc5_main_sold_out_is_shown_and_not_bookable", "test_uc5_alt_join_waiting_list",
             "test_uc5_alt_other_category_still_bookable", "test_uc5_exc_last_seat_taken_during_checkout",
             "test_uc5_exc_closed_quota"],
    "UC-6": ["test_uc6_main_customer_cancels_pending_order", "test_uc6_alt_cancel_link_from_order_page",
             "test_uc6_alt_organizer_cancels_in_backoffice", "test_uc6_exc_wrong_secret_is_404",
             "test_uc6_exc_self_cancel_disabled"],
}
FLOW = {"main": "main success flow", "alt": "alternative flow", "exc": "exception flow"}


def _uc_figs():
    out = []
    for uc, tests in UC_TESTS.items():
        for t in tests:
            kind = FLOW[t.split("_")[2]]
            note = " (strict xfail: documents defect A3-D01, the price is stored)" if "negative_price" in t else ""
            out.append((T + t + ".png", f"{uc} {kind}: screen at the end of automated test {t}{note}"))
    return out


FIGURES = {
    "1. System, scope and test plan": [
        ("gh_01_repository.png", "Public team repository Zubairilyas1/pretix-sqe on GitHub (branch zubair)"),
        ("pretix_w1_01_login.png", "pretix back-office login with the organizer test account (local instance, DEBUG off)"),
        ("pretix_w1_02_control_dashboard.png", "pretix back office after login: organizer dashboard"),
        ("pretix_w1_03_event_dashboard.png", "Event dashboard of the synthetic event SQE Annual Conference 2026"),
    ],
    "2. Static analysis and cyclomatic complexity": [
        ("sonar_06_w1w2_overview.png", "SonarQube Community Build: overview of the four W1/W2 source files"),
        ("sonar_07_w1w2_complexity.png", "SonarQube: cyclomatic complexity per W1/W2 file"),
        ("sonar_08_w1w2_issues.png", "SonarQube: open issues (code smells) in the W1/W2 files"),
    ],
    "6. White-box unit testing": [
        ("pytest_area1.png", "pytest-html report of the Area 1 suite (218 passed)"),
        ("cov_01_index.png", "coverage.py HTML report: quotas.py 239/239 statements, 143/144 branches"),
        ("cov_02_function_index.png", "coverage.py per-function view of quotas.py"),
        ("cov_03_quotas_branches.png", "coverage.py source view of quotas.py around the orders stage (branch markers)"),
        ("sonar_01_quotas_overview.png", "SonarQube overview of quotas.py with the Area 1 coverage report"),
        ("sonar_03_quotas_measures.png", "SonarQube coverage measures of quotas.py"),
        ("sonar_04_quotas_code_coverage.png", "SonarQube code view of quotas.py with line and branch coverage"),
    ],
    "7. Mutation analysis and CI quality gate": [
        ("mut_run1_baseline_summary.png", "Cosmic Ray HTML report, run 1 (baseline): 715 mutants, 65 surviving"),
        ("mut_run2_after_kills_summary.png", "Cosmic Ray HTML report, run 2 (after the new tests): 23 surviving, all equivalent"),
        ("mut_run2_survivor.png", "Cosmic Ray run 2: one surviving (equivalent) mutant with its diff"),
        ("mut_run2_custom_operator.png", "Cosmic Ray run 2: a mutant created by the custom operator sqe/SwapAvailabilityVerdict, killed"),
        ("sonar_02_quality_gate.png", "SonarQube quality gate SQE Area1 Gate (CI Gate 4): conditions on new code"),
        ("sonar_05_quotas_issues.png", "SonarQube issues of quotas.py"),
        ("gh_14_workflow_file.png", "CI workflow .github/workflows/sqe_quality_gate.yml on GitHub"),
        ("gh_03_actions_runs.png", "GitHub Actions: runs of the SQE CI Quality Gate workflow"),
        ("gh_04_green_run_all_gates.png", "A complete green run of pull request #15: Gates 1-4, the 8 mutation shards and Gate 5 passed"),
        ("console_gate5_merge.png", "Console output: Gate 5 merge job, all 715 mutants executed, score 96.78 % >= 85 %"),
        ("gh_05_pr15_checks.png", "Pull request #15 (zubair into main) with all gate checks"),
        ("console_branch_protection.png", "Console output: branch protection of main requires all five gates (GitHub API)"),
        ("gh_06_blocked_pr35.png", "Blocked pull request #35: the sold-out check changed from <= 0 to < 0"),
        ("gh_07_blocked_pr35_red_run.png", "Pull request #35: the CI run fails, the deploy job is skipped"),
        ("console_pr35_gate1_failure.png", "Console output: failing tests of Gate 1 on pull request #35 (gh run view --log-failed)"),
        ("console_pr35_merge_state.png", "Console output: merge state of pull request #35 is BLOCKED"),
        ("gh_08_fix_pr36.png", "Fix pull request #36 for defect D-Z01, merged; it closed issue #16"),
        ("gh_09_fix_pr36_commits.png", "Pull request #36: test commit (red) followed by the fix commit (green)"),
        ("gh_15_fix_run_failure.png", "Pull request #36: CI run of the regression-test commit fails"),
        ("gh_15_fix_run_success.png", "Pull request #36 after the fix (branch updated with main): all five gates pass"),
        ("gh_16_deploy_run_main.png", "Push of the merge to main: all gates pass, then the deploy job runs"),
        ("gh_02_pull_requests.png", "Pull requests of the team repository"),
    ],
    "8. API testing and test-data generation": [
        ("api_01_swagger_overview.png", "Our OpenAPI 3 specification of the pretix endpoints, rendered by Swagger UI"),
        ("api_02_swagger_create_order.png", "Swagger UI: the createOrder operation with its constraints"),
        ("pytest_area2.png", "pytest-html report of the Area 2 suite (490 passed, 30 xfailed = logged weaknesses)"),
    ],
    "9. Use cases and use-case test automation": [
        ("pytest_area3.png", "pytest-html report of the Area 3 suite"),
        ("pretix_w1_04_create_product_form.png", "W1: organizer fills in the new product form (price -5.00, new quota of 10)"),
        ("pretix_w1_05_negative_price_accepted_A3-D01.png", "W1: pretix stores the negative price (defect A3-D01)"),
        ("pretix_w1_06_price_corrected_to_50.png", "W1: price corrected to 50.00 on the Price tab"),
        ("pretix_w1_06b_product_saved.png", "W1: product saved"),
        ("pretix_w1_07_product_list.png", "W1: product list"),
        ("pretix_w1_08_quota_list.png", "W1: quota list with availability (the shared record)"),
        ("pretix_w1_09_quota_detail_before_sales.png", "W1: quota Main Stage Quota before any sale: 10 available"),
        ("pretix_w1_10_negative_quota_size_rejected.png", "W1: a negative quota size is rejected by the form"),
        ("pretix_w2_01_shop_front_page.png", "W2: shop front page with both ticket categories"),
        ("pretix_w2_02_max_per_order_rejected.png", "W2: 5 tickets rejected, the product allows at most 4 per order"),
        ("pretix_w2_02b_cart.png", "W2: cart with 2 tickets"),
        ("pretix_w2_03_contact_details.png", "W2: checkout step contact details"),
        ("pretix_w2_04_payment_method.png", "W2: checkout step payment method (bank transfer)"),
        ("pretix_w2_05_review_order.png", "W2: review page before the order is placed"),
        ("pretix_w2_06_order_confirmation.png", "W2: order confirmation page"),
        ("pretix_w1_11_quota_detail_after_sales.png", "Shared record after W2: quota shows 2 pending, 8 left"),
        ("pretix_w2_07_vip_sold_out.png", "W2: VIP Ticket (quota of 1) is SOLD OUT after its last seat was bought"),
        ("pretix_bo_01_order_list.png", "Back office: order list"),
        ("pretix_bo_02_order_pending.png", "Back office: order in state pending"),
        ("pretix_bo_03_mark_paid_form.png", "Back office: mark as paid (state change pending -> paid)"),
        ("pretix_bo_04_order_paid.png", "Back office: order in state paid"),
        ("pretix_bo_05_cancel_form.png", "Back office: cancel the VIP order"),
        ("pretix_bo_06_order_canceled.png", "Back office: order in state canceled"),
        ("pretix_w2_08_vip_available_again_after_cancel.png", "W2: after the cancellation the VIP seat is available again"),
        ("pretix_w2_09_customer_order_page_paid.png", "W2: customer's order page after payment"),
    ] + _uc_figs(),
    "10. Usability and accessibility": [
        (T + "test_task_w1_create_quota_reject_then_correct.png", "Task test W1: quota rejected (-5), then corrected"),
        (T + "test_task_w1_keyboard_only_quota_form.png", "Task test W1: quota form completed with the keyboard only"),
        (T + "test_task_w2_buy_tickets_reject_then_correct.png", "Task test W2: max-per-order error, then corrected purchase"),
        (T + "test_keyboard_only_checkout.png", "Keyboard-only checkout: order placed without the mouse"),
        (T + "test_skip_link_reaches_main_content.png", "Skip link moves the focus to the main content"),
        (T + "test_focus_is_visible_on_add_to_cart.png", "Visible keyboard focus on Add to cart"),
        ("lh_control_item_add_before.png", "Lighthouse, organizer product form, before the fix"),
        ("lh_control_item_add_after.png", "Lighthouse, organizer product form, after the fix"),
        ("lh_shop_before.png", "Lighthouse, customer shop page, before"),
        ("lh_shop_after.png", "Lighthouse, customer shop page, after"),
    ] + [(f"lh_uc{i}.png", f"Lighthouse report for the key screen of UC-{i} (accessibility, best practices, SEO)")
         for i in range(1, 7)] + [
        (T + "test_axe_organizer_item_create_page.png", "axe-core scan of the organizer product form (test page state)"),
        (T + "test_remediated_rule_stays_fixed_on_organizer_page.png", "Regression test: the fixed axe rule stays fixed"),
    ],
    "11. Defensive security": [
        ("pretix_sec_01_viewer_can_list_orders.png", "Access control: the viewer role can list orders"),
        ("pretix_sec_02_viewer_403_create_product.png", "Access control: the viewer role gets HTTP 403 on the product editor"),
        ("pretix_sec_03_wrong_order_secret_404.png", "Access control: an order URL with a wrong secret returns HTTP 404"),
        ("pretix_sec_04_anonymous_redirected_to_login.png", "Access control: an anonymous visitor is sent to the login page"),
        (T + "test_rbac_viewer_cannot_cancel_orders.png", "Automated RBAC test: viewer cannot cancel an order"),
        ("zap_01_summary.png", "OWASP ZAP 2.17.0 passive scan report: alert summary"),
        ("zap_02_alert_10020.png", "OWASP ZAP: alert 10020 (missing anti-clickjacking header) on the order page"),
        ("console_pip_audit.png", "Console output: pip-audit of the pinned Python dependencies"),
    ],
    "12. Performance and recovery": [
        ("console_k6_wl1a.png", "Console output: k6 summary of workload WL-1 run a (1 user), saved at run time"),
        ("console_k6_wl5a.png", "Console output: k6 summary of workload WL-2 run a (5 users), saved at run time"),
    ],
    "13. Defect management and root cause analysis": [
        ("gh_10_issues.png", "GitHub Issues: the 19 logged defects with severity, priority, area and triage labels"),
        ("gh_11_issue_16_dz01.png", "Issue #16 (D-Z01) with the full defect record, closed by pull request #36"),
        ("gh_12_issue_23_w07.png", "Issue #23 (W-07)"),
        ("../../figures/pareto_defects.png", "Defects by category (Pareto), generated by docs/sqe/figures/make_pareto.py"),
    ],
    "14. Monitoring": [
        ("gh_13_commits_zubair_branch.png", "Commit history of the zubair branch on GitHub"),
        ("console_git_authors.png", "Console output: commits per author since the baseline"),
        ("console_git_log_graph.png", "Console output: branch graph of the repository"),
    ],
}
