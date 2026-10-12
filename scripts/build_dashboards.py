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
    "apache2.service|nginx.service|mysql.service|mariadb.service|"
    "postgresql@16-main.service|"
    "php8.2-fpm.service|php8.3-fpm.service|php8.4-fpm.service|"
    "docker.service|redis.service|redis-server.service|ssh.service"
)
FS_MATCH = 'fstype!~"tmpfs|devtmpfs|overlay|squashfs|aufs",mountpoint!~"/boot/efi"'
DISK_DEV = 'device=~"sd.*|vd.*|nvme.*|xvd.*|mmcblk.*"'
NET_DEV = 'device!~"lo|veth.*|docker.*|br-.*|cali.*|flannel.*|cni.*|virbr.*"'


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
            "0": {"text": "Stopped", "color": "orange", "index": 0},
            "1": {"text": "Failed", "color": "red", "index": 1},
            "2": {"text": "Running", "color": "green", "index": 2},
        },
    }
]

HEALTH_MAP = [
    {
        "type": "value",
        "options": {
            "0": {"text": "Offline", "color": "red", "index": 0},
            "1": {"text": "Critical", "color": "red", "index": 1},
            "2": {"text": "Warning", "color": "orange", "index": 2},
            "3": {"text": "Healthy", "color": "green", "index": 3},
            "4": {"text": "No Data", "color": "blue", "index": 4},
        },
    }
]

SERVICE_NAME_MAP = [
    {
        "type": "value",
        "options": {
            "apache2": {"text": "Apache", "index": 0},
            "nginx": {"text": "Nginx", "index": 1},
            "mysql": {"text": "MySQL", "index": 2},
            "mariadb": {"text": "MariaDB", "index": 3},
            "postgresql@16-main": {"text": "PostgreSQL", "index": 4},
            "php8.2-fpm": {"text": "PHP 8.2", "index": 5},
            "php8.3-fpm": {"text": "PHP 8.3", "index": 6},
            "php8.4-fpm": {"text": "PHP 8.4", "index": 7},
            "docker": {"text": "Docker", "index": 8},
            "redis": {"text": "Redis", "index": 9},
            "redis-server": {"text": "Redis", "index": 10},
            "ssh": {"text": "SSH", "index": 11},
        },
    }
]

PERCENT_STEPS = [
    {"color": "green", "value": None},
    {"color": "orange", "value": 80},
    {"color": "red", "value": 90},
]

