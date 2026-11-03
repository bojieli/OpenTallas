#!/usr/bin/env bash
# DIE-HBM-61/SPLIT hcol_h0 lock-step: uncut kit core (ot_hbm_idx_score_hcol_h0, kit face shell) vs split composition
# (ra__fs + rb__fs).  run.sh KITRTL OUT   (fleet host; verilator 5).  MUT 0 must PASS, MUT 1 / 2 must FAIL.
set -u
KR=$1; O=$2; H=$(cd "$(dirname "$0")" && pwd); R=$H/../..; RT=$H/../../../../../../../rtl/hbm_accel/cores_split/reform_1103/ot_hbm_idx_score_hcol_h0
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p "$O"
LEAF=$(ls $KR/*.sv)
for s in ra rb; do python3 "$R/facewrap.py" --top ot_hbm_idx_score_hcol_h0_$s --out "$O/${s}__fs.sv" --pass-param MUT \
   $RT/ot_hbm_idx_score_hcol_h0_rgn.sv $KR/ot_rst_relay.sv $KR/ot_hdc_*.sv $KR/ot_hbm_face_reg.sv > "$O/${s}_ports.json" || exit 1; done
python3 "$R/lockstep_gen.py" "$H/spec.json" "$O/tb.sv"
for M in 0 1 2; do
  sed "s/ot_hbm_idx_score_hcol_h0__split u_dut/ot_hbm_idx_score_hcol_h0__split #(.MUT($M)) u_dut/" "$O/tb.sv" > "$O/tb_m$M.sv"
  rm -rf "$O/obj_m$M"; $V --binary -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb -Mdir "$O/obj_m$M" -o sim \
    "$O/tb_m$M.sv" $LEAF $RT/*.sv "$O/ra__fs.sv" "$O/rb__fs.sv" > "$O/build_m$M.log" 2>&1 || { tail -20 "$O/build_m$M.log"; exit 2; }
  "$O/obj_m$M/sim" > "$O/sim_m$M.log" 2>&1; echo "MUT $M: $(grep LOCKSTEP "$O/sim_m$M.log")"
done
sha256sum $LEAF $RT/*.sv > "$O/sources.sha256"
