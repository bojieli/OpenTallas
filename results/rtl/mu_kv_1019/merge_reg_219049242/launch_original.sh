#!/bin/bash
# REFILL-0725/MUKVREG2: KV-die MU bench + mutant regression on claude/mu-die-kv2-1019 @219049242 (adds KV-PVFST + MU-KV-HCTL2
# cm5 + MU-KV-PEER + MU-KV-BOOT over the 99e646e98 run of REFILL-1330/MUKVREG). Verilator 5.050. Unpinned ot-run (src on epyc4+epyc8).
set -u
D=/srv/opentallas-scratch/claude/refill-0725/MUKVREG2; S=$D/src; O=$D/out
L=/home/ubuntu/scratch/refill-0725/MUKVREG2/legs; mkdir -p $L
VL='$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
PFX="export PATH=\$HOME/.local/opentallas-tools/verilator-5.050/bin:\$PATH VERILATOR=$VL OT_VERILATOR=$VL; cd $S &&"
leg() { local n=$1 m=$2 t=$3; shift 3
  ( echo "# leg $n mem $m threads $t $(date -Is)"; echo "# cmd: $*"
    /home/ubuntu/bin/ot-run --mem $m --threads $t --dir $S --disk 10 -- bash -lc "$PFX mkdir -p $O/$n && { $*; } > $O/$n.out 2>&1; rc=\$?; echo \"# exit \$rc\" >> $O/$n.out; exit \$rc"
    echo "# ot-run rc=$? $(date -Is)" ) > $L/$n.log 2>&1 &
  sleep 2; }
leg host 48 16 "bash rtl/test/mu_qwen_1018/run_all.sh $S $D/head $O/host/runs 8"
leg hroot 24 16 "bash rtl/test/mu_qwen_1018/run_all_hroot.sh $S $O/hroot/runs"
leg kv 32 16 "bash rtl/test/mu_qwen_1018/run_all_kv.sh $S $O/kv/runs"
leg peer 32 16 "bash rtl/test/mu_qwen_1018/run_all_peer.sh $S $O/peer/runs"
leg kvboot 32 16 "mkdir -p $O/kvboot/runs; for c in tb_mu_kv_boot kb_sealwrong kb_gapnot kb_u0gap kb_collide; do bash rtl/test/mu_qwen_1018/run_mu_kv_boot.sh $S $O/kvboot/runs/\$c \$c > $O/kvboot/s_\$c.txt 2>&1 & done; wait; for f in $O/kvboot/s_*.txt; do echo \"== \$f\"; tail -n 3 \$f; done"
leg bootage 32 16 "rm -rf $O/bootage; mkdir -p $O/bootage/runs; xargs -P 8 -L 1 bash -c 'e=\$0; out=\$(bash tools/qwen_kv_die/kv_bootage_bench.sh $O/bootage/runs \"\$@\" 2>&1); rc=\$?; v=\$(echo \"\$out\" | grep -E \"^KVBA_|MISMATCH|ERROR|PHASE_C|%Error\" | tail -1); echo \"[\$e] \$* :: rc=\$rc :: \$v\"' < $D/bootage_cases.txt | sort > $O/bootage/summary.txt; cat $O/bootage/summary.txt"
wait
echo "ALL LEGS DONE $(date -Is)" > /home/ubuntu/scratch/refill-0725/MUKVREG2/ALL_DONE
