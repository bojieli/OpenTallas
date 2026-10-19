#!/usr/bin/env bash
# HBM-KITS-C/VMGLUE 2026-10-18 (g2): VM hub-glue TILE master (hfd_hgi_vms_glue_{sw,e,nw}_t) == its contract reference
# <tile>_ref (historical glue ot_vms_slice_static_glue, COMMIT_DELAY 8, one delay stage per bank-side port, tile reset
# release) in lockstep: random inputs on every port, periodic resets, every output bit compared (vms_glue_tile_equiv.py).
# pos must print "VMS_GLUE_LT_EQUIV <Q> PASS checks=N errors=0"; mutants (rmut: ring-stop flit bit; land: eg not landed;
# sid: E strap = the other E quadrant's sid; g3: hub pq without the g3 face-group edge; g4: pi / rce without the g4 relays) must print "VMS_GLUE_LT_EQUIV <Q> FAIL checks=N errors=M>0".
# Exit status 0 only on a counted PASS.
#   run_vms_glue_tile_equiv.sh Q pos|rmut|land|sid|g3|g4 OUT
set -uo pipefail
q=${1:?quadrant}; m=${2:?pos|rmut|land|sid|g3|g4}; OUT=$(realpath -m "${3:?out}"); mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/hbm_accel/generic/vm/static
src=($S/hfd_hgi_vms_glue_tiles.sv $S/hfd_hgi_vms_glue_tiles_ref.sv $S/hfd_hgi_vms_glue_lt.sv $S/hfd_hgi_vms_static_glue.sv
     $S/ot_vms_hub_static.sv $S/ot_vms_rstop_static.sv $S/ot_vms_rcl_static.sv $S/ot_vms_status_static.sv rtl/lib/ot_rst_relay.sv)
TAG=VMS_GLUE_LT_EQUIV
X=; [ "$m" != pos ] && X="--mut $m"
D="$OUT/$q$m"
"$V" --version
python3 tools/hbm_die_v16/vms_glue_tile_equiv.py --quadrant $q --out "$D" $X > "$D.gen.log" 2>&1 || { cat "$D.gen.log"; echo "$TAG $q GENFAIL"; exit 1; }
cat "$D.gen.log"
"$V" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module tb_vms_glue_lt -Mdir "$D/obj" \
  "${src[@]}" "$D/tb_vms_glue_lt.sv" > "$D.build.log" 2>&1 || { grep -m5 %Error "$D.build.log"; echo "$TAG $q BUILDFAIL"; exit 1; }
"$D/obj/Vtb_vms_glue_lt" > "$D.sim.log" 2>&1
rm -rf "$D/obj"
grep -E "$TAG|MISMATCH" "$D.sim.log" | tail -6
grep -Eq "^$TAG $q PASS checks=[1-9][0-9]* errors=0$" "$D.sim.log"   # exit 0 only on a counted PASS (mutants: non-zero)
