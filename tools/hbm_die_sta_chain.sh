#!/bin/bash
# HBM die STA chain (hbmdie-v10-sta, 2026-10-12): relay-instanced die case -> own clock plan (+ clock_plan.py balance,
# B2 SPEC sec 1 early taps) -> clock context -> relay STA Tcl (TT setup / FF hold / SS sensitivity on GRT parasitics,
# + OCV derate bound + GRT-vs-DRT wire-cap sensitivity, tools/hbm_die_relay_sta.py sensitivity()) -> full-die GRT+STA.
# Successor of /srv/opentallas-scratch/claude/die-evidence-2/hbm_r25g_chain.sh (steps 0/1/3/4/5 of it; IR, hold pads
# and region DRTs are separate).  Every heavy step is memory-admitted by ot-heavy.
# usage: V=<preset> hbm_die_sta_chain.sh <src dir> <run dir>     (resume: a recorded clock plan / built case is kept)
# results: <run>/STATUS.log; <run>/case/grt_sta.log  (grep OT_WNS / OT_FAIL_ENDPOINTS / OT_SENS / '^Total')
set -u
SRC=$(readlink -f $1); B=$2; mkdir -p $B; B=$(readlink -f $B); W=$B/case; V=${V:?preset}
export PYTHONHASHSEED=0
say() { echo "$(date '+%F %T %Z') $*" >> $B/STATUS.log; }
say "chain start src=$SRC ($(cat $SRC/SOURCE_COMMIT 2>/dev/null)) variant=$V"
cd $SRC
# 1. own clock plan (extract -> clock-only CTS trunk/region/htop/hreg -> record)
( C=$B/clock; mkdir -p $C; [ -f $C/plan.json ] && exit 0
  ot-heavy --mem 40 -- python3 tools/budgets/extract_die.py --src $SRC --die hbm --hbm-variant $V --out $C/model.json.gz > $C/extract.log 2>&1 || { say "CLOCK EXTRACT FAIL"; exit 1; }
  for g in trunk region htop hreg; do
    python3 tools/budgets/clock_plan.py emit --die-model $C/model.json.gz --group $g --name ${V}_$g --out $C/$g > $C/emit_$g.log 2>&1 &&
      ( cd $C/$g && ot-heavy --mem 24 -- bash run.sh > run.out 2>&1 ) &
  done; wait
  python3 tools/budgets/clock_plan.py record --die-model $C/model.json.gz $(for g in trunk region htop hreg; do [ -f $C/$g/run.sh ] && echo --case $C/$g; done) --out $C/plan.json > $C/record.log 2>&1
  say "CLOCK PLAN rc=$? $(tail -3 $C/record.log | tr '\n' ' ' | cut -c1-500)" ) &
CLOCK_PID=$!
# 0. die case (current view index) + relays
if [ ! -f $W/run.tcl ]; then
  rm -rf $W; ot-heavy --mem 30 -- python3 tools/hbm_die_views.py --variant $V die --work $W --case sta --relays > $B/case.log 2>&1 || { say "CASE FAIL (case.log)"; wait; exit 1; }
fi
say "case ready: $(tail -1 $B/case.log | cut -c1-400)"
python3 tools/hbm_die_clock_pins.py $W > $B/clock_pins.log 2>&1; say "relay/station clock pins: $(tail -1 $B/clock_pins.log)"
wait $CLOCK_PID
[ -f $B/clock/plan.json ] || { say "NO CLOCK PLAN: stop before STA"; exit 1; }
# 2. balance (B2 SPEC sec 1: early taps for late views); fall back to the recorded plan if it does not apply
P=$B/clock/plan.json
python3 tools/budgets/clock_plan.py balance --die-model $B/clock/model.json.gz --plan $P --libs $W --out $B/clock/plan_bal.json > $B/clock/balance.log 2>&1 \
  && P=$B/clock/plan_bal.json
say "balance: plan=$(basename $P) $(tail -1 $B/clock/balance.log | cut -c1-400)"
python3 tools/hbm_die_clock_context.py --die-model $B/clock/model.json.gz --clock-plan $P \
  --sheets results/rtl/budgets_20261006/sheets --no-sheet-ok --out $B/clock_ctx > $B/clock_ctx.log 2>&1 || { say "CLOCK CONTEXT FAIL"; exit 1; }
say "clock context: $(tail -1 $B/clock_ctx.log | cut -c1-300)"
python3 tools/hbm_die_relay_sta.py --case $W --clock-context $B/clock_ctx/clock_context.json \
  --measured results/rtl/budgets_20261006/measured_insertion.json --place-sens > $B/relay_sta.log 2>&1 || { say "RELAY STA GEN FAIL"; exit 1; }
say "relay sta: $(tail -1 $B/relay_sta.log | cut -c1-300)"
# placement-parasitic STA only (run_sta_place.tcl, hbmdie-v10-sta post_grt.sh): skip the case's own GRT
[ -n "${STOP_BEFORE_GRT:-}" ] && { say "STOP_BEFORE_GRT: run_sta_place.tcl ready"; exit 0; }
# 3. full-die GRT + STA (TT/FF/SS raw) + OCV / cap sensitivity
ot-heavy --mem 200 -- docker run --rm --name hbmdie_${V}_grtsta --memory=200g --cpus=16 -v $W:/work -v $W:/out openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /work/run_grt_sta.tcl > /out/grt_sta.log 2>&1; echo \$? > /out/grt_sta.log.exit; chmod -R a+rwX /out"
say "GRT+STA: $(grep -A12 'Final congestion' $W/grt_sta.log | grep '^Total' | tail -1) | $(grep -E 'OT_WNS|OT_FAIL_ENDPOINTS|OT_GRT_S|OT_CLOCK_CONTEXT' $W/grt_sta.log | tr '\n' ' ')"
say "SENS: $(grep -E '^OT_SENS ' $W/grt_sta.log | tr '\n' ' ')"
say "chain done"
