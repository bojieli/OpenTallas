#!/bin/bash
set -euo pipefail
cd ..
docker run --rm --network none -v "$PWD:/work" -w /work openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 yosys -Q -T -p 'read_liberty -lib out/all.lib; read_verilog out/netlist.v; hierarchy -top hidx_coupon1; write_json out/sta_names.json' >out/path_export.log 2>&1
python3 tools/hbm_hidx_coupon1/path_detail.py
sha256sum tools/hbm_hidx_coupon1/*.py tools/hbm_hidx_coupon1/*.sv tools/hbm_hidx_coupon1/*.sh tools/hbm_hidx_coupon1/*.tcl out/*.log out/*.json out/*.lib out/*.v out/image.txt out/*version.txt >out/SHA256SUMS
