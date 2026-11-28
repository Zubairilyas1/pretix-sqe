# Performance test plan (fixed BEFORE the runs of 27 Nov 2026)

This file is committed before the measurement runs it describes; the git history shows the order
(plan commit first, `results_v2/` afterwards).

## Operation
`POST /api/v1/organizers/{org}/events/{event}/orders/` with one ticket - the state-changing call of workflow W2
(it reads and consumes the shared `Quota`). Only this operation is measured (`k6_order_create.js`).

## Limits per workload
| Workload | p95 response time | Unexpected failures |
| :--- | :-: | :-: |
| WL-1: 1 virtual user (one box-office client) | **<= 500 ms** | **< 1 %** |
| WL-2: 5 virtual users at the same time (peak sales minute) | **<= 1000 ms** | **< 1 %** |

**Why these limits.**
* An order is created when the buyer presses "Place order". Research on response times (Nielsen: 0.1 s feels instant,
  1 s keeps the user's flow of thought) and the fact that the API call is only one part of the page round trip give
  a budget of about half a second for the server when there is no contention (WL-1).
* At a peak (WL-2) a short wait is acceptable, but the user must still stay within the 1 s flow limit, so p95 may grow
  to 1000 ms.
* "Unexpected failure" = any response that is not 201. With a quota of 1 000 000 seats no rejection is expected,
  so every 4xx/5xx is unexpected. 1 % is the common availability target for a single call during a sales peak;
  a failed order is lost revenue, so a stricter target would be appropriate for production.

## Protocol
* Same build (`zubair` branch, pretix baseline `c0d887738b6c`), same machine, same starting data (seed before every run).
* Each workload is run **twice**.
* Each run: **15 s ramp/warm-up** at the target number of users (tagged `phase:warmup`, not measured), then
  **60 s measured** at the target number of users (tagged `phase:measure`). Thresholds and reported numbers use only
  `phase:measure`.
* Reported per run: p95 (ms), requests completed per second, % unexpected failures - and the comparison with the limits.
* Raw output: `results_v2/<run>.txt` (console) and `results_v2/<run>.json` (`--summary-export`), seed proof
  `results_v2/seed_<run>.txt`, environment `results_v2/environment.txt`.
