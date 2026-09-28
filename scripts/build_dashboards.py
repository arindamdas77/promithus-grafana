#!/usr/bin/env python3
"""Build the operator dashboards mounted into Grafana."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "monitoring" / "grafana" / "dashboards"
DS = {"type": "prometheus", "uid": "prometheus-1"}
LOKI = {"type": "loki", "uid": "loki-1"}

LINKS = [
    {
        "title": "Infrastructure Overview",
        "type": "link",
        "icon": "dashboard",
        "url": "/d/infrastructure-overview/infrastructure-overview",
        "keepTime": True,
        "includeVars": True,
    },
    {
        "title": "Server Detail",
        "type": "link",
        "icon": "dashboard",
        "url": "/d/server-detail/server-detail",
        "keepTime": True,
        "includeVars": True,
    },
    {
        "title": "Website Monitoring",
        "type": "link",
        "icon": "dashboard",
        "url": "/d/website-monitoring/website-monitoring-48-sites",
        "keepTime": True,
        "includeVars": True,
    },
    {
        "title": "Alerts and Logs",
        "type": "link",
        "icon": "dashboard",
        "url": "/d/alerts-logs/alerts-and-logs",
        "keepTime": True,
        "includeVars": True,
    },
]

W = 'website=~"^(?:${website})$"'
SERVICES = (
    "apache2.service|nginx.service|mysql.service|"
    "php8.2-fpm.service|php8.3-fpm.service|php8.4-fpm.service|"
    "docker.service|postgresql.service"
)


def named(expr, name, gate="website"):
    return f'label_replace(({expr}), "__name__", "{name}", "{gate}", ".+")'


def prom(ref, expr, instant=True):
    return {
        "refId": ref,
        "expr": expr,
        "instant": instant,
        "range": not instant,
        "editorMode": "code",
        "datasource": DS,
        "legendFormat": "",
    }


def stat(pid, title, expr, x, y, w=3, h=4, mappings=None, unit=None, decimals=0, no_value="0", description=""):
    defaults = {
        "decimals": decimals,
        "color": {"mode": "thresholds"},
        "thresholds": {"mode": "absolute", "steps": [{"color": "blue", "value": None}]},
        "noValue": no_value,
    }
    if unit:
        defaults["unit"] = unit
    if mappings:
        defaults["mappings"] = mappings
    return {
        "id": pid,
        "type": "stat",
        "title": title,
        "description": description,
        "datasource": DS,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "targets": [prom("A", expr)],
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": {
            "reduceOptions": {"values": False, "calcs": ["lastNotNull"], "fields": ""},
            "orientation": "auto",
            "textMode": "value",
            "colorMode": "background",
            "graphMode": "none",
            "justifyMode": "auto",
        },
    }


def row(pid, title, y):
    return {
        "id": pid,
        "type": "row",
        "title": title,
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
        "panels": [],
    }


def website_status_expr():
    return (
        "((probe_success{job=\"blackbox-http\"," + W + "} == bool 1)"
        " * on(website, instance, job, target)"
        " (probe_duration_seconds{job=\"blackbox-http\"," + W + "} > bool 5))"
        " + on(website, instance, job, target)"
        " (((probe_success{job=\"blackbox-http\"," + W + "} == bool 1)"
        " * on(website, instance, job, target)"
        " (probe_duration_seconds{job=\"blackbox-http\"," + W + "} <= bool 5)) * 2)"
    )


STATUS_MAP = [
    {
        "type": "value",
        "options": {
            "0": {"text": "DOWN", "color": "red", "index": 0},
            "1": {"text": "SLOW", "color": "orange", "index": 1},
            "2": {"text": "UP", "color": "green", "index": 2},
        },
    }
]

UP_MAP = [
    {
        "type": "value",
        "options": {
            "0": {"text": "DOWN", "color": "red", "index": 0},
            "1": {"text": "UP", "color": "green", "index": 1},
        },
    }
]

SERVICE_MAP = [
    {
        "type": "value",
        "options": {
            "0": {"text": "INACTIVE", "color": "orange", "index": 0},
            "1": {"text": "FAILED", "color": "red", "index": 1},
            "2": {"text": "RUNNING", "color": "green", "index": 2},
        },
    }
]


def color_override(field, mappings, unit=None, decimals=None, width=None):
    props = [
        {"id": "mappings", "value": mappings},
        {"id": "custom.cellOptions", "value": {"mode": "basic", "type": "color-background"}},
    ]
    if unit:
        props.append({"id": "unit", "value": unit})
    if decimals is not None:
        props.append({"id": "decimals", "value": decimals})
    if width:
        props.append({"id": "custom.width", "value": width})
    return {"matcher": {"id": "byName", "options": field}, "properties": props}


def unit_override(field, unit, decimals, width=None):
    props = [{"id": "unit", "value": unit}, {"id": "decimals", "value": decimals}]
    if width:
        props.append({"id": "custom.width", "value": width})
    return {"matcher": {"id": "byName", "options": field}, "properties": props}


def table(pid, title, targets, y, h, organize, overrides, sort_field, sort_desc=False, description="", page=False):
    options = {
        "showHeader": True,
        "cellHeight": "sm",
        "footer": {"show": False, "reducer": ["sum"], "countRows": False, "fields": ""},
        "sortBy": [{"displayName": sort_field, "desc": sort_desc}],
        "frameIndex": 0,
    }
    if page:
        options["enablePagination"] = True
        options["pageSize"] = 15
    return {
        "id": pid,
        "type": "table",
        "title": title,
        "description": description,
        "datasource": DS,
        "gridPos": {"h": h, "w": 24, "x": 0, "y": y},
        "targets": targets,
        "transformations": [
            {"id": "joinByLabels", "options": {"join": organize["join"], "value": "__name__"}},
            {
                "id": "organize",
                "options": {
                    "excludeByName": organize["exclude"],
                    "indexByName": organize["index"],
                    "renameByName": organize["rename"],
                },
            },
            {"id": "sortBy", "options": {"sort": [{"desc": sort_desc, "field": sort_field}]}},
        ],
        "fieldConfig": {"defaults": {"custom": {"align": "auto"}}, "overrides": overrides},
        "options": options,
    }


def timeseries(pid, title, expr, x, y, w, h, unit, description=""):
    target = prom("A", expr, instant=False)
    target["legendFormat"] = "{{server}}"
    return {
        "id": pid,
        "type": "timeseries",
        "title": title,
        "description": description,
        "datasource": DS,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "targets": [target],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "decimals": 1,
                "custom": {"drawStyle": "line", "lineWidth": 2, "fillOpacity": 10, "showPoints": "never", "spanNulls": False},
            },
            "overrides": [],
        },
        "options": {
            "legend": {"displayMode": "list", "placement": "bottom", "calcs": []},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
    }


def shell():
    return {
        "annotations": {"list": []},
        "editable": False,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "links": LINKS,
        "schemaVersion": 39,
        "style": "dark",
        "tags": ["operations"],
        "timezone": "browser",
        "time": {"from": "now-6h", "to": "now"},
        "refresh": "30s",
        "version": 1,
    }


def server_metric_exprs(selector):
    job = f'job=~"server-0[123]"{selector}'
    swap = f"""
