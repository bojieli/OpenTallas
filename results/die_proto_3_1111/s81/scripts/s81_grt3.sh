#!/bin/bash
# DIE-PROTO-1 (ADVISORY, DO_NOT_COUNT) S81 combo die GRT (signal ft route.v M4-M7 at ADJ 0.75 + die clock M8-M9, 50 it) on
# the DIE-RECHECK-1 balanced-feed kit of the S81 plan of record plan_h2_2249 (e596e9588e72; ck_bal, read-only copy of
# kit inputs via a ro mount): TT stock + TT halving-off (opentallas/orfs:asap7lock-grtoff, OT_GRT_TRANSITION_MODE=off).
# The clock + related-pair die STA of this kit is DIE-RECHECK-1's (s81/auto/e596e9588e72/clock_summary.json).
set -u; B=/srv/opentallas-scratch2/claude/die-proto-3; D=$B/s81/grt_r7b; K=$B/s81/ck_auto_r7b_4cf8fb2f1479/kit
mkdir -p $D; IMG=openroad/orfs:latest; GOFF=opentallas/orfs:asap7lock-grtoff
log(){ echo "$1 $(date '+%F %T')" >> $D/CHAIN.log; }
log "START s81 kit $K plan $(python3 -I -c "import json;print(json.load(open('$K/kit.json'))['plan_sha256'][:12])")"
grt(){ # tag corner [image] [mode]
  local O=$D/grt_$1_$2; local G=${3:-$IMG}; local M=${4:-}; mkdir -p $O/clk
  cp $K/clock/ctree.v $K/clock/tree.json $O/clk/; cp $K/clock/ctree.tcl $O/clk/ctree_ck89.tcl
  CORNER=$2 ADJ=0.75 ADJ7=0 python3 -I $B/mk_combo_kv.py $K $O/clk $O > $O/mk.log 2>&1 || return 1
  docker run --rm --name dproto3-s81-${ST:-A}-grt-$1-$2 --memory=${GM:-64g} --memory-swap=${GM:-64g} --cpus=8 -e CORNER=$2 ${M:+-e OT_GRT_TRANSITION_MODE=$M} \
    -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out $G \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$2.log 2>&1; echo EXIT \$? >> /out/combo_$2.log; chown -R 1000:1000 /out"
}
grt st TT & grt st FF & grt off TT $GOFF off & wait
for t in st_TT st_FF off_TT; do log "GRT_$t $(grep -h -E 'EXIT|Total overflow|GRT-9103|Maximum resident' $D/grt_$t/combo_*.log | tr '\n' ' ')"; done
log CHAIN_DONE
