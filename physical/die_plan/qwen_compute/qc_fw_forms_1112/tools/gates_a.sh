#!/bin/bash
# QC-FW-FORMS 11-12 gates A (epyc9, nice): schema / G0 / station_lint / route_supply on s25 (base) and the fw plan.
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-fw-forms; S=$W/src; G=$W/gate; mkdir -p $G
B=$S/physical/die_plan/qwen_compute/plan_of_record/plan_qc99_s25.json; N=$W/cmp/c3.json
echo "gates_a start $(date) base=$(sha256sum $B|cut -c1-12) fw=$(sha256sum $N|cut -c1-12) check.py=$(sha256sum $S/tools/die_plan/check.py|cut -c1-12)" > $G/gates_a.log
for tag in base fw; do
  PL=$B; [ $tag = fw ] && PL=$N
  ( cd $S && nice -n 19 python3 -I -c "import sys; sys.path.insert(0, 'tools/die_plan'); import schema; sys.exit(schema.main(['schema.py', 'validate', '$PL']))" > $G/schema_$tag.log 2>&1; echo "rc=$?" >> $G/schema_$tag.log ) &
  ( mkdir -p $G/g0_$tag; cd $S && nice -n 19 python3 -I tools/die_plan/check.py $PL --out $G/g0_$tag --quiet > $G/g0_$tag.log 2>&1; echo "rc=$?" >> $G/g0_$tag.log ) &
  ( cd $S && nice -n 19 python3 -I tools/die_plan/station_lint.py $PL --tsv $G/station_lint_$tag.tsv > $G/station_lint_$tag.log 2>&1; echo "rc=$?" >> $G/station_lint_$tag.log ) &
  ( mkdir -p $G/rs_$tag; cd $S && nice -n 19 python3 -I tools/die_plan/route_supply.py $PL --die qwen_compute --repo $S --types slw_fw_v3,sle_fw_v3,slw_fw_v1__clf51c11d8__clc7ddab13 --out $G/rs_$tag > $G/rs_$tag.log 2>&1; echo "rc=$?" >> $G/rs_$tag.log ) &
done
wait
echo "gates_a end $(date)" >> $G/gates_a.log
