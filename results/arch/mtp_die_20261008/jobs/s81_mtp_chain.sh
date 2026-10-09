#!/bin/bash
# mtp-die 2026-10-08 (Claude): S81 die-level evidence for the MTP homes on EPYC3, one case per call.
#   <case>: l1wfc = m221pq layer1 die (r3 options + --field-margin 213.84, the main-generator frame fit) + --wfc-hard
#           headmtp = v9e head die + --pairs 511 (drafter moved to the draft dies) --mtp-seq --mtp-links 5
#   real case -> clock plan (extract_die -> clock_plan emit / CTS / record) -> die STA kit (die_sta.py, balanced latency)
#   -> full-die GRT k=1 + GRT-parasitic STA TT / FF / SS (dietop_grt_sta.sh) -> rebudget link dump (fwd clocks).
#   dsfd_wfc / dsfd_mtp_seq / the extra SerDes chains are interim (placeholder) libs until mtp-rom closes the blocks.
#   Memory-gated (admit.sh).  Usage: s81_mtp_chain.sh <case> <src tree (git archive of the commit)>
set -u
CASE=$1; S=$2; R=/srv/opentallas-scratch/claude/mtp-die/s81; M=$R/$CASE; mkdir -p $M
D81=/srv/opentallas-scratch/claude/s81-die
say() { echo "$(date '+%F %T %Z') $*" >> $M/STATUS.log; }
case $CASE in
  l1wfc)  export OT_S81_Q_LEF=physical/s81_die_views/q_elem_qs5f/q_elem.lef.gz
          A="$(cat $D81/m221pq_r3/options.txt) --field-margin 213.84 --wfc-hard"; DIE=layer1;;
  headmtp) export OT_S81_Q_LEF=results/rtl/dsrom_qz_20261004/Z20/Z20c/routed_element.lef.gz
          A="--gen r8 --rev r9 --elem-h 198.72 --cc-reach-um 215 --vch-interleave --link-fix --corr-interleave --hop-fix --meso-d8 --cfifo-v2 --hc-xface --link-split --sel-xstg --pin-relay --ch-heights 259.2,302.4,388.8,388.8,302.4,259.2,259.2 --bf-per-region 4 --geometry-fix --vm-face-mm2 2.659905216 --vch-w 1641.6 --hc-corr 1512 --die head --pairs 511 --mtp-seq --mtp-links 5"; DIE=head;;
  *) echo "unknown case"; exit 2;;
esac
echo "$A" > $M/options.txt
AO="$(echo $A | sed "s/--die $DIE//")"
say "start $CASE src=$S ($(cat $S/SOURCE_COMMIT 2>/dev/null)) die=$DIE"
cd $S
/srv/opentallas-scratch/admit.sh 40 -- python3 tools/dsrom_s81_fulldie.py real $A --work $M/a_real > $M/real_gen.log 2>&1 || { say "GEN_FAIL (real_gen.log)"; exit 1; }
say "GEN_DONE"
( mkdir -p $M/clock && python3 tools/budgets/extract_die.py --src $S --die s81r8_$DIE --s81-opts "$AO" --out $M/clock/model.json.gz > $M/clock/extract.log 2>&1 &&
  for g in htop hreg region; do python3 tools/budgets/clock_plan.py emit --die-model $M/clock/model.json.gz --group $g --name ${CASE}_$g --out $M/clock/$g > $M/clock/emit_$g.log 2>&1 && (cd $M/clock/$g && /srv/opentallas-scratch/admit.sh 40 -- bash run.sh > run.out 2>&1) & done; wait
  python3 tools/budgets/clock_plan.py record --die-model $M/clock/model.json.gz --case $M/clock/htop --case $M/clock/hreg --case $M/clock/region --out $M/clock/plan.json > $M/clock/record.log 2>&1 && gzip -kf $M/clock/plan.json
  say "clock plan: $(tail -3 $M/clock/record.log | tr '\n' ' ')" ) &
/srv/opentallas-scratch2/claude/s81-rerun/run_case.sh $M/a_real 24 40
[ "$(cat $M/a_real/run.log.exit 2>/dev/null)" = 0 ] || { say "PLACE_FAIL"; wait; exit 1; }
wait
PLAN=$M/clock/plan.json.gz; [ -f $PLAN ] || PLAN=$D81/m221pq_r3/clock/plan.json.gz
rm -rf $M/kit; mkdir -p $M/kit
python3 tools/s81/die_sta.py kit --gen-root $S --views-root $S --s81-opts "$AO" --die $DIE --out $M/kit --clock-plan $PLAN --index-out $M/kit/index.json > $M/kit/kit.log 2>&1 || say "KIT_FAIL (kit/kit.log)"
echo $S > $M/kit/src_root
say "kit: $(tail -1 $M/kit/kit.log) plan=$PLAN"
cd $M && /srv/opentallas-scratch/admit.sh 120 -- $D81/dietop_grt_sta.sh a_real grt kit 48 400
for c in tt ff ss; do echo "$c $(grep -E "^(worst slack|tns)" $M/grt/sta_$c.log 2>/dev/null | tr "\n" " ")"; done > $M/grt/summary.txt
say "GRT+STA: $(grep -h 'Total' $M/grt/grt.log 2>/dev/null | tail -1) | $(cat $M/grt/summary.txt | tr '\n' ' ')"
# rebudget forwarded-clock link dump (rebudget/s81_r3/run_fwd.sh recipe on this kit / SPEF)
RB=$M/rebudget; mkdir -p $RB; cp $S/tools/budgets/rebudget_links*.tcl $RB/ 2>/dev/null; cp /srv/opentallas-scratch/claude/rebudget/s81_r3/scope*.txt /srv/opentallas-scratch/claude/rebudget/s81_r3/rebudget_links_fwd.tcl $RB/ 2>/dev/null
for c in tt ff; do
  mm=$([ $c = tt ] && echo max || echo min)
  { sed -e "s#/kit/die.spef#/grt/die_grt.spef#g" $M/kit/sta_$c.tcl | grep -v "^report_"; echo "source /run/rebudget_links_fwd.tcl"; echo "ot_rb_fwd_clocks /run/scope_fwd.txt 833.333 85 50 $mm /kit/latency_$c.tcl"; echo "ot_rb_dump $mm /run/links_fwd_$c.tsv /run/scope_fwd.txt"; } > $RB/rbf_$c.tcl
  /srv/opentallas-scratch/admit.sh 35 -- docker run --rm --name mtpdie_rbf_${CASE}_$c --cpus=8 --memory=60g -v $RB:/run -v $M/grt:/grt:ro -v $M/kit:/kit:ro -v $S:$S:ro -w /run openroad/orfs:asap7lock \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v sta -no_init -exit /run/rbf_$c.tcl > /run/rbf_$c.log 2>&1; chmod -R a+rwX /run" &
  sleep 30
done
wait
say "links: $(grep -h OT_RB_DUMP $RB/rbf_*.log 2>/dev/null | tr '\n' ' ') | chain done"
