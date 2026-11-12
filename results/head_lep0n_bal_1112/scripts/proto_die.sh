#!/bin/bash
# DIE-PROTO-1 (ADVISORY, DO_NOT_COUNT): generic die prototype on a die plan of record.
#  (1) die_trial kit: every partition TYPE as an abstract (plan outline + every plan pin + OBS M1-M3 + hard-core OBS up to
#      the core view top layer, M5 without a view), die clock = balanced die H-tree (inv2, true polarity, rep 250, legal
#      sites by slide) to every plan tap; die route.v = every ft slot crossing + reset spine.
#  (2) combo die GRT (signal M4-M7 at ADJ 0.75 = the partition's own logic, clock M8-M9; DIE-KV-58 mk_combo form), 50 it:
#      TT + FF on the stock image, TT on opentallas/orfs:asap7lock-grtoff with OT_GRT_TRANSITION_MODE=off.
#  (3) tap arrivals (routed RC) -> related-pair die STA (die_sta_related, declared core insertion, CPPR LCA, nominal
#      12.24b gate) + a data-droop-class sensitivity run (10-27 rule, info).
# usage: proto_die.sh DIE PLAN TAG [extra die_trial kit args...]
set -u; DIE=$1; P=$2; V=$3; shift 3; X="$*"
B=${PB:-/srv/opentallas-scratch2/claude/die-proto-1}; W=${PW:-/srv/opentallas-scratch2/claude/wt/die-proto-1}; S=$W/tools/die_plan
D=$B/$DIE/$V; rm -rf $D; mkdir -p $D; cd $D; IMG=openroad/orfs:latest; GOFF=opentallas/orfs:asap7lock-grtoff
log(){ echo "$1 $(date '+%F %T')" >> $D/CHAIN.log; }
log "START $DIE plan $P sha $(sha256sum $P | cut -c1-12) wt $(git -C $W rev-parse --short=12 HEAD 2>/dev/null || cat $W/WT_SHA) args [$X]"
if [ -n "${KITSRC:-}" ]; then ln -s $KITSRC $D/kit; log "KIT reused $KITSRC"
elif [ -n "${OTCLK:-}" ]; then
  docker run --rm --name dproto-$DIE-$V-otclk --memory=${GM:-32g} --memory-swap=${GM:-32g} --cpus=8 -u 1000:1000 -v $B:$B -v $W:$W $IMG \
    bash -lc "cd $W && python3 tools/clk/ot_clk.py kit $OTCLK --out $D/tree > $D/kit.log 2>&1"; log "OTCLK_KIT $? $(tail -n 2 $D/kit.log | tr '\n' ' ')"
  ln -s $D/tree/kit $D/kit
else
docker run --rm --name dproto-$DIE-$V-kit --memory=${GM:-32g} --memory-swap=${GM:-32g} --cpus=8 -u 1000:1000 -v $B:$B -v $W:$W $IMG \
  bash -lc "cd $W && python3 $S/die_trial.py kit $P --out $D/kit --clock-cell inv2 --rep-um 250 --tree-site-slide $X > $D/kit.log 2>&1"; log "KIT $? $(tail -n 2 $D/kit.log | tr '\n' ' ')"
fi
K=$D/kit; [ -s $K/clock/tree.json ] && [ -s $K/grt/route.v ] || { log FAIL_KIT; exit 2; }
grt(){ # tag corner [image] [mode]
  local O=$D/grt_$1_$2; local G=${3:-$IMG}; local M=${4:-}; mkdir -p $O/clk
  cp $K/clock/ctree.v $K/clock/tree.json $O/clk/; cp $K/clock/ctree.tcl $O/clk/ctree_ck89.tcl
  CORNER=$2 ADJ=0.75 ADJ7=0 python3 -I $B/mk_combo_kv.py $K $O/clk $O > $O/mk.log 2>&1 || return 1
  docker run --rm --name dproto-$DIE-$V-grt-$1-$2 --memory=${GM:-32g} --memory-swap=${GM:-32g} --cpus=8 -e CORNER=$2 ${M:+-e OT_GRT_TRANSITION_MODE=$M} \
    -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out $G \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$2.log 2>&1; echo EXIT \$? >> /out/combo_$2.log; chown -R 1000:1000 /out"
}
grt st TT & grt st FF & grt off TT $GOFF off & wait
for t in st_TT st_FF off_TT; do log "GRT_$t $(grep -h -E 'EXIT|Total overflow|GRT-9103|Maximum resident' $D/grt_$t/combo_*.log | tr '\n' ' ')"; done
mkdir -p $D/proof
for C in TT FF; do python3 -s $S/trial_tap_arrivals.py $K/clock/tree.json $D/grt_st_$C/arr_$C.txt $C $D/proof/tap_arrivals_$C.json --physical-paths > $D/tta_$C.log 2>&1; log "TTA_$C $? $(tail -n 1 $D/tta_$C.log)"; done
( cd $S && nice python3 -s die_sta_related.py $D/proof --plan $P --out $D/sta --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell ${CC:-inv2} --kit-window-out $D/kitwin.json ) > $D/sta.log 2>&1; log "STA $? $(grep -E 'TT|FF' $D/sta.log | tail -n 6 | tr '\n' ' ')"
( cd $S && nice python3 -s die_sta_related.py $D/proof --plan $P --out $D/sta_droop --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell ${CC:-inv2} --margin-policy legacy --data-droop class ) > $D/sta_droop.log 2>&1; log "STA_DROOP $?"
log CHAIN_DONE
