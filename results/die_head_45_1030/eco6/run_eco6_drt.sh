#!/bin/bash
# DIE-HEAD-45 2026-10-30: LEP ECO6 route chain (copy of DIE-HEAD-44 ECO5 chain) (= DIE-HEAD-42 run_eco4_drt.sh form) for one variant on its ECO5 GRT DB:
# DRT (FLOW-9 eco_drt_pre.tcl + clock lock) -> clock diff -> fill/finish -> pin audit -> main resign.py at the current
# HEAD flow tag (tag signoff.py + lec.py on the same routed DB; PROVENANCE only if SIGNED + EQUIVALENT).
set -u
VAR=$1
D=/srv/opentallas-scratch2/claude/die-head-44
K0=/srv/opentallas-scratch2/claude/die-head-42/lep_eco4_kit
R=/srv/opentallas-scratch2/claude/codex-head-collect-1030
E=/srv/opentallas-scratch2/claude/die-head-45/eco6/eco6
K=/srv/opentallas-scratch2/claude/die-head-45/lep_eco6_kit
TAG=flow-20261030-e-head
T=/srv/opentallas-scratch2/claude/die-head-44/tools_$TAG
N=hbc_ot_s81hd_lep_pair
test "$(cat $E/rc)" = 0 || { echo "ECO6 rc != 0"; exit 2; }
test ! -e $K || { echo "$K exists (never relaunch into a run dir)"; exit 2; }
mkdir -p $K
rsync -a --exclude /run --exclude /firstdrt --exclude '/resign_*' --exclude '/signoff_*' --exclude /lec_routed --exclude /pre_infra_4_cts.odb --exclude /placed.csv --exclude /__pycache__ $K0/ $K/
B0=$K0/run/results/asap7/$N/base; B=$K/run/results/asap7/$N/base
mkdir -p $B $K/run/logs/asap7/$N/base $K/run/reports/asap7/$N/base $K/firstdrt/postroute_lock
rsync -a $K0/run/objects/ $K/run/objects/
for f in 1_2_yosys.v 1_2_yosys.sdc 1_synth.v 1_synth.sdc 4_cts.sdc clock_period.txt mem.json ot_face_flops.txt ot_unreg_pins.txt 5_1_grt.sdc; do cp $B0/$f $B/; done
cp $E/5_1_grt.odb $B/
for f in 4_1_cts.json 4_1_cts.log 5_1_grt.json 5_1_grt.log; do cp $K0/run/logs/asap7/$N/base/$f $K/run/logs/asap7/$N/base/; done
cat > $K/firstdrt_pre.tcl <<'TCL'
source /work/eco_drt_pre.tcl
source /work/clk_freeze.tcl
ot_clk_freeze /work/firstdrt
TCL
cat > $K/firstdrt_post.tcl <<'TCL'
ot_clk_dump /work/firstdrt/clk_after_drt.tsv after_first_drt
ot_clk_freeze /work/firstdrt/postroute_lock
ot_clk_dump /work/firstdrt/clk_after_fixed.tsv first_routed_clock_fixed
TCL
echo "kit staged $(date)" > $K/firstdrt/status
DK=docker; $DK ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name dh45-lep-eco6-drt-$$ --cpus=8 --memory=40g --memory-swap=40g -v "$K":/work -v "$R/clock_recipe.py":/clock_recipe.py:ro -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc 'set +e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
ACTION=verify INPUT_ODB=/work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/5_1_grt.odb RECIPE=/work/clock_infra_recipe.json REPORT=/work/firstdrt/verify_before_drt.json openroad -python -exit /clock_recipe.py > /work/firstdrt/verify_before_drt.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_2_route PRE_DETAIL_ROUTE_TCL=/work/firstdrt_pre.tcl POST_DETAIL_ROUTE_TCL=/work/firstdrt_post.tcl > /work/firstdrt/run_drt.log 2>&1
rc=$?;echo $rc > /work/firstdrt/drt.rc
if test $rc = 0;then
 python3 -I /work/clk_geom_diff.py /work/firstdrt/clk_freeze_pre.tsv /work/firstdrt/clk_after_fixed.tsv --pre-unrouted --json /work/firstdrt/clock_diff.json > /work/firstdrt/clock_diff.log 2>&1
 rc=$?
fi
if test $rc = 0;then
 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_3_fillcell do-5_route do-5_route.sdc do-finish > /work/firstdrt/run_finish.log 2>&1
 rc=$?;echo $rc > /work/firstdrt/finish.rc
fi
if test $rc = 0;then
 ODB=/work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/6_final.odb PINS=/work/pins.json OUT=/work/firstdrt/pin_audit.json openroad -python -exit /work/pin_audit_core.py > /work/firstdrt/pin_audit.log 2>&1
 rc=$?
fi
chown -R $HUID:$HGID /work
exit $rc'
rc=$?
echo "route chain rc=$rc $(date)" >> $K/firstdrt/status
test $rc = 0 || exit $rc
SIGNOFF_DOCKER=$DK python3 -I $D/resign.py run --kit $K --tag $TAG --tools $T/tools/die_plan --out $K/resign_$TAG --repo /home/ubuntu/OpenTallas --lane DIE-HEAD-45 --name dh45-eco6 --note "LEP ECO6 = LEP ECO5 f (ECO4 GRT DB + 11 macro clock leaves -> BUFx3, CLOCK-RESIDUAL; DRV margin 20 + hold margin 10) + 2 BUFx4f data buffers on gpay[101]/gpay[86] (OAI21x1 -> 121-um face-flop leg; ECO5 f re-sign TT slew 1 = beat_tx[157] 328.96)" > $K/firstdrt/resign.log 2>&1
rc=$?
echo "resign rc=$rc $(date)" >> $K/firstdrt/status
exit $rc
