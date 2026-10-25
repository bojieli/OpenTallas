#!/bin/bash
# prep_route.sh KIT I_TT_GRT : bind the core clock contract for route (METHODOLOGY 9.7 / GEOM F1-F2):
# I_sdc = measured GRT pin-register mean minus the cqb-measured mean GRT-vs-RCX clock offset (28 ps); rebind to the
# routed RCX mean after route (STA-only) if the signed mean differs by more than tol.  Hooks: cqb_hold_grt.tcl at GRT.
set -eu
K=$1; IG=$2; I=$(python3 -c "print(round($IG-28.0,2))")
N=$(ls -d $K/run/results/asap7/*/base | head -1)
rm -f $N/5_1_grt.odb $N/5_1_grt.sdc
for f in $K/constraint.sdc $N/4_cts.sdc; do sed -i -E "s/set_clock_latency -source [0-9.]+ \[get_clocks (\{)?vclk(\})?\]/set_clock_latency -source $I [get_clocks vclk]/" $f; grep -n "latency" $f; done
python3 - "$K/sdc_lint.json" "$I" <<'P'
import json,sys; p,i=sys.argv[1],float(sys.argv[2]); d=json.load(open(p)); d["insertion_ps"]=i; json.dump(d,open(p,"w"),indent=1)
P
cp /srv/opentallas-scratch2/claude/qc-plan/s8bp/tools/{signoff.py,cqb_hold_grt.tcl,run_cqb_route.sh} $K/
sed -i 's#^export POST_GLOBAL_ROUTE_TCL = .*#export POST_GLOBAL_ROUTE_TCL = /work/cqb_hold_grt.tcl#' $K/config.mk
grep -n POST_GLOBAL $K/config.mk
cat > $K/CORE_LATENCY.json <<J
{"rule": "coord/METHODOLOGY.md 9.7", "lane": "QC-S8BP", "I_TT_GRT_ps": $IG, "grt_rcx_offset_ps": 28.0, "I_TT_sdc_ps": $I,
 "early_tap_ps": $(python3 -c "print(round($I-250,2))"), "status": "pre-route calibrated estimate; rebind to routed RCX pin-register mean (F1)", "additional_cycles": 0}
J