ALERT_TEXT_MAP = [
    {
        "type": "value",
        "options": {
            "WebsiteDown": {"text": "Website is down"},
            "WebsiteSlow": {"text": "Website is slow"},
            "SSLCertificateExpiringSoon": {"text": "SSL expires within 14 days"},
            "SSLCertificateCritical": {"text": "SSL expires within 3 days"},
            "ServerDown": {"text": "Server is offline"},
            "NodeExporterDown": {"text": "Metrics exporter is offline"},
            "HighCPU": {"text": "CPU above 80%"},
            "CriticalCPU": {"text": "CPU above 95%"},
            "HighMemory": {"text": "Memory above 80%"},
            "CriticalMemory": {"text": "Memory above 90%"},
            "HighDisk": {"text": "Disk above 80%"},
            "CriticalDisk": {"text": "Disk above 90%"},
            "HighLoad": {"text": "Load is above CPU capacity"},
            "HighSwap": {"text": "Swap above 50%"},
            "MonitoringComponentDown": {"text": "Monitoring component is down"},
            "ServiceFailed": {"text": "A service has failed"},
            "ServiceStopped": {"text": "A service is stopped"},
            "DiskFillingSoon": {"text": "A disk may fill within 14 days"},
            "NetworkErrors": {"text": "Network errors are high"},
            "ServerRebooted": {"text": "Server rebooted"},
            "MonitoringDataStale": {"text": "Monitoring data is stale"},
            "ZombieProcesses": {"text": "Many zombie processes"},
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


def heat_override(field, width):
    return {
        "matcher": {"id": "byName", "options": field},
        "properties": [
            {"id": "unit", "value": "percent"},
            {"id": "decimals", "value": 0},
            {"id": "min", "value": 0},
            {"id": "max", "value": 100},
            {"id": "custom.width", "value": width},
            {"id": "color", "value": {"mode": "thresholds"}},
            {"id": "custom.cellOptions", "value": {"type": "color-text", "mode": "basic"}},
            {"id": "thresholds", "value": {"mode": "absolute", "steps": PERCENT_STEPS}},
        ],
    }


def tone(panel, kind):
    if kind == "good":
        steps = [{"color": "red", "value": None}, {"color": "green", "value": 1}]
    elif kind == "warn":
        steps = [{"color": "green", "value": None}, {"color": "orange", "value": 1}]
    elif kind == "bad":
        steps = [{"color": "green", "value": None}, {"color": "red", "value": 1}]
    else:
        steps = [{"color": "blue", "value": None}]
    panel["fieldConfig"]["defaults"]["thresholds"] = {"mode": "absolute", "steps": steps}
    return panel


def gauge(pid, title, expr, x, y, w, h, description, unit="percent", maximum=100, decimals=0, steps=None):
    target = prom("A", expr)
    target["legendFormat"] = "{{server}}"
    return {
        "id": pid,
        "type": "gauge",
        "title": title,
        "description": description,
        "datasource": DS,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "targets": [target],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "min": 0,
                "max": maximum,
                "decimals": decimals,
                "noValue": "No Data",
                "color": {"mode": "thresholds"},
                "thresholds": {"mode": "absolute", "steps": steps or PERCENT_STEPS},
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {"values": False, "calcs": ["lastNotNull"], "fields": ""},
            "orientation": "auto",
            "showThresholdLabels": False,
            "showThresholdMarkers": True,
            "sizing": "auto",
        },
    }


def note(pid, content, y, h=3):
    return {
        "id": pid,
        "type": "text",
        "gridPos": {"h": h, "w": 24, "x": 0, "y": y},
        "options": {"mode": "markdown", "content": content},
    }


def job_of(selector):
    return f'job=~"server-0[123]"{selector}'


def labelled(expr, issue, next_step, source="server", regex=".+"):
    return (
        "max by (server, issue, next_step) ("
        f'label_replace(label_replace(({expr}), "issue", "{issue}", "{source}", "{regex}"), '
        f'"next_step", "{next_step}", "server", ".+")'
        ")"
    )


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


def timeseries(pid, title, expr, x, y, w, h, unit, description="", decimals=1, maximum=None, thresholds=None):
    target = prom("A", expr, instant=False)
    target["legendFormat"] = "{{server}}"
    custom = {"drawStyle": "line", "lineWidth": 2, "fillOpacity": 10, "showPoints": "never", "spanNulls": False}
    defaults = {"unit": unit, "decimals": decimals, "custom": custom}
    if maximum is not None:
        defaults["min"] = 0
        defaults["max"] = maximum
    if thresholds:
        defaults["thresholds"] = {"mode": "absolute", "steps": thresholds}
        custom["thresholdsStyle"] = {"mode": "dashed"}
    return {
        "id": pid,
        "type": "timeseries",
        "title": title,
        "description": description,
        "datasource": DS,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "targets": [target],
        "fieldConfig": {"defaults": defaults, "overrides": []},
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


def job_metrics(selector):
    job = job_of(selector)
    match = f"{FS_MATCH},{job}"
    cpu = f'avg by (server, environment) (100 - (rate(node_cpu_seconds_total{{mode="idle",{job}}}[5m]) * 100))'
    cpu_server = f'avg by (server) (100 - (rate(node_cpu_seconds_total{{mode="idle",{job}}}[5m]) * 100))'
    memory = (
        "max by (server, environment) ("
        f"(1 - (node_memory_MemAvailable_bytes{{{job}}} / node_memory_MemTotal_bytes{{{job}}})) * 100"
        ")"
    )
    memory_server = (
        "max by (server) ("
        f"(1 - (node_memory_MemAvailable_bytes{{{job}}} / node_memory_MemTotal_bytes{{{job}}})) * 100"
        ")"
    )
    disk = (
        "max by (server, environment) (100 * (1 - ("
        f"node_filesystem_avail_bytes{{{match}}} / node_filesystem_size_bytes{{{match}}}"
        ")))"
    )
    disk_server = (
        "max by (server) (100 * (1 - ("
        f"node_filesystem_avail_bytes{{{match}}} / node_filesystem_size_bytes{{{match}}}"
        ")))"
    )
    disk_mount = (
        "100 * (1 - ("
        f"node_filesystem_avail_bytes{{{match}}} / node_filesystem_size_bytes{{{match}}}"
        "))"
    )
    root = (
        "max by (server) (100 * (1 - ("
        f'node_filesystem_avail_bytes{{mountpoint="/",fstype!~"tmpfs|overlay|squashfs",{job}}}'
        " / "
        f'node_filesystem_size_bytes{{mountpoint="/",fstype!~"tmpfs|overlay|squashfs",{job}}}'
        ")))"
    )
    swap = (
        "max by (server, environment) ("
        f"(((node_memory_SwapTotal_bytes{{{job}}} - node_memory_SwapFree_bytes{{{job}}}) "
        f"/ node_memory_SwapTotal_bytes{{{job}}}) * 100 "
        f"and on(server, environment, instance, job) (node_memory_SwapTotal_bytes{{{job}}} > 0)) "
        f"or ((node_memory_SwapTotal_bytes{{{job}}} == bool 0) * 0)"
        ")"
    )
    swap_server = (
        "max by (server) ("
        "("
        f"(((node_memory_SwapTotal_bytes{{{job}}} - node_memory_SwapFree_bytes{{{job}}}) "
        f"/ node_memory_SwapTotal_bytes{{{job}}}) * 100 "
        f"and (node_memory_SwapTotal_bytes{{{job}}} > 0))"
        f" or ((node_memory_SwapTotal_bytes{{{job}}} == bool 0) * 0)"
        ")"
        ")"
    )
    load = f"max by (server, environment) (node_load1{{{job}}})"
    load_server = f"max by (server) (node_load1{{{job}}})"
    load_ratio = (
        "max by (server, environment) ("
        f"node_load1{{{job}}} / on(server, instance) group_left(environment) "
        f'count by (server, instance) (node_cpu_seconds_total{{{job},mode="idle"}})'
        ")"
    )
    load_ratio_server = (
        "max by (server) ("
        f"node_load1{{{job}}} / on(server, instance) group_left "
        f'count by (server, instance) (node_cpu_seconds_total{{{job},mode="idle"}})'
        ")"
    )
    cpus = f'count by (server, environment) (node_cpu_seconds_total{{{job},mode="idle"}})'
    uptime = f"max by (server, environment) (time() - node_boot_time_seconds{{{job}}})"
    up = f"max by (server, environment) (up{{{job}}})"
    failed = (
        "count by (server, environment) ("
        f'node_systemd_unit_state{{{job},name=~"{SERVICES}",state="failed"}} == 1'
        ")"
    )
    return {
        "job": job,
        "match": match,
        "cpu": cpu,
        "cpu_server": cpu_server,
        "memory": memory,
        "memory_server": memory_server,
        "disk": disk,
        "disk_server": disk_server,
        "disk_mount": disk_mount,
        "root": root,
        "swap": swap,
        "swap_server": swap_server,
        "load": load,
        "load_server": load_server,
        "load_ratio": load_ratio,
        "load_ratio_server": load_ratio_server,
        "cpus": cpus,
        "uptime": uptime,
        "up": up,
        "failed": failed,
    }


def health_expr(selector):
    m = job_metrics(selector)
    up = m["up"]
    cpu = m["cpu"]
    critical = f'(({cpu}) > 90) or (({m["memory"]}) > 90) or (({m["disk"]}) > 90) or (({m["failed"]}) > 0)'
    warning = (
        f'(({cpu}) > 80) or (({m["memory"]}) > 80) or (({m["disk"]}) > 80) '
        f'or (({m["swap"]}) > 50) or (({m["load_ratio"]}) > 1.5)'
    )
    return (
        f"((({up} == 1) unless on (server, environment) ({cpu})) * 4) "
        f"or ({up} == 0) "
        f"or ((({up} == 1) * 1) and on (server, environment) ({critical})) "
        f"or ((({up} == 1) * 2) and on (server, environment) ({warning})) "
        f"or (({up} == 1) * 3)"
    )


def attention_expr(selector):
    m = job_metrics(selector)
    job = m["job"]
    days = (
        "max by (server, mountpoint) ("
        f"(node_filesystem_avail_bytes{{{m['match']}}} "
        f"/ (-delta(node_filesystem_avail_bytes{{{m['match']}}}[6h]) * 4)) "
        f"and (-delta(node_filesystem_avail_bytes{{{m['match']}}}[6h]) > 0)"
        ")"
    )
    parts = [
        labelled(
            f"((max by (server) (up{{{job}}})) == bool 0) == 1",
            "Server is offline",
            "Prometheus cannot collect metrics. Check power, the network path, and that Node Exporter is running on port 9100.",
        ),
        labelled(
            f"((max by (server) (up{{{job}}}) == 1) unless on (server) ({m['cpu_server']}))",
            "Metrics are missing",
            "Node Exporter answers, but CPU metrics are missing, so health cannot be judged.",
        ),
        labelled(f"({m['cpu_server']}) > 90", "CPU is above 90 percent", "Almost all CPU time is busy. Find the runaway or stuck program."),
        labelled(
            f"((({m['cpu_server']}) > 80) unless (({m['cpu_server']}) > 90))",
            "CPU is above 80 percent",
            "CPU is high right now. Check whether a backup, deploy, or application is responsible.",
        ),
        labelled(f"({m['memory_server']}) > 90", "Memory is above 90 percent", "RAM is nearly exhausted. Find the program using the most memory before the server starts swapping heavily."),
        labelled(
            f"((({m['memory_server']}) > 80) unless (({m['memory_server']}) > 90))",
            "Memory is above 80 percent",
            "RAM is getting full. Check application memory and whether cache can be freed.",
        ),
        labelled(
            f"({m['disk_mount']}) > 90",
            "Disk $1 is above 90 percent",
            "Free space on this filesystem before applications fail to write.",
            "mountpoint",
            ".+",
        ),
        labelled(
            f"((({m['disk_mount']}) > 80) unless (({m['disk_mount']}) > 90))",
            "Disk $1 is above 80 percent",
            "This filesystem is filling up. Find what is growing before it becomes critical.",
            "mountpoint",
            ".+",
        ),
        labelled(
            f"({m['swap_server']}) > 50",
            "Swap is above 50 percent",
            "The server is using disk as extra memory, which is slow. Find the program using the most RAM.",
        ),
        labelled(
            f"({m['load_ratio_server']}) > 1.5",
            "Load is above CPU capacity",
            "The 1-minute load is more than 1.5 times the number of CPUs, so work is waiting.",
        ),
        labelled(
            f'node_systemd_unit_state{{{job},name=~"{SERVICES}",state="failed"}} == 1',
            "Service failed: $1",
            "This service crashed. Read its log on Alerts and Logs, fix the error, then start it again.",
            "name",
            "(.+)",
        ),
        labelled(
            f'node_systemd_unit_state{{{job},name=~"{SERVICES}",state="inactive"}} == 1',
            "Service stopped: $1",
            "This service is installed but not running. Start it if it should be up.",
            "name",
            "(.+)",
        ),
        labelled(
            f"({days}) < 14",
            "Disk $1 may fill within 14 days",
            "At the growth rate of the last 6 hours, this filesystem runs out of space soon. Find the files that are growing.",
            "mountpoint",
            ".+",
        ),
        labelled(
            "sum by (server) ("
            f"rate(node_network_receive_errs_total{{{NET_DEV},{job}}}[5m]) "
            f"+ rate(node_network_transmit_errs_total{{{NET_DEV},{job}}}[5m])"
            ") > 1",
            "Network errors are above 1 per second",
            "The network interface is reporting errors. Check the link and recent network changes.",
        ),
        labelled(
            "sum by (server) ("
            f"rate(node_network_receive_drop_total{{{NET_DEV},{job}}}[5m]) "
            f"+ rate(node_network_transmit_drop_total{{{NET_DEV},{job}}}[5m])"
            ") > 1",
            "Dropped packets are above 1 per second",
            "Packets are being dropped. The server or the network path cannot keep up.",
        ),
        labelled(
            f'(sum by (server) (node_processes_state{{{job},state="Z"}})) >= 10',
            "Many zombie processes",
            "Ten or more finished programs were not collected by their parent. Find the application that is leaving them behind.",
        ),
        labelled(
            f'(sum by (server) (node_processes_state{{{job},state="D"}})) >= 5',
            "Processes are stuck on disk",
            "Several programs are waiting on disk. Check disk busy time and the application log.",
        ),
        labelled(
            f"(max by (server) (changes(node_boot_time_seconds{{{job}}}[30m]))) > 0",
            "Server rebooted in the last 30 minutes",
            "Confirm the reboot was planned and that web, database, and Docker services came back.",
        ),
    ]
    return "\nor\n".join(parts)


def filesystem_exprs(selector):
    match = job_metrics(selector)["match"]
    size = f"max by (server, mountpoint) (node_filesystem_size_bytes{{{match}}})"
    free = f"max by (server, mountpoint) (node_filesystem_avail_bytes{{{match}}})"
    used = (
        "max by (server, mountpoint) ("
        f"node_filesystem_size_bytes{{{match}}} - node_filesystem_avail_bytes{{{match}}}"
        ")"
    )
    pct = (
        "max by (server, mountpoint) (100 * (1 - ("
        f"node_filesystem_avail_bytes{{{match}}} / node_filesystem_size_bytes{{{match}}}"
        ")))"
    )
    daily = f"max by (server, mountpoint) (-delta(node_filesystem_avail_bytes{{{match}}}[6h]))"
    days = (
        "("
        "max by (server, mountpoint) ("
        f"(node_filesystem_avail_bytes{{{match}}} / (-delta(node_filesystem_avail_bytes{{{match}}}[6h]) * 4)) "
        f"and (-delta(node_filesystem_avail_bytes{{{match}}}[6h]) > 0)"
        ")"
        ") or ("
        f"(max by (server, mountpoint) (node_filesystem_size_bytes{{{match}}} * 0 + 1000000)) "
        "unless on (server, mountpoint) "
        f"(-delta(node_filesystem_avail_bytes{{{match}}}[6h]) > 0)"
        ")"
    )
    return {
        "size_bytes": size,
        "free_bytes": free,
        "used_bytes": used,
        "used_pct": pct,
        "daily_bytes": daily,
        "days_left": days,
    }


def proc_count(selector, state):
    job = job_of(selector)
    return (
        f'(sum by (server) (node_processes_state{{{job},state="{state}"}})) '
        f"or (max by (server) (up{{{job}}}) * 0)"
    )


def show_each(panel):
    panel["targets"][0]["legendFormat"] = "{{server}}"
    panel["options"]["reduceOptions"]["values"] = True
    panel["options"]["textMode"] = "value_and_name"
    return panel


def server_table(pid, title, y, h, selector):
    m = job_metrics(selector)
    job = m["job"]
    identity = label_replace_up(job)
    pieces = [
        ("A", named(identity, "up_status", "server")),
        ("B", named(f"max by (server, environment, nodename) (node_uname_info{{{job}}})", "hostname_ok", "server")),
        ("C", named(f"max by (server, environment, pretty_name) (node_os_info{{{job}}})", "os_ok", "server")),
        ("D", named(health_expr(selector), "health", "server")),
        ("E", named(m["cpu"], "cpu_pct", "server")),
        ("F", named(m["memory"], "mem_pct", "server")),
        ("G", named(m["disk"], "disk_pct", "server")),
        ("H", named(m["load"], "load1", "server")),
        ("I", named(m["cpus"], "cpu_count", "server")),
        ("J", named(m["uptime"], "uptime_s", "server")),
    ]
    organize = {
        "join": ["server", "environment"],
        "exclude": {
            "instance": True,
            "job": True,
            "Time": True,
            "__name__": True,
            "up_status": True,
            "hostname_ok": True,
            "os_ok": True,
            "mountpoint": True,
            "fstype": True,
            "device": True,
        },
        "index": {
            "server": 0,
            "nodename": 1,
            "ip": 2,
            "pretty_name": 3,
            "environment": 4,
            "health": 5,
            "cpu_pct": 6,
            "mem_pct": 7,
            "disk_pct": 8,
            "load1": 9,
            "cpu_count": 10,
            "uptime_s": 11,
        },
        "rename": {
            "server": "Server",
            "nodename": "Hostname",
            "ip": "IP address",
            "pretty_name": "Operating system",
            "environment": "Environment",
            "health": "Health",
            "cpu_pct": "CPU",
            "mem_pct": "Memory",
            "disk_pct": "Disk",
            "load1": "Load",
            "cpu_count": "CPUs",
            "uptime_s": "Uptime",
        },
    }
    panel = table(
        pid,
        title,
        [prom(ref, expr) for ref, expr in pieces],
        y,
        h,
        organize,
        [
            color_override("Health", HEALTH_MAP, decimals=0, width=120),
            heat_override("CPU", 90),
            heat_override("Memory", 100),
            heat_override("Disk", 90),
            unit_override("Load", "none", 2, 80),
            unit_override("CPUs", "none", 0, 70),
            unit_override("Uptime", "s", 0, 140),
        ],
        "Health",
        description=(
            "One row per server. Health is Healthy when CPU, memory, and disk are under 80%, "
            "swap is under 50%, and load is within CPU capacity. Warning means one of those is high. "
            "Critical means a resource is over 90% or a service has failed. Offline means Node Exporter "
            "cannot be scraped. Disk is the fullest data filesystem, excluding the small EFI partition. "
            "Open a server name for detail."
        ),
    )
    panel["fieldConfig"]["overrides"].append(
        {
            "matcher": {"id": "byName", "options": "Server"},
            "properties": [
                {
                    "id": "links",
                    "value": [
                        {
                            "title": "Open server",
                            "url": "/d/server-detail/server-detail?var-server=${__data.fields.Server}",
                            "targetBlank": False,
                        }
                    ],
                },
                {"id": "custom.width", "value": 240},
            ],
        }
    )
    for field, width in (("Hostname", 130), ("IP address", 140), ("Operating system", 190), ("Environment", 120)):
        panel["fieldConfig"]["overrides"].append(
            {"matcher": {"id": "byName", "options": field}, "properties": [{"id": "custom.width", "value": width}]}
        )
    return panel


def label_replace_up(job):
    return (
        f'label_replace(max by (server, environment, instance) (up{{{job}}}), '
        '"ip", "$1", "instance", "([^:]+):.*")'
    )


def service_expr(selector):
    base = f'{job_of(selector)},name=~"{SERVICES}"'
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
    panel = table(
        pid,
        title,
        [prom("A", service_expr(selector))],
        y,
        h,
        organize,
        [
            color_override("Status", SERVICE_MAP, decimals=0, width=140),
            {
                "matcher": {"id": "byName", "options": "Service"},
                "properties": [
                    {"id": "mappings", "value": SERVICE_NAME_MAP},
                    {"id": "custom.width", "value": 160},
                ],
            },
        ],
        "Server",
        description=(
            "Installed services only. A missing product is not listed and is not treated as healthy or failed. "
            "Docker shows whether the Docker service is running. Per-container CPU, memory, and restarts are not collected."
        ),
    )
    return panel


def attention_table(pid, title, y, h, selector):
    organize = {
        "join": ["server", "issue"],
        "exclude": {"instance": True, "job": True, "Time": True, "__name__": True, "environment": True, "mountpoint": True, "name": True},
        "index": {"server": 0, "issue": 1, "reading": 2, "next_step": 3},
        "rename": {
            "server": "Server",
            "issue": "What is happening",
            "reading": "Reading",
            "next_step": "What to check",
        },
    }
    return table(
        pid,
        title,
        [prom("A", named(attention_expr(selector), "reading", "server"))],
        y,
        h,
        organize,
        [
            unit_override("Reading", "none", 1, 110),
            {
                "matcher": {"id": "byName", "options": "What is happening"},
                "properties": [{"id": "custom.width", "value": 320}],
            },
            {
                "matcher": {"id": "byName", "options": "What to check"},
                "properties": [{"id": "custom.width", "value": 520}],
            },
        ],
        "Server",
        description=(
            "A row appears only when a live check is outside its limit. Reading is the current measurement: "
            "a percent for CPU, memory, disk, and swap; a ratio for load; a count for services and processes; "
            "errors per second for the network; days for a disk that is filling. An empty table means none of these checks are failing."
        ),
    )


def filesystem_table(pid, y, selector):
    exprs = filesystem_exprs(selector)
    pieces = [(ref, named(exprs[key], key, "server")) for ref, key in zip("ABCDEF", exprs)]
    organize = {
        "join": ["server", "mountpoint"],
        "exclude": {"instance": True, "job": True, "Time": True, "__name__": True, "device": True, "fstype": True, "environment": True},
        "index": {
            "server": 0,
            "mountpoint": 1,
            "size_bytes": 2,
            "used_bytes": 3,
            "free_bytes": 4,
            "used_pct": 5,
            "daily_bytes": 6,
            "days_left": 7,
        },
        "rename": {
            "server": "Server",
            "mountpoint": "Filesystem",
            "size_bytes": "Size",
            "used_bytes": "Used",
            "free_bytes": "Free",
            "used_pct": "Used",
            "daily_bytes": "Change in 6 hours",
            "days_left": "Days until full",
        },
    }
    # "Used" is used twice if both used_bytes and used_pct rename to Used. Keep percent name distinct.
    organize["rename"]["used_pct"] = "Used percent"
    panel = table(
        pid,
        "Disk space",
        [prom(ref, expr) for ref, expr in pieces],
        y,
        8,
        organize,
        [
            unit_override("Size", "bytes", 1, 110),
            unit_override("Used", "bytes", 1, 110),
            unit_override("Free", "bytes", 1, 110),
            heat_override("Used percent", 130),
            unit_override("Change in 6 hours", "bytes", 1, 160),
            {
                "matcher": {"id": "byName", "options": "Days until full"},
                "properties": [
                    {"id": "unit", "value": "d"},
                    {"id": "decimals", "value": 0},
                    {"id": "custom.width", "value": 150},
                    {
                        "id": "mappings",
                        "value": [
                            {
                                "type": "range",
                                "options": {"from": 3650, "to": 2000000, "result": {"text": "Stable", "color": "green"}},
                            }
                        ],
                    },
                    {
                        "id": "thresholds",
                        "value": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "red", "value": None},
                                {"color": "orange", "value": 14},
                                {"color": "green", "value": 30},
                            ],
                        },
                    },
                    {"id": "color", "value": {"mode": "thresholds"}},
                    {"id": "custom.cellOptions", "value": {"type": "color-text", "mode": "basic"}},
                ],
            },
        ],
        "Used percent",
        True,
        description=(
            "Important filesystems only. The small EFI partition is hidden because it does not hold application data. "
            "Change in 6 hours is the real change in used space, not a forecast. Positive means the disk filled. Negative means space was freed. "
            "Days until full extends that 6-hour change and is shown only while used space is growing. Otherwise it says Stable."
        ),
    )
    return panel


