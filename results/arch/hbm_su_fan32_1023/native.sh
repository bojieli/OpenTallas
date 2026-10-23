#!/bin/bash
set -euo pipefail
HERE=$(pwd)
docker run --rm -v "$HERE/src:/src:ro" -v "$HERE/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 make DESIGN_CONFIG=/work/config.mk synth > full_native_synth.log 2>&1
docker run --rm -v "$HERE/src:/src:ro" -v "$HERE/work:/work" -w /work openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 python3 /work/audit.py > full_native_audit.log 2>&1
