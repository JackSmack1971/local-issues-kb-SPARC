"""Security scanner for Python files.

Scans directories for potential secrets, missing input validation, and
SQL statements without placeholders.
"""

from __future__ import annotations

import argparse
import ast
import logging
import re
import sys
import uuid
from dataclasses import dataclass
from math import log2
from pathlib import Path
from typing import Iterable, List

logger = logging.getLogger(__name__)

SECRET_PATTERNS = [
    re.compile(r"api_key\s*=", re.IGNORECASE),
    re.compile(r"secret\s*=", re.IGNORECASE),
    re.compile(r"token\s*=", re.IGNORECASE),
]

HIGH_ENTROPY_THRESHOLD = 4.0


@dataclass
class Finding:
    path: Path
    message: str


def shannon_entropy(data: str) -> float:
    probabilities = [float(data.count(c)) / len(data) for c in set(data)]
    return -sum(p * log2(p) for p in probabilities)


def is_high_entropy(value: str) -> bool:
    return len(value) >= 20 and shannon_entropy(value) > HIGH_ENTROPY_THRESHOLD


def detect_secrets(source: str) -> bool:
    if any(pattern.search(source) for pattern in SECRET_PATTERNS):
        return True
    for match in re.finditer(r"['\"]([A-Za-z0-9+/=]{20,})['\"]", source):
        if is_high_entropy(match.group(1)):
            return True
    return False


def function_lacks_validation(node: ast.FunctionDef) -> bool:
    if not any("path" in arg.arg.lower() for arg in node.args.args):
        return False
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Attribute):
                if func.attr == "resolve":
                    return False
                if isinstance(func.value, ast.Name) and func.value.id == "re":
                    return False
            if isinstance(func, ast.Name) and func.id.startswith("re"):
                return False
    return True


def check_sql_placeholders(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Attribute) and func.attr in {"execute", "executemany"}:
                if child.args and isinstance(child.args[0], ast.Constant) and isinstance(child.args[0].value, str):
                    sql = child.args[0].value.lower()
                    if re.search(r"\b(select|insert|update|delete)\b", sql) and "?" not in sql:
                        return True
    return False


def scan_file(path: Path, *, correlation_id: str) -> List[Finding]:
    path = path.resolve()
    source = path.read_text(encoding="utf-8")
    findings: List[Finding] = []
    if detect_secrets(source):
        findings.append(Finding(path, "potential secret detected"))
    try:
        tree = ast.parse(source)
    except SyntaxError:
        logger.warning("Failed to parse %s", path, extra={"correlation_id": correlation_id})
        return findings
    for node in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if function_lacks_validation(node):
            findings.append(Finding(path, f"function '{node.name}' lacks input validation"))
    if check_sql_placeholders(tree):
        findings.append(Finding(path, "SQL statement without parameter placeholders"))
    return findings


def scan_paths(paths: Iterable[Path], *, correlation_id: str) -> List[Finding]:
    results: List[Finding] = []
    for path in paths:
        path = path.resolve()
        if path.is_dir():
            for file in path.rglob("*.py"):
                results.extend(scan_file(file, correlation_id=correlation_id))
        elif path.suffix == ".py":
            results.extend(scan_file(path, correlation_id=correlation_id))
    return results


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan Python files for security issues")
    parser.add_argument("path", nargs="?", default=".", help="Path to scan")
    args = parser.parse_args(argv)
    correlation_id = str(uuid.uuid4())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(correlation_id)s] %(message)s",
    )
    target = Path(args.path).resolve()
    if not target.exists():
        logger.error("Path %s does not exist", target, extra={"correlation_id": correlation_id})
        return 1
    findings = scan_paths([target], correlation_id=correlation_id)
    for finding in findings:
        logger.error("%s: %s", finding.path, finding.message, extra={"correlation_id": correlation_id})
    if findings:
        logger.error("Security scan failed with %d issue(s)", len(findings), extra={"correlation_id": correlation_id})
        return 1
    logger.info("Security scan passed", extra={"correlation_id": correlation_id})
    return 0


if __name__ == "__main__":
    import argparse

    sys.exit(main())
