#!/bin/bash
# CLAUDE DS-INTEGRATION combined-lever L20 bench: the run plan as executed on ot-epyc2 (one pinned snapshot).
#   S = the snapshot (git archive of the branch commit in SOURCE_COMMIT, plus the LA6 su_norm overlay in OVERLAY:
#       the measured LA6 lever's RTL, bench and tool are preserved in la6_inputs/ and are NOT on main's rtl/)
#   W = the work dir; every step writes W/<step>.json, `record` joins them and exits nonzero on any failure.
set -u
R=/srv/opentallas-scratch2/scratch/claude/dsrom-combined
S=$R/src_${1:?snapshot sha}
W=$R/run
A=/srv/opentallas-scratch/admit.sh
T=tools/dsrom_combined_l20.py
CASES=$R/cases/su_cases.pkl                 # sha256 1e00804b3cb6a348... (tools/dsrom_1m_su.py SU case set)
mkdir -p $W/logs
cd $S
st() { echo "$(date -Is) $*" >> $R/MANIFEST; }
st "plan start snapshot $(cat SOURCE_COMMIT)"
python3 $T static --work $W > $W/logs/static.log 2>&1; st "static rc=$?"
python3 $T edges --work $W --cases $CASES > $W/logs/edges.log 2>&1; st "edges rc=$?"
# field: v9 spine at L20 -- PQ 0 (control), PQ 0 + DS q-element QX 9 (new combination), PQ 1 + q-element (expected
# NOT buildable); PQ 1 alone is the committed v9 record (RTL pins current, no replay)
for cfg in pq1_q9 pq0 pq0_q9; do
  ( $A 24 -- python3 $T field --cfg $cfg --work $W --jobs 10 > $W/logs/field_$cfg.log 2>&1; st "field $cfg rc=$?" ) &
done
# su_norm LA6 (the overlay): every prepared case (L0 / L3 / L20 / L24 / head + stress), RTL FP units at N 64 and the
# DPI FP stand-ins at full lane count (the lever's cycle record), LA 6
( python3 tools/dsrom_su_norm.py prep --cases $CASES --out $W/norm > $W/logs/norm_prep.log 2>&1
  for v in hc q kv; do
    $A 24 -- python3 tools/dsrom_su_norm.py run --out $W/norm --variant $v --fp rtl --n 64 --la 6 > $W/logs/norm_${v}_rtl.log 2>&1; st "norm $v rtl rc=$?"
    $A 32 -- python3 tools/dsrom_su_norm.py run --out $W/norm --variant $v --fp dpi --la 6 > $W/logs/norm_${v}_dpi.log 2>&1; st "norm $v dpi rc=$?"
  done ) &
python3 $T compose --work $W > $W/logs/compose.log 2>&1; st "compose rc=$?"
wait
python3 $T units --work $W > $W/logs/units.log 2>&1; st "units rc=$?"
python3 $T record --work $W --out $W/record --source-commit "$(cat SOURCE_COMMIT)" > $W/logs/record.log 2>&1; st "record rc=$?"
st DONE
