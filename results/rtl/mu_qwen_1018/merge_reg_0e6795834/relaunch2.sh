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
# r2: coll legs r0 were hollow (cases=0): shlex-quoted --only regex passed unevaluated -> eval
for c in mu_bi mu_bi_neg_overlap mu_bi_mut_rlat mu_bi_mut_rank; do
  leg coll_$c 32 8 "a=\$(python3 tools/xdie_qtp8/cases.py args $c) && rm -rf $O/coll/$c && eval python3 tools/qwen_coll_tp8_static_links_bench.py --out $O/coll/$c \$a; rc=\$?; rm -rf $O/coll/$c/obj_*; exit \$rc"
done
wait
