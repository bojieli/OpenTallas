#!/bin/bash
# PATH-QC-SRAMIF vmr_s6i resume: restore pre-hold GRT DB, re-measure + bind per-corner pin-register I (main RCX basis, as btab/prog stageA), FF-only GRT hold with margin 5 (margin 0 left -3.15/41 after DPL legalisation; GEOM-REVIEW 06:5x keeps hold_margin 5), F6 dump.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); IMAGE=openroad/orfs:asap7lock; B=/work/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base
HB=$K/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base
echo "go_s6i_b start $(date -Is) host $(hostname)" >> "$K/image.txt"
cp "$HB/5_1_grt_prehold.odb" "$HB/5_1_grt.odb"; cp "$HB/route_prehold.guide" "$HB/route.guide"
for c in TT FF; do
  docker run --rm --name sramif-vmr-s6i-meas-$c-$$ --cpus=4 --memory=12g --memory-swap=12g -v "$K":/work -w /work \
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
p=k+'/CORE_LATENCY.json'; d=json.load(open(p)); d.update(I_TT_bound_ps=t,I_FF_bound_ps=f,status="vmr_s6i: per-corner bound = structured-CTS GRT pin-register mean on the main RCX-calibrated basis; rebind to routed RCX at sign-off (F1, --ff-vclk auto)",lane="PATH-QC-SRAMIF"); json.dump(d,open(p,'w'),indent=1)
PY
grep -n "latency" "$K/constraint.sdc"
OT_S6_HOLD_MARGIN=5 "$K/hold_s6.sh"; rc=$?
echo "go_s6i_b hold rc $rc $(date -Is)" >> "$K/image.txt"
"$K/f6_dump.sh" "$K" 5_1_grt > "$K/f6_grt.log" 2>&1
exit $rc