(
  (
    (
      (node_memory_SwapTotal_bytes{{{job}}} - node_memory_SwapFree_bytes{{{job}}})
      / node_memory_SwapTotal_bytes{{{job}}}
    ) * 100
  )
  and on(server, environment, instance, job)
  (node_memory_SwapTotal_bytes{{{job}}} > 0)
)
or
(
  (node_memory_SwapTotal_bytes{{{job}}} == bool 0) * 0
)
""".strip()
    return {
        "up_status": f'max by (server, environment) (up{{{job}}})',
        "cpu_pct": f'avg by (server, environment) (100 - (rate(node_cpu_seconds_total{{mode="idle",{job}}}[5m]) * 100))',
        "mem_pct": f'max by (server, environment) ((1 - (node_memory_MemAvailable_bytes{{{job}}} / node_memory_MemTotal_bytes{{{job}}})) * 100)',
        "swap_pct": f"max by (server, environment) ({swap})",
        "disk_pct": (
            "max by (server, environment) (100 * (1 - ("
            f'node_filesystem_avail_bytes{{mountpoint="/",fstype!~"tmpfs|overlay|squashfs",{job}}}'
            " / "
            f'node_filesystem_size_bytes{{mountpoint="/",fstype!~"tmpfs|overlay|squashfs",{job}}}'
            ")))"
        ),
        "load1": f"max by (server, environment) (node_load1{{{job}}})",
        "uptime_s": f"max by (server, environment) (time() - node_boot_time_seconds{{{job}}})",
    }


def server_table(pid, title, y, h, selector):
    exprs = server_metric_exprs(selector)
    refs = []
    for ref, (metric, expr) in zip("ABCDEFG", exprs.items()):
        refs.append(prom(ref, named(expr, metric, "server")))
    organize = {
        "join": ["server", "environment"],
        "exclude": {"instance": True, "job": True, "Time": True, "__name__": True, "mountpoint": True, "fstype": True, "device": True},
        "index": {
            "server": 0,
            "environment": 1,
            "up_status": 2,
            "cpu_pct": 3,
            "mem_pct": 4,
            "swap_pct": 5,
            "disk_pct": 6,
            "load1": 7,
            "uptime_s": 8,
        },
        "rename": {
            "server": "Server",
            "environment": "Environment",
            "up_status": "Status",
            "cpu_pct": "CPU",
            "mem_pct": "Memory",
            "swap_pct": "Swap",
            "disk_pct": "Disk",
            "load1": "Load",
            "uptime_s": "Uptime",
        },
    }
    panel = table(
        pid,
        title,
        refs,
        y,
        h,
        organize,
        [
            color_override("Status", UP_MAP, decimals=0, width=110),
            unit_override("CPU", "percent", 0, 90),
            unit_override("Memory", "percent", 0, 100),
            unit_override("Swap", "percent", 0, 90),
            unit_override("Disk", "percent", 0, 90),
            unit_override("Load", "none", 2, 90),
            unit_override("Uptime", "s", 0, 140),
        ],
        "Server",
        description="One row per server. Open Server Detail from a server name.",
    )
    panel["fieldConfig"]["overrides"].append(
        {
            "matcher": {"id": "byName", "options": "Server"},
            "properties": [
                {
                    "id": "links",
                    "value": [
                        {
                            "title": "Server detail",
                            "url": "/d/server-detail/server-detail?var-server=${__data.fields.Server}",
                            "targetBlank": False,
                        }
                    ],
                },
                {"id": "custom.width", "value": 280},
            ],
        }
    )
    return panel


def service_expr(selector):
    base = f'name=~"{SERVICES}"{selector}'
    expr = f"""
