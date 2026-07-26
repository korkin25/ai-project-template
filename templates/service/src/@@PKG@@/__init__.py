"""@@PROJECT@@ — @@DESCRIPTION@@.

The importable package. Its entrypoint is ``python -m @@PKG@@.main`` (that is what
``deploy/Dockerfile`` runs), so anything a deployment needs must be reachable from there.
"""

# Fallback only. The version that matters at runtime arrives in the APP_VERSION environment
# variable, which the Helm chart sets from .Chart.AppVersion — i.e. from the GitVersion
# SemVer that CI stamped onto BOTH the image tag and the chart version. That is the one
# number that lets a platform operator map a running pod back to a commit, and it cannot be
# known at build time of this file.
#
# Never hand-edit this to a "real" version: a hardcoded version that disagrees with the image
# tag is worse than an obviously fake one, because it looks authoritative in /health output.
__version__ = "0.0.0"
