#!/usr/bin/env bash
# HBM-SMBUDGET (10-19): fleet driver of the relative SM service end-to-end bench (smb_unit.py, tb_hbm_svg_rel_sm.sv).
#   run_smb_unit.sh REV SMWROOT BUNDLE OUTROOT JOB
# JOB: smoke  = base build, L00 only (positive)
#      pos    = base build, L00:0,L02:2,L14:14,head:0 back to back from ONE resident table + store (positive, must PASS)
#      late   = base build, L14:14 with the router ids 40 edges AFTER the first routed go (must FAIL: issuer late-go fault)
#      imut1 / imut2 / imut3 = issuer mutant builds (layer stride / expert id / row_off ignored), L14:14 (must FAIL)
#      xmut4  = xc without its RELOC stages, L14:14 (must FAIL)
# Archives REV's tools + RTL into OUTROOT/src on ot-epyc5 (holds SMWROOT and BUNDLE); each JOB builds its own Verilator
# object (work/obj_<defines>) and writes out/<JOB>.json + .log.
set -uo pipefail
REV=$1; SMW=$2; BUNDLE=$3; OUT=$4; JOB=$5; HOST=${HOST:-ot-epyc5}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV")
if [ "${NOSYNC:-0}" != 1 ]; then
ssh "$HOST" "mkdir -p $OUT/src $OUT/out $OUT/work && rm -rf $OUT/src/*" || exit 2
git -C "$WT" archive "$SHA" tools/hbm_layer_vehicle tools/hdc_golden_v41.py tools/hdc_golden.py tools/rtl_gpu_sm_exact.py \
  tools/rtl_hdc_v41_blockdot_campaign.py tools/hbm_svc_packed136_image.py tools/w19_payload_loader.py \
  rtl/hbm_accel/loader/service_native rtl/hbm_accel/sm/static rtl/hbm_accel/host_static_20261015/ot_static_run_target.sv \
  rtl/test/hbm_accel/svg_rel rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_relay.sv rtl/model_ready_hbm_r14 \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 \
  physical/asap7_memory_macros_v2/ot_sram_1r1w2c_8x285_m1 \
  results/rtl/hbm_ds_layer_tput_1018/fixtures/L00 results/rtl/hbm_ds_layer_tput_1018/fixtures/L02 \
  results/rtl/hbm_ds_layer_tput_1018/fixtures/L14 results/rtl/hbm_ds_layer_tput_1018/fixtures/head | ssh "$HOST" "tar -x -C $OUT/src" || exit 2
echo "$SHA" | ssh "$HOST" "cat > $OUT/src/REV"
fi
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
FIX=$OUT/src/results/rtl/hbm_ds_layer_tput_1018/fixtures
T="cd $OUT/src && $VL HDC_V41_ARITH=chunk8 python3 tools/hbm_layer_vehicle/smb_unit.py run --fix $FIX --smw $SMW --bundle $BUNDLE --work $OUT/work"
case "$JOB" in
  regional_smoke) J="$T --layers L00:0 --define SMB_SRAMFIFO,SMB_NATIVE_LANDING,SMB_NATIVE_RETURN --name regional_smoke --out $OUT/out/regional_smoke.json" ;;
  regional_mut2) J="$T --layers L00:0 --define SMB_SRAMFIFO,SMB_NATIVE_LANDING,SMB_NATIVE_RETURN,SMB_RETURN_MUT=2 --name regional_mut2 --out $OUT/out/regional_mut2.json" ;;
  native_smoke) J="$T --layers L00:0 --define SMB_SRAMFIFO,SMB_NATIVE_LANDING --name native_smoke --out $OUT/out/native_smoke.json" ;;
  native_mut2) J="$T --layers L00:0 --define SMB_SRAMFIFO,SMB_NATIVE_LANDING,SMB_FIFOMUT=2 --name native_mut2 --out $OUT/out/native_mut2.json" ;;
  sram_smoke) J="$T --layers L00:0 --define SMB_SRAMFIFO --name sram_smoke --out $OUT/out/sram_smoke.json" ;;
  sram_mut1) J="$T --layers L00:0 --define SMB_SRAMFIFO,SMB_FIFOMUT=1 --name sram_mut1 --out $OUT/out/sram_mut1.json" ;;
  sram_mut2) J="$T --layers L00:0 --define SMB_SRAMFIFO,SMB_FIFOMUT=2 --name sram_mut2 --out $OUT/out/sram_mut2.json" ;;
  smoke) J="$T --layers L00:0 --name smoke --out $OUT/out/smoke.json" ;;
  trace) J="$T --layers L00:0 --define TRACE --name trace --out $OUT/out/trace.json" ;;
  pos)   J="export SMB_PACE_NUM=${PNUM:-200}; $T --layers L00:0,L02:2,L14:14,head:0 --name pos --out $OUT/out/pos.json" ;;
  probe)  J="export SMB_PACE_ADD=${PADD:-8} SMB_BSCALE=${BSCALE:-1}; $T --layers L14:14 --name probe${PADD:-8}_${BSCALE:-1} --out $OUT/out/probe${PADD:-8}_${BSCALE:-1}.json" ;;
  l14)   J="$T --layers L14:14 --name l14 --out $OUT/out/l14.json" ;;
  late)  J="$T --layers L14:14 --mut late_ids --name late --out $OUT/out/late.json" ;;
  imut1) J="$T --layers L14:14 --define IMUT=1 --name imut1 --out $OUT/out/imut1.json" ;;
  imut2) J="$T --layers L14:14 --define IMUT=2 --name imut2 --out $OUT/out/imut2.json" ;;
  imut3) J="$T --layers L14:14 --define IMUT=3 --name imut3 --out $OUT/out/imut3.json" ;;
  xmut4) J="$T --layers L14:14 --define XMUT=4 --name xmut4 --out $OUT/out/xmut4.json" ;;
  *) echo "unknown JOB $JOB"; exit 2 ;;
esac
/home/ubuntu/bin/ot-run --mem ${MEM:-64} --threads 16 --dir "$OUT" -- bash -c "$J > $OUT/out/${LOGN:-$JOB}.log 2>&1; echo ${JOB}_RC \$?; tail -n 3 $OUT/out/${LOGN:-$JOB}.log"
echo "SMB_UNIT_DONE $JOB"
