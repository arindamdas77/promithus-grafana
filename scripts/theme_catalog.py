#!/usr/bin/env python3
"""Color themes for the generated Grafana dashboards.

Grafana 13.2.2 dashboard JSON can color series, gauges, thresholds, and value
mappings. It cannot set the page background, panel chrome, table header, or
link color, and it has no color-picker variable. Those extra colors are stored
for the theme studio preview. Status hues stay recognizable on every preset.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME_DIR = ROOT / "monitoring" / "theme"
ACTIVE_PATH = THEME_DIR / "active.json"
PREVIOUS_PATH = THEME_DIR / "previous.json"

COLOR_KEYS = (
    "accent",
    "secondary",
    "background",
    "panel",
    "border",
    "heading",
    "body",
    "tableHeader",
    "tableRow",
    "tableRowAlt",
    "link",
    "interactive",
    "healthy",
    "warning",
    "critical",
    "offline",
    "nodata",
    "gaugeOk",
    "gaugeWarn",
    "gaugeCritical",
)


def _palette(accent, secondary, background, panel, border, heading, body, table_header, table_row, table_alt, link, series, grafana_theme, status=None):
    status = status or {}
    colors = {
        "accent": accent,
        "secondary": secondary,
        "background": background,
        "panel": panel,
        "border": border,
        "heading": heading,
        "body": body,
        "tableHeader": table_header,
        "tableRow": table_row,
        "tableRowAlt": table_alt,
        "link": link,
        "interactive": accent,
        "healthy": status.get("healthy", "#16a34a"),
        "warning": status.get("warning", "#d97706"),
        "critical": status.get("critical", "#dc2626"),
        "offline": status.get("offline", "#64748b"),
        "nodata": status.get("nodata", "#94a3b8"),
        "gaugeOk": status.get("gaugeOk", status.get("healthy", "#16a34a")),
        "gaugeWarn": status.get("gaugeWarn", status.get("warning", "#d97706")),
        "gaugeCritical": status.get("gaugeCritical", status.get("critical", "#dc2626")),
        "series": series,
    }
    return colors


PRESETS = [
    {
        "id": "midnight-blue",
        "name": "Midnight Blue",
        "grafanaTheme": "dark",
        "blurb": "Dark navy surfaces with blue and cyan data colors.",
        "colors": _palette(
            "#38bdf8", "#22d3ee", "#0b1220", "#121a2b", "#243049", "#e8f1ff", "#c5d4e8",
            "#162033", "#0f1728", "#152033", "#7dd3fc",
            ["#38bdf8", "#22d3ee", "#818cf8", "#67e8f9"],
            "dark",
        ),
    },
    {
        "id": "ocean-teal",
        "name": "Ocean Teal",
        "grafanaTheme": "dark",
        "blurb": "Deep blue-green surfaces with turquoise data colors.",
        "colors": _palette(
            "#2dd4bf", "#5eead4", "#042f2e", "#083c3a", "#115e59", "#ecfdf5", "#ccfbf1",
            "#0f3f3c", "#042f2e", "#0a3331", "#5eead4",
            ["#2dd4bf", "#22d3ee", "#67e8f9", "#a7f3d0"],
            "dark",
        ),
    },
    {
        "id": "purple-neon",
        "name": "Purple Neon",
        "grafanaTheme": "dark",
        "blurb": "Charcoal surfaces with violet data colors. Status hues stay standard.",
        "colors": _palette(
            "#a78bfa", "#c084fc", "#16141f", "#221f2e", "#3b3352", "#f5f3ff", "#ddd6fe",
            "#2a2438", "#16141f", "#1e1a2b", "#c4b5fd",
            ["#a78bfa", "#e879f9", "#818cf8", "#f0abfc"],
            "dark",
        ),
    },
    {
        "id": "emerald-green",
        "name": "Emerald Green",
        "grafanaTheme": "dark",
        "blurb": "Deep green surfaces with mint data colors.",
        "colors": _palette(
            "#34d399", "#6ee7b7", "#052e1c", "#0b3d28", "#166534", "#ecfdf5", "#d1fae5",
            "#0d3b2a", "#052e1c", "#0a3324", "#6ee7b7",
            ["#34d399", "#2dd4bf", "#86efac", "#fbbf24"],
            "dark",
        ),
    },
    {
        "id": "sunset-orange",
        "name": "Sunset Orange",
        "grafanaTheme": "dark",
        "blurb": "Dark slate surfaces with orange and amber data colors.",
        "colors": _palette(
            "#fb923c", "#fbbf24", "#1c1410", "#2a1d16", "#7c4a1e", "#fff7ed", "#ffedd5",
            "#3a2618", "#1c1410", "#261910", "#fdba74",
            ["#fb923c", "#fbbf24", "#fdba74", "#f97316"],
            "dark",
        ),
    },
    {
        "id": "light-professional",
        "name": "Light Professional",
        "grafanaTheme": "light",
        "blurb": "White and light gray with blue accents. Switch Grafana to the light preference.",
        "colors": _palette(
            "#2563eb", "#0ea5e9", "#f4f7fb", "#ffffff", "#d7dee8", "#0f172a", "#334155",
            "#e8eef6", "#ffffff", "#f8fafc", "#1d4ed8",
            ["#2563eb", "#0891b2", "#7c3aed", "#ea580c"],
            "light",
            {
                "healthy": "#15803d",
                "warning": "#b45309",
                "critical": "#b91c1c",
                "offline": "#475569",
                "nodata": "#64748b",
                "gaugeOk": "#15803d",
                "gaugeWarn": "#b45309",
                "gaugeCritical": "#b91c1c",
            },
        ),
    },
    {
        "id": "dark-professional",
        "name": "Dark Professional",
        "grafanaTheme": "dark",
        "blurb": "Charcoal and graphite with cool blue accents. This is the default.",
        "colors": _palette(
            "#6ea8fe", "#8b9cb3", "#111315", "#1c1f24", "#2e333a", "#f3f4f6", "#c5c9d1",
            "#1c1f24", "#141618", "#1a1d22", "#9ec1ff",
            ["#6ea8fe", "#5eead4", "#fbbf24", "#c4b5fd"],
            "dark",
        ),
    },
    {
        "id": "high-contrast",
        "name": "High Contrast",
        "grafanaTheme": "dark",
        "blurb": "Black surfaces and status colors chosen to stay easy to tell apart.",
        "colors": _palette(
            "#00e5ff", "#ffff00", "#000000", "#0a0a0a", "#ffffff", "#ffffff", "#ffffff",
            "#000000", "#000000", "#141414", "#00e5ff",
            ["#00e5ff", "#ff00ff", "#ffff00", "#00ff80"],
            "dark",
            {
                "healthy": "#00c853",
                "warning": "#ffd600",
                "critical": "#ff1744",
                "offline": "#b0b0b0",
                "nodata": "#66ccff",
                "gaugeOk": "#00c853",
                "gaugeWarn": "#ffd600",
                "gaugeCritical": "#ff1744",
            },
        ),
    },
]

PRESET_BY_ID = {item["id"]: item for item in PRESETS}
DEFAULT_ID = "dark-professional"


def default_theme():
    preset = PRESET_BY_ID[DEFAULT_ID]
    return {
        "id": preset["id"],
        "name": preset["name"],
        "grafanaTheme": preset["grafanaTheme"],
        "colors": json.loads(json.dumps(preset["colors"])),
    }


def _rgb(value):
    text = value.lstrip("#")
    return tuple(int(text[index:index + 2], 16) for index in (0, 2, 4))


def _luminance(value):
    channels = []
    for channel in _rgb(value):
        unit = channel / 255
        channels.append(unit / 12.92 if unit <= 0.04045 else ((unit + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(left, right):
    lighter = max(_luminance(left), _luminance(right))
    darker = min(_luminance(left), _luminance(right))
    return (lighter + 0.05) / (darker + 0.05)


def _distance(left, right):
    return sum((a - b) ** 2 for a, b in zip(_rgb(left), _rgb(right))) ** 0.5


def _is_green(value):
    red, green, blue = _rgb(value)
    return green > red + 15 and green > blue + 15 and green > 70


def _is_red(value):
    red, green, blue = _rgb(value)
    return red > green + 20 and red > blue + 20 and red > 80


def _is_amber(value):
    red, green, blue = _rgb(value)
    return red > 160 and green > 80 and blue < 160 and red >= green - 10 and green > blue + 20


def validate_theme(theme):
    errors = []
    if not isinstance(theme, dict):
        return ["Theme must be an object."]
    name = theme.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > 60:
        errors.append("Theme name must be 1 to 60 characters.")
    if theme.get("grafanaTheme") not in {"light", "dark"}:
        errors.append("Grafana preference must be light or dark.")
    colors = theme.get("colors")
    if not isinstance(colors, dict):
        return errors + ["Colors are missing."]
    for key in COLOR_KEYS:
        value = colors.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            errors.append(f"{key} must be a #rrggbb color.")
    series = colors.get("series")
    if not isinstance(series, list) or not 3 <= len(series) <= 6:
        errors.append("Chart series needs 3 to 6 colors.")
    else:
        for index, value in enumerate(series):
            if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                errors.append(f"Series color {index + 1} must be a #rrggbb color.")
        if all(isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value) for value in series):
            for left in range(len(series)):
                for right in range(left + 1, len(series)):
                    if _distance(series[left], series[right]) < 28:
                        errors.append("Chart series colors are too similar to tell apart.")
                        break
    if errors:
        return errors
    checks = (
        ("healthy", _is_green, "Healthy must stay green."),
        ("gaugeOk", _is_green, "The low gauge color must stay green."),
        ("warning", _is_amber, "Warning must stay amber or yellow."),
        ("gaugeWarn", _is_amber, "The middle gauge color must stay amber or yellow."),
        ("critical", _is_red, "Critical must stay red."),
        ("gaugeCritical", _is_red, "The high gauge color must stay red."),
    )
    for key, test, message in checks:
        if not test(colors[key]):
            errors.append(message)
    if _distance(colors["critical"], colors["healthy"]) < 120:
        errors.append("Critical and healthy are too close.")
    if _distance(colors["critical"], colors["warning"]) < 50:
        errors.append("Critical and warning are too close.")
    if _distance(colors["offline"], colors["critical"]) < 70:
        errors.append("Offline is too close to critical.")
    if _distance(colors["nodata"], colors["critical"]) < 70:
        errors.append("No-data is too close to critical.")
    if _distance(colors["nodata"], colors["offline"]) < 32:
        errors.append("No-data and offline must stay distinguishable.")
    if _is_red(colors["offline"]) or _is_green(colors["offline"]):
        errors.append("Offline must stay a neutral gray, not red or green.")
    if _contrast(colors["heading"], colors["background"]) < 4.5:
        errors.append("Heading text does not contrast with the dashboard background.")
    if _contrast(colors["body"], colors["background"]) < 4.5:
        errors.append("Body text does not contrast with the dashboard background.")
    light_surface = _luminance(colors["background"]) > 0.45
    if light_surface and theme["grafanaTheme"] != "light":
        errors.append("A light background needs the light Grafana preference.")
    if not light_surface and theme["grafanaTheme"] != "dark":
        errors.append("A dark background needs the dark Grafana preference.")
    return errors


def normalize_theme(theme):
    colors = theme["colors"]
    clean = {
        "id": str(theme.get("id") or "custom")[:40],
        "name": theme["name"].strip(),
        "grafanaTheme": theme["grafanaTheme"],
        "colors": {},
    }
    for key in COLOR_KEYS:
        clean["colors"][key] = colors[key].lower()
    clean["colors"]["series"] = [value.lower() for value in colors["series"]]
    return clean


def load_theme():
    if not ACTIVE_PATH.exists():
        return default_theme()
    try:
        theme = json.loads(ACTIVE_PATH.read_text())
    except json.JSONDecodeError:
        return default_theme()
    if validate_theme(theme):
        return default_theme()
    return normalize_theme(theme)


def server_names():
    text = (ROOT / "group_vars" / "all.yml").read_text()
    return re.findall(r'^\s*- name:\s*"([^"]+)"', text, flags=re.M)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
