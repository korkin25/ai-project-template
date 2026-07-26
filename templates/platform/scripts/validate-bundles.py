#!/usr/bin/env python3
"""Validate every environment bundle against bundle.schema.json, plus the checks a schema cannot express.

Run by CI on every merge request. A typo in a bundle must fail here rather than silently
render nothing — which is why the schema sets ``additionalProperties: false`` throughout and
why the semantic checks below exist at all.

Usage::

    validate-bundles.py                 # every clusters/*/environments/*/bundle.yaml
    validate-bundles.py path/to/bundle.yaml ...
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
    from jsonschema import Draft7Validator
except ImportError:  # pragma: no cover - environment problem
    sys.exit("ERROR: PyYAML and jsonschema are required (pip install pyyaml jsonschema)")

BUNDLE_GLOB = "clusters/*/environments/*/bundle.yaml"
SCHEMA_PATH = Path("bundle.schema.json")


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def semantic_checks(path: Path, bundle: dict[str, Any]) -> list[str]:
    """Checks JSON Schema cannot express: cross-field consistency and files on disk."""
    problems: list[str] = []
    env_dir = path.parent
    values_dir = env_dir / "values"

    named: list[tuple[str, str]] = []
    for item in bundle.get("microservices") or []:
        named.append((item.get("service", "<unnamed>"), "microservices"))
    for item in bundle.get("platform") or []:
        named.append((item.get("component", "<unnamed>"), "platform"))

    seen: dict[str, str] = {}
    for name, where in named:
        if name in seen:
            problems.append(
                f"name {name!r} appears in both {seen[name]} and {where} — "
                f"both would render to the same HelmRelease in namespace {bundle.get('namespace')!r}"
            )
        seen[name] = where

    # A missing values file is legal (the chart's defaults apply) but is far more often a
    # typo in the name than a deliberate choice, so it is reported as a warning-level problem.
    for name, _ in named:
        candidate = values_dir / f"{name}.yaml"
        if not candidate.is_file():
            problems.append(f"no values file {candidate} for {name!r} — chart defaults will be used (typo?)")

    # An orphaned values file is always a mistake: it silently affects nothing.
    if values_dir.is_dir():
        declared = {name for name, _ in named} | {"common"}
        for candidate in sorted(values_dir.glob("*.yaml")):
            if candidate.stem not in declared:
                problems.append(f"{candidate} is not referenced by any entry in the bundle — dead file")

    # The pull secret is declared twice because it is used by two different clients, and
    # nothing else notices when the two drift apart. `imagePullSecret` in the bundle is what
    # render.py injects into the Flux OCIRepository, so Flux can pull the CHART;
    # `imagePullSecrets` in values/common.yaml lands on the pod spec, so the kubelet can pull
    # the IMAGE. A mismatch fails asymmetrically and reads badly: the Kustomization reconciles
    # green while pods sit in ImagePullBackOff, or the chart never fetches at all and no pod
    # exists to look at. Both are minutes of confusion that this one comparison removes.
    common = values_dir / "common.yaml"
    declared_secret = bundle.get("imagePullSecret")
    if declared_secret and common.is_file():
        common_values = load_yaml(common) or {}
        entries = common_values.get("imagePullSecrets") or []
        names = [e.get("name") for e in entries if isinstance(e, dict)]
        if names and declared_secret not in names:
            problems.append(
                f"imagePullSecret {declared_secret!r} in the bundle is not among "
                f"{names!r} in {common} — Flux would pull the chart with one Secret and the "
                f"kubelet the image with another"
            )

    # The directory name is part of the promotion workflow; a mismatch makes "copy the version
    # from dev to stage" land in the wrong place.
    if bundle.get("name") and env_dir.name not in bundle["name"]:
        problems.append(
            f"bundle name {bundle['name']!r} does not contain the environment directory name "
            f"{env_dir.name!r} — promotion between environments relies on this correspondence"
        )

    return problems


def main() -> int:
    args = sys.argv[1:]
    paths = [Path(p) for p in args] if args else [Path(p) for p in sorted(glob.glob(BUNDLE_GLOB))]

    if not paths:
        print(f"No bundle.yaml found matching {BUNDLE_GLOB} — nothing to validate.")
        return 0

    if not SCHEMA_PATH.is_file():
        print(f"ERROR: {SCHEMA_PATH} not found (run from the repository root)", file=sys.stderr)
        return 1

    import json

    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        validator = Draft7Validator(json.load(handle))

    namespaces: dict[str, Path] = {}
    failures = 0

    for path in paths:
        try:
            bundle = load_yaml(path)
        except yaml.YAMLError as exc:
            print(f"FAIL {path}: not valid YAML: {exc}", file=sys.stderr)
            failures += 1
            continue

        if not isinstance(bundle, dict):
            print(f"FAIL {path}: expected a mapping at the top level", file=sys.stderr)
            failures += 1
            continue

        problems = [
            f"{'.'.join(str(p) for p in error.absolute_path) or '<root>'}: {error.message}"
            for error in sorted(validator.iter_errors(bundle), key=lambda e: list(e.absolute_path))
        ]
        problems += semantic_checks(path, bundle)

        # Two environments sharing a namespace would have their HelmReleases overwrite
        # each other — the schema cannot see across files, so it is checked here.
        namespace = bundle.get("namespace")
        if namespace:
            if namespace in namespaces and namespaces[namespace] != path:
                problems.append(f"namespace {namespace!r} is already used by {namespaces[namespace]}")
            namespaces.setdefault(namespace, path)

        if problems:
            failures += 1
            print(f"FAIL {path}", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
        else:
            n = len(bundle.get("microservices") or []) + len(bundle.get("platform") or [])
            print(f"OK   {path} ({n} components, namespace {bundle.get('namespace')})")

    if failures:
        print(f"\n{failures} of {len(paths)} bundle(s) failed validation.", file=sys.stderr)
        return 1

    print(f"\nAll {len(paths)} bundle(s) valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
