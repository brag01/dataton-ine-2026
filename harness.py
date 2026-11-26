"""Maintenance checks for ine_gt. Only the live test stage queries the INE portal."""

from __future__ import annotations

import argparse
import ast
import inspect
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def run(*args: str) -> int:
    print("+", PYTHON, *args, flush=True)
    return subprocess.call([PYTHON, *args], cwd=ROOT)


def inspect_repo() -> int:
    files = [ROOT / name for name in ("README.md", "AGENTS.md", "pyproject.toml")]
    files.extend(sorted((ROOT / "src/ine_gt").glob("*.py")))
    files.extend(sorted((ROOT / "tests").glob("*.py")))
    contents = {path: path.read_text(encoding="utf-8") for path in files}
    for path, source in contents.items():
        if not source.strip():
            raise ValueError(f"Empty file: {path}")
        if path.suffix == ".py":
            ast.parse(source, filename=str(path))
        print(path.relative_to(ROOT), f"({len(source.splitlines())} lines)")

    import ine_gt
    if Path(ine_gt.__file__).resolve().parent != ROOT / "src/ine_gt":
        raise ValueError("Install this checkout in editable mode before running inspect.")
    example = re.search(r"^```python\n(.*?)^```", contents[ROOT / "README.md"], re.M | re.S)
    if not example:
        raise ValueError("README is missing its Python quickstart.")
    tree = ast.parse(example[1])
    aliases = {alias.asname or alias.name for node in tree.body if isinstance(node, ast.Import)
               for alias in node.names if alias.name == "ine_gt"}
    checked = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            func = node.func
            if isinstance(func.value, ast.Name) and func.value.id in aliases:
                if func.attr not in ine_gt.__all__:
                    raise ValueError(f"Unknown public function: {func.attr}")
                inspect.signature(getattr(ine_gt, func.attr)).bind(
                    *node.args, **{kw.arg: kw.value for kw in node.keywords})
                checked.add(func.attr)
    if not {"cargar_serie", "mostrar_fuente"} <= checked:
        raise ValueError("Quickstart must load a series and show its source.")
    print("README quickstart signatures verified:", ", ".join(sorted(checked)))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("inspect", "build", "audit", "persona", "live"))
    stage = parser.parse_args().stage
    if stage == "inspect":
        return inspect_repo()
    if stage == "build":
        return run("-m", "pip", "install", "-e", ".[dev]")
    if stage == "audit":
        return run("-m", "pytest", "-q", "-p", "no:cacheprovider", "tests")
    if stage == "live":
        return run("-m", "pytest", "-q", "-s", "-p", "no:cacheprovider", "tests/live_portal.py")
    return run("-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_persona.py")


if __name__ == "__main__":
    raise SystemExit(main())
