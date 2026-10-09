#!/bin/bash
# die-evidence-2 2026-10-09 (Claude): HBM GENERIC die (R25G = r25s + r25m + r25iqg + fmt3 wide SM grid, indexer
# rebased; preset in tools/hbm_accel_die_fp.py @ claude/hbm-forks-20261009) die-level academic-validation chain.
# R25G builds only as a NETWORK PROBE (the generator refuses the retiled SM network as unqualified): every record here
# is labelled network_probe.  Remote host, memory-gated (/srv/opentallas-scratch/admit.sh).
#   0. strict die-top lint (python graph + tie-off classes) on R25G
#   1. own clock plan (extract_die -> clock-only CTS trunk/region/htop/hreg -> record)       [parallel]
#   2. IR: every generator window (case c, PSM), recorded with hbm_accel_die_price.record    [parallel]
#   3. die case with the CURRENT view index (closed views; interim/placeholder = labelled) + relays
#   4. clock context (measured insertion sheets) -> relay STA Tcl
#   5. full-die GRT + STA TT/FF/SS RAW (no pads)  -> derive rule-H1 hold pads from the raw FF report
#   6. STA-only re-run with the derived pads (raw + padded per corner)
#   7. 4 guided representative-region DRTs on the GRT checkpoint (hub / attn / ioedge / svc-sm)
# usage: [SKIP_IR=1] hbm_r25g_chain.sh <src dir> <run dir>   (re-launch resumes: a recorded clock plan is kept)
set -u
SRC=$(readlink -f $1); B=$2; mkdir -p $B; B=$(readlink -f $B); W=$B/case; V=r25g
ADMIT=/srv/opentallas-scratch/admit.sh
say() { echo "$(date '+%F %T %Z') $*" >> $B/STATUS.log; }
say "chain start src=$SRC ($(cat $SRC/SOURCE_COMMIT)) variant=$V (network_probe)"
cd $SRC
# 0. lint
( mkdir -p $B/lint; $ADMIT 40 -- python3 tools/die_top_lint.py lint --die hbm --variant $V --out $B/lint > $B/lint/lint.log 2>&1
  say "LINT rc=$? $(tail -1 $B/lint/lint.log | cut -c1-400)" ) &
# 1. clock plan
( C=$B/clock; mkdir -p $C; [ -f $C/plan.json ] && exit 0      # resume: the plan is already recorded
  $ADMIT 40 -- python3 tools/budgets/extract_die.py --src $SRC --die hbm --hbm-variant $V --out $C/model.json.gz > $C/extract.log 2>&1 || { say "CLOCK EXTRACT FAIL"; exit 1; }
  for g in trunk region htop hreg; do
    python3 tools/budgets/clock_plan.py emit --die-model $C/model.json.gz --group $g --name ${V}_$g --out $C/$g > $C/emit_$g.log 2>&1 &&
      ( cd $C/$g && $ADMIT 24 -- bash run.sh > run.out 2>&1 ) &
  done; wait
  python3 tools/budgets/clock_plan.py record --die-model $C/model.json.gz $(for g in trunk region htop hreg; do [ -f $C/$g/run.sh ] && echo --case $C/$g; done) --out $C/plan.json > $C/record.log 2>&1
  say "CLOCK PLAN rc=$? $(tail -3 $C/record.log | tr '\n' ' ' | cut -c1-500)" ) &