def memory_table(pid, y, selector):
    job = job_of(selector)
    total = f"max by (server) (node_memory_MemTotal_bytes{{{job}}})"
    available = f"max by (server) (node_memory_MemAvailable_bytes{{{job}}})"
    used = f"max by (server) (node_memory_MemTotal_bytes{{{job}}} - node_memory_MemAvailable_bytes{{{job}}})"
    pct = job_metrics(selector)["memory_server"]
    pieces = [
        ("A", named(total, "mem_total", "server")),
        ("B", named(used, "mem_used", "server")),
        ("C", named(available, "mem_available", "server")),
        ("D", named(pct, "mem_pct", "server")),
    ]
    return table(
        pid,
        "Memory",
        [prom(ref, expr) for ref, expr in pieces],
        y,
        6,
        {
            "join": ["server"],
            "exclude": {"instance": True, "job": True, "Time": True, "__name__": True, "environment": True},
            "index": {"server": 0, "mem_total": 1, "mem_used": 2, "mem_available": 3, "mem_pct": 4},
            "rename": {
                "server": "Server",
                "mem_total": "Total",
                "mem_used": "Used",
                "mem_available": "Available",
                "mem_pct": "Used percent",
            },
        },
        [
            unit_override("Total", "bytes", 1, 120),
            unit_override("Used", "bytes", 1, 120),
            unit_override("Available", "bytes", 1, 130),
            heat_override("Used percent", 130),
        ],
        "Server",
        description=(
            "RAM as the operating system reports it. Available includes memory Linux can reclaim from cache, "
            "so Used is memory applications cannot have. Values are shown in GiB."
        ),
    )


