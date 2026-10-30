#!/bin/bash
# DIE-HEAD-40: Codex legal88 chain after build_event_stable6 (canonicalize ROOT88 -> native enrich + boot account -> raw START meta -> G0C -> review).
# usage: chain.sh TAG  (needs src25${TAG}_codex)
set -e; T=$1; cd /srv/opentallas-scratch2/claude/die-head-40/event
OT="$HOME/.local/bin/ot-run --hosts localhost --mem 8 --threads 1 --dir $PWD --"
$OT python3 canonicalize_current88b.py meta_tools src25${T}_codex src25${T}_final > canon_$T.otrun.log 2>&1
python3 enrich_final_native.py src25${T}_final src25${T}_native /srv/opentallas-scratch2/claude/codex-head-collect-1030/parent_sizing/domain_census_v2 > enrich_$T.log 2>&1
python3 account_boot88_v2.py src25${T}_native >> enrich_$T.log 2>&1
$OT python3 ncd_tools/tools/s81_head/head_raw_start_contract.py src25${T}_native/source_plan.json src25${T}_native/source_sidecar.json src25${T}_native/start_stages_src25q.json src25${T}_native/s81_head_top.sv --out meta_$T > meta_$T.otrun.log 2>&1
cp -r src25${T}_native/core_pins src25${T}_native/native_domains meta_$T/; cp src25${T}_native/serdes_parent_tree_prep.json meta_$T/ 2>/dev/null || true
set +e
$OT python3 ncd_tools/tools/die_plan/check.py meta_$T/source_plan.json --landing meta_$T/source_sidecar.json --completeness --out meta_${T}_g0 > g0_$T.otrun.log 2>&1
$OT python3 plan_review.py meta_$T/source_plan.json review_$T --tools ncd_tools/tools/die_plan --g0 meta_${T}_g0/g0_report.json > review_$T.otrun.log 2>&1
echo CHAIN_DONE_$T $(date)
