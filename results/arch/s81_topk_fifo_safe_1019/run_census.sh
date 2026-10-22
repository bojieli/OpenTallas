#!/bin/bash
set -euo pipefail
cd src
docker run --rm -v "$PWD":/work -w /work openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -s results/arch/s81_topk_fifo_safe_1019/census.ys > census.log 2>&1
