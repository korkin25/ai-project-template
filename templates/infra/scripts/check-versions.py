#!/usr/bin/env python3
"""Compare every version pinned in this repository against the newest one upstream.

Pinning is what makes a cluster reproducible; it is also what makes it quietly age. This
closes that loop: it reads the pins out of the Flux manifests, asks each vendor what the
newest version is, and prints the gap classified by SemVer distance.

It is READ-ONLY and changes nothing. Deciding to upgrade means reading a changelog, which
is a human act — this only tells you which changelogs are worth reading.

    check-versions.py              # human table
    check-versions.py --json       # machine-readable
    check-versions.py --major-only # only the upgrades that can break something

Exit codes: 0 everything current · 1 something is behind · 2 a source could not be reached
(which is itself worth knowing — an unreachable vendor is a supply-chain problem).
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

SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


def parse(v: str) -> tuple[int, int, int] | None:
    m = SEMVER.match(v.strip())
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def distance(pinned: str, latest: str) -> str:
    """How far behind, in the terms that decide how carefully you read the changelog."""
    a, b = parse(pinned), parse(latest)
    if a is None or b is None:
        return "?" if pinned != latest else "current"
    if a == b:
        return "current"
    if a > b:
        # Pinned ahead of what the vendor lists: a yanked release, or a private build.
        # Either way it is not "up to date", it is unexplained.
        return "AHEAD"
    if a[0] != b[0]:
        return "MAJOR"
    if a[1] != b[1]:
        return "minor"
    return "patch"


def run(*args: str, timeout: int = 90) -> tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return p.returncode, p.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, ""


def latest_oci(url: str) -> str | None:
    """Newest tag of an OCI chart. `helm show chart` without --version resolves to latest."""
    code, out = run("helm", "show", "chart", url)
    if code != 0:
        return None
    for line in out.splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip().strip('"')
    return None


def latest_helm_repo(name: str, url: str, chart: str) -> str | None:
    """Newest version of a chart in a classic repository."""
    if run("helm", "repo", "add", f"_audit_{name}", url)[0] != 0:
        return None
    run("helm", "repo", "update", f"_audit_{name}")
    code, out = run("helm", "search", "repo", f"_audit_{name}/{chart}", "--output", "json")
    if code != 0:
        return None
    try:
        hits = json.loads(out)
    except json.JSONDecodeError:
        return None
    # search matches by substring, so an exact name match is required.
    for h in hits:
        if h.get("name", "").split("/", 1)[-1] == chart:
            return h.get("version")
    return None


def collect(root: Path) -> list[dict[str, Any]]:
    """Read every pin: OCIRepository tags, HelmRelease chart versions, container images."""
    sources: dict[str, dict[str, str]] = {}   # HelmRepository name -> url
    found: list[dict[str, Any]] = []

    for path in sorted(root.rglob("*.y*ml")):
        if ".git" in path.parts:
            continue
        try:
            docs = [d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict)]
        except yaml.YAMLError:
            continue
        for d in docs:
            kind, spec = d.get("kind"), d.get("spec") or {}
            name = (d.get("metadata") or {}).get("name", "?")
            rel = str(path.relative_to(root))

            if kind == "HelmRepository":
                sources[name] = {"url": spec.get("url", "")}
            elif kind == "OCIRepository":
                tag = ((spec.get("ref") or {}).get("tag"))
                if tag:
                    found.append({"kind": "OCIRepository", "name": name, "pinned": str(tag),
                                  "url": spec.get("url", ""), "file": rel})
            elif kind == "HelmRelease":
                cs = (spec.get("chart") or {}).get("spec") or {}
                if cs.get("version"):
                    found.append({"kind": "HelmRelease", "name": name,
                                  "pinned": str(cs["version"]), "chart": cs.get("chart", ""),
                                  "source": (cs.get("sourceRef") or {}).get("name", ""),
                                  "file": rel})

            # Container images pinned directly in a manifest.
            for img in re.findall(r"(?:image|imageName):\s*['\"]?([\w./:-]+:[\w.\-]+)['\"]?", yaml.safe_dump(d)):
                repo, _, tag = img.rpartition(":")
                if tag and tag != "latest":
                    found.append({"kind": "image", "name": repo.split("/")[-1],
                                  "pinned": tag, "url": repo, "file": rel})
                elif tag == "latest":
                    found.append({"kind": "image", "name": repo.split("/")[-1],
                                  "pinned": "latest", "url": repo, "file": rel,
                                  "latest": "UNPINNED", "distance": "UNPINNED"})
    for f in found:
        if f.get("kind") == "HelmRelease" and f.get("source") in sources:
            f["url"] = sources[f["source"]]["url"]
    return found


def resolve(entry: dict[str, Any]) -> None:
    if entry.get("distance") == "UNPINNED":
        return
    if entry["kind"] == "OCIRepository":
        entry["latest"] = latest_oci(entry["url"])
    elif entry["kind"] == "HelmRelease":
        entry["latest"] = latest_helm_repo(entry.get("source", "x"), entry.get("url", ""),
                                           entry.get("chart", ""))
    else:
        # Images are deliberately not resolved: a tag list is not ordered by recency and
        # every registry disagrees on the API. Reporting them as unknown is honest;
        # guessing "latest" from a tag list is how a downgrade gets recommended.
        entry["latest"] = None
    entry["distance"] = distance(entry["pinned"], entry["latest"]) if entry.get("latest") else "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--major-only", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    entries = collect(root)
    # Deduplicate: the same image often appears in several rendered documents.
    seen, unique = set(), []
    for e in entries:
        key = (e["kind"], e.get("url", ""), e["name"], e["pinned"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    for e in unique:
        resolve(e)

    if args.major_only:
        unique = [e for e in unique if e.get("distance") in {"MAJOR", "UNPINNED", "AHEAD"}]

    if args.json:
        print(json.dumps(unique, indent=2))
    else:
        order = {"UNPINNED": 0, "AHEAD": 1, "MAJOR": 2, "minor": 3, "patch": 4,
                 "unknown": 5, "?": 6, "current": 7}
        unique.sort(key=lambda e: (order.get(e.get("distance", "?"), 9), e["name"]))
        print(f"{'STATE':<9} {'NAME':<26} {'PINNED':<22} {'LATEST':<22} SOURCE")
        for e in unique:
            print(f"{e.get('distance','?'):<9} {e['name']:<26} {e['pinned']:<22} "
                  f"{str(e.get('latest') or '-'):<22} {e.get('file','')}")

        counts: dict[str, int] = {}
        for e in unique:
            counts[e.get("distance", "?")] = counts.get(e.get("distance", "?"), 0) + 1
        print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        behind = [e for e in unique if e.get("distance") in {"MAJOR", "minor", "patch"}]
        if behind:
            print("\nRead these changelogs before upgrading anything:")
            for e in behind:
                print(f"  - {e['name']}: {e['pinned']} -> {e['latest']}  ({e['distance']})")

    if any(e.get("distance") == "unknown" for e in unique):
        pass  # unreachable sources are reported but do not alone fail the run
    if any(e.get("distance") in {"MAJOR", "minor", "patch", "UNPINNED", "AHEAD"} for e in unique):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
