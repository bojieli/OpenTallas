#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "$1")
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=rtl/dsrom_sys/s81_dv/svc_rs
COMMON=(-DOT_SVC_H8 -DOT_SVC_ALLQ -DRS_OBS -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -I$D --output-split 20000 --output-split-cfuncs 2000 -fno-inline --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O0)
SRC=(rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job_a0.sv rtl/dsrom_sys/s81_ph/svc/dsfd_svc_pc.sv "$O/att_trace.sv" "$O/sms_trace.sv" "$D/dsdv_svc_sx_hrow.sv" "$D/dsdv_svc_sx.sv" "$D/dsdv_svc_rs.sv")
for e in 0 1;do
 "$VL" --cc --build -j 4 --protect-lib rsc${e}_pl --top-module dsdv_svc_rs_c -Mdir "$O/pl$e" -GENTRY=$e -GSMT=0 -GH=8 "${COMMON[@]}" "${SRC[@]}" -v rtl/dsrom_sys/s81_ph/svc/dsfd_svc_c.sv > "$O/build$e.log" 2>&1 || { tail -25 "$O/build$e.log";exit 1; }
done
"$VL" --binary --top-module tb_join -Mdir "$O/obj" -j 4 "${COMMON[@]}" "$O/pl0/rsc0_pl.sv" "$O/pl1/rsc1_pl.sv" "$O/tb_join.sv" "$O/pl0/librsc0_pl.a" "$O/pl1/librsc1_pl.a" > "$O/build_tb.log" 2>&1
for l in 0 120;do
 "$O/obj/Vtb_join" +dir=$O +late=$l > "$O/run_late$l.log" 2>&1
 grep -E '^JOIN' "$O/run_late$l.log"
done
test "$(grep -c '^JOIN_PASS' "$O/run_late0.log")" = 16
test "$(grep -c '^JOIN_FAIL' "$O/run_late0.log")" = 0
grep -Eq '^JOIN_LOCAL.*lf1' "$O/run_late120.log"
