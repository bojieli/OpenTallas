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
  # S81-DIE-R3 11-17: mk_combo_kv.py from the tools tree with OT_DIE_PLAN_TOOLS=$S (a copy beside $B found no die_sta module:
  # all three route steps crashed while the chain exited 0); $B/mk_combo_kv.py only when the tree has none
  local MK=$S/mk_combo_kv.py; [ -f $MK ] || MK=$B/mk_combo_kv.py
  OT_DIE_PLAN_TOOLS=$S CORNER=$2 ADJ=0.75 ADJ7=0 python3 -I $MK $K $O/clk $O > $O/mk.log 2>&1 || { echo "MK_$1_$2" >> $D/FAILS; return 1; }
  docker run --rm --name dproto-$DIE-$V-grt-$1-$2 --memory=${GM:-32g} --memory-swap=${GM:-32g} --cpus=8 -e CORNER=$2 ${M:+-e OT_GRT_TRANSITION_MODE=$M} \
    -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $K:/work:ro -v $O:/out $G \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$2.log 2>&1; echo EXIT \$? >> /out/combo_$2.log; chown -R 1000:1000 /out"
}
grt st TT & grt st FF & grt off TT $GOFF off & wait
for t in st_TT st_FF off_TT; do log "GRT_$t $(grep -h -E 'EXIT|Total overflow|GRT-9103|Maximum resident' $D/grt_$t/combo_*.log 2>/dev/null | tr '\n' ' ')"
  grep -qx "EXIT 0" $D/grt_$t/combo_*.log 2>/dev/null || echo "GRT_$t" >> $D/FAILS; done
mkdir -p $D/proof/clk
# CA steps (landed_phase_ocv) read RUN/clk/tree.json: the die_trial kit clock tree is the proof clock (S81-DIE-R3 11-17)
cp $K/clock/tree.json $K/clock/ctree.v $D/proof/clk/ || echo PROOF_CLK >> $D/FAILS
for C in TT FF; do python3 -s $S/trial_tap_arrivals.py $K/clock/tree.json $D/grt_st_$C/arr_$C.txt $C $D/proof/tap_arrivals_$C.json --physical-paths > $D/tta_$C.log 2>&1; rc=$?; log "TTA_$C $rc $(tail -n 1 $D/tta_$C.log)"; [ $rc = 0 ] || echo "TTA_$C" >> $D/FAILS; done
# KIT-OPS-6 11-15: CA steps always run (landed_phase_ocv, count_align_plan/bind, die_sta_related --count-align); legacy T/2 run kept as sta_legacy (LEGACY)
# HEAD-DIE-R 11-16 (COORD r400): the CA steps run on the tools of the plan's OWN published source tree (the nearest parent
# holding .src-manifest.json), so the count-aligned bind matches the plan's sidecar/FREG declarations; CA_TOOLS overrides;
# a plan outside any published tree keeps the worktree tools ($S).
CAT=${CA_TOOLS:-}; if [ -z "$CAT" ]; then pd=$(cd "$(dirname "$P")" && pwd)
  while [ "$pd" != / ]; do [ -f "$pd/.src-manifest.json" ] && { CAT=$pd/tools/die_plan; break; }; pd=$(dirname "$pd"); done; fi
[ -f "${CAT:-/nonexistent}/die_chain_ca.sh" ] || CAT=$S; log "CA_TOOLS $CAT"
CA_TOOLS=$CAT bash $CAT/die_chain_ca.sh $D/proof $P $D/ca ${CC:-inv2} --kit-window-out $D/kitwin.json; rc=$?; [ $rc = 0 ] || echo CA_CHAIN >> $D/FAILS; log "CA_CHAIN $rc (STA_CA in $D/ca/CHAIN.log; legacy T/2 = LEGACY)"
( cd $S && nice python3 -s die_sta_related.py $D/proof --plan $P --out $D/sta_droop --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell ${CC:-inv2} --margin-policy legacy --data-droop class ) > $D/sta_droop.log 2>&1; rc=$?; [ $rc = 0 ] || echo STA_DROOP >> $D/FAILS; log "STA_DROOP $rc"
# any failed step -> CHAIN_FAIL + exit 1 (an all-crashed route used to end CHAIN_DONE with exit 0)
if [ -s $D/FAILS ]; then log "CHAIN_FAIL $(tr '\n' ' ' < $D/FAILS)"; exit 1; fi
log CHAIN_DONE
