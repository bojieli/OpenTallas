#!/bin/bash
# DIE-QC-33 A0 reset-relay LEC (recipe of results/qc_a0_kits_13_1029/bhop/lec_main.sh = tools/die_plan/strap_lec.py yosys flow:
# proc; flatten; async2sync; opt -full; equiv_make; equiv_struct; equiv_simple; equiv_induct; equiv_status -assert).
# gold = 68204ac61dc a0c (before), gate = this branch a0c; pinned body = black box (-lib).  usage: lec_rrst.sh TILE OUT
#   off      : ICG 0 both, gate ICG_RRST default 0                          -> must be EQUIVALENT
#   icg2_rr0 : ICG 2 both, gate ICG_RRST 0 (default)                        -> must be EQUIVALENT (B-hop kits unchanged)
#   icg2_cut : ICG 2 both, gate ICG_RRST 1 with ot_rst_relay as a wire     -> must be EQUIVALENT (reset = only difference)
#   icg2_rr1 : ICG 2 both, gate ICG_RRST 1 real relay                      -> NOT equivalent (expected: release +2+1 edges)
#   mut      : like icg2_cut, gate body tile_id inverted                     -> must be NOT equivalent (negative control)
set -uo pipefail
TILE=$1; OUT=$(mkdir -p "$2" && realpath "$2")
Y=${YOSYS:-$HOME/.local/opentallas-tools/bin/yosys}
BODY=rtl/physical/a0_rc14_selected_2000/qfd_tile_${TILE}_rp2_45.sv
NEW=rtl/physical/a0_core/qfd_tile_${TILE}_a0c.sv
git show 68204ac61dc:$NEW | sed -e "s/module qfd_tile_${TILE}_a0c /module gold /" > "$OUT/gold.sv"
sed "s/module qfd_tile_${TILE}_a0c /module gate /" "$NEW" > "$OUT/gate.sv"
sed -e "s/module qfd_tile_${TILE}_a0c /module gate /" -e "s/\.tile_id(tile_id)/.tile_id(~tile_id)/" "$NEW" > "$OUT/gate_mut.sv"
cat > "$OUT/icg_model.v" <<'V'
module ICGx8DC_ASAP7_75t_R (input CLK, input ENA, input SE, output GCLK); assign GCLK = CLK & (ENA | SE); endmodule
V
cat > "$OUT/relay_cut.v" <<'V'
module ot_rst_relay #(parameter integer REGIONS = 4, parameter integer SYNC_STAGES = 2, parameter integer TREE_STAGES = 1)
  (input wire clk, input wire rst_n_in, output wire [REGIONS-1:0] rst_n); assign rst_n = {REGIONS{rst_n_in}}; endmodule
V
run() { # label gatefile relayfile chparams
  local L=$1 G=$2 R=$3 P=$4
  cat > "$OUT/$L.ys" <<YS
read_verilog -DSYNTHESIS -sv -lib $BODY
read_verilog -DSYNTHESIS -sv $OUT/icg_model.v
read_verilog -DSYNTHESIS -sv $R
read_verilog -DSYNTHESIS -sv rtl/physical/a0_core/ot_a0_icg_hop.sv
read_verilog -DSYNTHESIS -sv $OUT/gold.sv
read_verilog -DSYNTHESIS -sv $G
chparam -set REGROOT_MODE 9 gold gate
$P
hierarchy -check
setattr -mod -unset keep_hierarchy
proc
flatten gold gate
setundef -undriven -expose
async2sync
opt -full
opt_clean -purge
equiv_make gold gate lec_eq
hierarchy -top lec_eq
async2sync
equiv_struct
equiv_simple
equiv_induct
equiv_status -assert
YS
  "$Y" -q -l "$OUT/$L.log" -s "$OUT/$L.ys" > /dev/null 2>&1; local rc=$?
  local un=$(grep -o "[0-9]* unproven" "$OUT/$L.log" | tail -1)
  local eqc=$(grep -o "Found [0-9]* \$equiv cells" "$OUT/$L.log" | tail -1)
  echo "LEC $TILE $L rc=$rc ${eqc:-} ${un:-0 unproven} -> $([[ $rc == 0 ]] && echo EQUIVALENT || echo NOT_EQUIVALENT)"
}
REAL=rtl/lib/ot_rst_relay.sv
run off "$OUT/gate.sv" $REAL ""
run icg2_rr0 "$OUT/gate.sv" $REAL "chparam -set ICG 2 gold gate"
run icg2_cut "$OUT/gate.sv" "$OUT/relay_cut.v" "chparam -set ICG 2 gold gate
chparam -set ICG_RRST 1 gate"
run icg2_rr1 "$OUT/gate.sv" $REAL "chparam -set ICG 2 gold gate
chparam -set ICG_RRST 1 gate"
run mut "$OUT/gate_mut.sv" "$OUT/relay_cut.v" "chparam -set ICG 2 gold gate
chparam -set ICG_RRST 1 gate"
