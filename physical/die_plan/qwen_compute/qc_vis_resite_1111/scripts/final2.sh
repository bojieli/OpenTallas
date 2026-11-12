set -uo pipefail; W=/srv/opentallas-scratch2/claude/qc-vis-resite; cd $W
SC=/srv/opentallas-scratch2/claude/qc-event-s25/gate/src_s25fix/physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar_pv.json
echo apply start $(date)
nice -n 19 python3 -I scripts/apply_vis_resite.py planq/plan_qc99_s25.json delta_stm_vis10.json planq/stage_a.json --repo srcm --sidecar $SC sidecar_stage_a.json || exit 1
(cd srcm && nice -n 19 python3 -I tools/die_plan/collector_reattach.py ../planq/plan_qc99_s25.json ../planq/stage_a.json ../planq/plan_qc99_s25_vis.json ../reattach_report.json --sidecar ../sidecar_stage_a.json ../sidecar_pv_vis.json) || exit 1
cp sidecar_pv_vis.json srcb/physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar_pv.json
sha256sum planq/plan_qc99_s25_vis.json sidecar_pv_vis.json
bash scripts/gates.sh plan_qc99_s25_vis &
SRC=$W/srcb bash scripts/bind2.sh plan_qc99_s25_vis &
wait; echo final end $(date)
