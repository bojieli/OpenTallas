#!/bin/bash
# kit_face_bench.sh OUT MODE (KV-AHUB 10-19): closure-job bench for the SAFE AHUB kits (qkd_ahub_sfa / qkd_ahub_sfb) whose
# synthesis source is the fixed-GEN7 face-copy native netlist rtl/hdc/nearhbm/qkd_ahub_static_dw_safe_face_native.v
# (4b05445f7, AP_OFS ffd9ffdaffd8ffd8 / FR_OFS -7 / Z_IN_STRIDE 4).  Lockstep vs the actual RTL source on the 7 production
# calendars (tools/qwen_kv_die/ahub_safe/native_bench.sh, Verilator 5.050).  Fleet only.
#   MODE m0      the kit source                                  -> expect PASS
#   MODE face_d  committed AM face-copy D-inversion netlist      -> expect FAIL (witness negative_witnesses/face_D_invert.log)
#   MODE sticky  committed sticky-RESETN netlist, reset phase 1350 -> expect FAIL (witness negative_witnesses/sticky_RESETN.log)
set -u
O=$(realpath -m "$1"); MODE=${2:-m0}
mkdir -p "$O"
NW=results/arch/kv_ahub_face_copy_1019/negative_witnesses
case "$MODE" in
  m0) export AHUB_NATIVE_SOURCE=rtl/hdc/nearhbm/qkd_ahub_static_dw_safe_face_native.v ;;
  face_d) zcat "$NW/face_D.v.gz" > "$O/face_D.v"; export AHUB_NATIVE_SOURCE="$O/face_D.v" ;;
  sticky) zcat "$NW/sticky_RESETN.v.gz" > "$O/sticky_RESETN.v"; export AHUB_NATIVE_SOURCE="$O/sticky_RESETN.v" ;;
  *) echo "AHUB_DW FAIL unknown mode $MODE"; exit 2 ;;
esac
if [ "$MODE" = m0 ]; then
  echo "$(sha256sum "$AHUB_NATIVE_SOURCE")"
  echo "57a9e0f37cb7a6ac77eb1c9714500030e4736f6cfa0c9c22a28b5d790c3976e1  rtl/hdc/nearhbm/qkd_ahub_static_dw_safe_face_native.v" | sha256sum -c - \
    || { echo "AHUB_DW FAIL kit source hash"; exit 1; }
fi
bash tools/qwen_kv_die/ahub_safe/native_bench.sh "$O" 0
rc=$?
if [ "$MODE" = sticky ]; then
  # the default run has no reset pulse in the occupied window; the witness is the phase-1350 reset (80-edge hold / drain)
  [ -x "$O/obj_m0/Vtb_qkd_ahub_static_dw_safe" ] || { echo "AHUB_DW FAIL no sticky build"; exit 1; }
  "$O/obj_m0/Vtb_qkd_ahub_static_dw_safe" +reset_phase=1350 > "$O/run_sticky.log" 2>&1
  grep -E '^AHUB_DW FAIL mut=[0-9]+ first' "$O/run_sticky.log" | head -2
  line=$(grep -E '^AHUB_DW (PASS|FAIL mut=[0-9]+ errors)' "$O/run_sticky.log" | tail -1)
  echo "${line:-AHUB_DW FAIL no verdict line}"
  case "$line" in "AHUB_DW PASS"*) exit 0;; *) exit 1;; esac
fi
exit $rc
