#!/bin/bash
# DIE-QC-44 VMR C1full M6-stub fix variant: same C1 DRC0 DB + Codex pre.tcl (signals stripped, re-GRT, full DRT, clocks kept)
# with a rebuilt M6 strip (m6_strip_q44.py: via enclosures bloated by SIDE both axes, SIDE<128). Then finish -> signoff -> LEC -> readback.
set -u
V=$1; R=/srv/opentallas-scratch2/claude/die-qc-44; D=$R/vmr$V; K=$D/kit
B=/work/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m1/base
cp $R/pre.tcl $D/pre.tcl
docker run --rm --name dieqc44-vmr$V-$$ --memory=24g --cpus=8 -v "$K":/work -v "$D":/eco -w /OpenROAD-flow-scripts/flow -e OT_F4G_LOCK=none -e OT_M6_STRIP=/work/m6_strip_q44.txt openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 PRE_DETAIL_ROUTE_TCL=/eco/pre.tcl POST_DETAIL_ROUTE_TCL=/work/f4g_post_drt.tcl do-5_2_route" > "$D/route.log" 2>&1
echo "route rc=$? $(date)" >> $D/status
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
docker run --rm --memory=16g -v /srv/opentallas-scratch2/claude:/s -e SRC=/s/codex-qc-kits-2249/vmrC1/C1_DRC0_layerfail.odb -e ODB=/s/die-qc-44/vmr$V/kit/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m1/base/5_2_route.odb -e OUT=/s/die-qc-44/vmr$V/readback.json openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /s/die-qc-44/vmr_readback.py" > $D/readback.log 2>&1
echo "readback rc=$? $(grep -o "\"data_above_M5\": [0-9]*" $D/readback.json) $(date)" >> $D/status
bash $R/finish_q44.sh "$K" FULL > $D/finish.log 2>&1; echo "finish rc=$? $(date)" >> $D/status
M=/srv/opentallas-scratch2/claude/die-qc-37-vmr/main_sofix/tools/die_plan
SIGNOFF_DOCKER=docker python3 -I "$M/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --ff-vclk auto --out "$D/signoff" --image openroad/orfs:asap7lock > "$D/signoff.log" 2>&1; echo "signoff rc=$? $(date)" >> $D/status
docker run --rm --name dieqc44-lec$V-$$ --memory=24g --cpus=8 -v "$K":/work -v "$D":/eco -v "$M":/m:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist $B/6_final.v --out /eco/lec" > "$D/lec.log" 2>&1; echo "lec rc=$? $(date)" >> $D/status
