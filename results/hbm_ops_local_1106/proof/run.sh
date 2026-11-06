#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
RTL=../../../physical/die_plan/hbm/over_cap_split/reform_1106/ops_local/rtl
iverilog -g2012 -s tb -o /tmp/ops_local_proof_$$.vvp lbank.sv lgroup2_lf_captured.sv "$RTL/ot_hgi_su_lgroup2_local_1106.sv" tb_ops_local.sv
vvp /tmp/ops_local_proof_$$.vvp
rm /tmp/ops_local_proof_$$.vvp
