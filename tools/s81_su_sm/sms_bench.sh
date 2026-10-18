#!/bin/bash
# S81U-2: exact bench of the per-slice SM share ot_s81_su_sms (smq + smh) vs the slab's SM stop (smt + 2 smh, DOP SRL+2).
#   bash tools/s81_su_sm/sms_bench.sh OUTDIR MUT [TI SEED NJOB]   (MUT 0 = base: PASS; 1, 2, 3, 5 = mutants: FAIL)
#   SMT=1 bash ...: the share's head subtree is the HARDENED regional-cluster composition dsfd_su_t_smh (-DSU_SMU_T:
#   4 lane quads dsfd_su_t_smhq + root dsfd_su_t_smhr over the hard leaf tops); MUT 6 = its root -> quad hop short.
# The verdict line "SMS PASS ..." / "SMS FAIL ..." is printed LAST and unconditionally.
set -u
OUT=$1; MUT=$2; TI=${3:-5}; SEED=${4:-1017}; NJOB=${5:-12}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SMTX=()
if [ "${SMT:-0}" = 1 ]; then
  D="$ROOT/rtl/dsrom_sys"
  SMTX=(-DSU_SMU_T "$D/s81_dv/su_sm/dsfd_su_t_smh.sv" "$D/s81_dv/su_sm/dsfd_su_t_smhq.sv" "$D/s81_dv/su_sm/dsfd_su_t_smhr.sv"
        "$D/s81_suhc/hier/dsfd_su_t_sm.sv")
fi
mkdir -p "$OUT"
S="$ROOT/rtl"
VL=${OPENTALLAS_TOOLS_ROOT:-$HOME/.local/opentallas-tools}/verilator-5.050/bin/verilator
[ -x "$VL" ] || VL=verilator
"$VL" --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_s81_su_sms -Mdir "$OUT/obj" -j 16 --unroll-count 4 -fno-dfg \
  -GMUT=$MUT -GTI=$TI -GSEED=$SEED -GNJOB=$NJOB -CFLAGS -O1 "${SMTX[@]}" \
  "$S/dsrom_sys/s81_dv/su_sm/test/tb_s81_su_sms.sv" "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_sms.sv" \
  "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_smq.sv" "$S/dsrom_sys/s81_dv/su_sm/ot_s81_su_smh.sv" \
  "$S/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv" "$S/hdc/ot_hdc_delay.sv" "$S/hdc/ot_hdc_fastfp_lat_f12.sv" \
  "$S/hdc/ot_hdc_fastfp.sv" "$S/hdc/ot_hdc_fp32_add_lat.sv" "$S/hdc/ot_hdc_fp32_f12.sv" "$S/hdc/ot_hdc_fp32_mul_lat.sv" \
  "$S/hdc/ot_hdc_prefix.sv" "$S/hdc/ot_hdc_sfu.sv" "$S/hdc/v41x/ot_dsrom_fp32_add_l6.sv" "$S/hdc/v41x/ot_dsrom_su_add6.sv" \
  "$S/hdc/v41x/ot_dsrom_su_f12.sv" "$S/hdc/v41x/ot_dsrom_su_fdiv_f12.sv" "$S/hdc/v41x/ot_dsrom_su_softmax_add6.sv" \
  "$S/hdc/v41x/ot_dsrom_su_softmax_add.sv" "$S/hdc/v41x/ot_dsrom_su_softmax_f12r.sv" \
  "$S/hdc/v41x/ot_dsrom_su_softmax_m9.sv" "$S/hdc/v41x/ot_hdc_v41x_sfu.sv" > "$OUT/build.log" 2>&1
rc=$?
if [ $rc -ne 0 ]; then tail -8 "$OUT/build.log"; echo "SMS FAIL MUT=$MUT build rc=$rc"; exit 1; fi
"$OUT/obj/Vtb_s81_su_sms" > "$OUT/run.log" 2>&1
grep -v "^SMS PASS\|^SMS FAIL" "$OUT/run.log" | tail -14
V=$(grep -E "^SMS (PASS|FAIL)" "$OUT/run.log" | tail -1)
[ -n "$V" ] || V="SMS FAIL MUT=$MUT no verdict"
echo "$V"
case "$V" in "SMS PASS"*) exit 0;; *) exit 1;; esac
