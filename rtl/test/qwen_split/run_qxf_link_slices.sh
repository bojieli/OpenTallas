#!/bin/bash
# QXF-LINK 2026-10-18 slice benches for TOKEN-XDIE-QWEN F1 / F2 / F4 (Verilator 5.050; iverilog where the bench is iverilog-only).
# usage (repository root, fleet): run_qxf_link_slices.sh OUTDIR    -> one line per case: <name> expect=<..> got=<..> -> OK|UNEXPECTED
#   F2  tb_native_attention_static_ctl (real programme + static ctl + codec): MODE 0 PASS with the namespace STATUS word,
#       MODES 1..8 detect their fault, MUT 3 (legacy STATUS 0) FAILS "STATUS corrupt"; the result-face benches (both faces)
#       MODE 0 PASS with the namespace STATUS word.
#   F1  run_native59_dv_service_bench.sh (dv service vs the old compute service, bit-exact; the Q window change keeps it).
#   F4  test_d2d_txdp.py (compiler TXDP law, parametric masters, committed image == compiler); run_d2d_program.sh (DRV 0 / 1,
#       the masters built with the compile's txdp.svh, production image check) and run_d2d_dies.sh.
set -u
OUT=$1; mkdir -p "$OUT"
R=$(pwd)
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
V=verilator
S=rtl/qwen_sys/split_20261014
CTL=("$S/qkd_native_attention_record.sv" "$S/qkd_native59_command_guard.sv" "$S/qkd_native59_descriptor_producer.sv"
     "$S/qkd_native_attention_static_ctl.sv" "$S/qkd_native_attention_programme.sv")
res() { echo "$1 expect=$2 got=$3 -> $([ "$2" = "$3" ] && echo OK || echo UNEXPECTED)"; }
vb() { # name top -G... -- sources
  local n=$1 top=$2; shift 2
  $V --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --top-module "$top" --Mdir "$OUT/$n.obj" "$@" \
    > "$OUT/$n.build.log" 2>&1 || { echo "$n BUILD_FAIL"; grep -m5 %Error "$OUT/$n.build.log"; return 1; }
}
sha256sum "${CTL[@]}" "$S/qkd_attn_service_root.sv" "$S/qkd_attn_result_face.sv" "$S/qkd_attn_result_face_s.sv" \
  rtl/test/qwen_split/tb_native_attention_static_ctl.sv rtl/test/qwen_split/tb_qkd_attn_result_face.sv \
  rtl/test/qwen_split/tb_qkd_attn_result_face_s.sv rtl/qwen_split/qfd_native59_dv_service.sv \
  rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh \
  tools/qwen_split/d2d_link_calendar.py tools/qwen_split/d2d_cal_seq_image.py tools/qwen_split/d2d_pinreg_gen.py \
  tools/qwen_split/test_d2d_txdp.py tools/qwen_split/d2d_cal_image_production.sh "$0" > "$OUT/source.sha256"
# ---- F2: static ctl
for mut in 0 3; do
  if vb ctl_m$mut tb_native_attention_static_ctl -GMUT=$mut "${CTL[@]}" rtl/test/qwen_split/tb_native_attention_static_ctl.sv; then
    for mode in 0 1 2 3 4 5 6 7 8; do
      [ $mut = 3 ] && [ $mode != 0 ] && continue
      "$OUT/ctl_m$mut.obj/Vtb_native_attention_static_ctl" +MODE=$mode > "$OUT/ctl_m${mut}_mode$mode.log" 2>&1
      got=FAIL; grep -q '^PASS' "$OUT/ctl_m${mut}_mode$mode.log" && got=PASS
      exp=PASS; [ $mut = 3 ] && exp=FAIL
      res "f2_static_ctl_mut${mut}_mode$mode" $exp $got; [ $got = FAIL ] && grep -m1 -i 'fatal\|STATUS' "$OUT/ctl_m${mut}_mode$mode.log" | sed 's/^/    /'
    done
  fi
  rm -rf "$OUT/ctl_m$mut.obj"
done
for f in result_face result_face_s; do
  if vb face_$f tb_qkd_attn_$f "${CTL[@]}" "$S/qkd_attn_service_root.sv" "$S/qkd_attn_$f.sv" rtl/test/qwen_split/tb_qkd_attn_$f.sv; then
    "$OUT/face_$f.obj/Vtb_qkd_attn_$f" +MODE=0 > "$OUT/face_$f.log" 2>&1
    got=FAIL; grep -q '^PASS' "$OUT/face_$f.log" && got=PASS; res "f2_tb_qkd_attn_${f}_mode0" PASS $got
  fi
  rm -rf "$OUT/face_$f.obj"
done
# ---- F1: native59 regression (equivalence vs the old compute service + its mutants)
bash rtl/test/qwen_split/run_native59_dv_service_bench.sh "$OUT/n59" > "$OUT/n59.log" 2>&1; rc=$?
res f1_native59_dv_service_bench PASS $([ $rc = 0 ] && echo PASS || echo FAIL); sed 's/^/    /' "$OUT/n59.log" | head -12
# ---- F4: compiler TXDP + D2D benches
python3 tools/qwen_split/test_d2d_txdp.py > "$OUT/test_d2d_txdp.log" 2>&1
res f4_test_d2d_txdp PASS $(grep -q TEST_D2D_TXDP_PASS "$OUT/test_d2d_txdp.log" && echo PASS || echo FAIL)
for drv in 0 1; do
  BACKEND=verilator DRV=$drv JOBS=4 bash rtl/test/qwen_split/run_d2d_program.sh "$OUT/d2d_program_drv$drv" > "$OUT/d2d_program_drv$drv.log" 2>&1; rc=$?
  res f4_d2d_program_drv$drv PASS $([ $rc = 0 ] && echo PASS || echo FAIL); tail -3 "$OUT/d2d_program_drv$drv.log" | sed 's/^/    /'
  rm -rf "$OUT/d2d_program_drv$drv/obj"
done
BACKEND=verilator JOBS=4 bash rtl/test/qwen_split/run_d2d_program.sh "$OUT/d2d_program_mut3" 3 > "$OUT/d2d_program_mut3.log" 2>&1; rc=$?
res f4_d2d_program_mut3_producer_late FAIL $([ $rc = 0 ] && echo PASS || echo FAIL); rm -rf "$OUT/d2d_program_mut3/obj"
bash rtl/test/qwen_split/run_d2d_dies.sh "$OUT/d2d_dies" > "$OUT/d2d_dies.log" 2>&1; rc=$?
res f4_d2d_dies PASS $([ $rc = 0 ] && echo PASS || echo FAIL); tail -2 "$OUT/d2d_dies.log" | sed 's/^/    /'
