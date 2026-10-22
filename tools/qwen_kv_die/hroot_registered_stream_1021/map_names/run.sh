#!/usr/bin/env bash
set -euo pipefail
image='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
# The exact pinned image is set below; this replay adds output metadata only.
image='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$image" bash map.sh >map_docker.log 2>&1
