"""Alert manager evaluating metrics against thresholds and writing active alerts."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Alert:
    """Represents a single alert."""

    name: str
    message: str
    severity: str


class AlertManager:
    """Evaluates metrics and writes active alerts to a JSON file."""

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        *,
        output_path: Optional[Path] = None,
    ) -> None:
        if thresholds is None:
            thresholds = load_thresholds(parse_args([]))
        self.thresholds = thresholds
        self.output_path = output_path or Path("alerts") / "active_alerts.json"

    def evaluate(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Return alerts for metrics breaching thresholds."""
        t = self.thresholds
        alerts: List[Alert] = []

        rate = metrics.get("collection_success_rate")
        if rate is not None and rate < t["collection_success_rate"]:
            alerts.append(
                Alert(
                    "collection_success_rate",
                    "Collection success rate below threshold",
                    "ERROR",
                )
            )

        build_time = metrics.get("index_build_time_seconds")
        if build_time is not None and build_time > t["index_build_time_seconds"]:
            alerts.append(
                Alert(
                    "index_build_time_seconds",
                    "Index build time exceeds threshold",
                    "WARN",
                )
            )

        disk_usage = metrics.get("disk_usage")
        if disk_usage is not None:
            if disk_usage > t["disk_usage_critical"]:
                alerts.append(
                    Alert(
                        "disk_usage",
                        "Disk usage above critical threshold",
                        "CRITICAL",
                    )
                )
            elif disk_usage > t["disk_usage_warn"]:
                alerts.append(
                    Alert(
                        "disk_usage",
                        "Disk usage above warning threshold",
                        "WARN",
                    )
                )

        mem = metrics.get("memory_usage_mb")
        if mem is not None and mem > t["memory_usage_mb"]:
            alerts.append(
                Alert(
                    "memory_usage_mb",
                    "Memory usage above threshold",
                    "WARN",
                )
            )

        rate_limited = metrics.get("api_rate_limited_ratio")
        if rate_limited is not None and rate_limited > t["api_rate_limited_ratio"]:
            alerts.append(
                Alert(
                    "api_rate_limited_ratio",
                    "API rate-limited requests ratio too high",
                    "WARN",
                )
            )

        fts5_ok = metrics.get("fts5_integrity_ok", True)
        if not fts5_ok:
            alerts.append(
                Alert(
                    "fts5_integrity",
                    "FTS5 integrity check failed",
                    "CRITICAL",
                )
            )

        return alerts

    def write_alerts(self, alerts: List[Alert]) -> None:
        """Write alerts to the configured output file."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(a) for a in alerts]
        with self.output_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    def critical(self, message: str) -> None:
        """Write a single critical alert with the given message."""
        if not isinstance(message, str) or not message:
            raise ValueError("message must be a non-empty string")
        self.write_alerts([Alert("manual", message, "CRITICAL")])

    def check(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Evaluate metrics and persist active alerts."""
        alerts = self.evaluate(metrics)
        self.write_alerts(alerts)
        return alerts


def load_thresholds(
    args: argparse.Namespace,
    config_path: Path = Path(__file__).resolve().parent / "config" / "thresholds.json",
) -> Dict[str, float]:
    """Load thresholds with env and CLI overrides."""
    with config_path.open("r", encoding="utf-8") as fh:
        thresholds: Dict[str, float] = json.load(fh)
    for key, value in list(thresholds.items()):
        env_val = os.getenv(f"ALERT_{key.upper()}")
        if env_val is not None:
            thresholds[key] = type(value)(env_val)
        cli_val = getattr(args, key, None)
        if cli_val is not None:
            thresholds[key] = cli_val
    return thresholds


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments for threshold overrides."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection-success-rate", type=float)
    parser.add_argument("--index-build-time-seconds", type=float)
    parser.add_argument("--disk-usage-warn", type=float)
    parser.add_argument("--disk-usage-critical", type=float)
    parser.add_argument("--memory-usage-mb", type=float)
    parser.add_argument("--api-rate-limited-ratio", type=float)
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point parsing flags and writing alerts for provided metrics."""
    args = parse_args(argv)
    thresholds = load_thresholds(args)
    manager = AlertManager(thresholds)
    manager.check({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
