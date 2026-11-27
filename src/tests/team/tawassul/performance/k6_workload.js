// k6 workload for W2 (customer checkout) against the pretix REST API.
//
// One iteration = the purchase a box-office / reseller client performs:
//   1. GET  quota availability      (read the shared record)
//   2. POST orders/                 (create a pending order, 1 ticket)
//   3. GET  orders/{code}/          (read it back)
//
// SLA (Task 3.4): p95 response time <= 500 ms and failure rate < 1 %.
//
// Runs (each repeated twice, reseeding before each run):
//   docker run --rm -i -e VUS=1 -e TOKEN=<token> -e ITEM=<id> -e QUOTA=<id> grafana/k6 run - < k6_workload.js
//   docker run --rm -i -e VUS=5 ...
import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

const BASE = __ENV.BASE || 'http://host.docker.internal:8000';
const EV = `${BASE}/api/v1/organizers/perf-org/events/perf-conf`;
const VUS = parseInt(__ENV.VUS || '1');
const HEADERS = {
  // pretix only answers for its configured domain (url= in perf_pretix.cfg); the
  // container reaches the host as host.docker.internal, so send the real Host,
  // as a reverse proxy in front of pretix would.
  'Host': __ENV.HOST_HEADER || 'localhost:8000',
  'Authorization': `Token ${__ENV.TOKEN}`,
  'Content-Type': 'application/json',
};

const orderCreate = new Trend('order_create_ms', true);

export const options = {
  scenarios: {
    checkout: {
      executor: 'constant-vus',
      vus: VUS,
      duration: __ENV.DURATION || '60s',   // 60 s steady state
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<=500'],
    http_req_failed: ['rate<0.01'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'max'],
};

export default function () {
  const avail = http.get(`${EV}/quotas/${__ENV.QUOTA}/availability/`, { headers: HEADERS, tags: { step: 'availability' } });
  check(avail, { 'availability 200': (r) => r.status === 200 });

  const body = JSON.stringify({
    email: `k6-${__VU}-${__ITER}@sqe.test`,
    locale: 'en',
    sales_channel: 'web',
    payment_provider: 'banktransfer',
    send_email: false,
    positions: [{ item: parseInt(__ENV.ITEM), price: '10.00' }],
  });
  const created = http.post(`${EV}/orders/`, body, { headers: HEADERS, tags: { step: 'order_create' } });
  orderCreate.add(created.timings.duration);
  const ok = check(created, { 'order 201': (r) => r.status === 201 });

  if (ok) {
    const code = created.json('code');
    const read = http.get(`${EV}/orders/${code}/`, { headers: HEADERS, tags: { step: 'order_read' } });
    check(read, { 'order read 200': (r) => r.status === 200 && r.json('code') === code });
  }
}
