"""Persist analysis results as JSON or Markdown in the outputs folder."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from core.utils import MediaInspectorError

ReportFormat = Literal["json", "md", "markdown"]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def write_report(data: dict[str, Any], fmt: str, source_path: Path) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = source_path.stem.replace(" ", "_")
    normalized = _normalize_format(fmt)

    if normalized == "json":
        dest = OUTPUTS_DIR / f"{stem}_{stamp}.json"
        dest.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return dest

    dest = OUTPUTS_DIR / f"{stem}_{stamp}.md"
    dest.write_text(_to_markdown(data), encoding="utf-8")
    return dest


def _normalize_format(fmt: str) -> Literal["json", "markdown"]:
    value = fmt.lower().strip()
    if value == "json":
        return "json"
    if value in {"md", "markdown"}:
        return "markdown"
    raise MediaInspectorError(f"Unsupported report format '{fmt}'. Use json or md.")


def _to_markdown(data: dict[str, Any], heading: str = "MediaInspector Report") -> str:
    lines = [
        f"# {heading}",
        "",
        f"_Generated at {datetime.now(timezone.utc).isoformat()}_",
        "",
    ]
    _render_section(lines, data, level=2)
    return "\n".join(lines).rstrip() + "\n"


def _render_section(lines: list[str], payload: Any, level: int) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            title = str(key).replace("_", " ").title()
            if isinstance(value, dict):
                lines.append(f"{'#' * min(level, 6)} {title}")
                lines.append("")
                _render_section(lines, value, level + 1)
            elif isinstance(value, list):
                lines.append(f"{'#' * min(level, 6)} {title}")
                lines.append("")
                if not value:
                    lines.append("_None_")
                    lines.append("")
                elif all(isinstance(item, dict) for item in value):
                    for index, item in enumerate(value, start=1):
                        lines.append(f"{'#' * min(level + 1, 6)} Item {index}")
                        lines.append("")
                        _render_section(lines, item, level + 2)
                else:
                    for item in value:
                        lines.append(f"- {item}")
                    lines.append("")
            else:
                display = "_None_" if value is None or value == "" else str(value)
                lines.append(f"- **{title}:** {display}")
        if payload and not any(isinstance(v, (dict, list)) for v in payload.values()):
            lines.append("")
        return

    lines.append(str(payload))
    lines.append("")
