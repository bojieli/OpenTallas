#!/bin/bash
# REFILL-1330/MUKVREG: KV-die MU bench + mutant regression on claude/mu-die-kv-1019 99e646e98 (Verilator 5.050, ot-epyc5).
set -u
D=/srv/opentallas-scratch/claude/refill-1330/MUKVREG; S=$D/src; O=$D/out
L=/home/ubuntu/scratch/refill-1330/MUKVREG/legs; mkdir -p $L
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
# KV-BOOTAGE lockstep benches + mutants (the 24 lines of results/rtl/kv_bootage_1019/run_all_benches.sh)
cat > /home/ubuntu/scratch/refill-1330/MUKVREG/bootage_cases.txt <<'C'
pass vport 0 D=0 R=8
pass vport 0 D=0 R=16
pass vport 0 D=3 R=17
pass vport 0 D=15 R=31
fail vport 6 D=0 R=16
fail vport 7 D=3 R=17
fail vport 8 D=0 R=16
pass pvctl 0 A=95
pass pvctl 0 A=108
fail pvctl 1 A=108
fail pvctl 2 A=108
pass attn 0 PL=0 FD=1 FMUT=0
pass attn 0 PL=37 FD=49 FMUT=0
fail attn 4 PL=37 FD=49 FMUT=0
fail attn 5 PL=37 FD=49 FMUT=0
fail attn 0 PL=37 FD=49 FMUT=6
fail attn 0 PL=37 FD=49 FMUT=7
pass calgen 0 Q=28 R=76 F=1
pass calgen 0 Q=57 R=87 F=49
fail calgen 6 Q=57 R=87 F=49
fail calgen 7 Q=57 R=87 F=49
pass dcfg 0
fail dcfg 6
fail dcfg 7
C
scp -q -o ControlPath=none /home/ubuntu/scratch/refill-1330/MUKVREG/bootage_cases.txt ot-epyc5:$D/bootage_cases.txt
leg bootage 32 16 "mkdir -p $O/bootage/runs; while read -r e b rest; do echo \"\$e \$b \$rest\"; done < $D/bootage_cases.txt | xargs -P 8 -L 1 bash -c 'e=\$0; out=\$(bash tools/qwen_kv_die/kv_bootage_bench.sh $O/bootage/runs \"\$@\" 2>&1); rc=\$?; v=\$(echo \"\$out\" | grep -E \"^KVBA_\" | tail -1); echo \"[\$e] \$* :: rc=\$rc :: \$v\"' | sort > $O/bootage/summary.txt; cat $O/bootage/summary.txt"
wait
echo "ALL LEGS DONE $(date -Is)" > /home/ubuntu/scratch/refill-1330/MUKVREG/ALL_DONE
