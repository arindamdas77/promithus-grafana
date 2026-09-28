#!/bin/sh
# Render Alertmanager config from environment variables.
# Empty SMTP/webhook values stay unconfigured. No placeholder credentials are written.
set -eu

out=/out/alertmanager.yml
status=/out/channels.txt

reject_unsafe() {
  printf '%s' "$1" | grep -q "['\"\\]" && return 0 || return 1
}

email=0
sms=0
webhook=0

smtp_host="${SMTP_HOST:-}"
smtp_port="${SMTP_PORT:-587}"
smtp_from="${SMTP_FROM:-}"
smtp_to="${SMTP_TO:-}"
smtp_user="${SMTP_USER:-}"
smtp_password="${SMTP_PASSWORD:-}"
sms_url="${SMS_WEBHOOK_URL:-}"
hook_url="${ALERT_WEBHOOK_URL:-}"

for value in "$smtp_host" "$smtp_port" "$smtp_from" "$smtp_to" "$smtp_user" "$smtp_password" "$sms_url" "$hook_url"; do
  if reject_unsafe "$value"; then
    echo "Refusing notification value with quotes or backslashes" >&2
    exit 1
  fi
done

if [ -n "$smtp_host" ] && [ -n "$smtp_from" ] && [ -n "$smtp_to" ]; then
  email=1
fi
if [ -n "$sms_url" ]; then
  sms=1
fi
if [ -n "$hook_url" ]; then
  webhook=1
fi

cat > "$out" << EOF
route:
  receiver: default
  group_by: ['alertname', 'severity', 'server', 'website']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: default
EOF

if [ "$email" -eq 1 ]; then
  cat >> "$out" << EOF
    email_configs:
      - to: '$smtp_to'
        from: '$smtp_from'
        smarthost: '${smtp_host}:${smtp_port}'
        require_tls: ${SMTP_REQUIRE_TLS:-true}
EOF
  if [ -n "$smtp_user" ]; then
    cat >> "$out" << EOF
        auth_username: '$smtp_user'
        auth_password: '$smtp_password'
EOF
  fi
fi

if [ "$sms" -eq 1 ]; then
  cat >> "$out" << EOF
    webhook_configs:
      - url: '$sms_url'
        send_resolved: true
EOF
fi

if [ "$webhook" -eq 1 ]; then
  cat >> "$out" << EOF
    webhook_configs:
      - url: '$hook_url'
        send_resolved: true
EOF
fi

{
  if [ "$email" -eq 1 ]; then echo "email=CONFIGURED"; else echo "email=NOT CONFIGURED"; fi
  if [ "$sms" -eq 1 ]; then echo "sms=CONFIGURED"; else echo "sms=NOT CONFIGURED"; fi
  if [ "$webhook" -eq 1 ]; then echo "webhook=CONFIGURED"; else echo "webhook=NOT CONFIGURED"; fi
} > "$status"

echo "Alertmanager config rendered"
