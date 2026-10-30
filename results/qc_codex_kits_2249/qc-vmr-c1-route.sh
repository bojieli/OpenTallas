#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-qc-kits-2249/vmrC1;K=$D/kit
B=/work/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m1/base
docker run --rm --memory=24g --cpus=8 -v "$K":/work -v "$D":/eco -w /OpenROAD-flow-scripts/flow -e OT_F4G_LOCK=fixed openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 PRE_DETAIL_ROUTE_TCL=/eco/pre.tcl POST_DETAIL_ROUTE_TCL=/work/f4g_post_drt.tcl do-5_2_route' > "$D/route.log" 2>&1
# The original C1 chain's finish / signoff / LEC recipes target this own kit.
bash /srv/opentallas-scratch2/claude/die-qc-42-vmrC/finish_c.sh "$K" STUB > "$D/finish.log" 2>&1
M=/srv/opentallas-scratch2/claude/die-qc-37-vmr/main_sofix/tools/die_plan
set +e
SIGNOFF_DOCKER=docker python3 -I "$M/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --ff-vclk auto --out "$D/signoff" --image openroad/orfs:asap7lock > "$D/signoff.log" 2>&1;SO=$?
docker run --rm --memory=24g --cpus=8 -v "$K":/work -v "$D":/eco -v "$M":/m:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist $B/6_final.v --out /eco/lec" > "$D/lec.log" 2>&1;LR=$?
echo "DONE signoff=$SO lec=$LR"
exit "$SO"
