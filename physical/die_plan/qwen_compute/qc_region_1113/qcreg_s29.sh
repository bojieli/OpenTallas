#!/bin/bash
# qcreg.sh RUNDIR PLAN MAP FEED : QC-REGION-1 copy of HOLD-TAP-1 qcreg.sh for the s29 plan; QC REGIONAL die clock estimate = QC-CLKGATE-1 qcgate.sh "region proof"
# leg with the clock built as die_trial link_htree on the plan-derived region map (clock fed along the region links, balanced
# local tree per region), signal + clock combo GRT, routed tap arrivals, die STA related pairs.  ADVISORY, DO_NOT_COUNT.
set -u; export PYTHONDONTWRITEBYTECODE=1
B=$1; P=$2; MAP=$3; FEED=$4; W=${W:-/srv/opentallas-scratch2/claude/qc-region-1/wt}; S=$W/tools/die_plan; MK=/srv/opentallas-scratch2/claude/qc-region-1/ht1/mk_combo_kv.py; MD=$(dirname $MAP)
IMG=openroad/orfs:latest; LIB=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
N=qcr1reg$(basename $B); mkdir -p $B
log(){ echo "$1 $(date "+%F %T")" >> $B/CHAIN.log; }
KARGS="--clock-cell inv2 --rep-um 250 --tree-site-legal --tree-site-slide --kit-workers 8 --tree-form link_htree --region-trees $MAP --feed $FEED --leaf-um 200 --tree-opt region_stub=1"
log "START plan $P sha $(sha256sum $P | cut -c1-16) tools $W (read-only) kit args [$KARGS]"
docker run --rm --name $N-kit --memory=64g --memory-swap=64g --cpus=8 -u 1000:1000 -v $B:$B -v $MD:$MD:ro -v $(dirname $P):$(dirname $P):ro -v $W:$W:ro $IMG bash -lc \
   "cd $W && python3 -B $S/die_trial.py kit $P --out $B/kit $KARGS > $B/kit.log 2>&1"
log "KIT $? $(tail -n 1 $B/kit.log | cut -c1-200)"
K=$B/kit
[ -s $K/clock/tree.json ] && [ -s $K/grt/route.v ] || { log FAIL_KIT; exit 2; }
grt(){ local O=$B/reg/grt_$1; mkdir -p $O/clk
  cp $K/clock/ctree.v $K/clock/tree.json $O/clk/; cp $K/clock/ctree.tcl $O/clk/ctree_ck89.tcl
  CORNER=$1 ADJ=0.75 ADJ7=0 python3 -I $MK $K $O/clk $O > $O/mk.log 2>&1 || return 1
  docker run --rm --name $N-reg-$1 --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$1 \
    -e LIBDIR=$LIB -v $K:/work:ro -v $O:/out $IMG \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$1.log 2>&1; echo EXIT \$? >> /out/combo_$1.log; chown -R 1000:1000 /out"; }
grt TT & grt FF & wait
for C in TT FF; do log "REG_GRT_$C $(grep -h -E "EXIT|Total overflow|GRT-9103|Maximum resident" $B/reg/grt_$C/combo_$C.log | tr "\n" " ")"; done
mkdir -p $B/reg/proof
for C in TT FF; do python3 -s -B $S/trial_tap_arrivals.py $K/clock/tree.json $B/reg/grt_$C/arr_$C.txt $C $B/reg/proof/tap_arrivals_$C.json --physical-paths > $B/reg/tta_$C.log 2>&1; log "REG_TTA_$C $? $(tail -n 1 $B/reg/tta_$C.log | cut -c1-200)"; done
( cd $S && nice python3 -s -B die_sta_related.py $B/reg/proof --plan $P --out $B/reg/sta --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell inv2 --kit-window-out $B/reg/kitwin.json ) > $B/reg/sta.log 2>&1; log "REG_STA $? $(tail -n 3 $B/reg/sta.log | tr "\n" " " | cut -c1-900)"
log CHAIN_DONE
