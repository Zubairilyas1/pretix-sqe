// k6 workload v2 (see PERF_TEST_PLAN.md): one operation, POST orders/ with one ticket.
//
// Two scenarios with the SAME number of users:
//   warmup  : 15 s, tagged phase=warmup   (ramp / warm caches, NOT measured)
//   measure : 60 s, starts at 15 s, tagged phase=measure (all reported numbers and thresholds)
//
//   docker run --rm -i -e VUS=1 -e P95=500  -e TOKEN=<token> -e ITEM=1 grafana/k6:0.57.0 run --summary-export=/dev/stdout - < k6_order_create.js
//   docker run --rm -i -e VUS=5 -e P95=1000 ...
import http from 'k6/http';
import { check } from 'k6';

const BASE = __ENV.BASE || 'http://host.docker.internal:8000';
const EV = `${BASE}/api/v1/organizers/perf-org/events/perf-conf`;
const VUS = parseInt(__ENV.VUS || '1');
const P95 = parseInt(__ENV.P95 || '500');
const HEADERS = {
  // pretix only answers for its configured domain; send the real Host as a reverse proxy would
  'Host': __ENV.HOST_HEADER || 'localhost:8000',
  'Authorization': `Token ${__ENV.TOKEN}`,
  'Content-Type': 'application/json',
};

export const options = {
  scenarios: {
    warmup: { executor: 'constant-vus', vus: VUS, duration: '15s', tags: { phase: 'warmup' } },
    measure: { executor: 'constant-vus', vus: VUS, duration: '60s', startTime: '15s', tags: { phase: 'measure' } },
  },
  thresholds: {
    'http_req_duration{phase:measure}': [`p(95)<=${P95}`],
    'http_req_failed{phase:measure}': ['rate<0.01'],
    'http_reqs{phase:measure}': ['count>0'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'max'],
};

export default function () {
  const body = JSON.stringify({
    email: `k6-${__VU}-${__ITER}@sqe.test`,
    locale: 'en',
    sales_channel: 'web',
    payment_provider: 'banktransfer',
    send_email: false,
    positions: [{ item: parseInt(__ENV.ITEM), price: '10.00' }],
  });
  const r = http.post(`${EV}/orders/`, body, { headers: HEADERS });
  check(r, { 'order 201': (res) => res.status === 201 });
}
