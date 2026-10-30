#!/usr/bin/env bash
# DIE-HBM-30-O: build d30o = opstore_a_v1.py (d29d) -> station_resite (q_b113 types, reach 360) -> G0 + G0C
set -eu
R=/srv/opentallas-scratch2/claude/die-hbm-30/plan; W=/srv/opentallas-scratch2/claude/wt/die-hbm-27; D=$W/results/die_hbm_1029/hbm30/opstore
cd $R; rm -rf d30o_pre d30o_rs d30o
python3 $D/opstore_a_v1.py /srv/opentallas-scratch2/claude/die-hbm-29/plan/d29d d30o_pre /srv/opentallas-scratch2/claude/die-hbm-28k/out_opa/opstore_a_delta.json > $D/opstore_a_v1.log
systemd-run --user --scope -q -p MemoryMax=32G python3 $W/tools/die_plan/station_resite.py d30o_pre d30o_rs --types q_b113,q_b113__physical_v1 --reach 360 --jobs 16 > $D/station_resite.log 2>&1
cp -al d30o_pre d30o; for f in die_plan.json station_resite_report.json; do rm -f d30o/$f; cp d30o_rs/$f d30o/$f; done; rm -rf d30o_rs
rm -f d30o/g0_report.json
cp d30o_pre/opstore_a_v1_report.json $D/; cp d30o/station_resite_report.json $D/
sha256sum d30o/die_plan.json > $D/d30o_sha256.txt
systemd-run --user --scope -q -p MemoryMax=32G python3 $W/tools/die_plan/check.py d30o/die_plan.json > $D/d30o_g0.log 2>&1 || true
mv d30o/g0_report.json $D/d30o_g0_report.json
systemd-run --user --scope -q -p MemoryMax=32G python3 $W/tools/die_plan/check.py d30o/die_plan.json --completeness > $D/d30o_g0c.log 2>&1 || true
mv d30o/g0_report.json $D/d30o_g0c_report.json
tail -1 $D/d30o_g0.log; tail -1 $D/d30o_g0c.log
