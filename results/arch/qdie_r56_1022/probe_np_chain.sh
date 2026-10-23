#!/bin/bash
# QDIE-R56 (copy of SQC-QDIE5 probe_np_chain.sh): wait for TAG's placed real case (chain/case_r22k/floorplan.odb), then the
# read-only NO-PDN M9 signal-only GRT probe (congestion_iterations 0, recipe bs) via ot-run; per-layer summary to lane.
T=$1; H=ot-gold1; R=/srv/opentallas-scratch/claude/codex-qdie-2000/$T; L=/home/ubuntu/claude-takeover-20261007/lanes
D=/home/ubuntu/scratch/sqc-qdie3/grtprobe; M=/home/ubuntu/scratch/qdie-r56
scp -q -o ControlPath=none $D/grt_probe_np.sh $D/grt_probe_summ.py $M/padband.py $H:/tmp/ || exit 1
until ssh -n -o ControlPath=none $H "grep -q 'real case:' $R/chain/STATUS.log && [ -s $R/chain/case_r22k/floorplan.odb ]" 2>/dev/null; do
  if ssh -n -o ControlPath=none $H "grep -q 'chain rc=\|REAL CASE FAIL' $R/chain.log $R/chain/STATUS.log" 2>/dev/null; then
    echo "[QDIE-R56 $(date +%H:%M)] $T chain ended before a placed case (no probe): $(ssh -n -o ControlPath=none $H "tail -2 $R/PILOT.log" | tr '\n' ' ' | cut -c1-300)" >> $L/STEWARD-QK.md; exit 0; fi
  ssh -n -o ControlPath=none $H "grep -q 'follow: GEN failed\|strict bind not PASS\|diag follow: bind FAIL\|phase2 FAIL\|reset projection rc=[1-9]' $R/PILOT.log" 2>/dev/null && {
    echo "[QDIE-R56 $(date +%H:%M)] $T follow stopped before placement: $(ssh -n -o ControlPath=none $H "tail -2 $R/PILOT.log" | tr '\n' ' ' | cut -c1-300)" >> $L/STEWARD-QK.md; exit 0; }
  sleep 300; done
RC=bs; O=$R-grtprobe-nopdn-$RC
python3 /home/ubuntu/bin/ot-run --mem 90 --threads 16 --disk 5 --priority die --dir $R -- env PROBE_MEM=120 bash /tmp/grt_probe_np.sh $R/chain/case_r22k/floorplan.odb $O $RC > $M/probe_np_${T}_$RC.out 2>&1 < /dev/null
S=$(ssh -n -o ControlPath=none $H "cat $O/summary.txt; python3 /tmp/padband.py $O $R/out/case" 2>/dev/null | head -20)
echo "[QDIE-R56 $(date +%H:%M)] NO-PDN M9 GRT PROBE $T signal-only (bs, congestion_iterations 0, case floorplan.odb pre-PDN): $(grep -h -A12 '^M4 ' $M/probe_np_${T}_$RC.out 2>/dev/null | head -0) $(echo "$S" | tr '\n' ' ' | cut -c1-1600) ($H:$O)" >> $L/STEWARD-QK.md
