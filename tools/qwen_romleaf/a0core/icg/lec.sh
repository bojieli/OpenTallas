#!/bin/bash
# DIE-QC-16 A0 ICG wrapper LEC (yosys, recipe of tools/die_plan/strap_lec.py: proc; flatten; async2sync; opt -full;
# equiv_make; equiv_struct; equiv_simple; equiv_induct; equiv_status -assert).  The pinned body qfd_tile_<t>_rp2_45 is the
# same file on both sides -> read as a black box (-lib, pins compared).  usage: lec.sh TILE MAIN_A0C.sv OUTDIR (repo root)
#   off   : main a0c  vs branch a0c (ICG default 0)                        -> must be EQUIVALENT
#   on    : main a0c  vs branch a0c ICG=1, SYNTHESIS form, ICGx8DC = its function with ENA held (GCLK = CLK & (ENA|SE))
#                                                                          -> NOT equivalent by design since QC-PG-5: me_idle is
#            the real body port, so the synthesised gate really closes; ON-vs-OFF is the valid-qualified bench (12:4x ruling)
#   mut   : main a0c  vs branch a0c ICG=0 with u_g .tile_id(~tile_id)       -> must NOT be equivalent
set -uo pipefail
TILE=$1; MAIN=$(realpath "$2"); OUT=$(mkdir -p "$3" && realpath "$3")
Y=${YOSYS:-$HOME/.local/opentallas-tools/bin/yosys}
BODY=rtl/physical/a0_rc14_selected_2000/qfd_tile_${TILE}_rp2_45.sv
NEW=rtl/physical/a0_core/qfd_tile_${TILE}_a0c.sv
sed -e "s/module qfd_tile_${TILE}_a0c /module gold /" -e "s/^\(        \.ck(ck),\)$/\1 .me_idle(me_idle_nc),/" "$MAIN" > "$OUT/gold.sv"
# QC-PG-5: the black-box body (branch) has the new output me_idle; gold connects it to a dangling wire so the two u_g cells
# have the same port set (equiv_struct matches cells by connection); the dangling output adds no function.
grep -q "me_idle(me_idle_nc)" "$OUT/gold.sv" || { echo "LEC $TILE gold me_idle hook not applied"; exit 2; }
sed "s/module qfd_tile_${TILE}_a0c /module gate /" "$NEW" > "$OUT/gate.sv"
sed -e "s/module qfd_tile_${TILE}_a0c /module gate /" -e "s/\.tile_id(tile_id)/.tile_id(~tile_id)/" "$NEW" > "$OUT/gate_mut.sv"
cat > "$OUT/icg_model.v" <<'V'
module ICGx8DC_ASAP7_75t_R (input CLK, input ENA, input SE, output GCLK); assign GCLK = CLK & (ENA | SE); endmodule
V
run() { # label gatefile chparam
  local L=$1 G=$2 P=$3
  cat > "$OUT/$L.ys" <<YS
read_verilog -DSYNTHESIS -sv -lib $BODY
read_verilog -DSYNTHESIS -sv $OUT/icg_model.v
read_verilog -DSYNTHESIS -sv $OUT/gold.sv
read_verilog -DSYNTHESIS -sv $G
chparam -set REGROOT_MODE 9 gold gate
$P
hierarchy -check
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
  local un=$(grep -o "Found [0-9]* unproven" "$OUT/$L.log" | tail -1)
  local eqc=$(grep -o "Found [0-9]* \$equiv cells" "$OUT/$L.log" | tail -1)
  echo "LEC $TILE $L rc=$rc ${eqc:-} ${un:-0 unproven} -> $([[ $rc == 0 ]] && echo EQUIVALENT || echo NOT_EQUIVALENT)"
}
run off "$OUT/gate.sv" ""
run on "$OUT/gate.sv" "chparam -set ICG 1 gate"
run mut "$OUT/gate_mut.sv" ""
