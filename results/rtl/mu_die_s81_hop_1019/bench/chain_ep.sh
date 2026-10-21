#!/bin/bash
# MU-DIE-S81/HOP: wait for the two cut_7 fleet jobs (ot-run clients), copy the run dirs back (no obj), run epcheck +
# the strict trace check on every run.  usage: chain_ep.sh <base ot-run pid> <rtl_tagdrop ot-run pid>
set -u
H=/home/ubuntu/scratch/mu-die-s81/hop; W=/home/ubuntu/wt/mu-die-s81-hop-1019; D=/srv/opentallas-scratch/claude/mu-die-s81-hop
exec >> $H/logs/chain_ep.log 2>&1
echo "$(date +%H:%M) chain_ep waiting on $*"
for p in "$@"; do while kill -0 $p 2>/dev/null; do sleep 60; done; done
mkdir -p $H/runs
for h in $(grep -ohE "RAN on [a-z0-9-]+" $H/logs/ot-run_base.log $H/logs/ot-run_rtl_tagdrop.log | awk '{print $3}' | sort -u) ot-epyc7 ot-epyc8; do
  timeout 600 rsync -a --exclude obj $h:$D/out_* $H/runs/ 2>/dev/null; done
tail -n 2 $H/logs/ot-run_base.log $H/logs/ot-run_rtl_tagdrop.log
cd $W
for x in R_cut_7_L0_hop012:out_base R_cut_7_L0_hop012_tagdrop:out_base_tagdrop R_cut_7_L0_hop012_wrongcopy:out_base_wrongcopy \
         R_cut_7_L0_hop012:out_rtl_tagdrop; do r=${x%:*}; o=${x#*:}
  timeout 900 python3 tools/s81_dv/dv_cut_replay.py epcheck --replay $H/R/$r --run $H/runs/$o --out $H/runs/$o/epcheck.json > $H/logs/epcheck_$o.log 2>&1
  timeout 900 python3 tools/s81_dv/dv_cut_replay.py check --replay $H/R/$r --run $H/runs/$o --out $H/runs/$o/check.json > $H/logs/check_$o.log 2>&1
  echo "$(date +%H:%M) $o: $(tail -n1 $H/logs/epcheck_$o.log | cut -c1-300) | $(tail -n1 $H/logs/check_$o.log) | $(grep -h 'TB_DV_SLICE\|rate' $H/runs/$o/status 2>/dev/null | tr '\n' ' ')"
done
echo "$(date +%H:%M) chain_ep DONE (expect: out_base PASS; out_base_tagdrop / out_base_wrongcopy / out_rtl_tagdrop FAIL)"
