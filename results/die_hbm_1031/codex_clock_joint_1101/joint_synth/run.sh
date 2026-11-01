#!/bin/bash
set -euo pipefail
O=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name codex-hbm-joint-start-synth --memory=2g --memory-swap=2g --cpus=2 -v "$O:/o" openroad/orfs:asap7lock bash /o/inside.sh
