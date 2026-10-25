#!/bin/bash
# PATH-QC-PROGVMR vmr_s6j (ot-run job): vmr_s6i 3_place (unchanged: MIF=1, F6 anchors) -> STRUCTURAL clock change only:
# SE tap split into SEa/SEb (mscts_spec.tcl) -> CTS + GRT -> stageA per-corner pin-reg I re-measure + bind (main RCX basis,
# as go_s6i_b) -> FF-only GRT hold at margin 0 + up to 2 post-DPL passes (hold_s6.sh / hold_pass.tcl, unchanged) -> F6 dump
# -> fresh-session pair probe (pair_probe.tcl, fresh GRT; same basis as the s6i probe: s6i fresh = FF -16.23/164).
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); IMAGE=openroad/orfs:asap7lock; B=/work/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base
HB=$K/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base
echo "go_s6j start $(date -Is) host $(hostname)" >> "$K/image.txt"
docker run --rm --name progvmr-vmr-s6j-cg-$$ --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-cts do-5_1_grt; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; exit \$rc" > "$K/run_cg.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "go_s6j cts/grt rc $rc $(date -Is)" >> "$K/image.txt"; [ $rc = 0 ] || exit $rc
grep -h "OT_MSCTS_TRUNK\|OT_MSCTS_BUILD sinks\|OT_MSCTS_TAP\|OT_MSCTS_WINDOW" "$K/run/logs/asap7/kq_qfd_dv_s8x_vmr_rw60/base/"{4_1_cts,5_1_grt}.log > "$K/s6j_taps.txt" 2>/dev/null
cp "$HB/5_1_grt.odb" "$HB/5_1_grt_prehold.odb"; cp "$HB/route.guide" "$HB/route_prehold.guide"
for c in TT FF; do
  docker run --rm --name progvmr-vmr-s6j-meas-$c-$$ --cpus=4 --memory=12g --memory-swap=12g -v "$K":/work -w /work \
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
p=k+'/CORE_LATENCY.json'; d=json.load(open(p)); d.update(I_TT_bound_ps=t,I_FF_bound_ps=f,status="vmr_s6j: per-corner bound = structured-CTS GRT pin-register mean on the main RCX-calibrated basis; rebind to routed RCX at sign-off (F1, --ff-vclk auto)",lane="PATH-QC-PROGVMR"); json.dump(d,open(p,'w'),indent=1)
PY
OT_S6_HOLD_MARGIN=0 "$K/hold_s6.sh"; rc=$?
echo "go_s6j hold m0+passes rc $rc $(date -Is)" >> "$K/image.txt"
"$K/f6_dump.sh" "$K" 5_1_grt > "$K/f6_grt.log" 2>&1
TT=$(sed -n 's/^export OT_VCLK_TT = //p' "$K/config.mk"); FF=$(sed -n 's/^export OT_VCLK_FF = //p' "$K/config.mk")
docker run --rm --name progvmr-vmr-s6j-probe-$$ --cpus=8 --memory=16g --memory-swap=16g -v "$K":/work -w /work -e RESULTS_DIR=$B -e OT_PROBE_ODB=5_1_grt.odb \
  -e OT_PROBE_LIB=ot_sram_1r1w_1024x256_m2_r2c2_ff.lib -e OT_PROBE_TAG=vmr_s6j_post -e OT_PROBE_FROM='pw16_data*' -e OT_RC_CAL=0.8,0.9 -e OT_MSCTS_SPEC=/work/mscts_spec.tcl \
  -e OT_MSCTS_CORR=/work/mscts_corr.tcl -e OT_VCLK_TT=$TT -e OT_VCLK_FF=$FF $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /work/pair_probe.tcl > /work/pair_probe_s6j.log 2>&1"
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "go_s6j probe done $(date -Is)" >> "$K/image.txt"
exit $rc
