#!/bin/bash
# REFILL-1725/KVREG 10-19: KV-die MU bench + mutant regression (MUKVREG2 legs, 102 cases) re-run on main 566b12ac1 merged with
# claude/kv-pc2 ebc61997d, kv-grp2 a5b15ce36, kv-emb2 d9631325d (main copy kept), kv-health e336c7782 = claude/refill1725-kvreg-1019 @fa813c53c.
# head = the same pre-MU tree as MUKVREG2 (MU0 identity baseline). Verilator 5.050. Unpinned ot-run (staged on ot-epyc8).
set -u
D=/srv/opentallas-scratch/claude/refill-1725/KVREG; S=$D/src; O=$D/out
L=/home/ubuntu/scratch/refill-1725/KVREG/legs; mkdir -p $L
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
leg kvboot 32 16 "mkdir -p $O/kvboot/runs; for c in tb_mu_kv_boot kb_sealwrong kb_gapnot kb_u0gap kb_collide; do bash rtl/test/mu_qwen_1018/run_mu_kv_boot.sh $S $O/kvboot/runs/\$c \$c > $O/kvboot/s_\$c.txt 2>&1 & done; bash rtl/test/mu_qwen_1018/run_mu_kv.sh $S $O/kvboot/lint lint_mu_kv_tiles > $O/kvboot/s_lint.txt 2>&1 & wait; for f in $O/kvboot/s_*.txt; do echo \"== \$f\"; tail -n 3 \$f; done"
leg bootage 32 16 "rm -rf $O/bootage; mkdir -p $O/bootage/runs; xargs -P 8 -L 1 bash -c 'e=\$0; out=\$(bash tools/qwen_kv_die/kv_bootage_bench.sh $O/bootage/runs \"\$@\" 2>&1); rc=\$?; v=\$(echo \"\$out\" | grep -E \"^KVBA_|MISMATCH|ERROR|PHASE_C|%Error\" | tail -1); echo \"[\$e] \$* :: rc=\$rc :: \$v\"' < $D/bootage_cases.txt | sort > $O/bootage/summary.txt; cat $O/bootage/summary.txt"
wait
echo "ALL LEGS DONE $(date -Is)" > /home/ubuntu/scratch/refill-1725/KVREG/ALL_DONE
