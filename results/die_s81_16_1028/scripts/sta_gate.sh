#!/bin/bash
# DIE-S81-16 (COORD 16:xx): die STA on main (CLK-INV-CAL-1 + cell-paths, 013a9a854) in GATE mode (--core-insertion view,
# signed --core-view where a signed view exists, fail closed elsewhere) next to DECLARED mode (same views, plan declared
# insertion where none matches).  usage: sta_gate.sh MAIN_WT PROOF PLAN OUT
MT=$1/tools/die_plan; PR=$2; PL=$3; O=$4; mkdir -p $O
V=$1/physical/die_plan/s81/cores/views; CV=""
for d in $V/*/; do m=$(basename $d); [ -f $d/${m}_tt.lib ] && [ -f $d/${m}_ff.lib ] && CV="$CV --core-view $m=$d"; done
echo "$CV" | tr ' ' '\n' | grep -c "=" > $O/core_views.n
STA="--corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --clock-cell inv2"
echo "START $(date) main $(git -C $1 rev-parse --short HEAD) proof $PR plan $(sha256sum $PL | cut -c1-12) views $(cat $O/core_views.n)" > $O/status
for M in view declared; do
  python3 $MT/die_sta_related.py $PR --plan $PL --out $O/sta_$M $STA $CV --core-insertion $M > $O/sta_$M.log 2>&1
  echo "$M rc $?" >> $O/status
  grep -E "proof (TT|FF) intra|kit-contract|core.insertion|missing|real.view|verdict" $O/sta_$M.log | cut -c1-260 | head -12 >> $O/status
done
# DIAGNOSTIC (not a gate): same views without pin-file provenance matching (S81 views carry no provenance.json)
python3 $MT/die_sta_related.py $PR --plan $PL --out $O/sta_declared_nomatch $STA $CV --no-core-view-match-pins --core-insertion declared > $O/sta_declared_nomatch.log 2>&1
echo "declared_nomatch (DIAGNOSTIC) rc $?" >> $O/status
grep -E "proof (TT|FF) intra" $O/sta_declared_nomatch.log | cut -c1-330 >> $O/status
python3 - $O >> $O/status <<'PY'
import json, sys
for M in ("view", "declared"):
    try:
        J = json.load(open(f"{sys.argv[1]}/sta_{M}/die_sta_related.json"))
    except Exception as e:
        print(M, "no json", e); continue
    s = J.get("summary", {}).get("intra", {})
    ci = J["corners"]["FF"].get("core_insertion", {})
    rv = J["corners"]["FF"]["classes"]["intra"].get("real_view", {})
    kc = J["corners"]["FF"]["classes"]["intra"].get("kit_contract_hold_ocv", {})
    print(f"SUMMARY {M}: TT setup {s.get('tt_setup_ps')} FF hold {s.get('ff_hold_ps')} verdict {s.get('verdict')} kit-contract "
          f"{s.get('ff_hold_kit_contract_ps')} (W need {s.get('kit_contract_window_needed_ps')}) kit+OCV need {kc.get('window_needed_ps')} "
          f"neg {kc.get('neg_pairs')} | early core taps {ci.get('early_core_taps')} source {ci.get('source')} | real-view pairs "
          f"{rv.get('pairs_with_real_endpoint')} hold {rv.get('worst_hold_slack_ps')}")
PY
echo "DONE $(date)" >> $O/status
