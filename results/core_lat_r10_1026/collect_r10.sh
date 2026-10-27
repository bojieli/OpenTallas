#!/bin/bash
# S81-CORE-LAT-R10 collect (run on the kit's host): collect_r10.sh KITDIR  -> KITDIR/meas/meas_ck_{TT,FF}.tsv + summary
set -euo pipefail
K=$(cd "$1" && pwd); B=$(dirname "$0")
O=$(ls $K/run/results/asap7/*/base/5_1_grt.odb | tail -1); S=$(ls $K/run/results/asap7/*/base/4_cts.sdc $K/run/results/asap7/*/base/5_1_grt.sdc 2>/dev/null | tail -1)
mkdir -p $K/meas; cp $B/meas_ck_s81.tcl $K/meas/
for c in TT FF; do
  docker run --rm --memory=16g --memory-swap=16g -v $K:/work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
    ODB=${O/$K//work} SDC=${S/$K//work} OT_CORNER=$c OUT=/work/meas/meas_ck_$c.tsv openroad -exit /work/meas/meas_ck_s81.tcl" > $K/meas/meas_$c.log 2>&1
done
python3 - "$K" <<'PY'
import sys, statistics as st, json
k = sys.argv[1]; out = {}
for c, col in (("TT", 2), ("FF", 4)):          # TT: arrival_max_rise (setup basis); FF: arrival_min_rise (hold basis)
    v = [float(l.split("\t")[col]) * 1 for l in open(f"{k}/meas/meas_ck_{c}.tsv") if not l.startswith("#")]
    v = [x for x in v if x == x]
    out[c] = dict(n=len(v), mean=round(st.mean(v), 2), min=round(min(v), 2), max=round(max(v), 2), window=round(max(v) - min(v), 2))
json.dump(out, open(f"{k}/meas/summary.json", "w"), indent=1); print(json.dumps(out))
PY
chown -R $(id -u):$(id -g) $K/meas 2>/dev/null || true
