#!/bin/bash
set -euo pipefail
G=$(pwd); SRC=$G/src; RUN=$G/gate_run; O=$G/gate_post
mkdir -p "$RUN" "$O"
cd "$SRC"
export CK_SS_MEAN=594 OT_ORFS_CORNER_OVERRIDE=TC
export OT_CTS_FIX_HOOKS=physical/s81_native_bf/margin/pinclk_group.tcl
export OT_MM_FF_SDC=physical/s81_bf_hier/signoff_col.sdc
export SIGNOFF_SDC=physical/s81_bf_hier/signoff_col.sdc PER=.730
OUT=$RUN/routes SRC=$SRC BLOCK=col bash physical/s81_bf_hier/route_hier.sh compact199_pinreg_gate --die-w 450.144 --die-h 198.72 --hm 0.030 --bxst 2 --fxst 2 --pinlat 1 --local-clock-pin --extra '--step-tcl POST_DETAIL_PLACE=physical/s81_bf_hier/pinflop_band.tcl --pnr-stop-after cts'
B=$(find "$RUN/routes/compact199_pinreg_gate/work/orfs/results/asap7" -name 4_1_cts.odb -printf '%h\n' | head -1)
test -n "$B"
python3 tools/closure_loop/ck_insertion.py --base "$B" --clock core_clk --route-corner TC --raw-source --output "$O/ck.json" > "$O/ck.log" 2>&1
for odb in 3_5_place_dp 4_1_cts; do
 printf 'read_db /base/%s.odb\nsource /src/tools/ref_tile/layout_dump.tcl\nexit\n' "$odb" > "$O/layout_$odb.tcl"
 docker run --rm -e OT_LAYOUT_OUT=/o/layout_$odb.json -e OT_LAYOUT_CLOCKS=clk -e OT_LAYOUT_TOP=ot_v41_bf_col -v "$B:/base:ro" -v "$SRC:/src:ro" -v "$O:/o" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /o/layout_$odb.tcl > "$O/layout_$odb.log" 2>&1
 python3 tools/ref_tile/layout_png.py "$O/layout_$odb.json" "$O/png_$odb" --title "compact199 pin registers $odb"
done
