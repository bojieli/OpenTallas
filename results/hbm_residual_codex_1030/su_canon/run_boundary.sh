#!/bin/bash
set -e
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
R=/srv/opentallas-scratch2/claude/codex-hbm-residual-1030/query
W=/srv/opentallas-scratch2/claude/wt/codex-hbm-residual-1030
cd "$R"
cat > su_boundary.ys <<EOF
read_verilog -sv -lib $W/rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg/ot_hbm_su_pg_lane_exp_core.sv $W/rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg/ot_hbm_su_pg_lanes4_core.sv
read_verilog -sv ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691.sv ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77.sv ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526.sv ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691__native.sv ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77__native.sv ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526__native.sv ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691__mutant.sv ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77__mutant.sv ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526__mutant.sv
proc
opt_clean
write_json su_boundary.json
EOF
yosys -Q -T -s su_boundary.ys > su_boundary_yosys.log
python3 boundary_wiring_proof.py su_boundary.json su_native_ids.json su_boundary_proof.json | tee su_boundary_proof.log
