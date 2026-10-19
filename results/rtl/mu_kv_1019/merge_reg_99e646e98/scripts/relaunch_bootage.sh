#!/bin/bash
set -u
D=/srv/opentallas-scratch/claude/refill-1330/MUKVREG; S=$D/src; O=$D/out
L=/home/ubuntu/scratch/refill-1330/MUKVREG/legs
VL='$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
PFX="export PATH=\$HOME/.local/opentallas-tools/verilator-5.050/bin:\$PATH VERILATOR=$VL OT_VERILATOR=$VL; cd $S &&"
n=bootage; cmd="rm -rf $O/bootage; mkdir -p $O/bootage/runs; xargs -P 8 -L 1 bash -c 'e=\$0; out=\$(bash tools/qwen_kv_die/kv_bootage_bench.sh $O/bootage/runs \"\$@\" 2>&1); rc=\$?; v=\$(echo \"\$out\" | grep -E \"^KVBA_|MISMATCH|ERROR|PHASE_C|%Error\" | tail -1); echo \"[\$e] \$* :: rc=\$rc :: \$v\"' < $D/bootage_cases.txt | sort > $O/bootage/summary.txt; cat $O/bootage/summary.txt"
( echo "# leg $n r2 $(date -Is)"; /home/ubuntu/bin/ot-run --mem 32 --threads 16 --dir $S --disk 10 -- bash -lc "$PFX { $cmd; } > $O/$n.out 2>&1; rc=\$?; echo \"# exit \$rc\" >> $O/$n.out; exit \$rc"; echo "# ot-run rc=$? $(date -Is)" ) > $L/$n.log 2>&1
