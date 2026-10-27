import ast
from pathlib import Path
import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"

FORBIDDEN_IMPORTS = {
    "api": ("app.core", "app.db", "app.config"),
    "controllers": ("app.api",),
    "core": ("app.api", "app.controllers", "app.db", "app.config", "sqlite3", "fastapi", "pydantic"),
    "db": ("app.api", "app.controllers", "app.core", "app.config"),
}

CLOCK_FILE = APP_DIR / "controllers" / "clock.py"
CLOCK_CALLS = {"today", "now", "utcnow"}


def imported_modules(source: str) -> list[str]:
    modules = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "app":
                modules.extend(f"app.{alias.name}" for alias in node.names)
            else:
                modules.append(node.module)
    return modules


def forbidden_imports(source: str, forbidden: tuple[str, ...]) -> list[str]:
    return [
        module
        for module in imported_modules(source)
        if any(module == name or module.startswith(name + ".") for name in forbidden)
    ]


def clock_calls(source: str) -> list[str]:
    return [
        node.func.attr
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in CLOCK_CALLS
        and not (isinstance(node.func.value, ast.Name) and node.func.value.id == "clock")
    ]


def python_files(layer_dir: Path):
    return sorted(layer_dir.rglob("*.py"))


def test_checker_catches_forbidden_imports():
    source = "import sqlite3\nfrom app.db import connection\nfrom app import core\nimport json\n"
    assert forbidden_imports(source, FORBIDDEN_IMPORTS["core"]) == ["sqlite3", "app.db"]


def test_checker_catches_from_app_import_layer():
    assert forbidden_imports("from app import db\n", FORBIDDEN_IMPORTS["core"]) == ["app.db"]


def test_checker_does_not_confuse_similar_names():
    assert forbidden_imports("import app.dbx\nfrom app.database import x\n", ("app.db",)) == []


def test_checker_allows_asking_the_date_through_the_clock_module():
    assert clock_calls("from app.controllers import clock\nx = clock.today()\n") == []


def test_checker_catches_clock_calls():
    source = "from datetime import date, datetime\nx = date.today()\ny = datetime.now()\n"
    assert clock_calls(source) == ["today", "now"]


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_IMPORTS))
def test_layer_imports_respect_the_dependency_rules(layer):
    layer_dir = APP_DIR / layer
    if not layer_dir.exists():
        pytest.skip(f"A camada {layer} ainda nao existe")
    violations = {}
    for path in python_files(layer_dir):
        found = forbidden_imports(path.read_text(encoding="utf-8"), FORBIDDEN_IMPORTS[layer])
        if found:
            violations[str(path.relative_to(APP_DIR))] = found
    assert violations == {}


def test_only_the_clock_file_reads_the_clock():
    violations = {}
    for path in python_files(APP_DIR):
        if path == CLOCK_FILE:
            continue
        found = clock_calls(path.read_text(encoding="utf-8"))
        if found:
            violations[str(path.relative_to(APP_DIR))] = found
    assert violations == {}


def test_the_clock_file_exists_and_reads_the_clock():
    assert clock_calls(CLOCK_FILE.read_text(encoding="utf-8")) == ["now"]
