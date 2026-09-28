#!/bin/sh
# Read-only health report for the running monitoring stack.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/.env"
  set +a
fi

GRAFANA_USER="${GRAFANA_USER:-admin}"
if [ -z "${GRAFANA_PASSWORD:-}" ]; then
  echo "GRAFANA_PASSWORD is not set. Copy .env.example to .env."
  exit 1
fi

PROM="http://127.0.0.1:9090"
GRAFANA="http://127.0.0.1:3012"
BLACKBOX="http://127.0.0.1:9115"
AM="http://127.0.0.1:9093"
LOKI="http://127.0.0.1:3100"

prom_query() {
  curl -fsS --get "$PROM/api/v1/query" --data-urlencode "query=$1"
}

scalar() {
  python3 -c 'import json,sys
data=json.load(sys.stdin)
result=data.get("data",{}).get("result",[])
if not result:
    print("0")
else:
    print(result[0]["value"][1])'
}

ok() {
  printf "%-24s %s\n" "$1" "$2"
}

fail=0
mark() {
  name="$1"
  url="$2"
  if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
    ok "$name" "OK"
  else
    ok "$name" "FAIL"
    fail=1
  fi
}

echo "Monitoring health report"
echo "========================"

mark "Prometheus" "$PROM/-/ready"
mark "Grafana" "$GRAFANA/api/health"
mark "Blackbox" "$BLACKBOX/metrics"
mark "Alertmanager" "$AM/-/ready"
mark "Loki" "$LOKI/ready"

servers=$(prom_query 'count(up{job=~"server-0[123]"} == 1)' | scalar | cut -d. -f1)
server_targets=$(prom_query 'count(up{job=~"server-0[123]"})' | scalar | cut -d. -f1)
websites=$(prom_query 'count(probe_success{job="blackbox-http"})' | scalar | cut -d. -f1)
web_up=$(prom_query 'count(probe_success{job="blackbox-http"} == 1)' | scalar | cut -d. -f1)
web_down=$(prom_query 'count(probe_success{job="blackbox-http"} == 0)' | scalar | cut -d. -f1)
web_slow=$(prom_query 'count(probe_duration_seconds{job="blackbox-http"} > 5)' | scalar | cut -d. -f1)
ok "Servers" "${servers}/${server_targets}"
ok "Websites" "${websites}/48"
ok "Websites UP" "$web_up"
ok "Websites DOWN" "$web_down"
ok "Websites SLOW" "$web_slow"

if [ "$servers" = "3" ] && [ "$server_targets" = "3" ]; then
  :
else
  fail=1
fi
if [ "$websites" = "48" ]; then
  :
else
  fail=1
fi

rules_ok=OK
for rules in /etc/prometheus/rules/server-alerts.yml /etc/prometheus/rules/website-alerts.yml /etc/prometheus/rules/monitoring-stack.yml; do
  if ! docker exec prometheus promtool check rules "$rules" >/dev/null 2>&1; then
    rules_ok=FAIL
    fail=1
  fi
done
if ! docker exec prometheus promtool check config /etc/prometheus/prometheus.yml >/dev/null 2>&1; then
  rules_ok=FAIL
  fail=1
fi
ok "Prometheus rules" "$rules_ok"

ds=$(curl -fsS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA/api/datasources/uid/prometheus-1")
ds_uid=$(printf '%s' "$ds" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("uid",""))')
ds_url=$(printf '%s' "$ds" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("url",""))')
if [ "$ds_uid" = "prometheus-1" ] && [ "$ds_url" = "http://prometheus:9090" ]; then
  ok "Grafana Datasource" "OK"
else
  ok "Grafana Datasource" "FAIL"
  fail=1
fi

search=$(curl -fsS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA/api/search?type=dash-db")
for uid in infrastructure-overview server-detail website-monitoring alerts-logs server-monitoring; do
  if printf '%s' "$search" | python3 -c 'import json,sys; uid=sys.argv[1]; data=json.load(sys.stdin); raise SystemExit(0 if any(d.get("uid")==uid for d in data) else 1)' "$uid"; then
    ok "$uid" "OK"
  else
    ok "$uid" "FAIL"
    fail=1
  fi
done

if curl -fsS --get "$LOKI/loki/api/v1/query" --data-urlencode 'query=count_over_time({job=~".+"}[15m])' | python3 -c 'import json,sys; data=json.load(sys.stdin); raise SystemExit(0 if data.get("data",{}).get("result") else 1)'; then
  ok "Log ingestion" "OK"
else
  ok "Log ingestion" "NO DATA"
fi

channels=$(docker run --rm -v monitoring_alertmanager_config:/out alpine:3.20 cat /out/channels.txt 2>/dev/null || true)
email=$(printf '%s\n' "$channels" | awk -F= '/^email=/{print $2}')
sms=$(printf '%s\n' "$channels" | awk -F= '/^sms=/{print $2}')
ok "Email" "${email:-NOT CONFIGURED}"
ok "SMS" "${sms:-NOT CONFIGURED}"

grafana_errors=$(docker logs grafana --since 10m 2>&1 | grep -E 'Datasource provisioning error|data source not found|dashboard provisioning error' || true)
if [ -n "$grafana_errors" ]; then
  ok "Grafana provisioning" "FAIL"
  fail=1
else
  ok "Grafana provisioning" "OK"
fi

echo "========================"
if [ "$fail" -eq 0 ]; then
  echo "Result: PASS"
else
  echo "Result: FAIL"
  exit 1
fi