def identity_table(pid, y, selector):
    job = job_of(selector)
    pieces = [
        ("A", named(label_replace_up(job), "up_ok", "server")),
        ("B", named(f"max by (server, nodename, release) (node_uname_info{{{job}}})", "host_ok", "server")),
        ("C", named(f"max by (server, pretty_name) (node_os_info{{{job}}})", "os_ok", "server")),
        ("D", named(f"max by (server) (node_boot_time_seconds{{{job}}} * 1000)", "boot_ms", "server")),
        ("E", named(f"max by (server) (changes(node_boot_time_seconds{{{job}}}[7d]))", "reboots_7d", "server")),
    ]
    return table(
        pid,
        "Server identity",
        [prom(ref, expr) for ref, expr in pieces],
        y,
        6,
        {
            "join": ["server"],
            "exclude": {
                "instance": True,
                "job": True,
                "Time": True,
                "__name__": True,
                "environment": True,
                "up_ok": True,
                "host_ok": True,
                "os_ok": True,
            },
            "index": {"server": 0, "nodename": 1, "ip": 2, "pretty_name": 3, "release": 4, "boot_ms": 5, "reboots_7d": 6},
            "rename": {
                "server": "Server",
                "nodename": "Hostname",
                "ip": "IP address",
                "pretty_name": "Operating system",
                "release": "Kernel",
                "boot_ms": "Last boot",
                "reboots_7d": "Reboots in 7 days",
            },
        },
        [
            {
                "matcher": {"id": "byName", "options": "Last boot"},
                "properties": [{"id": "unit", "value": "dateTimeFromNow"}, {"id": "custom.width", "value": 160}],
            },
            unit_override("Reboots in 7 days", "none", 0, 160),
        ],
        "Server",
        description=(
            "Hostname and operating system come from the server itself. IP address is the address Prometheus uses to scrape it. "
            "Last boot is the most recent restart. Reboots in 7 days counts boot-time changes and does not by itself mean the server is unhealthy."
        ),
    )


