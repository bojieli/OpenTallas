#!/bin/bash
set -euo pipefail
python3 tools/hbm_hidx_coupon1/csa_audit.py >out/csa_audit.log
# Actual native electrical checks including nonviolating worst checks.
docker run --rm --network none -v "$PWD:/work" -w /work openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit tools/hbm_hidx_coupon1/sta_all.tcl >out/sta_all.log 2>&1
if grep -Eq '\[ERROR|^Error:' out/sta_all.log; then exit 1;fi
grep -q 'data arrival time' out/sta_all.log
sha256sum tools/hbm_hidx_coupon1/*.py tools/hbm_hidx_coupon1/*.sv tools/hbm_hidx_coupon1/*.sh tools/hbm_hidx_coupon1/*.tcl out/*.log out/*.json out/*.lib out/*.v >out/CSA_SHA256SUMS
