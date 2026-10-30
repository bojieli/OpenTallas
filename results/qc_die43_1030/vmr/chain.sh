#!/bin/bash
# DIE-QC-43: continue Codex vmrC1full chain after DRT 0 (finish_c.sh line-7 syntax bug fixed in a copy): finish -> signoff TT/FF -> post-route LEC
set -u
D=/srv/opentallas-scratch2/claude/codex-qc-kits-2249/vmrC1full; K=$D/kit; O=/srv/opentallas-scratch2/claude/die-qc-43/vmr
B=/work/run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m1/base
bash $O/finish_c43.sh "$K" FULL > $O/finish.log 2>&1; FR=$?
echo "finish rc=$FR $(date)" >> $O/status
M=/srv/opentallas-scratch2/claude/die-qc-37-vmr/main_sofix/tools/die_plan
SIGNOFF_DOCKER=docker python3 -I "$M/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --ff-vclk auto --out "$O/signoff" --image openroad/orfs:asap7lock > "$O/signoff.log" 2>&1; SO=$?
echo "signoff rc=$SO $(date)" >> $O/status
docker run --rm --name dieqc43-lec-$$ --memory=24g --cpus=8 -v "$K":/work -v "$O":/eco -v "$M":/m:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist $B/6_final.v --out /eco/lec" > "$O/lec.log" 2>&1; LR=$?
echo "lec rc=$LR $(date)" >> $O/status
