# k6 Performance Test Report: W2 checkout via the REST API

**Date:** 2026-11-26
**Tool:** Grafana k6 (Docker image `grafana/k6`)
**Script:** `k6_workload.js`
**Raw results:** `results/k6_run_*.txt` (console summary), `results/k6_run_*.json` (`--summary-export`) and `results/seed_*.txt` (reset proof)

## 1. Workload and SLA

One iteration is the purchase a box-office or reseller client makes:
1. `GET quotas/{id}/availability/`: read the shared record
2. `POST orders/`: create a pending order with 1 ticket
3. `GET orders/{code}/`: read it back

| SLA | Threshold (k6) |
| :--- | :--- |
| 95th percentile response time ≤ 500 ms | `http_req_duration: p(95)<=500` |
| Failure rate < 1 % | `http_req_failed: rate<0.01` |

**Protocol:** steady state of 60 s at a constant number of virtual users (VUs).

| Run | VUs | Repeats |
| :-: | :-: | :-: |
| Run 1, baseline | 1 | 1a, 1b |
| Run 2, concurrency | 5 | 2a, 2b |

**Identical starting data:** `seed_perf_event.py` deletes all orders and carts and resets the quota to 1 000 000 before **every** run. Each `results/seed_*.txt` shows the same seeded state.

**System under test:** pretix at baseline `c0d887738b6c`, `DEBUG=false`, compressed static assets, served by waitress (8 threads) with whitenoise (`perf_server.py`). SQLite database. Run on one laptop (Windows 10), with k6 in Docker Desktop on the same machine.

## 2. Results

| Run | VUs | Requests | Throughput (req/s) | Iterations/s | Avg (ms) | Median (ms) | **p95 (ms)** | p95 order create (ms) | **Error %** | SLA |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 1a | 1 | 264 | 4.39 | 1.46 | 226.8 | 164.7 | **472.4** | 570.5 | **0.00** | ✅ met |
| 1b | 1 | 300 | 4.97 | 1.66 | 199.9 | 148.5 | **397.7** | 479.5 | **0.00** | ✅ met |
| 2a | 5 | 458 | 7.40 | 3.12 | 664.8 | 539.9 | **1 390** | 1 570 | **26.41** | ❌ failed |
| 2b | 5 | 390 | 6.38 | 2.59 | 777.6 | 616.6 | **1 580** | 1 760 | **21.53** | ❌ failed |

**Averages of the two repeats:**

| VUs | p95 (ms) | Throughput (req/s) | Errors |
| :-: | :-: | :-: | :-: |
| 1 | 435 | 4.68 | 0 % |
| 5 | 1 485 | 6.89 | 24.0 % |

Repeat variation is 17 % for p95 at 1 VU and 13 % at 5 VUs. That is normal for a shared laptop, and both repeats lead to the same verdict.

## 3. Analysis

1. **Baseline (1 VU) meets the SLA**, but only just: p95 435 ms against a 500 ms limit. The **order-creation request alone** has p95 480–570 ms, so it already misses the target in run 1a. The reads (availability, order detail) are fast and pull the overall p95 down.
2. **At 5 VUs the SLA fails on both criteria.** p95 rises about 3.4× (to 1.4–1.6 s). Throughput rises only 1.5× (4.7 to 6.9 req/s), so the server is saturated on writes, not on CPU for reads.
3. **All failures are order creations.** The `availability 200` and `order read 200` checks pass at 100 %, while `order 201` succeeds in only 37–46 % of attempts. The server log for every failure shows `django.db.utils.OperationalError: database is locked`, returned to the client as **HTTP 500**.
   - **Cause:** SQLite allows one writer at a time, and pretix's order creation takes write locks (quota check, order, positions, payment, transaction ledger) in one transaction. Concurrent writers wait, then time out.
   - **This is a property of the test database.** pretix's supported production database is PostgreSQL, which has row-level locking.
4. **Correctness under load holds.** After run 2b the database contained:

| Measure | Value |
| :--- | :-: |
| successful `POST orders/` responses | 74 |
| orders in the database | 74 |
| order positions | 74 |
| orders without positions | 0 |
| seats taken from the quota | 74 |

Every failed request was rolled back completely: no half-written orders and no lost seats. This matches the failure-recovery test (`test_failure_recovery.py`).

5. **Graceful degradation is missing:** an overloaded database surfaces as HTTP **500**, not as `503 Service Unavailable` with `Retry-After` or as `409`. A client cannot tell "try again" from "bug". Combined with Area 2's W-03 (retry without an idempotency key creates a duplicate), a naive client retry policy is risky. Recorded as risk **PR-PERF-01**.

## 4. Threats to validity
- SQLite instead of PostgreSQL. The 5-VU error rate would most likely be much lower on PostgreSQL; the latency trend is still meaningful.
- waitress on Windows instead of gunicorn and nginx on Linux.
- k6 and pretix share one laptop, so k6's own CPU use is included in the measurements.
- Only 60 s per run, with no warm-up phase. The first iterations include cold caches.
- The workload covers the API path of W2 only; the presale web checkout (HTML rendering) is not load-tested.

## 5. Recommendations
1. Repeat runs 2a/2b on PostgreSQL before using these numbers for a release decision.
2. Make `POST orders/` the SLA focus, since it has the highest p95 even at 1 VU.
3. Return 503 with `Retry-After` on lock timeouts, and recommend `X-Idempotency-Key` for all API clients.

## 6. How to reproduce
```bash
cd src
set PRETIX_CONFIG_FILE=tests/team/tawassul/performance/perf_pretix.cfg
../.venv/Scripts/python manage.py migrate
../.venv/Scripts/python manage.py compilejsi18n && ../.venv/Scripts/python manage.py collectstatic --noinput && ../.venv/Scripts/python manage.py compress
../.venv/Scripts/python tests/team/tawassul/performance/patch_manifest_windows.py   # Windows only
../.venv/Scripts/python tests/team/tawassul/performance/perf_server.py              # keep running
# per run (1a, 1b with VUS=1; 2a, 2b with VUS=5):
../.venv/Scripts/python manage.py shell -c "exec(open('tests/team/tawassul/performance/seed_perf_event.py').read())"
docker run --rm -i -e VUS=1 -e TOKEN=<.perf_token> -e ITEM=1 -e QUOTA=1 grafana/k6 run - < tests/team/tawassul/performance/k6_workload.js
```
