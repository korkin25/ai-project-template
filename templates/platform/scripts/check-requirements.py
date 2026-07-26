#!/usr/bin/env python3
"""Verify a live cluster against requirements.yaml.

The platform repo declares what it needs; an infra repo satisfies it. This script closes
the loop, so an unmet prerequisite is a named failure *before* deploying rather than a
CrashLoopBackOff an hour later.

Run it against whichever cluster the current kubecontext points at::

    check-requirements.py                       # required items only decide the exit code
    check-requirements.py --strict              # optional items fail too
    check-requirements.py --context laptop-local

Exit codes: 0 all satisfied · 1 something required is missing · 2 cannot reach the cluster.

Data services are reported as UNVERIFIED rather than guessed at: "a Kafka-compatible bus"
can be satisfied by an operator, a chart or a managed endpoint, and probing for one
implementation would report a false failure for the others.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("ERROR: PyYAML is required (pip install pyyaml)")

OK, MISSING, UNVERIFIED = "OK", "MISSING", "UNVERIFIED"
MARK = {OK: "  ok  ", MISSING: " MISS ", UNVERIFIED: "  ??  "}


class Cluster:
    """Thin kubectl wrapper. Everything it does is read-only."""

    def __init__(self, context: str | None = None) -> None:
        self._base = ["kubectl"] + (["--context", context] if context else [])
        self._api_resources: set[tuple[str, str]] | None = None

    def _run(self, *args: str) -> tuple[int, str]:
        proc = subprocess.run(
            self._base + list(args), capture_output=True, text=True, check=False
        )
        return proc.returncode, proc.stdout

    def reachable(self) -> bool:
        return self._run("version", "-o", "json")[0] == 0

    def server_version(self) -> str:
        code, out = self._run("version", "-o", "json")
        if code != 0:
            return ""
        try:
            return json.loads(out).get("serverVersion", {}).get("gitVersion", "")
        except json.JSONDecodeError:
            return ""

    def api_resources(self) -> set[tuple[str, str]]:
        """(apiGroup, Kind) available on the server."""
        if self._api_resources is None:
            self._api_resources = set()
            code, out = self._run("api-resources", "--no-headers")
            if code == 0:
                # Columns: NAME [SHORTNAMES] APIVERSION NAMESPACED KIND — SHORTNAMES is
                # omitted when empty, so only the trailing three are positionally stable.
                # Counting from the right: [-1] KIND, [-2] NAMESPACED, [-3] APIVERSION.
                for line in out.splitlines():
                    parts = line.split()
                    if len(parts) < 3:
                        continue
                    kind, apiversion = parts[-1], parts[-3]
                    group = apiversion.split("/")[0] if "/" in apiversion else ""
                    self._api_resources.add((group, kind))
        return self._api_resources

    def has_kind(self, group: str, kind: str) -> bool:
        return any(g == group and k == kind for g, k in self.api_resources())

    def get_json(self, kind: str, *args: str) -> list[dict[str, Any]]:
        code, out = self._run("get", kind, "-o", "json", *args)
        if code != 0:
            return []
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return []
        return data.get("items", [data]) if data else []

    def ready_pods(self, namespace: str, name_contains: str) -> int:
        count = 0
        for pod in self.get_json("pods", "-n", namespace):
            if name_contains not in pod.get("metadata", {}).get("name", ""):
                continue
            conditions = pod.get("status", {}).get("conditions") or []
            if any(c.get("type") == "Ready" and c.get("status") == "True" for c in conditions):
                count += 1
        return count


def version_satisfies(actual: str, constraint: str) -> bool:
    """Support the one operator the contract uses: >=X.Y.Z."""
    match = re.match(r"^\s*>=\s*(\d+)\.(\d+)", constraint)
    got = re.search(r"(\d+)\.(\d+)", actual or "")
    if not match or not got:
        return False
    return (int(got.group(1)), int(got.group(2))) >= (int(match.group(1)), int(match.group(2)))


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str, bool, str]] = []

    def add(self, section: str, item: str, status: str, required: bool, note: str = "") -> None:
        self.rows.append((section, item, status, required, note))

    def render(self, strict: bool) -> int:
        section = None
        for sec, item, status, required, note in self.rows:
            if sec != section:
                print(f"\n{sec}")
                section = sec
            flag = "required" if required else "optional"
            print(f"  [{MARK[status]}] {item:<34} {flag:<9} {note}")

        missing_required = [r for r in self.rows if r[2] == MISSING and r[3]]
        missing_optional = [r for r in self.rows if r[2] == MISSING and not r[3]]
        unverified = [r for r in self.rows if r[2] == UNVERIFIED]

        print(
            f"\n{len([r for r in self.rows if r[2] == OK])} satisfied, "
            f"{len(missing_required)} required missing, "
            f"{len(missing_optional)} optional missing, "
            f"{len(unverified)} unverified."
        )
        if missing_required:
            print("\nRequired but missing — the platform cannot be deployed here:", file=sys.stderr)
            for _, item, _, _, note in missing_required:
                print(f"  - {item}: {note}", file=sys.stderr)
        if unverified:
            print("\nVerify by hand (capability, not a fixed implementation):")
            for _, item, _, _, note in unverified:
                print(f"  - {item}: {note}")

        if missing_required:
            return 1
        return 1 if (strict and missing_optional) else 0


def check(reqs: dict[str, Any], cluster: Cluster, report: Report) -> None:
    cl = reqs.get("cluster") or {}
    if constraint := cl.get("kubernetesVersion"):
        actual = cluster.server_version()
        status = OK if version_satisfies(actual, constraint) else MISSING
        report.add("cluster", f"kubernetes {constraint}", status, True, f"found {actual or 'unknown'}")

    for sc in cl.get("storageClasses") or []:
        items = cluster.get_json("storageclass")
        if sc.get("name") == "*default*":
            found = [
                i["metadata"]["name"]
                for i in items
                if (i.get("metadata", {}).get("annotations") or {}).get(
                    "storageclass.kubernetes.io/is-default-class"
                )
                == "true"
            ]
            report.add(
                "cluster",
                "default storage class",
                OK if found else MISSING,
                True,
                f"found {found[0]}" if found else "no class is marked default",
            )
        else:
            names = [i["metadata"]["name"] for i in items]
            report.add(
                "cluster",
                f"storageclass/{sc['name']}",
                OK if sc["name"] in names else MISSING,
                True,
            )

    for op in reqs.get("operators") or []:
        required = bool(op.get("required"))
        # Explicit (group, kind) pairs, never a cross product of two lists — that would
        # invent combinations like source.toolkit.fluxcd.io/HelmRelease and report a
        # perfectly healthy cluster as broken.
        missing_kinds = [
            f"{res['group']}/{res['kind']}"
            for res in op.get("resources") or []
            if not cluster.has_kind(res["group"], res["kind"])
        ]
        notes: list[str] = []
        status = OK
        if missing_kinds:
            status = MISSING
            notes.append("no CRD " + ", ".join(missing_kinds))

        # An installed CRD with no running controller is the failure that looks like success.
        for dep in op.get("deployments") or []:
            n = cluster.ready_pods(dep.get("namespace", "default"), dep.get("nameContains", ""))
            if n == 0:
                status = MISSING
                notes.append(f"no ready pod matching {dep.get('nameContains')!r} in {dep.get('namespace')}")
            else:
                notes.append(f"{n} ready pod(s)")

        report.add("operators", op["name"], status, required, "; ".join(notes))

    for res in reqs.get("namedResources") or []:
        kind, name = res["kind"], res["name"]
        namespaces = res.get("namespaces") or [None]
        missing_in: list[str] = []
        for ns in namespaces:
            args = ["-n", ns] if ns else ["-A"]
            names = [i["metadata"]["name"] for i in cluster.get_json(kind.lower(), *args)]
            if name not in names:
                missing_in.append(ns or "cluster")
        label = f"{kind}/{name}"
        if missing_in:
            report.add("named resources", label, MISSING, bool(res.get("required")), "absent in " + ", ".join(missing_in))
        else:
            where = ", ".join(n for n in namespaces if n) or "cluster-scoped"
            report.add("named resources", label, OK, bool(res.get("required")), where)

    for svc in reqs.get("dataServices") or []:
        report.add("data services", svc["name"], UNVERIFIED, bool(svc.get("required")), svc.get("capability", ""))

    for model in reqs.get("modelAccess") or []:
        node_reqs = (model.get("nodeRequirements") or {}).get("resources") or []
        if not node_reqs:
            report.add("model access", model["name"], UNVERIFIED, bool(model.get("required")), model.get("capability", ""))
            continue
        nodes = cluster.get_json("nodes")
        satisfied = [
            n["metadata"]["name"]
            for n in nodes
            if all(r in (n.get("status", {}).get("capacity") or {}) for r in node_reqs)
        ]
        report.add(
            "model access",
            model["name"],
            OK if satisfied else MISSING,
            bool(model.get("required")),
            f"nodes {satisfied}" if satisfied else f"no node advertises {', '.join(node_reqs)}",
        )

    for net in reqs.get("networking") or []:
        has = cluster.has_kind("gateway.networking.k8s.io", "Gateway")
        gateways = [i["metadata"]["name"] for i in cluster.get_json("gateway", "-A")] if has else []
        report.add(
            "networking",
            net["name"],
            OK if gateways else MISSING,
            bool(net.get("required")),
            f"gateways {gateways}" if gateways else ("CRD present, no Gateway object" if has else "no Gateway API CRD"),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default="requirements.yaml")
    parser.add_argument("--context", help="kubecontext to check")
    parser.add_argument("--strict", action="store_true", help="optional items also fail the run")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(f"ERROR: {path} not found (run from the repository root)", file=sys.stderr)
        return 2

    reqs = yaml.safe_load(path.read_text(encoding="utf-8"))
    cluster = Cluster(args.context)
    if not cluster.reachable():
        print("ERROR: cannot reach the cluster — check KUBECONFIG / --context", file=sys.stderr)
        return 2

    name = (reqs.get("metadata") or {}).get("name", path.stem)
    print(f"Checking cluster against '{name}' requirements ({cluster.server_version()})")

    report = Report()
    check(reqs, cluster, report)
    return report.render(args.strict)


if __name__ == "__main__":
    sys.exit(main())
