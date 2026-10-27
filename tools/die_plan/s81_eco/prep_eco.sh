#!/bin/bash
# S81-ECO-1 prep: copy a routed legacy core kit, keep results up to 4_cts, rebind the GRT hold repair to the FF vclk frame
#   prep_eco.sh SRC_KIT OUT
set -euo pipefail
SRC=$1; OUT=$2; R=/srv/opentallas-scratch2/claude/s81-eco-1-1027; TL=$R/tool/tools/die_plan
test ! -e $OUT || { echo "exists $OUT"; exit 2; }
mkdir -p $OUT
rsync -a --exclude /signoff --exclude '/signoff*.log' --exclude '/run_*.log' --exclude '/sta_*' --exclude /views $SRC/ $OUT/
B=$(ls -d $OUT/run/results/asap7/*/base); L=$(ls -d $OUT/run/logs/asap7/*/base); RP=$(ls -d $OUT/run/reports/asap7/*/base 2>/dev/null || true)
# keep stages 1-4; drop GRT / route / finish products so make reruns them from 4_cts.odb
rm -f $B/5_* $B/6_* $B/route.guide $B/*.lef $B/*_bc.lib $B/*_tc.lib $L/5_* $L/6_* ; [ -n "$RP" ] && rm -f $RP/5_* $RP/6_* || true
rm -f $OUT/pin_audit.json $OUT/FAIL_* 2>/dev/null || true
for f in vclk_corner.tcl; do cp $TL/$f $OUT/; done
# GRT hooks: kit's own hook + FF vclk bind (pre) / back to TT (post)
printf '# S81-ECO-1: kit drv.tcl, then the FF vclk binding of main vclk_corner.tcl (OT_VCLK_CORNER=ff)\nsource /work/drv.tcl\nsource /work/vclk_corner.tcl\n' > $OUT/eco_grt_pre.tcl
cp $R/tool/physical/common_flow/hold_pad_hb4.tcl $OUT/
printf '# S81-ECO-1: HB4 hold pad (main hold_pad_hb4.tcl: HB4xp67 allowed only inside repair_timing -hold), kit post-GRT DRV + hold pass (now in the FF vclk frame), then vclk back to TT\nsource /work/hold_pad_hb4.tcl\nsource /work/post_grt_drv.tcl\nif {[info exists ::env(OT_VCLK_CORNER)] && $::env(OT_VCLK_CORNER) eq "ff"} { ot_vclk_bind tt }\n' > $OUT/eco_grt_post.tcl
cat >> $OUT/config.mk <<CFG
# S81-ECO-1 2026-10-27 (COORD RETIME-VIEWS-2 ruling): FF hold repair in the FF vclk frame (METHODOLOGY 12.3: TT 250 / FF 202.5)
export OT_VCLK_TT = 250.0000
export OT_VCLK_FF = 202.5000
override export PRE_GLOBAL_ROUTE_TCL = /work/eco_grt_pre.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/eco_grt_post.tcl
CFG
# sdc_lint context: declare the per-corner FF insertion (sdc_lint fails closed on OT_VCLK_FF without it)
python3 -I -c "import json,sys; p=sys.argv[1]; d=json.load(open(p)); d['insertion_ff_ps']=202.5; json.dump(d,open(p,'w'),indent=1)" $OUT/sdc_lint.json
# runner: FF-only GRT step in the FF vclk frame; sign-off at TT vclk 250 / FF bound 202.5 with main signoff (R19 tool)
python3 -I $TL/signoff.py bundle $OUT >/dev/null
sed -i 's/if \[ \\$rc = 0 \]; then \\$M grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=15;/if [ \\$rc = 0 ]; then OT_VCLK_CORNER=ff \\$M grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=15;/' $OUT/run_kit.sh
if ! grep -q 'OT_VCLK_CORNER=ff \\$M grt' $OUT/run_kit.sh; then
  # kits whose GRT ran inside 'make GOAL' in the kit tc+bc session: add core_flow.FF_GRT_STEP (cts in kit corners, then FF-only GRT)
  sed -i 's/^  if \[ \\$rc = 0 \]; then \\$M \$GOAL; rc=\\$?; fi; \\$/  if [ \\$rc = 0 ]; then \\$M cts; rc=\\$?; fi; if [ \\$rc = 0 ]; then OT_VCLK_CORNER=ff \\$M grt CORNER=BC CORNERS=bc; rc=\\$?; fi; \\\n  if [ \\$rc = 0 ]; then \\$M \$GOAL; rc=\\$?; fi; \\/' $OUT/run_kit.sh
fi
grep -q 'OT_VCLK_CORNER=ff \\$M grt' $OUT/run_kit.sh || { echo "runner patch failed"; exit 3; }
sed -i 's|--corners tt,ff \\|--corners tt,ff --ff-vclk bound-ff --ff-bound-ps 202.5 --ff-vclk-contract "METHODOLOGY 12.3 die FF core latency 202.5 (S81-ECO-1)" \\|' $OUT/run_kit.sh
grep -q 'ff-bound-ps 202.5' $OUT/run_kit.sh || { echo "signoff patch failed"; exit 3; }
sed -i 's/^NAME=\(.*\)$/NAME=s81eco1-$(basename "$K")-$$/' $OUT/run_kit.sh
printf '{"lane":"S81-ECO-1","source_kit":"%s:%s","tool":"claude/s81-core-lat-r19-1027@abcf698a79","change":"FF-only GRT hold repair rebound to vclk FF 202.5 (was TT 250); results kept up to 4_cts"}\n' "$(hostname)" "$SRC" > $OUT/ECO.json
echo "ready $OUT $(du -sh $OUT | cut -f1)"
