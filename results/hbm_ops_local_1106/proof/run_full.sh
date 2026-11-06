#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
RTL=../../../physical/die_plan/hbm/over_cap_split/reform_1106/ops_local/rtl
D=$(mktemp -d)
trap 'rm -rf "$D"' EXIT
sed 's/\.MACRO(1)/.MACRO(0)/g' opsa_baseline.sv > "$D/old.sv"
sed 's/\.MACRO(1)/.MACRO(0)/g' "$RTL/ot_hgi_sfu_opsa_dist_1106.sv" > "$D/new.sv"
iverilog -g2012 -s tb_full -o "$D/proof.vvp" lbank.sv lgroup2_lf_captured.sv "$RTL/ot_hgi_su_lgroup2_local_1106.sv" "$D/old.sv" "$D/new.sv" tb_full.sv
vvp "$D/proof.vvp"
