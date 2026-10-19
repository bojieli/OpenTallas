#!/bin/bash
# MU-DIE-S81/HOP: SU + MU programmes with the lowered stage hop (L0 / L14 / L20; L2 waits hwin NEV 16)
cd /home/ubuntu/wt/mu-die-s81-hop-1019
H=/home/ubuntu/scratch/mu-die-s81/hop
cc() { L=$1; C=$2; if [ "$C" = su ]; then o=$H/prog/prog_${L}_su; x=""; else o=$H/prog/prog_${L}_mu_$C; x="--mu-cal results/arch/mu_s81_1018/calendar_ar_q4.json --mu-ctx --mu-win $C"; fi
  rm -rf $o; timeout 1500 python3 tools/s81_dv/dv_layer_compile.py --layer $L --out $o --die-src /home/ubuntu/scratch/mu-die-s81/tok/tree_mu $x \
    --fixtures /home/ubuntu/scratch/layerbench-s81/fixtures/$L > $H/logs/cc_${L}_$C.log 2>&1; echo "$L $C rc=$? $(grep '^{' $H/logs/cc_${L}_$C.log)"; }
for x in L0:A L0:su L14:su L20:su L14:A L14:B L20:A L20:B; do cc ${x%:*} ${x#*:} & done; wait
