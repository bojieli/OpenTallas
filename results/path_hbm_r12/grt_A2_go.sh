#!/bin/bash
# PATH-HBM-R12 read-only die GRT probe on planA2 (sha 1eb7ee48; all hard-core obs_max M5), 50 congestion iterations (no it5 edit); die_trial from claude/path-hbm-r12-1026 (=r11 2947bd5953)
B=/srv/opentallas-scratch2/claude/path-hbm-r12-1026/grt_A2; WT=/srv/opentallas-scratch2/claude/wt/path-hbm-r12-1026; R=~/.local/bin/ot-run
echo START $(date) $(git -C $WT rev-parse --short HEAD) $(sha256sum $B/plan/die_plan.json | cut -c1-12)
$R --mem 32 --threads 4 --dir $B --stage $WT --stage $B -- bash -c "cd $WT && python3 tools/die_plan/die_trial.py kit $B/plan/die_plan.json --out $B/kit" > $B/kit_build.log 2>&1 ; echo KIT rc=$? $(date)
grep -c "congestion_iterations 50 " $B/kit/grt/grt.tcl
$R --mem 32 --threads 16 --priority die --dir $B/kit --stage $B/kit -- env MEM=32 bash $B/kit/run_grt.sh > $B/grt.otrun.log 2>&1
echo GRT rc=$? $(date); grep -c "GRT-011[34]" $B/kit/grt/grt.log; grep "^Total" $B/kit/grt/grt.log | tail -n 1
