#!/bin/bash
# PATH-QC-SU btab_s6 stage A (ot-run job): structured re-CTS from btab_t2 3_place, + M5 pin-edge keep-out (pre_grt_s6b.tcl) (mscts_core, spec mscts_spec.tcl) ->
# GRT with s5 POST_GRT (DRV + max wire 100 + tap balance on GRT RC) -> per-corner pin-register I measured on the main
# FLOW RCX-calibrated estimate (cf/main/postcts_gate.tcl basis setRC_rcx_asap7.tcl) and BOUND (config OT_VCLK_TT/FF,
# constraint.sdc TT latency, sdc_lint.json insertion_ps/insertion_ff_ps; rebind to routed RCX at sign-off, F1)
# -> FF-only GRT hold repair + gate (hold_s6.sh).  No route here: route only after GEOM PASS (autopilot, run_s6.sh).
set -uo pipefail
K=$(cd "${1:-$(dirname "$0")}" && pwd); IMAGE=openroad/orfs:asap7lock; B=/work/run/results/asap7/kq_qfd_dv_s8x_btab_adj0/base
HB=$K/run/results/asap7/kq_qfd_dv_s8x_btab_adj0/base
echo "stageA start $(date -Is) host $(hostname) image $(docker image inspect --format '{{.Id}}' $IMAGE)" >> "$K/image.txt"
docker run --rm --name pqsu-btab-s6-ctsgrt-$$ --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-cts do-5_1_grt; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; exit \$rc" > "$K/run_ctsgrt.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
grep -h "S6P_FACE\|OT_MSCTS_BUILD\|OT_MSCTS_WINDOW\|S5_" "$K"/run/logs/asap7/*/base/4_1_cts.log "$K"/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | tail -20
[ $rc = 0 ] || { echo "stageA cts/grt rc $rc" >> "$K/image.txt"; exit $rc; }
cp "$HB/5_1_grt.odb" "$HB/5_1_grt_prehold.odb"; cp "$HB/route.guide" "$HB/route_prehold.guide"
for c in TT FF; do
  docker run --rm --name pqsu-btab-s6-meas-$c-$$ --cpus=4 --memory=12g --memory-swap=12g -v "$K":/work -w /work \
    -e OT_VCLK_TT=400 -e OT_VCLK_FF=400 -e OT_POSTCTS_TOL=1000 -e OT_POSTCTS_GRT=1 -e OT_CORNER=$c -e ODB=$B/5_1_grt.odb -e LAYER_PARASITICS_FILE=/work/cf/main/setRC_rcx_asap7.tcl $IMAGE \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/cf/main/postcts_gate.tcl" > "$K/meas_I_$c.log" 2>&1
  mv "$K/postcts_gate_$(echo $c | tr A-Z a-z).json" "$K/meas_I_$c.json" 2>/dev/null
done
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
ITT=$(python3 -c "import json;print('%.2f'%json.load(open('$K/meas_I_TT.json'))['pinreg_mean_ps'])") || exit 5
IFF=$(python3 -c "import json;print('%.2f'%json.load(open('$K/meas_I_FF.json'))['pinreg_mean_ps'])") || exit 5
echo "stageA bound I TT $ITT FF $IFF (main RCX-calibrated GRT estimate, pin registers)" | tee -a "$K/image.txt"
sed -i '/^export OT_VCLK_TT/d; /^export OT_VCLK_FF/d' "$K/config.mk"; printf 'export OT_VCLK_TT = %s\nexport OT_VCLK_FF = %s\n' "$ITT" "$IFF" >> "$K/config.mk"
sed -i "s/^set_clock_latency -source [0-9.]* \[get_clocks vclk\]/set_clock_latency -source $ITT [get_clocks vclk]/" "$K/constraint.sdc"
python3 - "$K" "$ITT" "$IFF" <<'PY'
import json,sys
k,t,f=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
p=k+'/sdc_lint.json'; d=json.load(open(p)); d['insertion_ps']=t; d['insertion_ff_ps']=f; json.dump(d,open(p,'w'),indent=1)
p=k+'/CORE_LATENCY.json'; d=json.load(open(p)); d.update(I_TT_bound_ps=t,I_FF_bound_ps=f,status="btab_s6: per-corner bound = structured-CTS GRT pin-register mean on the main RCX-calibrated basis; rebind to routed RCX at sign-off (F1, --ff-vclk auto)",lane="PATH-QC-SU"); json.dump(d,open(p,'w'),indent=1)
PY
grep -n "latency" "$K/constraint.sdc"
"$K/hold_s6.sh"; rc=$?
echo "stageA end $(date -Is) rc $rc" >> "$K/image.txt"; exit $rc
