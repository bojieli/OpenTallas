set -uo pipefail; W=/srv/opentallas-scratch2/claude/qc-vis-resite; cd $W
RT=physical/die_plan/qwen_compute/qc_start_1106/runtime; G=/srv/opentallas-scratch2/claude/dq97/taps1111/bind_gr
echo s27full start $(date)
nice -n 19 python3 -I -B scripts/apply_vis_resite.py planq27/plan_qc99_s26.json delta_stm_vis.json planq27/s27_stage_a.json --repo srcs27 --sidecar sidecar_s26.json sidecar_s27_stage_a.json || exit 1
(cd srcs27 && nice -n 19 python3 -I -B tools/die_plan/collector_reattach.py ../planq27/plan_qc99_s26.json ../planq27/s27_stage_a.json ../planq27/plan_qc99_s27.json ../reattach_s27.json --sidecar ../sidecar_s27_stage_a.json ../sidecar_s27.json) || exit 1
cp sidecar_s27.json srcs27/$RT/sidecar_pv.json
sha256sum planq27/plan_qc99_s27.json sidecar_s27.json
SRC=$W/srcs27 PQ=planq27 bash scripts/gates27.sh plan_qc99_s26 plan_qc99_s27 &
( P=plan_qc99_s27; S=$W/srcs27; PL=$W/planq27/$P.json; O=$W/bind_$P; L=$W/bind_$P.log
  echo "bind start $(date) plan=$(sha256sum $PL|cut -c1-12) sidecar=$(sha256sum $S/$RT/sidecar_pv.json|cut -c1-12) bind.py=$(sha256sum $S/tools/die_plan/bind.py|cut -c1-12)" > $L
  rm -rf $O; mkdir -p $O; for f in asbuilt.json asbuilt.yosys.log asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json provenance_elab.json; do cp -a $G/$f $O/$f; done
  s=$(date +%s); cd $S && timeout -s ABRT 5400 nice -n 19 python3 -I -B -X faulthandler tools/die_plan/bind.py bind $PL --out $O --asbuilt $S/$RT/asbuilt_sw2_pv.json --strict >> $L 2>&1
  echo "BIND_RC=$? wall=$(( $(date +%s)-s )) s end $(date)" >> $L ) &
wait; echo s27full end $(date)
