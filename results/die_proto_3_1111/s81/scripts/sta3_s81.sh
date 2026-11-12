#!/bin/bash
# DIE-PROTO-3 (ADVISORY, DO_NOT_COUNT): S81 ready7b related-pair die STA, declared vs 35 signed type views (mean / bound)
set -u; B=/srv/opentallas-scratch2/claude/die-proto-3; V=auto_r7b_4cf8fb2f1479; A=$B/s81/auto/r7b_4cf8fb2f1479
TL=$A/repo/tools/die_plan; PLAN=$A/repo/physical/die_plan/s81/plan_h2_2249.json; PR=$B/s81/proof_$V; D=$B/s81/sta3
mkdir -p $D
run(){ v=$1; shift; ( cd $TL && prlimit --as=96000000000 nice python3 -s die_sta_related.py $PR --plan $PLAN --out $D/$v --corner TT --corner FF --core-insertion declared --cppr-lca --kit-window-out $D/$v.kitwin.json "$@" ) > $D/$v.log 2>&1; echo "STA_$v rc=$? $(date)" >> $D/STA3.log; }
K(){ for f in $B/s81/kits_$1/*.kit.json; do t=$(basename $f .kit.json); printf -- "--kit %s=%s " $t $f; done; }
run mean $(K mean); run bound $(K bound)
echo STA3_DONE >> $D/STA3.log
