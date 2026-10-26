#!/bin/bash
set -euo pipefail
B=$(cd "$(dirname "$0")" && pwd)
cd "$B"
sha256sum -c MAP_MEM_INPUTS.sha256
docker run --rm --user "$(id -u):$(id -g)" -v "$B:/work" -w /work openroad/orfs:asap7lock bash map_hp13_mem_inner.sh
