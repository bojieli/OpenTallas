#!/bin/bash
set -euo pipefail
cd ..
docker run --rm --network none -v "$PWD:/work" -w /work openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 yosys -Q -T -p 'read_liberty -ignore_miss_func -ignore_miss_dir out/all.lib; read_verilog out/netlist.v; rename hidx_coupon1 mapped; read_verilog -sv tools/hbm_hidx_coupon1/coupon.sv; rename hidx_coupon1 reference; read_verilog -sv tools/hbm_hidx_coupon1/formal_mapped.sv; hierarchy -check -top formal_mapped; setattr -mod -unset keep_hierarchy; prep -top formal_mapped -flatten; sat -seq 3 -prove-skip 2 -prove bad 0 -verify -show-ports' >out/formal_mapped.log 2>&1
