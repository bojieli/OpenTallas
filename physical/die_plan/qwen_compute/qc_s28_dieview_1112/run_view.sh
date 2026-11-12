#!/bin/bash
# QC-S28-DIEVIEW: route_supply + die_hop_scan + qc_die_audit on a plan in the hardlinked view tree (epyc9).
# usage: run_view.sh PLAN_NAME_IN_plan_of_record TAG
set -u
W=/srv/opentallas-scratch2/claude/qc-s28-dieview
cd $W/srcview
P=physical/die_plan/qwen_compute/plan_of_record/$1
T=$2
O=$W/out_$T; mkdir -p $O
nice -n 19 python3 -I tools/die_plan/route_supply.py $P --die qwen_compute --repo . --release-cache $W/release_cache.json --out $O/rs > $O/rs.stdout 2> $O/rs.stderr &
nice -n 19 python3 -I tools/die_plan/die_hop_scan.py $P $O/hops.json > $O/hops.stdout 2> $O/hops.stderr &
wait
nice -n 19 python3 -I $W/qc_die_audit.py $P $O/audit --rs $O/rs/route_supply_qwen_compute.tsv --cells $W/route_supply_cells.json --stages $W/kit_wave_stages.tsv --jobs 8 > $O/audit.stdout 2>&1
gzip -kf $O/audit/audit.json
sha256sum $P | cut -c1-12 > $O/plan.sha
echo DONE $T $(cat $O/plan.sha); cat $O/hops.stdout
