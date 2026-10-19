#!/bin/bash
set -euo pipefail
cd ..
python3 tools/hbm_hidx_coupon1/summary.py
docker run --rm --network none openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 yosys -V >out/yosys_version.txt
iverilog -V >out/iverilog_version.txt 2>&1
sha256sum tools/hbm_hidx_coupon1/* out/*.log out/*.json out/*.lib out/*.v out/image.txt out/*version.txt >out/SHA256SUMS