CLOCK_PID=$!
# 2. IR (all windows of the generator; ~1-4 GB each)
[ -n "${SKIP_IR:-}" ] || ( I=$B/ir/$V; mkdir -p $I
  for w in $(python3 tools/hbm_accel_die_fp.py irwin --ds-var $V); do
    python3 tools/hbm_accel_die_fp.py ir --ds-var $V --window $w --work $I/c_$w > $I/gen_$w.log 2>&1 || { say "IR gen $w FAIL"; continue; }
    ( $ADMIT 8 -- docker run --rm --name de2_ir_${V}_$w --memory=24g -v $I/c_$w:/work openroad/orfs:asap7lock \
        bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 2 -no_init -exit /work/run.tcl > /work/run.log 2>&1; echo \$? > /work/run.log.exit; chmod -R a+rwX /work" ) &
    while [ $(jobs -rp | wc -l) -ge 24 ]; do sleep 20; done
  done; wait
  python3 -c "
import sys; sys.path.insert(0, 'tools')
import hbm_accel_die_fp as F, hbm_accel_die_price as PR
v = F.variant_arg('$V'); m = F.build(v, network_probe=True)
PR.record(m, '$B/ir', '$B/ir/feasibility_$V.json', '')
" > $B/ir/record.log 2>&1
  say "IR rc=$? $(python3 -c "import json;print(json.load(open('$B/ir/feasibility_$V.json'))['ir_summary'].get('$V'))" 2>&1 | cut -c1-600)" ) &
# 3. die case (current views)
rm -rf $W; $ADMIT 40 -- python3 tools/hbm_die_views.py --variant $V die --work $W --case sta --relays > $B/case.log 2>&1 || { say "CASE FAIL (case.log)"; wait; exit 1; }
say "case ready: $(tail -2 $B/case.log | tr '\n' ' ' | cut -c1-600)"
wait $CLOCK_PID
[ -f $B/clock/plan.json ] || { say "NO CLOCK PLAN: stop before STA"; wait; exit 1; }
python3 tools/hbm_die_clock_context.py --die-model $B/clock/model.json.gz --clock-plan $B/clock/plan.json \
  --sheets results/rtl/budgets_20261006/sheets --out $B/clock_ctx > $B/clock_ctx.log 2>&1 || { say "CLOCK CONTEXT FAIL"; wait; exit 1; }
say "clock context: $(tail -1 $B/clock_ctx.log)"
python3 tools/hbm_die_relay_sta.py --case $W --clock-context $B/clock_ctx/clock_context.json \
  --measured results/rtl/budgets_20261006/measured_insertion.json > $B/relay_sta.log 2>&1 || { say "RELAY STA GEN FAIL"; wait; exit 1; }
say "relay sta: $(tail -1 $B/relay_sta.log)"
# 5. GRT + raw STA
$ADMIT 90 -- docker run --rm --name de2_hbm_${V}_grt --memory=200g -v $W:/work -v $W:/out openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /work/run_grt_sta.tcl > /out/grt_sta.log 2>&1; chmod -R a+rwX /out"
say "GRT+STA raw: $(grep -A12 'Final congestion' $W/grt_sta.log | grep '^Total' | tail -1) | $(grep -E 'OT_WNS|OT_FAIL_ENDPOINTS|OT_GRT_S' $W/grt_sta.log | tr '\n' ' ')"
[ -f $W/ckpt_grt.odb ] || { say "NO GRT CHECKPOINT"; wait; exit 1; }
# rule-H1 pads from the raw FF hold report, then STA-only (same global route re-run in-session)
python3 tools/die_hold_pads.py $W/paths_ff.txt --out $B/hold_pads.json --summary $B/hold_pads_summary.json > $B/pads.log 2>&1
say "H1 pads: $(tail -1 $B/pads.log | cut -c1-400)"
python3 tools/hbm_die_relay_sta.py --case $W --clock-context $B/clock_ctx/clock_context.json \
  --measured results/rtl/budgets_20261006/measured_insertion.json --hold-pads $B/hold_pads.json > $B/relay_sta_pad.log 2>&1
mkdir -p $W/sta_pad
( $ADMIT 90 -- docker run --rm --name de2_hbm_${V}_stapad --memory=200g -v $W:/work -v $W/sta_pad:/out openroad/orfs:asap7lock \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /work/run_grt_sta_only.tcl > /out/sta.log 2>&1; chmod -R a+rwX /out"
  say "STA padded: $(grep -E 'OT_CLOCK_CONTEXT|OT_WNS|OT_HOLD_PADS|OT_FAIL_ENDPOINTS' $W/sta_pad/sta.log | tr '\n' ' ')" ) &
# 7. regions (R25G outline 31,734 x 25,162 um): hub at the centre crossing, attention half-tile pair, S SerDes IO edge,
#    SM + svc corner
for r in "hub 15100 11800 16600 13300" "attn 1100 6300 2600 7800" "ioedge 13700 3600 15700 6100" "smsvc 1400 1100 2900 2600"; do
  set -- $r
  python3 tools/hbm_die_region_drt.py stage --case $W --name $1 --window $2 $3 $4 $5 --tool-path $SRC/tools/hbm_die_region_drt.py >> $B/regions.log 2>&1 || { say "region stage $1 FAIL"; continue; }
  ( $ADMIT 80 -- bash $W/regiong_$1/start_region.sh > $W/regiong_$1/start.out 2>&1
    say "region $1: $(tail -1 $W/regiong_$1/STATUS.log 2>/dev/null)" ) &
  sleep 600
done
wait
say "chain done"
