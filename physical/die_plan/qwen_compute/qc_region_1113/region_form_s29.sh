#!/bin/bash
# region_form_s29.sh IN_PLAN SIDE_IN OUT_PLAN SIDE_OUT [REPORT] : QC s29 REGION FORM (QC-REGION-1), one guarded step.
# Order in the s29 chain: CTLCAP head -> hand delta -> fw_v3 knee -> REGION FORM (this) -> R-REACH-1/4 -> START/monitor
# relays -> reset_steps -> strict bind.  exit 0 applied, 3 CONFLICT (nothing written), 4 post-check failed, 5 re-apply
# guard did not refuse.  Siblings (clock_merge / bind_requirements / kit_pricing) are copied from IN to OUT.
# RF = repo tree holding tools/die_plan/region_form.py (+ the link_htree schema keys) and the committed form files.
set -u
RF=${RF:-/srv/opentallas-scratch2/claude/qc-region-1/wt}
D=$RF/physical/die_plan/qwen_compute/plan_of_record
IN=$1; SIN=$2; OUT=$3; SOUT=$4; REP=${5:-${OUT%.json}.region_form.json}
echo "in $(sha256sum $IN | cut -c1-12) side $(sha256sum $SIN | cut -c1-12) tool $(sha256sum $RF/tools/die_plan/region_form.py | cut -c1-12) regions $(sha256sum $D/regions_s29.json | cut -c1-12) feed $(sha256sum $D/feed_s29.json | cut -c1-12) ca $(sha256sum $D/ca_s29.json | cut -c1-12)"
python3 -I -B $RF/tools/die_plan/region_form.py apply $IN $OUT --sidecar $SIN $SOUT \
  --regions $D/regions_s29.json --feed $D/feed_s29.json --ca $D/ca_s29.json --report $REP; rc=$?
[ $rc -eq 0 ] || { echo "STOP region_form rc=$rc (3 = CONFLICT, 4 = post-check)"; exit $rc; }
T=$(mktemp -d); python3 -I -B $RF/tools/die_plan/region_form.py apply $OUT $T/re.json --sidecar $SOUT $T/side_re.json \
  --regions $D/regions_s29.json --feed $D/feed_s29.json --ca $D/ca_s29.json >/dev/null; rc=$?; rm -rf $T
[ $rc -eq 3 ] && echo "RE-APPLY CONFLICT ok" || { echo "RE-APPLY rc=$rc (expected 3)"; exit 5; }
for k in clock_merge bind_requirements kit_pricing; do [ -f ${IN%.json}.$k.json ] && cp -p ${IN%.json}.$k.json ${OUT%.json}.$k.json; done
echo "DONE region form plan $(sha256sum $OUT | cut -c1-12) side $(sha256sum $SOUT | cut -c1-12)"
