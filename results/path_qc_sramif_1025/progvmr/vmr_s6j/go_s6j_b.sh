#!/bin/bash
# PATH-QC-PROGVMR vmr_s6j hold resume: the first hold step died at ot_ms_assign_corr (mscts_corr.tcl kept a stale "SE" key,
# its tap no longer exists after the split -> STA-2200 null object). Key removed; CTS/GRT/stageA bind kept (I TT 346.69 FF 267.90).
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); HB=$K/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base
cp "$HB/5_1_grt_prehold.odb" "$HB/5_1_grt.odb"; cp "$HB/route_prehold.guide" "$HB/route.guide"
sed -n "/^docker run --rm --name progvmr-vmr-s6j-probe/,\$p" "$K/go_s6j.sh" > "$K/.probe_tail.sh"
OT_S6_HOLD_MARGIN=0 "$K/hold_s6.sh"; rc=$?
echo "go_s6j_b hold m0+passes rc $rc $(date -Is)" >> "$K/image.txt"
"$K/f6_dump.sh" "$K" 5_1_grt > "$K/f6_grt.log" 2>&1
IMAGE=openroad/orfs:asap7lock; B=/work/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base
TT=$(sed -n "s/^export OT_VCLK_TT = //p" "$K/config.mk"); FF=$(sed -n "s/^export OT_VCLK_FF = //p" "$K/config.mk")
docker run --rm --name progvmr-vmr-s6j-probe-$$ --cpus=8 --memory=16g --memory-swap=16g -v "$K":/work -w /work -e RESULTS_DIR=$B -e OT_PROBE_ODB=5_1_grt.odb \
  -e OT_PROBE_LIB=ot_sram_1r1w_1024x256_m2_r2c2_ff.lib -e OT_PROBE_TAG=vmr_s6j_post -e OT_PROBE_FROM="pw16_data*" -e OT_RC_CAL=0.8,0.9 -e OT_MSCTS_SPEC=/work/mscts_spec.tcl \
  -e OT_MSCTS_CORR=/work/mscts_corr.tcl -e OT_VCLK_TT=$TT -e OT_VCLK_FF=$FF $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /work/pair_probe.tcl > /work/pair_probe_s6j.log 2>&1"
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "go_s6j_b probe done $(date -Is)" >> "$K/image.txt"
exit $rc
