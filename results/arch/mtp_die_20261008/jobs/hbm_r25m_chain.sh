#!/bin/bash
# mtp-die 2026-10-08 (Claude): HBM accelerator r25m (r25 + hfd_mtp low spine slot) die-level evidence on EPYC1.
#   clock plan (extract_die --hbm-variant r25m -> clock_plan emit / CTS / record) || case (hbm_die_views die --variant r25m
#   --case sta --relays) -> relay STA kit -> full-die GRT + GRT-parasitic STA (TT setup / FF hold / SS) -> rebudget link
#   dump (hfd_mtp ports enter the link model).  hfd_mtp is a generated placeholder (interim lib) until mtp-hbm's
#   hfd_mtp route closes.  Memory-gated (admit.sh).  Usage: hbm_r25m_chain.sh <src tree (git archive of the commit)>
set -u
SRC=$1; B=/srv/opentallas-scratch/claude/mtp-die/hbm_r25m; W=$B/grt
mkdir -p $B $W; cd $B
say() { echo "$(date '+%F %T %Z') $*" >> $B/STATUS.log; }
say "chain start src=$SRC ($(cat $SRC/SOURCE_COMMIT 2>/dev/null))"
( mkdir -p $B/clock && cd $SRC && python3 tools/budgets/extract_die.py --src $SRC --die hbm --hbm-variant r25m --out $B/clock/model.json.gz > $B/clock/extract.log 2>&1 &&
  for g in trunk region htop hreg; do python3 tools/budgets/clock_plan.py emit --die-model $B/clock/model.json.gz --group $g --name r25m_$g --out $B/clock/$g > $B/clock/emit_$g.log 2>&1 && (cd $B/clock/$g && /srv/opentallas-scratch/admit.sh 40 -- bash run.sh > run.out 2>&1) & done; wait
  python3 tools/budgets/clock_plan.py record --die-model $B/clock/model.json.gz $(for g in trunk region htop hreg; do [ -f $B/clock/$g/run.sh ] && echo --case $B/clock/$g; done) --out $B/clock/plan.json > $B/clock/record.log 2>&1
  say "clock plan: $(tail -3 $B/clock/record.log | tr '\n' ' ')" ) &
( cd $SRC && python3 tools/hbm_die_views.py --variant r25m die --work $W --case sta --relays ) > $B/case.log 2>&1 || { say "CASE FAIL (case.log)"; wait; exit 1; }
cp /srv/opentallas-scratch/claude/hbm-die/r25_grt/clock_context.json $W/ 2>/dev/null
( cd $SRC && python3 tools/hbm_die_relay_sta.py --case $W --clock-context $W/clock_context.json \
    --measured results/rtl/budgets_20261006/measured_insertion.json --hold-pads /srv/opentallas-scratch/claude/die-evidence/hbm_r25/hold_pads.json ) > $B/relay_sta.log 2>&1 || say "RELAY STA GEN FAIL (relay_sta.log)"
say "case ready: $(tail -2 $B/case.log | tr '\n' ' ') | $(tail -1 $B/relay_sta.log)"
/srv/opentallas-scratch/admit.sh 70 -- docker run --rm --name mtpdie_hbm_r25m_grt --memory=150g -v $W:/work -v $W:/out openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /work/run_grt_sta.tcl > /out/grt_sta.log 2>&1; chmod -R a+rwX /out"
say "GRT+STA: $(grep -A12 'Final congestion' $W/grt_sta.log | grep '^Total' | tail -1) | $(grep -E 'OT_WNS|OT_FAIL_ENDPOINTS' $W/grt_sta.log | tr '\n' ' ')"
# rebudget link dump on this case (same session recipe as rebudget/hbm_r25/run_rb.tcl, case path swapped)
if [ -f $W/ckpt_grt.odb ]; then
  mkdir -p $B/rebudget && sed -e "s#/srv/opentallas-scratch/claude/die-evidence/hbm_r25/grt3#$W#g" /srv/opentallas-scratch/claude/rebudget/hbm_r25/run_rb.tcl > $B/rebudget/run_rb.tcl
  cp $SRC/tools/budgets/rebudget_links.tcl $B/rebudget/ 2>/dev/null; cp /srv/opentallas-scratch/claude/rebudget/hbm_r25/scope*.txt $B/rebudget/ 2>/dev/null
  /srv/opentallas-scratch/admit.sh 70 -- docker run --rm --name mtpdie_hbm_r25m_rb --memory=150g -v $W:/work:ro -v $W:$W:ro -v $B/rebudget:/rb openroad/orfs:asap7lock \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /rb/run_rb.tcl > /rb/rb.log 2>&1; chmod -R a+rwX /rb"
  say "links: $(grep -h 'OT_RB_DUMP\|^Error' $B/rebudget/rb.log | tr '\n' ' ')"
fi
wait
say "chain done"
