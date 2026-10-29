#!/bin/bash
# QC-PG-5 ICG body re-pin LEC: main vs branch for the 4 threaded body modules at once (top qfd_tile_<t>_rp2_45, flattened
# through ot_qwen_rom_tile_nk -> ot_qwen_rom_tile_w12 -> ot_qwen_rom_tile_logic_w12; the matvec engine, arith, macros,
# leaf/node hard children are black boxes read -lib from the same files on both sides).  The new output me_idle exists
# only on the gate side and is not compared; every existing output must be EQUIVALENT.
#   usage: lec_body.sh TILE OUTDIR [MUT]   (repo root; MUT=1 inverts tile_id into u_tile on the gate side -> must FAIL)
set -uo pipefail
TILE=$1; OUT=$(mkdir -p "$2" && realpath "$2"); MUT=${3:-0}
Y=${YOSYS:-$HOME/.local/opentallas-tools/bin/yosys}
REF=${REF:-origin/main}
CHG=(rtl/physical/a0_rc14_selected_2000/qfd_tile_${TILE}_rp2_45.sv rtl/physical/ot_qwen_rom_tile_nk.sv
     rtl/physical/a0_rc15_selected_2000/ot_qwen_rom_tile_w12_land32.sv)
eval "$(grep "^SRCS=" physical/ref_tile/qfd_tile_${TILE}_a0cv6/kit.env)"
LIB=()
for f in $SRCS; do skip=0; for c in "${CHG[@]}" rtl/physical/a0_core/qfd_tile_${TILE}_a0c.sv; do [[ $f == $c ]] && skip=1; done; [[ $skip == 0 ]] && LIB+=("$f"); done
mkdir -p "$OUT/gold" "$OUT/gate"
for c in "${CHG[@]}"; do b=$(basename "$c"); git show "$REF:$c" > "$OUT/gold/$b"; cp "$c" "$OUT/gate/$b"; done
L=lec_body_$TILE$([[ $MUT != 0 ]] && echo _mut)
if [[ $MUT != 0 ]]; then sed -i "s/\.tile_id(tile_id_q)/.tile_id(~tile_id_q)/" "$OUT/gate/qfd_tile_${TILE}_rp2_45.sv"; fi
side() { # dir name
  local libs; libs=$(for f in "${LIB[@]}"; do echo "read_verilog -DSYNTHESIS -sv -lib $f"; done)
  cat <<YS
design -reset
$libs
read_verilog -DSYNTHESIS -sv $OUT/$1/ot_qwen_rom_tile_w12_land32.sv
read_verilog -DSYNTHESIS -sv $OUT/$1/ot_qwen_rom_tile_nk.sv
read_verilog -DSYNTHESIS -sv $OUT/$1/qfd_tile_${TILE}_rp2_45.sv
chparam -set REGROOT 9 -set RPH 3 qfd_tile_${TILE}_rp2_45
hierarchy -top qfd_tile_${TILE}_rp2_45
proc
flatten
rename qfd_tile_${TILE}_rp2_45 $1
design -stash $1
YS
}
{ side gold; side gate
  cat <<YS
design -reset
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
delete -port gate/w:me_idle
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
} > "$OUT/$L.ys"
/usr/bin/time -v "$Y" -q -l "$OUT/$L.log" -s "$OUT/$L.ys" > "$OUT/$L.stdout" 2>&1; rc=$?
un=$(grep -o "Found [0-9]* unproven" "$OUT/$L.log" | tail -1); eqc=$(grep -o "Found [0-9]* \$equiv cells" "$OUT/$L.log" | tail -1)
echo "LEC_BODY $TILE mut=$MUT rc=$rc ${eqc:-} ${un:-0 unproven} -> $([[ $rc == 0 ]] && echo EQUIVALENT || echo NOT_EQUIVALENT)"
