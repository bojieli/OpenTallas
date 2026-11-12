#!/bin/bash
# DIE-PROTO-3 (ADVISORY, DO_NOT_COUNT): HEAD FREG die related-pair STA variants on the routed die clock proof.
#  decl  : declared 12.3 budget on every block (= proto_die STA) + count-align (ca2 bind + FREG K+1)
#  mean  : 19 SIGNED types as interface models (signed insertion_pinflops mean), 6 unsigned declared; + CA
#  bound : same, signed lat = pin-flop min..max (type-wide bound)
set -u; B=/srv/opentallas-scratch2/claude/die-proto-3; W=/srv/opentallas-scratch2/claude/wt/die-proto-3; D=$B/head/freg
TL=$W/tools/die_plan; PLAN=$W/physical/die_plan/s81_head/plan_of_record/l48hp1/source_plan_freg.json
BIND=$B/head/bind_freg_ca2.json; RING=$W/results/die_head_21_1028/hk4/clock_profile/ca_ring_hd_tile_dh20.json
run(){ V=$1; shift; O=$D/sta3_$V; mkdir -p $O
  ( cd $TL && prlimit --as=48000000000 nice python3 -s die_sta_related.py $D/proof --plan $PLAN --out $O --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell inv --count-align $BIND --ca-write-fall --ca-ring $RING --kit-window-out $O/kitwin.json $* ) > $O.log 2>&1
  echo "STA_$V rc=$? $(date)" >> $D/STA3.log; }
K(){ for f in $B/head/kits_$1/*.kit.json; do t=$(basename $f .kit.json); printf -- "--kit %s=%s " $t $f; done; }
run decl & run mean $(K mean) & run bound $(K bound) & wait
echo STA3_DONE >> $D/STA3.log
