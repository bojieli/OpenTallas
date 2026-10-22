#!/bin/bash
# REFILL-0730/MUQWREG: full MU bench + mutant regression on claude/mu-qwen-all-1019 0e6795834 (Verilator 5.050).
# Legs run via ot-run on the two staged hosts (ot-agidock128, ot-pve1); src = $D/src (git archive of 0e6795834 subset).
set -u
D=/srv/opentallas-scratch/claude/refill-0730/MUQWREG; S=$D/src; O=$D/out
L=/home/ubuntu/scratch/refill-0730/MUQWREG/legs; mkdir -p $L
VL='$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
PFX="export PATH=\$HOME/.local/opentallas-tools/verilator-5.050/bin:\$PATH VERILATOR=$VL OT_VERILATOR=$VL; cd $S &&"
leg() { # name mem threads cmd
  local n=$1 m=$2 t=$3; shift 3
  ( echo "# leg $n mem $m threads $t $(date -Is)"; echo "# cmd: $*"
    /home/ubuntu/bin/ot-run --mem $m --threads $t --dir $S --disk 10 -- bash -lc "$PFX mkdir -p $O/$n && { $*; } > $O/$n.out 2>&1; rc=\$?; echo \"# exit \$rc\" >> $O/$n.out; exit \$rc"
    echo "# ot-run rc=$? $(date -Is)" ) > $L/$n.log 2>&1 &
  sleep 2
}
# HOST: MU 1 benches + mutants + MU 0 identity (ex_new vs pre-MU head tree)
# r1: FACES builds OOM/terminated at 16 GB (exit 143) -> 48 GB
for g in FACES1 FACES4; do leg amix_$g 48 8 "bash results/rtl/mu_qwen_1018/amix/run_group.sh $g $O/amix_w/$g"; done
wait
