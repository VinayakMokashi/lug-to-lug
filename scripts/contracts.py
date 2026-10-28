"""Generate the Python data contracts from the JSON Schemas in data/schemas.

    uv run poe contracts          # write the generated modules
    uv run poe contracts-check    # fail if they are out of date (CI runs this)

The schemas are the single source of truth (ADR-0004). The Pydantic models in
packages/core/src/lugtolug_core/contracts/ are generated from them and never edited
by hand; the web app generates its TypeScript types from the same files
(apps/web/scripts/contracts.mjs).
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "data" / "schemas"
TARGET = ROOT / "packages" / "core" / "src" / "lugtolug_core" / "contracts"
COMMON = "common.schema.json"

# Schema file -> generated module. common.schema.json only holds shared definitions;
# each module gets the ones its schema uses.
MODULES = {
    "stand-in-spec.schema.json": "stand_in.py",
    "catalogue-entry.schema.json": "catalogue.py",
    "annotation.schema.json": "annotation.py",
}

CODEGEN_OPTIONS = [
    "--input-file-type=jsonschema",
    "--output-model-type=pydantic_v2.BaseModel",
    "--target-python-version=3.12",
    "--use-standard-collections",
    "--use-union-operator",
    "--use-annotated",
    # Strict types accept what JSON Schema accepts: no "40" for 40, no "yes" for true.
    "--strict-types",
    "str",
    "int",
    "float",
    "bool",
    "--field-constraints",
    "--strict-nullable",
    "--enum-field-as-literal=all",
    "--collapse-root-models",
    "--use-title-as-name",
    "--use-schema-description",
    "--use-field-description",
    "--use-double-quotes",
    "--output-datetime-class=AwareDatetime",
    "--disable-timestamp",
    "--formatters=builtin",
]


def bundle(schema_name: str) -> dict[str, Any]:
    """Return the schema with the shared definitions it uses copied into its own $defs.

    Generating from a bundled schema keeps unused shared definitions out of the module.
    """
    schema: dict[str, Any] = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
    shared: dict[str, Any] = json.loads((SCHEMAS / COMMON).read_text(encoding="utf-8"))["$defs"]
    local: dict[str, Any] = schema.setdefault("$defs", {})
    prefix = f"{COMMON}#/$defs/"

    def walk(node: object) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith(prefix):
                name = ref.removeprefix(prefix)
                if name not in local:
                    local[name] = copy.deepcopy(shared[name])
                    walk(local[name])
                elif local[name] != shared[name]:
                    raise SystemExit(f"{schema_name}: a local definition is named {name}")
                node["$ref"] = f"#/$defs/{name}"
            for value in list(node.values()):
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
    return schema


def _run(*args: str) -> None:
    # Fixed argument lists built in this file, never user input.
    subprocess.run([sys.executable, "-m", *args], check=True, cwd=ROOT)  # noqa: S603


def generate(out_dir: Path) -> None:
    """Write every generated module into out_dir, formatted like the rest of the code."""
    for schema, module in MODULES.items():
        bundled = out_dir / schema
        bundled.write_text(json.dumps(bundle(schema), indent=2), encoding="utf-8")
        header = (
            f"# Generated from data/schemas/{schema} by scripts/contracts.py.\n"
            "# Do not edit: change the schema, then run `uv run poe contracts`."
        )
        _run(
            "datamodel_code_generator",
            f"--input={bundled}",
            f"--output={out_dir / module}",
            f"--custom-file-header={header}",
            *CODEGEN_OPTIONS,
        )
    config = f"--config={ROOT / 'pyproject.toml'}"
    # Long descriptions from the schemas stay unwrapped, as in pyproject.toml.
    _run("ruff", "check", "--fix", "--quiet", "--ignore=E501", config, str(out_dir))
    _run("ruff", "format", "--quiet", config, str(out_dir))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if the files are stale")
    check = parser.parse_args().check

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        generate(out)
        stale = []
        for module in MODULES.values():
            fresh = (out / module).read_text(encoding="utf-8")
            target = TARGET / module
            current = target.read_text(encoding="utf-8") if target.exists() else None
            if fresh == current:
                continue
            if check:
                stale.append(target.relative_to(ROOT).as_posix())
            else:
                target.write_text(fresh, encoding="utf-8", newline="\n")
                print(f"wrote {target.relative_to(ROOT).as_posix()}")

    if stale:
        print("Out of date with data/schemas (run `uv run poe contracts`):", *stale, sep="\n  ")
        return 1
    if check:
        print("Contracts are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