max by (server, name) (
  (node_systemd_unit_state{{{base}, state="active"}} == 1) * 2
  or
  (node_systemd_unit_state{{{base}, state="failed"}} == 1) * 1
  or
  (node_systemd_unit_state{{{base}, state="inactive"}} == 1) * 0
)
""".strip()
    return f'label_replace({named(expr, "unit_state", "name")}, "service", "$1", "name", "(.*)\\\\.service")'


def service_table(pid, title, y, h, selector):
    organize = {
        "join": ["server", "service"],
        "exclude": {"instance": True, "job": True, "Time": True, "__name__": True, "name": True, "state": True, "type": True},
        "index": {"service": 0, "server": 1, "unit_state": 2},
        "rename": {"service": "Service", "server": "Server", "unit_state": "Status"},
    }
    return table(
        pid,
        title,
        [prom("A", service_expr(selector))],
        y,
        h,
        organize,
        [color_override("Status", SERVICE_MAP, decimals=0, width=140)],
        "Server",
        description="Services Node Exporter actually reports on these hosts.",
    )


def infrastructure():
    dash = shell()
    dash.update(
        {
            "uid": "infrastructure-overview",
            "title": "Infrastructure Overview",
            "description": "Is everything healthy? Start here, then open the server, website, or logs.",
            "tags": ["operations", "overview"],
            "templating": {"list": []},
        }
    )
    crit = 'count(ALERTS{alertstate="firing",severity="critical"}) or vector(0)'
    warn = 'count(ALERTS{alertstate="firing",severity="warning"}) or vector(0)'
    panels = [
        stat(1, "Total Servers", 'count(up{job=~"server-0[123]"}) or vector(0)', 0, 0, description="Node Exporter targets."),
        stat(2, "Servers UP", 'count(up{job=~"server-0[123]"} == 1) or vector(0)', 3, 0),
        stat(3, "Servers DOWN", 'count(up{job=~"server-0[123]"} == 0) or vector(0)', 6, 0),
        stat(4, "Total Websites", 'count(probe_success{job="blackbox-http"}) or vector(0)', 9, 0),
        stat(5, "Websites UP", 'count(probe_success{job="blackbox-http"} == 1) or vector(0)', 12, 0),
        stat(6, "Websites DOWN", 'count(probe_success{job="blackbox-http"} == 0) or vector(0)', 15, 0),
        stat(7, "Critical Alerts", crit, 18, 0, description="Firing critical alerts."),
        stat(8, "Warning Alerts", warn, 21, 0),
        row(9, "SERVER HEALTH", 4),
        server_table(10, "Servers", 5, 8, ""),
        row(11, "SERVICES", 13),
        service_table(12, "Service Status", 14, 10, ""),
        row(13, "MONITORING STACK", 24),
        stat(14, "Prometheus", 'up{job="prometheus"}', 0, 25, w=5, h=4, mappings=UP_MAP, no_value="DOWN"),
        stat(15, "Grafana", 'up{job="grafana"}', 5, 25, w=5, h=4, mappings=UP_MAP, no_value="DOWN"),
        stat(16, "Blackbox", 'up{job="blackbox-exporter"}', 10, 25, w=5, h=4, mappings=UP_MAP, no_value="DOWN"),
        stat(17, "Alertmanager", 'up{job="alertmanager"}', 15, 25, w=4, h=4, mappings=UP_MAP, no_value="DOWN"),
        stat(18, "Loki", 'up{job="loki"}', 19, 25, w=5, h=4, mappings=UP_MAP, no_value="DOWN"),
    ]
    for item in panels:
        if item["title"] in {"Servers DOWN", "Websites DOWN", "Critical Alerts"}:
            item["fieldConfig"]["defaults"]["thresholds"] = {
                "mode": "absolute",
                "steps": [{"color": "green", "value": None}, {"color": "red", "value": 1}],
            }
        elif item["title"] == "Warning Alerts":
            item["fieldConfig"]["defaults"]["thresholds"] = {
                "mode": "absolute",
                "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 1}],
            }
        elif item["title"] in {"Servers UP", "Websites UP"}:
            item["fieldConfig"]["defaults"]["thresholds"] = {
                "mode": "absolute",
                "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}],
            }
    dash["panels"] = panels
    return dash


def server_detail():
    dash = shell()
    sel = ',server=~"^(?:${server})$"'
    job = f'job=~"server-0[123]"{sel}'
    exprs = server_metric_exprs(sel)
    dash.update(
        {
            "uid": "server-detail",
            "title": "Server Detail",
            "description": "One server at a time. Select All to compare the three servers.",
            "tags": ["operations", "servers"],
            "templating": {
                "list": [
                    {
                        "name": "server",
                        "label": "Server",
                        "type": "query",
                        "datasource": DS,
                        "definition": 'label_values(up{job=~"server-0[123]"}, server)',
                        "query": {"query": 'label_values(up{job=~"server-0[123]"}, server)', "refId": "StandardVariableQuery"},
                        "includeAll": True,
                        "allValue": ".+",
                        "multi": False,
                        "refresh": 1,
                        "sort": 1,
                        "current": {"selected": True, "text": "All", "value": "$__all"},
                        "options": [{"selected": True, "text": "All", "value": "$__all"}],
                        "regex": "",
                        "hide": 0,
                    }
                ]
            },
        }
    )
    cards = []
    titles = [
        ("Status", "up_status", UP_MAP, None),
        ("CPU", "cpu_pct", None, "percent"),
        ("Memory", "mem_pct", None, "percent"),
        ("Swap", "swap_pct", None, "percent"),
        ("Disk", "disk_pct", None, "percent"),
        ("Load", "load1", None, "none"),
        ("Uptime", "uptime_s", None, "s"),
    ]
    for index, (title, key, mapping, unit) in enumerate(titles):
        width = 4 if index < 3 else 3
        x = sum(4 if i < 3 else 3 for i in range(index)) if index < 3 else 12 + (index - 3) * 3
        # 4+4+4=12, then 3*4=12. Wait 7 cards: 3*4=12 and 4*3=12. Indices 0,1,2 width 4. 3,4,5,6 width 3.
        if index < 3:
            x = index * 4
            w = 4
        else:
            x = 12 + (index - 3) * 3
            w = 3
        cards.append(
            stat(
                index + 1,
                title,
                named(exprs[key], key, "server"),
                x,
                0,
                w=w,
                h=4,
                mappings=mapping,
                unit=unit,
                decimals=2 if title == "Load" else 0,
                description="Filtered by the server variable.",
            )
        )
    graphs = [
        ("CPU", f'avg by (server) (100 - (rate(node_cpu_seconds_total{{mode="idle",{job}}}[5m]) * 100))', "percent", 0),
        ("Memory", f'max by (server) ((1 - (node_memory_MemAvailable_bytes{{{job}}} / node_memory_MemTotal_bytes{{{job}}})) * 100)', "percent", 12),
        ("Swap", f"max by (server) ({exprs['swap_pct']})", "percent", 0),
        ("Disk", exprs["disk_pct"].replace("max by (server, environment)", "max by (server)"), "percent", 12),
        ("Load", f"max by (server) (node_load1{{{job}}})", "none", 0),
        ("Network Receive", f'sum by (server) (rate(node_network_receive_bytes_total{{device!~"lo|veth.*|docker.*|br-.*",{job}}}[5m]))', "Bps", 12),
        ("Network Transmit", f'sum by (server) (rate(node_network_transmit_bytes_total{{device!~"lo|veth.*|docker.*|br-.*",{job}}}[5m]))', "Bps", 0),
    ]
    panels = cards + [row(8, "TIME SERIES", 4)]
    y = 5
    pid = 20
    for title, expr, unit, x in graphs:
        if x == 0 and pid != 20:
            y += 8
        panels.append(timeseries(pid, title, expr, x, y, 12, 8, unit))
        pid += 1
    y += 8
    panels.append(row(30, "SERVICES ON THIS SERVER", y))
    panels.append(service_table(31, "Service Status", y + 1, 10, sel))
    panels.append(
        {
            "id": 32,
            "type": "text",
            "title": "Next step",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": y + 11},
            "options": {
                "mode": "markdown",
                "content": "If a service is FAILED or a resource is high, open **Alerts and Logs** and filter the same server.",
            },
        }
    )
    dash["panels"] = panels
    return dash


def empty_or(expr, label, metric):
    placeholder = (
        'label_replace(label_replace(label_replace(vector(0), "website", "'
        + label
        + '", "__name__", ".*"), "target", "-", "__name__", ".*"), "__name__", "'
        + metric
        + '", "website", "'
        + label
        + '")'
    )
    return f"({expr}) or (({placeholder}) unless on() ({expr}))"


def reason_map():
    options = {
        "0": ("No HTTP response", "red"),
        "200": ("OK", "green"),
        "201": ("Created", "green"),
        "204": ("No content", "green"),
        "301": ("Redirect", "blue"),
        "302": ("Redirect", "blue"),
        "400": ("Bad request", "orange"),
        "401": ("Unauthorized", "orange"),
        "403": ("Forbidden", "orange"),
        "404": ("Not found", "yellow"),
        "500": ("Server error", "red"),
        "502": ("Bad gateway", "red"),
        "503": ("Unavailable", "red"),
        "504": ("Gateway timeout", "red"),
    }
    return [{
        "type": "value",
        "options": {
            code: {"text": label, "color": color, "index": index}
            for index, (code, (label, color)) in enumerate(options.items())
        },
    }]


def loki_stat(pid, title, expr, x, y, w=4, description=""):
    return {
        "id": pid,
        "type": "stat",
        "title": title,
        "description": description,
        "datasource": LOKI,
        "gridPos": {"h": 4, "w": w, "x": x, "y": y},
        "targets": [{"refId": "A", "datasource": LOKI, "expr": expr, "queryType": "instant"}],
        "fieldConfig": {
            "defaults": {
                "decimals": 0,
                "noValue": "0",
                "color": {"mode": "thresholds"},
                "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "red", "value": 1}]},
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {"values": False, "calcs": ["lastNotNull"], "fields": ""},
            "colorMode": "background",
            "graphMode": "none",
            "textMode": "value",
        },
    }


def loki_bars(pid, title, targets, x, y, w, h, description=""):
    return {
        "id": pid,
        "type": "bargauge",
        "title": title,
        "description": description,
        "datasource": LOKI,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "targets": targets,
        "fieldConfig": {
            "defaults": {"decimals": 0, "min": 0, "color": {"mode": "palette-classic"}},
            "overrides": [],
        },
        "options": {
            "orientation": "horizontal",
            "displayMode": "gradient",
            "showUnfilled": False,
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        },
    }


def loki_target(ref, expr, legend):
    return {
        "refId": ref,
        "datasource": LOKI,
        "expr": expr,
        "queryType": "instant",
        "legendFormat": legend,
    }


def logs_panel(pid, title, expr, y, h, description):
    return {
        "id": pid,
        "type": "logs",
        "title": title,
        "description": description,
        "datasource": LOKI,
        "gridPos": {"h": h, "w": 24, "x": 0, "y": y},
        "targets": [{"refId": "A", "datasource": LOKI, "expr": expr, "queryType": "range"}],
        "options": {
            "showTime": True,
            "showLabels": True,
            "showCommonLabels": False,
            "wrapLogMessage": True,
            "prettifyLogMessage": False,
            "enableLogDetails": True,
            "dedupStrategy": "none",
            "sortOrder": "Descending",
        },
    }


def website():
    status = website_status_expr()
    http = f'probe_http_status_code{{job="blackbox-http",{W}}}'
    duration = f'probe_duration_seconds{{job="blackbox-http",{W}}}'
    success = f'probe_success{{job="blackbox-http",{W}}}'
    down_match = f"({success} == 0)"
    slow_match = f"({duration} > 5)"
    ssl_ms = (
        f'(probe_ssl_earliest_cert_expiry{{job="blackbox-http",{W}}} * 1000)'
        f' or ({success} * 0)'
    )
    ssl_days = (
        f'((probe_ssl_earliest_cert_expiry{{job="blackbox-http",{W}}} - time()) / 86400)'
        f' or (({success} * 0) - 1)'
    )
    last = f'(timestamp({success}) * 1000)'

    def phase(name):
        return f'probe_http_duration_seconds{{job="blackbox-http",phase="{name}",{W}}}'

    dash = shell()
    dash.update(
        {
            "uid": "website-monitoring",
            "title": "Website Monitoring - 48 Sites",
            "description": "Read top to bottom: how many are down, why, then timing and certificates.",
            "tags": ["blackbox", "ssl", "uptime", "website"],
            "refresh": "30s",
            "templating": {
                "list": [
                    {
                        "name": "website",
                        "label": "Website",
                        "type": "query",
                        "datasource": DS,
                        "definition": 'label_values(probe_success{job="blackbox-http"}, website)',
                        "query": {"query": 'label_values(probe_success{job="blackbox-http"}, website)', "refId": "StandardVariableQuery"},
                        "includeAll": True,
                        "allValue": ".+",
                        "multi": False,
                        "refresh": 1,
                        "sort": 1,
                        "current": {"selected": True, "text": "All", "value": "$__all"},
                        "options": [{"selected": True, "text": "All", "value": "$__all"}],
                        "regex": "",
                    }
                ]
            },
        }
    )
    cards = [
        stat(1, "Total", f"count({success}) or vector(0)", 0, 0, w=5),
        stat(2, "UP", f"count({success} == 1) or vector(0)", 5, 0, w=5),
        stat(3, "DOWN", f"count({success} == 0) or vector(0)", 10, 0, w=5),
        stat(4, "SLOW", f"count({duration} > 5) or vector(0)", 15, 0, w=4, description="Answered, but slower than 5 seconds."),
        stat(5, "SSL Expiring", f'count(((probe_ssl_earliest_cert_expiry{{job="blackbox-http",{W}}} - time()) < 14 * 24 * 3600) and (probe_ssl_earliest_cert_expiry{{job="blackbox-http",{W}}} > 0)) or vector(0)', 19, 0, w=5, description="Certificates with fewer than 14 days left."),
    ]
    for item in cards:
        if item["title"] == "DOWN":
            item["fieldConfig"]["defaults"]["thresholds"]["steps"] = [{"color": "green", "value": None}, {"color": "red", "value": 1}]
        elif item["title"] in {"SLOW", "SSL Expiring"}:
            item["fieldConfig"]["defaults"]["thresholds"]["steps"] = [{"color": "green", "value": None}, {"color": "orange", "value": 1}]
        elif item["title"] == "UP":
            item["fieldConfig"]["defaults"]["thresholds"]["steps"] = [{"color": "red", "value": None}, {"color": "green", "value": 1}]

    code_cards = []
    code_specs = [
        (200, "HTTP 200", False),
        (0, "No response", True),
        (401, "HTTP 401", True),
        (403, "HTTP 403", True),
        (404, "HTTP 404", False),
        (502, "HTTP 502", True),
        (503, "HTTP 503", True),
        (504, "HTTP 504", True),
    ]
    for index, (code, title, bad) in enumerate(code_specs):
        panel = stat(
            40 + index,
            title,
            f'count(probe_http_status_code{{job="blackbox-http",{W}}} == {code}) or vector(0)',
            index * 3,
            8,
            w=3,
            description="404 stays UP: several APIs have no route at /.",
        )
        if code == 200:
            panel["fieldConfig"]["defaults"]["thresholds"]["steps"] = [{"color": "red", "value": None}, {"color": "green", "value": 1}]
        elif bad:
            panel["fieldConfig"]["defaults"]["thresholds"]["steps"] = [{"color": "green", "value": None}, {"color": "red", "value": 1}]
        else:
            panel["fieldConfig"]["defaults"]["thresholds"]["steps"] = [{"color": "green", "value": None}, {"color": "yellow", "value": 1}]
        code_cards.append(panel)

    reason_override = {
        "matcher": {"id": "byName", "options": "What happened"},
        "properties": [
            {"id": "mappings", "value": reason_map()},
            {"id": "decimals", "value": 0},
            {"id": "custom.width", "value": 170},
            {"id": "custom.cellOptions", "value": {"mode": "basic", "type": "color-background"}},
        ],
    }
    status_override = color_override("Status", STATUS_MAP, decimals=0, width=110)
    http_override = {
        "matcher": {"id": "byName", "options": "HTTP Status"},
        "properties": [
            {"id": "decimals", "value": 0},
            {"id": "custom.width", "value": 120},
            {"id": "custom.cellOptions", "value": {"mode": "basic", "type": "color-text"}},
            {
                "id": "thresholds",
                "value": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "green", "value": 200},
                        {"color": "blue", "value": 300},
                        {"color": "orange", "value": 400},
                        {"color": "red", "value": 500},
                    ],
                },
            },
        ],
    }
    website_link = {
        "matcher": {"id": "byName", "options": "Website"},
        "properties": [
            {"id": "custom.width", "value": 300},
            {
                "id": "links",
                "value": [{
                    "title": "Open this website",
                    "url": "/d/website-monitoring/website-monitoring-48-sites?var-website=${__data.fields.Website}",
                }],
            },
        ],
    }
    join = ["website", "target"]
    exclude = {"instance": True, "job": True, "Time": True, "__name__": True, "target": True, "phase": True}

    def website_table(pid, title, y, h, pieces, index, rename, sort_field, sort_desc, description, page=False, extra=None):
        overrides = [website_link, status_override, reason_override, http_override, unit_override("Response Time", "s", 2, 130)]
        if extra:
            overrides.extend(extra)
        panel = table(
            pid,
            title,
            [prom(ref, expr) for ref, expr in pieces],
            y,
            h,
            {"join": join, "exclude": exclude, "index": index, "rename": rename},
            overrides,
            sort_field,
            sort_desc,
            description,
            page,
        )
        return panel

    ssl_override = {
        "matcher": {"id": "byName", "options": "SSL"},
        "properties": [
            {"id": "decimals", "value": 0},
            {"id": "custom.width", "value": 160},
            {
                "id": "mappings",
                "value": [
                    {"type": "value", "options": {"-1": {"text": "No certificate", "color": "red", "index": 0}}},
                    {"type": "range", "options": {"from": 0, "to": 3, "result": {"text": "Critical", "color": "red"}}},
                    {"type": "range", "options": {"from": 3, "to": 14, "result": {"text": "Expiring", "color": "orange"}}},
                    {"type": "range", "options": {"from": 14, "to": 10000, "result": {"text": "OK", "color": "green"}}},
                ],
            },
            {"id": "custom.cellOptions", "value": {"mode": "basic", "type": "color-background"}},
        ],
    }
    down_ssl = empty_or(
        f"(({ssl_days}) and on(website, instance, job, target) {down_match})",
        "No websites currently down",
        "ssl_health",
    )
    down_pieces = [
        ("A", empty_or(f"({status}) and on(website, instance, job, target) {down_match}", "No websites currently down", "website_status")),
        ("B", empty_or(f"({http}) and on(website, instance, job, target) {down_match}", "No websites currently down", "reason")),
        ("C", down_ssl),
    ]
    slow_pieces = [
        ("A", empty_or(f"({status}) and on(website, instance, job, target) {slow_match}", "No slow websites", "website_status")),
        ("B", empty_or(f"({http}) and on(website, instance, job, target) {slow_match}", "No slow websites", "reason")),
    ]
    all_pieces = [
        ("A", named(status, "website_status")),
        ("B", named(http, "reason")),
        ("C", named(ssl_days, "ssl_health")),
    ]
    ssl_pieces = [
        ("A", named(ssl_ms, "ssl_expiry_ms")),
        ("B", named(ssl_days, "ssl_health")),
    ]
    ssl_panel = table(
        21,
        "SSL certificates",
        [prom(ref, expr) for ref, expr in ssl_pieces],
        71,
        12,
        {
            "join": join,
            "exclude": exclude,
            "index": {"website": 0, "ssl_health": 1, "ssl_expiry_ms": 2},
            "rename": {"website": "Website", "ssl_health": "SSL", "ssl_expiry_ms": "Expiry date"},
        },
        [
            website_link,
            ssl_override,
            {
                "matcher": {"id": "byName", "options": "Expiry date"},
                "properties": [
                    {"id": "unit", "value": "dateTimeAsIso"},
                    {"id": "custom.width", "value": 220},
                    {
                        "id": "mappings",
                        "value": [{"type": "value", "options": {"0": {"text": "No certificate", "color": "red", "index": 0}}}],
                    },
                ],
            },
        ],
        "SSL",
        description="OK, Expiring, Critical, or No certificate, with the certificate date.",
        page=True,
    )
    ssl_panel["gridPos"]["y"] = 8

    panels = cards + [
        {
            "id": 30,
            "type": "text",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 4},
            "options": {
                "mode": "markdown",
                "content": (
                    "Status is **UP**, **DOWN**, or **SLOW**. "
                    "**What happened** says Unavailable, Forbidden, Unauthorized, or No HTTP response. "
                    "**SSL** says OK, Expiring, Critical, or No certificate. "
                    "A page that only says the route is missing is still UP."
                ),
            },
        },
        row(17, "SSL", 7),
        ssl_panel,
        row(32, "DOWN WEBSITES", 20),
        website_table(
            9,
            "Down websites",
            21,
            8,
            down_pieces,
            {"website": 0, "website_status": 1, "reason": 2, "ssl_health": 3},
            {"website": "Website", "website_status": "Status", "reason": "What happened", "ssl_health": "SSL"},
            "Website",
            False,
            "Only sites that failed. The message row appears when every site is up.",
            extra=[ssl_override],
        ),
        row(10, "SLOW WEBSITES", 29),
        website_table(
            11,
            "Slow websites",
            30,
            6,
            slow_pieces,
            {"website": 0, "website_status": 1, "reason": 2},
            {"website": "Website", "website_status": "Status", "reason": "What happened"},
            "Website",
            False,
            "Sites that answered and took more than 5 seconds.",
        ),
        row(12, "ALL WEBSITES", 36),
        website_table(
            13,
            "All websites",
            37,
            12,
            all_pieces,
            {"website": 0, "website_status": 1, "reason": 2, "ssl_health": 3},
            {"website": "Website", "website_status": "Status", "reason": "What happened", "ssl_health": "SSL"},
            "Status",
            False,
            "Every monitored site, in words.",
            page=True,
            extra=[ssl_override],
        ),
    ]
    dash["panels"] = panels
    return dash


def alert_key(selector):
    return f'label_join(ALERTS{{{selector}}}, "alert_key", "/", "alertname", "server", "website", "instance")'


def without_alertstate(selector):
    kept = [part.strip() for part in selector.split(",") if not part.strip().startswith("alertstate=")]
    return ",".join(kept)


def alert_started(selector):
    return f'label_join((ALERTS_FOR_STATE{{{without_alertstate(selector)}}} * 1000), "alert_key", "/", "alertname", "server", "website", "instance")'


def alert_duration(selector):
    return f'label_join((time() - ALERTS_FOR_STATE{{{without_alertstate(selector)}}}), "alert_key", "/", "alertname", "server", "website", "instance")'


def alert_placeholder(message, metric):
    return (
        'label_replace(label_replace(label_replace(vector(0), "alertname", "'
        + message
        + '", "__name__", ".*"), "alert_key", "none", "__name__", ".*"), "__name__", "'
        + metric
        + '", "alertname", "'
        + message
        + '")'
    )


def alerts_logs():
    dash = shell()
    dash.update(
        {
            "uid": "alerts-logs",
            "title": "Alerts and Logs",
            "description": "Website alerts, server alerts, then logs split by server and by log type.",
            "tags": ["operations", "alerts", "logs"],
            "templating": {
                "list": [
                    {
                        "name": "search",
                        "label": "Search",
                        "type": "textbox",
                        "query": "",
                        "current": {"text": "", "value": ""},
                        "options": [],
                    },
                ]
            },
        }
    )
    web_sel = 'alertstate="firing",category=~"website|ssl"'
    srv_sel = 'alertstate="firing",category!~"website|ssl"'
    severity_map = [{
        "type": "value",
        "options": {
            "critical": {"text": "critical", "color": "red"},
            "warning": {"text": "warning", "color": "orange"},
        },
    }]
    alert_overrides = [
        color_override("Severity", severity_map, width=120),
        unit_override("Started", "dateTimeAsIso", 0, 190),
        unit_override("Duration", "s", 0, 130),
        {
            "matcher": {"id": "byName", "options": "Alert"},
            "properties": [
                {"id": "custom.width", "value": 240},
                {
                    "id": "mappings",
                    "value": [{
                        "type": "value",
                        "options": {
                            "WebsiteDown": {"text": "Website is down"},
                            "WebsiteSlow": {"text": "Website is slow"},
                            "SSLCertificateExpiringSoon": {"text": "SSL expires within 14 days"},
                            "SSLCertificateCritical": {"text": "SSL expires within 3 days"},
                            "ServerDown": {"text": "Server is down"},
                            "NodeExporterDown": {"text": "Node Exporter is down"},
                            "HighCPU": {"text": "CPU above 80%"},
                            "CriticalCPU": {"text": "CPU above 95%"},
                            "HighMemory": {"text": "Memory above 80%"},
                            "CriticalMemory": {"text": "Memory above 90%"},
                            "HighDisk": {"text": "Disk above 80%"},
                            "CriticalDisk": {"text": "Disk above 90%"},
                            "HighLoad": {"text": "Load is high"},
                            "HighSwap": {"text": "Swap above 50%"},
                            "MonitoringComponentDown": {"text": "Monitoring component is down"},
                        },
                    }],
                },
                {
                    "id": "links",
                    "value": [
                        {"title": "Server detail", "url": "/d/server-detail/server-detail?var-server=${__data.fields.Server}"},
                        {"title": "Website", "url": "/d/website-monitoring/website-monitoring-48-sites?var-website=${__data.fields.Website}"},
                    ],
                },
            ],
        },
    ]

    def alert_table(pid, title, y, selector, empty_message, description):
        pieces = [
            ("A", f'({named(alert_key(selector), "firing", "alertname")}) or ({alert_placeholder(empty_message, "firing")} unless on() (ALERTS{{{selector}}}))'),
            ("B", f'({named(alert_started(selector), "started_ms", "alertname")}) or ({alert_placeholder(empty_message, "started_ms")} unless on() (ALERTS{{{selector}}}))'),
            ("C", f'({named(alert_duration(selector), "duration_s", "alertname")}) or ({alert_placeholder(empty_message, "duration_s")} unless on() (ALERTS{{{selector}}}))'),
        ]
        return table(
            pid,
            title,
            [prom(ref, expr) for ref, expr in pieces],
            y,
            9,
            {
                "join": ["alert_key"],
                "exclude": {"instance": True, "job": True, "Time": True, "__name__": True, "alert_key": True, "alertstate": True, "category": True, "target": True},
                "index": {"alertname": 0, "severity": 1, "server": 2, "website": 3, "started_ms": 4, "duration_s": 5},
                "rename": {"alertname": "Alert", "severity": "Severity", "server": "Server", "website": "Website", "started_ms": "Started", "duration_s": "Duration"},
            },
            alert_overrides,
            "Severity",
            False,
            description,
        )

    panels = [
        stat(1, "Critical", 'count(ALERTS{alertstate="firing",severity="critical"}) or vector(0)', 0, 0, w=6),
        stat(2, "Warning", 'count(ALERTS{alertstate="firing",severity="warning"}) or vector(0)', 6, 0, w=6),
        stat(3, "Website alerts", 'count(ALERTS{alertstate="firing",category=~"website|ssl"}) or vector(0)', 12, 0, w=6),
        stat(4, "Server alerts", 'count(ALERTS{alertstate="firing",category!~"website|ssl"}) or vector(0)', 18, 0, w=6, description="Server, CPU, memory, disk, and monitoring-stack alerts."),
        {
            "id": 7,
            "type": "text",
            "gridPos": {"h": 3, "w": 24, "x": 0, "y": 4},
            "options": {
                "mode": "markdown",
                "content": "Website alerts and server alerts are separate. Below that, each server has its own logs, and each service has its own panel.",
            },
        },
        row(8, "ALERTS BY WEBSITE", 7),
        alert_table(9, "Website alerts", 8, web_sel, "No website alerts", "One row per firing website or SSL alert."),
        row(10, "ALERTS BY SERVER", 17),
        alert_table(11, "Server alerts", 18, srv_sel, "No server alerts", "Server alerts appear here. The row says so when none are firing."),
    ]
    log_groups = [
        ("MAXBRIDGE DEVELOPMENT SERVER", "Maxbridge.*", [
            ("apache2", "Apache"),
            ("mysql", "MySQL"),
            ("php8.2-fpm", "PHP 8.2"),
            ("php8.3-fpm", "PHP 8.3"),
            ("php8.4-fpm", "PHP 8.4"),
        ]),
        ("DHELLAVITA", "Dhellavita", [
            ("apache2", "Apache"),
            ("php8.2-fpm", "PHP 8.2"),
        ]),
        ("CITYSYNC", "Citysync", [
            ("nginx", "Nginx"),
        ]),
    ]
    y = 27
    pid = 40
    for heading, server_match, services in log_groups:
        panels.append(row(pid, heading, y))
        pid += 1
        y += 1
        for service, label in services:
            expr = '{server=~"' + server_match + '", service="' + service + '", log_type="file"} |= "$search"'
            panels.append(logs_panel(
                pid,
                label,
                expr,
                y,
                7,
                heading.title() + " — " + label + " only. An empty panel means this log has no new lines.",
            ))
            pid += 1
            y += 7
    panels[0]["fieldConfig"]["defaults"]["thresholds"]["steps"] = [{"color": "green", "value": None}, {"color": "red", "value": 1}]
    panels[1]["fieldConfig"]["defaults"]["thresholds"]["steps"] = [{"color": "green", "value": None}, {"color": "orange", "value": 1}]
    panels[2]["fieldConfig"]["defaults"]["thresholds"]["steps"] = [{"color": "green", "value": None}, {"color": "red", "value": 1}]
    panels[3]["fieldConfig"]["defaults"]["thresholds"]["steps"] = [{"color": "green", "value": None}, {"color": "red", "value": 1}]
    dash["panels"] = panels
    return dash




def promql_from(dash):
    found = []

    def walk(panels):
        for panel in panels or []:
            for target in panel.get("targets") or []:
                expr = target.get("expr")
                ds = target.get("datasource") or panel.get("datasource") or {}
                if expr and ds.get("type") == "prometheus":
                    found.append((dash["title"], panel.get("title"), expr))
            walk(panel.get("panels"))

    walk(dash.get("panels"))
    return found


def fill_custom_options(dash):
    for var in dash.get("templating", {}).get("list", []):
        if var.get("type") != "custom" or var.get("options"):
            continue
        options = []
        for part in var.get("query", "").split(","):
            text, _, value = part.partition(":")
            text, value = text.strip(), value.strip()
            if not text:
                continue
            options.append({"text": text, "value": value, "selected": value == var.get("current", {}).get("value")})
        var["options"] = options


def main():
    dashboards = {
        "infrastructure-overview.json": infrastructure(),
        "server-detail.json": server_detail(),
        "website-monitoring.json": website(),
        "alerts-logs.json": alerts_logs(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    queries = []
    for name, dash in dashboards.items():
        fill_custom_options(dash)
        path = OUT / name
        path.write_text(json.dumps(dash, indent=2) + "\n")
        queries.extend(promql_from(dash))
        print(f"wrote {path}")
    query_path = ROOT / "scripts" / ".dashboard-queries.txt"
    lines = []
    for title, panel, expr in queries:
        lines.append(f"# {title} :: {panel}\n{expr}\n")
    query_path.write_text("\n".join(lines))
    print(f"queries {len(queries)}")


if __name__ == "__main__":
    main()
