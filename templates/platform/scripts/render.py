#!/usr/bin/env python3
"""Render environment bundles into Flux resources.

Reads ``clusters/<cluster>/environments/<env>/bundle.yaml`` plus that environment's
``values/`` directory, and emits one ``OCIRepository`` + one ``HelmRelease`` per entry.

The rendered output is never committed: Flux reconciles from the bundle via a
Kustomization that runs this renderer, and CI shows the rendered diff on a merge request.
Committing the output would create a second source of truth and guarantee drift.

Layout of the generated resources::

    OCIRepository  flux-system/<bundle-name>-<name>   pins the chart at an exact version
    HelmRelease    <namespace>/<name>                 references it via chartRef

The ``OCIRepository`` lives in the Flux namespace because the registry pull secret lives
there and is shared by every environment; its name therefore carries the bundle prefix to
stay unique. The ``HelmRelease`` is already scoped by its namespace and does not.

Usage::

    render.py clusters/example-cluster/environments/dev        # to stdout
    render.py --out-dir rendered/ clusters/*/environments/*   # one file per environment
    render.py --all                                           # discover every environment
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - environment problem, not a data problem
    sys.exit("ERROR: PyYAML is required (pip install pyyaml)")

DEFAULT_INTERVAL = "30m"
HELM_CHART_MEDIA_TYPE = "application/vnd.cncf.helm.chart.content.v1.tar+gzip"


class BundleError(Exception):
    """A bundle is structurally valid YAML but cannot be rendered."""


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge ``override`` onto ``base``; dicts merge recursively, everything else replaces.

    Lists replace rather than concatenate: appending would make it impossible for an
    environment to *shorten* a list inherited from common.yaml.
    """
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise BundleError(f"{path}: expected a mapping at the top level, got {type(data).__name__}")
    return data


def global_values(bundle: dict[str, Any]) -> dict[str, Any]:
    """Values every chart in the environment receives under ``global``.

    These come from the bundle rather than from values files so that an environment cannot
    accidentally point at another environment's registry or secret path.
    """
    globals_: dict[str, Any] = {"namespace": bundle["namespace"], "imageRegistry": bundle["imageRegistry"]}
    for bundle_key, chart_key in (("publishDomain", "publishDomain"), ("vaultPathPrefix", "vaultPathPrefix")):
        if bundle.get(bundle_key):
            globals_[chart_key] = bundle[bundle_key]
    return globals_


def entries(bundle: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """Flatten both lists into ``(name, chart, entry)``, skipping disabled ones."""
    out: list[tuple[str, str, dict[str, Any]]] = []
    for item in bundle.get("microservices") or []:
        if item.get("disabled"):
            continue
        out.append((item["service"], item["service"], item))
    for item in bundle.get("platform") or []:
        if item.get("disabled"):
            continue
        out.append((item["component"], item["chart"], item))

    seen: dict[str, None] = {}
    for name, _, _ in out:
        if name in seen:
            raise BundleError(
                f"duplicate name {name!r}: a microservice and a platform component cannot share "
                f"a name — they would render to the same HelmRelease"
            )
        seen[name] = None
    return out


def render_environment(env_dir: Path) -> list[dict[str, Any]]:
    bundle_path = env_dir / "bundle.yaml"
    if not bundle_path.is_file():
        raise BundleError(f"{env_dir}: no bundle.yaml")

    bundle = load_yaml(bundle_path)
    for required in ("name", "namespace", "imageRegistry"):
        if not bundle.get(required):
            raise BundleError(f"{bundle_path}: missing required field {required!r}")

    values_dir = env_dir / "values"
    common = load_yaml(values_dir / "common.yaml")
    interval = bundle.get("interval") or DEFAULT_INTERVAL
    pull_secret = bundle.get("imagePullSecret")
    namespace = bundle["namespace"]
    prefix = bundle["name"]

    resources: list[dict[str, Any]] = []
    for name, chart, entry in entries(bundle):
        values_path = values_dir / f"{name}.yaml"
        values = deep_merge(common, load_yaml(values_path))
        values = deep_merge({"global": global_values(bundle)}, values)

        source_name = f"{prefix}-{name}"
        source: dict[str, Any] = {
            "apiVersion": "source.toolkit.fluxcd.io/v1",
            "kind": "OCIRepository",
            "metadata": {"name": source_name, "namespace": "flux-system"},
            "spec": {
                "interval": interval,
                "url": f"{entry['repoURL'].rstrip('/')}/{chart}",
                "ref": {"tag": entry["chartVersion"]},
                "layerSelector": {"mediaType": HELM_CHART_MEDIA_TYPE, "operation": "copy"},
            },
        }
        if pull_secret:
            source["spec"]["secretRef"] = {"name": pull_secret}

        release: dict[str, Any] = {
            "apiVersion": "helm.toolkit.fluxcd.io/v2",
            "kind": "HelmRelease",
            "metadata": {"name": name, "namespace": namespace},
            "spec": {
                "interval": interval,
                "releaseName": name,
                "chartRef": {"kind": "OCIRepository", "name": source_name, "namespace": "flux-system"},
                "install": {"remediation": {"retries": 3}},
                # remediateLastFailure keeps a bad upgrade from sitting broken until a human
                # notices; the previous release is restored automatically.
                "upgrade": {"remediation": {"retries": 3, "remediateLastFailure": True}},
                "values": values,
            },
        }
        resources.extend((source, release))

    return resources


def discover(patterns: list[str]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        for match in sorted(glob.glob(pattern)):
            path = Path(match)
            if path.is_dir() and (path / "bundle.yaml").is_file():
                found.append(path)
            elif path.name == "bundle.yaml":
                found.append(path.parent)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", help="environment directories (globs allowed)")
    parser.add_argument("--all", action="store_true", help="render every clusters/*/environments/*")
    parser.add_argument("--out-dir", metavar="DIR", help="write <cluster>-<env>.yaml per environment instead of stdout")
    args = parser.parse_args()

    patterns = list(args.paths)
    if args.all or not patterns:
        patterns = ["clusters/*/environments/*"]

    env_dirs = discover(patterns)
    if not env_dirs:
        print(f"ERROR: no environment with a bundle.yaml matched {patterns}", file=sys.stderr)
        return 1

    failures = 0
    for env_dir in env_dirs:
        try:
            resources = render_environment(env_dir)
        except (BundleError, KeyError, yaml.YAMLError) as exc:
            print(f"ERROR: {env_dir}: {exc}", file=sys.stderr)
            failures += 1
            continue

        document = "---\n" + "---\n".join(
            yaml.safe_dump(resource, sort_keys=False, default_flow_style=False) for resource in resources
        )
        if args.out_dir:
            out_dir = Path(args.out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            # clusters/<cluster>/environments/<env> -> <cluster>-<env>.yaml
            name = f"{env_dir.parents[1].name}-{env_dir.name}.yaml"
            (out_dir / name).write_text(document, encoding="utf-8")
            print(f"wrote {out_dir / name} ({len(resources) // 2} releases)", file=sys.stderr)
        else:
            sys.stdout.write(document)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
