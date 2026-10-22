#!/bin/bash
# KV-HEALTH 10-19 tile benches (fleet, Verilator 5.050): run_health_tile_bench.sh OUT {h273|h273b|or2} MUT
set -euo pipefail
O=${1:?out}; T=${2:?h273|or2}; M=${3:-0}
mkdir -p "$O"; verilator --version
case $T in
  h273) TOP=tb_qkd_rst_region_pr_h273
        SRC="rtl/qwen_sys/split_20261014/qkd_rst_region.sv rtl/qwen_sys/split_20261014/qkd_rst_region_pr.sv rtl/qwen_sys/split_20261014/qkd_rst_region_pr_h273.sv rtl/test/qwen_split/tb_qkd_rst_region_pr_h273.sv";;
  h273b) TOP=tb_qkd_rst_region_pr_h273b
        SRC="rtl/qwen_sys/split_20261014/qkd_rst_region.sv rtl/qwen_sys/split_20261014/qkd_rst_region_po.sv rtl/qwen_sys/split_20261014/qkd_rst_region_pr.sv rtl/qwen_sys/split_20261014/qkd_rst_region_pr_h273.sv rtl/qwen_sys/split_20261014/qkd_rst_region_pr_h273b.sv rtl/test/qwen_split/tb_qkd_rst_region_pr_h273b.sv";;
  or2)  TOP=tb_qkd_hp_or2
        SRC="rtl/qwen_sys/kv_health_20261019/qkd_hp_or2.sv rtl/test/qwen_split/tb_qkd_hp_or2.sv";;
  *) echo "unknown $T"; exit 2;;
esac
verilator --binary -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-initial unique --x-assign unique \
  --top-module $TOP -GMUT=$M -Mdir "$O/obj" $SRC > "$O/build.log" 2>&1 || { tail -20 "$O/build.log"; exit 3; }
"$O/obj/V$TOP" +verilator+rand+reset+2
