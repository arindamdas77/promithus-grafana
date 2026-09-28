#!/bin/sh
# Pull recent warning-and-above journal lines from the monitored servers over SSH
# and push them to Loki. This host can reach the servers, but they cannot reach
# this host inbound, so Grafana Alloy on the servers cannot push here.
set -eu

LOKI_URL="${LOKI_URL:-http://loki:3100/loki/api/v1/push}"
SSH_OPTS="-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -o UserKnownHostsFile=/root/.ssh/known_hosts -i /root/.ssh/id_ed25519"

UNITS="apache2.service nginx.service mysql.service php8.2-fpm.service php8.3-fpm.service php8.4-fpm.service docker.service postgresql.service"
unit_args=""
for unit in $UNITS; do
  unit_args="$unit_args -u $unit"
done

mkdir -p /state

ship_files() {
  server="$1"
  environment="$2"
  host="$3"
  port="$4"
  user="$5"
  state="/state/$(printf '%s' "$server" | tr ' ' '_')"
  if [ -f "$state" ]; then
    cutoff=$(cat "$state")
  else
    now=$(date +%s)
    cutoff=$((now - 7200))
  fi

  payload=$(ssh $SSH_OPTS -p "$port" "$user@$host" "CUTOFF=$cutoff SERVER='$server' ENVIRONMENT='$environment' python3 -" << 'PY'
import json, os
from datetime import datetime, timezone
from pathlib import Path

cutoff = int(os.environ["CUTOFF"])
server, environment = os.environ["SERVER"], os.environ["ENVIRONMENT"]
files = {
    Path("/var/log/apache2/error.log"): "apache2",
    Path("/var/log/nginx/error.log"): "nginx",
    Path("/var/log/mysql/error.log"): "mysql",
    Path("/var/log/php8.2-fpm.log"): "php8.2-fpm",
    Path("/var/log/php8.3-fpm.log"): "php8.3-fpm",
    Path("/var/log/php8.4-fpm.log"): "php8.4-fpm",
}
streams = {}
now = datetime.now().astimezone()

def parse_epoch(line):
    text = line.strip()
    if text.startswith("[") and "]" in text:
        inside = text[1:text.find("]")]
        for fmt in ("%a %b %d %H:%M:%S.%f %Y", "%d-%b-%Y %H:%M:%S"):
            try:
                return datetime.strptime(inside, fmt).replace(tzinfo=now.tzinfo)
            except ValueError:
                continue
    for fmt in ("%Y/%m/%d %H:%M:%S",):
        try:
            return datetime.strptime(text[:19], fmt).replace(tzinfo=now.tzinfo)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text[:26].replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None

for path, service in files.items():
    if not path.is_file():
        continue
    try:
        lines = path.read_text(errors="replace").splitlines()[-80:]
    except OSError:
        continue
    for line in lines:
        if not line.strip() or len(line) > 2000:
            continue
        parsed = parse_epoch(line)
        if parsed is None or int(parsed.timestamp()) < cutoff:
            continue
        streams.setdefault(service, []).append([str(int(parsed.timestamp() * 1_000_000_000)), line.strip()])

payload = {
    "streams": [
        {
            "stream": {
                "server": server,
                "environment": environment,
                "service": service,
                "job": "remote-file",
                "log_type": "file",
            },
            "values": values[-40:],
        }
        for service, values in streams.items()
        if values
    ]
}
print(json.dumps(payload))
PY
)

  count=$(printf '%s' "$payload" | jq '(.streams | length)' 2>/dev/null || echo 0)
  if [ "$count" != "0" ] && [ "$count" != "null" ]; then
    code=$(curl -sS -o /tmp/loki-files.out -w '%{http_code}' \
      -H 'Content-Type: application/json' \
      -X POST "$LOKI_URL" \
      --data "$payload" || echo "000")
    if [ "$code" = "204" ] || [ "$code" = "200" ]; then
      echo "$server: shipped $count file log streams"
      date +%s > "$state"
    else
      echo "$server: file log push failed (HTTP $code)"
      date +%s > "$state"
    fi
  else
    echo "$server: no new error-log lines"
    date +%s > "$state"
  fi
}

ship_one() {
  server="$1"
  environment="$2"
  host="$3"
  port="$4"
  user="$5"
  ship_files "$server" "$environment" "$host" "$port" "$user"

  raw=$(ssh $SSH_OPTS -p "$port" "$user@$host" \
    "journalctl $unit_args --since '90 seconds ago' -p warning -o json --no-pager -q" 2>/dev/null || true)

  if [ -z "$raw" ]; then
    echo "$server: no recent warning logs"
    return 0
  fi

  payload=$(printf '%s\n' "$raw" | jq -s -c --arg server "$server" --arg environment "$environment" '
    map(select(.MESSAGE != null))
    | map(. + {
        unit: (._SYSTEMD_UNIT // "journal"),
        text: (
          if (.MESSAGE | type) == "array" then
            (.MESSAGE | map(if type == "number" then [.] | implode else tostring end) | join(""))
          else
            (.MESSAGE | tostring)
          end
        )
      })
    | map(select((.text | length) > 0 and (.text | length) < 2000))
    | .[0:150]
    | group_by(.unit)
    | map({
        stream: {
          server: $server,
          environment: $environment,
          service: (.[0].unit | sub("\\.service$"; "")),
          job: "remote-journal",
          log_type: "journal"
        },
        values: map([
          ((.__REALTIME_TIMESTAMP | tostring) + "000"),
          .text
        ])
      })
    | {streams: .}
  ')

  count=$(printf '%s' "$payload" | jq '(.streams | length)')
  if [ "$count" = "0" ] || [ "$count" = "null" ]; then
    echo "$server: no recent warning logs"
    return 0
  fi

  code=$(curl -sS -o /tmp/loki-push.out -w '%{http_code}' \
    -H 'Content-Type: application/json' \
    -X POST "$LOKI_URL" \
    --data "$payload" || echo "000")

  if [ "$code" = "204" ] || [ "$code" = "200" ]; then
    echo "$server: shipped $count log streams"
  else
    echo "$server: loki push failed (HTTP $code)"
    return 0
  fi
}

ship_one "Maxbridge Development Server" "development" "89.116.32.43" "1807" "root"
ship_one "Dhellavita" "production" "46.28.44.148" "22" "root"
ship_one "Citysync" "production" "187.127.135.132" "22" "root"
