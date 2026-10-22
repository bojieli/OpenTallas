#!/bin/bash
# S81-PINREG4 10-19: compact199 pinreg prepabs recipe (spec bfh_compact199_col_pinreg_prepabs_1019, source 24cf7e2e3, RTL
# unchanged) with the T-OUT output hold budget (physical/s81_bf_hier/signoff_col_hb.sdc) as the route FF scene SDC and
# sign-off SDC, stopped after CTS.  Unlike gate2 (single WC repair scene, launch 173 at CTS, then 263-281 routed) this
# gate repairs in the loop's mm mode (OT_ROUTE_HOLD_CORNERS=mm: SS setup + FF hold, + .ot_mm/ff_ioref_last.sdc), the
# mode the closed route used, so the CTS output hold pad is the route's.  Then insertion, layout PNGs, native TT probe.
set -euo pipefail
G=$(pwd); SRC=$G/src; RUN=$G/gate_run; O=$G/gate_post
mkdir -p "$RUN" "$O"
cd "$SRC"
export CK_SS_MEAN=594 OT_ORFS_CORNER_OVERRIDE=TC OT_ROUTE_HOLD_CORNERS=mm
export OT_CTS_FIX_HOOKS=physical/s81_native_bf/margin/pinclk_group.tcl
export OT_MM_FF_SDC=physical/s81_bf_hier/signoff_col_hb.sdc
export SIGNOFF_SDC=physical/s81_bf_hier/signoff_col_hb.sdc PER=.730
OUT=$RUN/routes SRC=$SRC BLOCK=col bash physical/s81_bf_hier/route_hier.sh c199hb_gate --die-w 450.144 --die-h 198.72 --hm 0.030 --bxst 2 --fxst 2 --pinlat 1 --local-clock-pin --extra '--step-tcl POST_DETAIL_PLACE=physical/s81_bf_hier/pinflop_band.tcl --pnr-stop-after cts' || echo "ROUTE_RC=$?"
B=$(find "$RUN/routes/c199hb_gate/work/orfs/results/asap7" -name 4_1_cts.odb -printf '%h\n' | head -1)
test -n "$B"
L=$(find "$RUN/routes/c199hb_gate/work/orfs/logs/asap7" -name 4_1_cts.log | head -1)
grep -h "OT_HOLD_MM\|BF_IO\|RSZ-0046\|RSZ-0032\|OT_HOLD_GUARD\|BF_PINCLK post" "$L" > "$O/cts_hold.txt" || true
python3 tools/closure_loop/ck_insertion.py --base "$B" --clock core_clk --route-corner TC --raw-source --output "$O/ck.json" > "$O/ck.log" 2>&1 || echo "CK_RC=$?"
for odb in 3_5_place_dp 4_1_cts; do
 printf 'read_db /base/%s.odb\nsource /src/tools/ref_tile/layout_dump.tcl\nexit\n' "$odb" > "$O/layout_$odb.tcl"
 docker run --rm -e OT_LAYOUT_OUT=/o/layout_$odb.json -e OT_LAYOUT_CLOCKS=clk -e OT_LAYOUT_TOP=ot_v41_bf_col -v "$B:/base:ro" -v "$SRC:/src:ro" -v "$O:/o" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /o/layout_$odb.tcl > "$O/layout_$odb.log" 2>&1 || true
 python3 tools/ref_tile/layout_png.py "$O/layout_$odb.json" "$O/png_$odb" --title "compact199 T-OUT hold budget $odb" > "$O/png_$odb.log" 2>&1 || true
done
docker run --rm -v "$B:/base:ro" -v "$SRC:/src:ro" -v "$O:/o" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/results/rtl/s81_bf_compact_20261010/compact199_hb_1019/native_probe_hb.tcl > "$O/native_probe.log" 2>&1 || echo "PROBE_RC=$?"
echo GATE_DONE
