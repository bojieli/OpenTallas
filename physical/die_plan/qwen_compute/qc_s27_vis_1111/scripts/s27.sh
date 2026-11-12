set -uo pipefail; W=/srv/opentallas-scratch2/claude/qc-vis-resite; cd $W
G26=/srv/opentallas-scratch2/claude/qc-event-s26/gate; RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
echo s27 start $(date)
[ -d srcs27 ] || cp -a $G26/src_s26b srcs27
mkdir -p planq27; for l in cells census cores die_io.json macro_pins sink_bins; do ln -sfn $(readlink -f $G26/planq/$l 2>/dev/null || readlink -f planq/$l) planq27/$l; done
cp $G26/planq/plan_qc99_s26.json planq27/plan_qc99_s26.json
cp $G26/src_s26b/$RT/sidecar_pv.json sidecar_s26.json
sha256sum planq27/plan_qc99_s26.json sidecar_s26.json | cut -c1-12
nice -n 19 python3 -I -B scripts/apply_vis_resite.py planq27/plan_qc99_s26.json delta_stm_vis10.json planq27/s27_stage_a.json --repo srcs27 --sidecar sidecar_s26.json sidecar_s27_stage_a.json || exit 1
(cd srcs27 && nice -n 19 python3 -I -B tools/die_plan/collector_reattach.py ../planq27/plan_qc99_s26.json ../planq27/s27_stage_a.json ../planq27/plan_qc99_s27.json ../reattach_s27.json --sidecar ../sidecar_s27_stage_a.json ../sidecar_s27.json) || exit 1
cp sidecar_s27.json srcs27/$RT/sidecar_pv.json
sha256sum planq27/plan_qc99_s27.json sidecar_s27.json
echo s27 composed $(date)