def firing_alert_table(pid, y, server_match):
    selector = f'alertstate="firing",server=~"{server_match}"'
    kept = f'server=~"{server_match}"'
    key = f'label_join(ALERTS{{{selector}}}, "alert_key", "/", "alertname", "server", "website", "instance")'
    started = (
        f'label_join((ALERTS_FOR_STATE{{{kept}}} * 1000), "alert_key", "/", "alertname", "server", "website", "instance")'
    )
    duration = (
        f'label_join((time() - ALERTS_FOR_STATE{{{kept}}}), "alert_key", "/", "alertname", "server", "website", "instance")'
    )
    pieces = [
        ("A", named(key, "firing", "alertname")),
        ("B", named(started, "started_ms", "alertname")),
        ("C", named(duration, "duration_s", "alertname")),
    ]
    overrides = [
        {
            "matcher": {"id": "byName", "options": "Alert"},
            "properties": [
                {"id": "mappings", "value": ALERT_TEXT_MAP},
                {"id": "custom.width", "value": 280},
            ],
        },
        {
            "matcher": {"id": "byName", "options": "Severity"},
            "properties": [
                {"id": "mappings", "value": [{
                    "type": "value",
                    "options": {
                        "critical": {"text": "Critical", "color": "red"},
                        "warning": {"text": "Warning", "color": "orange"},
                    },
                }]},
                {"id": "custom.cellOptions", "value": {"mode": "basic", "type": "color-background"}},
                {"id": "custom.width", "value": 120},
            ],
        },
        unit_override("Started", "dateTimeAsIso", 0, 190),
        unit_override("How long", "s", 0, 140),
    ]
    return table(
        pid,
        "How long it has been alerting",
        [prom(ref, expr) for ref, expr in pieces],
        y,
        8,
        {
            "join": ["alert_key"],
            "exclude": {
                "instance": True,
                "job": True,
                "Time": True,
                "__name__": True,
                "alert_key": True,
                "alertstate": True,
                "category": True,
                "target": True,
                "website": True,
            },
            "index": {"alertname": 0, "severity": 1, "server": 2, "started_ms": 3, "duration_s": 4},
            "rename": {
                "alertname": "Alert",
                "severity": "Severity",
                "server": "Server",
                "started_ms": "Started",
                "duration_s": "How long",
            },
        },
        overrides,
        "How long",
        True,
        description=(
            "Prometheus alerts for the selected server. How long is the time since the alert started firing. "
            "An empty table means this server has no firing alert. Website alerts stay on the website dashboard."
        ),
    )


