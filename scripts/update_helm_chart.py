#!/usr/bin/env python3
"""Prepare the valkey-helm chart files for one Valkey GA release."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_CHART_VERSION_RE = re.compile(r"^version:\s*\"?([0-9]+\.[0-9]+\.[0-9]+)\"?\s*$", re.MULTILINE)
_APP_VERSION_RE = re.compile(r"^appVersion:\s*\"?([0-9]+\.[0-9]+\.[0-9]+)\"?\s*$", re.MULTILINE)


def _version_tuple(value: str) -> tuple[int, int, int]:
    if not _VERSION_RE.fullmatch(value):
        raise ValueError(f"invalid three-part version: {value}")
    return tuple(map(int, value.split(".")))  # type: ignore[return-value]


def update_chart(chart: str, readme: str, app_version: str) -> tuple[str, str, str]:
    """Return updated Chart.yaml, README, and the new chart version.

    A chart already tracking this or a newer Valkey version is left unchanged.
    """
    requested = _version_tuple(app_version)
    chart_match = _CHART_VERSION_RE.search(chart)
    app_match = _APP_VERSION_RE.search(chart)
    if chart_match is None or app_match is None:
        raise ValueError("could not find chart version and appVersion")

    current_app = _version_tuple(app_match.group(1))
    current_chart = _version_tuple(chart_match.group(1))
    if current_app >= requested:
        return chart, readme, chart_match.group(1)

    next_chart = f"{current_chart[0]}.{current_chart[1]}.{current_chart[2] + 1}"
    new_chart = _CHART_VERSION_RE.sub(f"version: {next_chart}", chart, count=1)
    new_chart = _APP_VERSION_RE.sub(f'appVersion: "{app_version}"', new_chart, count=1)

    new_readme = re.sub(
        r"!\[Version: [^\]]*\]",
        f"![Version: {next_chart}]",
        readme,
        count=1,
    )
    new_readme = re.sub(
        r"(?<!App)Version-[0-9.]+-informational",
        f"Version-{next_chart}-informational",
        new_readme,
        count=1,
    )
    new_readme = re.sub(
        r"!\[AppVersion: [^\]]*\]",
        f"![AppVersion: {app_version}]",
        new_readme,
        count=1,
    )
    new_readme = re.sub(
        r"AppVersion-[0-9.]+-informational",
        f"AppVersion-{app_version}-informational",
        new_readme,
        count=1,
    )
    if new_readme == readme:
        raise ValueError("could not find Helm version badges in README")
    if f"![Version: {next_chart}]" not in new_readme or f"![AppVersion: {app_version}]" not in new_readme:
        raise ValueError("could not update both Helm version badges in README")
    return new_chart, new_readme, next_chart


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chart", type=Path, required=True)
    parser.add_argument("--readme", type=Path, required=True)
    parser.add_argument("--app-version", required=True)
    args = parser.parse_args()

    chart = args.chart.read_text(encoding="utf-8")
    readme = args.readme.read_text(encoding="utf-8")
    new_chart, new_readme, chart_version = update_chart(chart, readme, args.app_version)
    args.chart.write_text(new_chart, encoding="utf-8")
    args.readme.write_text(new_readme, encoding="utf-8")
    print(f"chart_version={chart_version}")


if __name__ == "__main__":
    main()