def infrastructure():
    dash = shell()
    dash.update(
        {
            "uid": "infrastructure-overview",
            "title": "Infrastructure Overview",
            "description": "Start here. Green is healthy, orange needs attention, red is critical or offline.",
            "tags": ["operations", "overview"],
            "templating": {"list": []},
        }
    )
    health = health_expr("")
    panels = [
        note(
            1,
            "Green is healthy. Orange needs a look. Red means a resource is nearly full, a service has failed, or the server is offline. "
            "Open a server name for memory, disk, network, and what to check next. "
            "Container CPU and memory are not on this dashboard because cAdvisor is not installed.",
            0,
            3,
        ),
        tone(stat(2, "Servers", f"count({health}) or vector(0)", 0, 3, w=4, description="Servers Prometheus is configured to scrape."), "info"),
        tone(stat(3, "Healthy", f"count(({health}) == 3) or vector(0)", 4, 3, w=4, description="CPU, memory, and disk under 80%, swap under 50%, and load within CPU capacity."), "good"),
        tone(stat(4, "Warnings", f"count(({health}) == 2) or vector(0)", 8, 3, w=4, description="At least one resource is above its warning line."), "warn"),
        tone(stat(5, "Critical", f"count(({health}) == 1) or vector(0)", 12, 3, w=4, description="A resource is above 90% or an important service has failed."), "bad"),
        tone(stat(6, "Offline", f"count(({health}) == 0) or vector(0)", 16, 3, w=4, description="Node Exporter did not answer the last scrape."), "bad"),
        tone(stat(7, "No Data", f"count(({health}) == 4) or vector(0)", 20, 3, w=4, description="The exporter answered, but CPU metrics are missing."), "warn"),
        tone(stat(8, "Websites", 'count(probe_success{job="blackbox-http"}) or vector(0)', 0, 7, w=4, description="Sites checked by Blackbox."), "info"),
        tone(stat(9, "Websites up", 'count(probe_success{job="blackbox-http"} == 1) or vector(0)', 4, 7, w=4), "good"),
        tone(stat(10, "Websites down", 'count(probe_success{job="blackbox-http"} == 0) or vector(0)', 8, 7, w=4), "bad"),
        tone(stat(11, "Critical alerts", 'count(ALERTS{alertstate="firing",severity="critical"}) or vector(0)', 12, 7, w=6, description="Firing critical alerts for servers and websites."), "bad"),
        tone(stat(12, "Warning alerts", 'count(ALERTS{alertstate="firing",severity="warning"}) or vector(0)', 18, 7, w=6, description="Firing warning alerts. Open Alerts and Logs for how long each one has lasted."), "warn"),
        row(13, "SERVERS", 11),
        server_table(14, "Server health", 12, 8, ""),
        row(15, "WHAT NEEDS ATTENTION", 20),
        attention_table(16, "Current problems", 21, 8, ""),
        row(17, "SERVICES", 29),
        service_table(18, "Service status", 30, 10, ""),
        row(19, "MONITORING STACK", 40),
        stat(20, "Prometheus", 'up{job="prometheus"}', 0, 41, w=5, h=4, mappings=UP_MAP, no_value="Offline"),
        stat(21, "Grafana", 'up{job="grafana"}', 5, 41, w=5, h=4, mappings=UP_MAP, no_value="Offline"),
        stat(22, "Blackbox", 'up{job="blackbox-exporter"}', 10, 41, w=5, h=4, mappings=UP_MAP, no_value="Offline"),
        stat(23, "Alertmanager", 'up{job="alertmanager"}', 15, 41, w=4, h=4, mappings=UP_MAP, no_value="Offline"),
        stat(24, "Loki", 'up{job="loki"}', 19, 41, w=5, h=4, mappings=UP_MAP, no_value="Offline"),
    ]
    dash["panels"] = panels
    return dash


def server_detail():
    dash = shell()
    sel = ',server=~"^(?:${server})$"'
    m = job_metrics(sel)
    job = m["job"]
    dash.update(
        {
            "uid": "server-detail",
            "title": "Server Detail",
            "description": "One server, or all three. Gauges turn orange at 80% and red at 90%.",
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
    swap_steps = [
        {"color": "green", "value": None},
        {"color": "orange", "value": 50},
        {"color": "red", "value": 80},
    ]
    panels = [
        note(
            1,
            "CPU, memory, and disk gauges are orange from 80% and red from 90%. "
            "Swap is orange from 50% because using disk as memory slows the server. "
            "Load per CPU above 1.5 means work is waiting. "
            "A single zombie process is shown but does not mark the server unhealthy.",
            0,
            3,
        ),
        gauge(2, "CPU", m["cpu_server"], 0, 3, 6, 6, "Share of CPU time that is not idle, averaged over 5 minutes."),
        gauge(3, "Memory", m["memory_server"], 6, 3, 6, 6, "RAM that applications cannot use. Linux cache counts as available."),
        gauge(
            4,
            "Disk",
            m["disk_server"],
            12,
            3,
            6,
            6,
            "Fullest data filesystem. The EFI partition is excluded.",
        ),
        gauge(
            5,
            "Swap",
            m["swap_server"],
            18,
            3,
            6,
            6,
            "Share of swap in use. 0% on a server with no swap file is normal.",
            steps=swap_steps,
        ),
        show_each(stat(
            6, "Health", health_expr(sel), 0, 9, w=4, h=4, mappings=HEALTH_MAP, decimals=0, no_value="No Data",
            description="Combined status from CPU, memory, disk, swap, load, failed services, and whether metrics are arriving.",
        )),
        show_each(stat(
            7, "Uptime", m["uptime"], 4, 9, w=4, h=4, unit="s", decimals=0,
            description="Time since the last boot.",
        )),
        show_each(stat(
            8, "Load", m["load"], 8, 9, w=4, h=4, unit="none", decimals=2,
            description="1-minute load average. Compare it with CPUs. A load above the CPU count means work is queued.",
        )),
        show_each(stat(
            9, "CPUs", m["cpus"], 12, 9, w=4, h=4, decimals=0,
            description="Number of CPU cores Node Exporter can see.",
        )),
        show_each(stat(
            10, "Load per CPU", m["load_ratio"], 16, 9, w=4, h=4, unit="none", decimals=2,
            description="Load divided by CPU count. Above 1.5 the server is overloaded.",
        )),
        show_each(stat(
            11, "Reboots in 7 days", f"max by (server) (changes(node_boot_time_seconds{{{job}}}[7d]))", 20, 9, w=4, h=4, decimals=0,
            description="How many times the boot time changed in 7 days. This is context, not a failure by itself.",
        )),
        row(12, "IDENTITY", 13),
        identity_table(13, 14, sel),
        row(14, "MEMORY", 20),
        memory_table(15, 21, sel),
        row(16, "DISK SPACE", 27),
        filesystem_table(17, 28, sel),
        row(18, "WHAT NEEDS ATTENTION", 36),
        tone(stat(
            19,
            "Problems right now",
            f"count({attention_expr(sel)}) or vector(0)",
            0,
            37,
            w=6,
            h=4,
            description="Count of live checks outside their limit for the selected server.",
        ), "bad"),
        {
            "id": 20,
            "type": "text",
            "gridPos": {"h": 4, "w": 18, "x": 6, "y": 37},
            "options": {
                "mode": "markdown",
                "content": (
                    "The first table is the live measurement. The second table is the matching alert and how long it has been firing. "
                    "Open **Alerts and Logs** for the service log."
                ),
            },
        },
    ]
    panels.extend([
        attention_table(21, "Current problems", 41, 8, sel),
        firing_alert_table(22, 49, "^(?:${server})$"),
        row(23, "TRENDS", 57),
    ])
    charts = [
        ("CPU", m["cpu_server"], "percent", "CPU percent over time. The dashed lines are 80% and 90%.", {"maximum": 100, "thresholds": PERCENT_STEPS}),
        ("Memory", m["memory_server"], "percent", "Memory percent over time.", {"maximum": 100, "thresholds": PERCENT_STEPS}),
        ("Root disk", m["root"], "percent", "Main filesystem (/) only. Other filesystems are in the disk table.", {"maximum": 100, "thresholds": PERCENT_STEPS}),
        ("Swap", m["swap_server"], "percent", "Swap percent over time. A long orange stretch means memory pressure is not a short spike.", {"maximum": 100, "thresholds": swap_steps}),
        ("Load", m["load_server"], "none", "1-minute load average.", {"decimals": 2}),
        ("Load per CPU", m["load_ratio_server"], "none", "Load divided by CPU count.", {"decimals": 2}),
        ("Download", f'sum by (server) (rate(node_network_receive_bytes_total{{{NET_DEV},{job}}}[5m]))', "Bps", "Traffic arriving at the server, excluding loopback and Docker bridges.", {}),
        ("Upload", f'sum by (server) (rate(node_network_transmit_bytes_total{{{NET_DEV},{job}}}[5m]))', "Bps", "Traffic leaving the server, excluding loopback and Docker bridges.", {}),
        ("Disk read", f'sum by (server) (rate(node_disk_read_bytes_total{{{DISK_DEV},{job}}}[5m]))', "Bps", "Bytes read per second from real disks. CD-ROM devices are excluded.", {}),
        ("Disk write", f'sum by (server) (rate(node_disk_written_bytes_total{{{DISK_DEV},{job}}}[5m]))', "Bps", "Bytes written per second from real disks.", {}),
        ("Disk busy", f'max by (server) (rate(node_disk_io_time_seconds_total{{{DISK_DEV},{job}}}[5m]) * 100)', "percent", "How much of the time the disk was busy. Near 100% the disk is the bottleneck.", {"maximum": 100, "thresholds": PERCENT_STEPS}),
        ("Network errors", f'sum by (server) (rate(node_network_receive_errs_total{{{NET_DEV},{job}}}[5m]) + rate(node_network_transmit_errs_total{{{NET_DEV},{job}}}[5m]))', "ops", "Receive and transmit errors per second on real interfaces.", {}),
        ("Dropped packets", f'sum by (server) (rate(node_network_receive_drop_total{{{NET_DEV},{job}}}[5m]) + rate(node_network_transmit_drop_total{{{NET_DEV},{job}}}[5m]))', "ops", "Receive and transmit drops per second. Occasional drops can be normal; a sustained rise is not.", {}),
    ]
    y = 58
    pid = 30
    for index, (title, expr, unit, description, opts) in enumerate(charts):
        x = 0 if index % 2 == 0 else 12
        if index and x == 0:
            y += 8
        panels.append(timeseries(pid, title, expr, x, y, 12, 8, unit, description, **opts))
        pid += 1
    y += 8
    panels.append(row(pid, "SERVICES", y))
    pid += 1
    y += 1
    panels.append(service_table(pid, "Service status", y, 10, sel))
    pid += 1
    y += 10
    panels.append(row(pid, "PROCESSES", y))
    pid += 1
    y += 1
    panels.append(show_each(stat(
        pid, "Running", proc_count(sel, "R"), 0, y, w=8, h=4, decimals=0,
        description="Programs actively using a CPU at the last sample.",
    )))
    pid += 1
    panels.append(show_each(tone(stat(
        pid, "Waiting on disk", proc_count(sel, "D"), 8, y, w=8, h=4, decimals=0,
        description="Programs stuck in uninterruptible disk wait. A few can be normal during writes. Five or more is a problem.",
    ), "info")))
    panels[-1]["fieldConfig"]["defaults"]["thresholds"] = {
        "mode": "absolute",
        "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 5}],
    }
    pid += 1
    panels.append(show_each(stat(
        pid, "Zombies", proc_count(sel, "Z"), 16, y, w=8, h=4, decimals=0,
        description="Finished programs whose parent has not collected them. One is usually harmless. Ten or more means an application is leaking child processes.",
    )))
    panels[-1]["fieldConfig"]["defaults"]["thresholds"] = {
        "mode": "absolute",
        "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 10}],
    }
    pid += 1
    y += 4
    panels.append(note(
        pid,
        "Docker container status, CPU, memory, and restarts are **not available**. "
        "This stack does not run cAdvisor. The service table above shows only whether the Docker service itself is running. "
        "Adding container panels would require installing cAdvisor on each server and a new Prometheus scrape job.",
        y,
        3,
    ))
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
                {"id": "custom.width", "value": 280},
                {"id": "mappings", "value": ALERT_TEXT_MAP},
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
