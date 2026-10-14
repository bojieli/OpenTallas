#!/bin/bash
# FUSED.QDQ WIDE throughput bench (tput-gate-1010): tb_hgi_quant_wide_tput (Verilator): m0 PASS; m1 (header A bit) and
# w1 (wide tag mutant) FAIL; w3 (forced packet path) PASS (control).
# usage (from the repo root): tools/hgi_unit_tput/run_qdq.sh <vectors dir> <out dir>
# env: OVERLAP (0 historical serial issuer; 1 issue on ready independently of completions), QDQ_DEFS (extra Verilator defines, e.g. +define+OT_QW_DEC3 for the 3-tile decoder), SERIAL_SHAPE (0|1), WQ (0|1|2: 1 flat lane-quad ot_hgi_quant_wide_q, 2 hierarchical ot_hgi_quant_wide_h, 3 opt-in record-overlap), VERILATOR
set -euo pipefail
vec=$(realpath "$1"); out=$(realpath -m "$2"); mkdir -p "$out"
VL=${VERILATOR:-verilator}
"$VL" --version > "$out/tool_version"
hdc=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv
     rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv)
src=("${hdc[@]}" physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv
     rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/ot_hgi_quant_decode.sv
     rtl/hbm_accel/generic/ot_hgi_quant_vm_transport.sv rtl/hbm_accel/generic/ot_hgi_quant_record.sv
     rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/ot_hgi_quant_wide.sv rtl/hbm_accel/generic/ot_hgi_quant_wide_q.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_rq.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_wq.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_dec.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_dec3.sv rtl/hbm_accel/generic/qw/ot_hgi_quant_wide_h.sv rtl/hbm_accel/generic/qw/ot_hgi_quant_wide_ov.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_ovc.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_ovd.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_ovg.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_ovw.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_ovr.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_ovrow.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_hh.sv rtl/hbm_accel/generic/qw/ot_hgi_qw_lg2.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/hbm_accel/generic/ot_hgi_quant_unit.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     rtl/test/hbm_accel/generic/tb_hgi_quant_wide_tput.sv)
cfg=("m0:-GMUT=0 -GWMUT=0" "m1:-GMUT=1 -GWMUT=0" "w1:-GMUT=0 -GWMUT=1" "w3:-GMUT=0 -GWMUT=3")
if [ "${WQ:-0}" = 3 ]; then cfg+=("sk:-GMUT=0 -GWMUT=0 -GACKSKEW=40" "r2:-GMUT=0 -GWMUT=2 -GACKSKEW=40"); fi
for c in "${cfg[@]}"; do t=${c%%:*}; g=${c#*:}
  "$VL" --binary --timing -O3 -j 8 -Wno-fatal -Wno-lint -Wno-style ${QDQ_DEFS:-} $g -GSERIAL_SHAPE=${SERIAL_SHAPE:-0} -GWQ=${WQ:-0} -GOVERLAP=${OVERLAP:-0} -GDEPENDENCY=${DEPENDENCY:-0} \
    --top-module tb_hgi_quant_wide_tput -Mdir "$out/$t.obj" -o sim "${src[@]}" > "$out/$t.build" 2>&1 &
done
wait
for c in "${cfg[@]}"; do t=${c%%:*}
  set +e; "$out/$t.obj/sim" +DIR="$vec" > "$out/$t.log" 2>&1; rc=$?; set -e; echo "$rc" > "$out/$t.rc"
done
ok=1
positive=(m0 w3); negative=(m1 w1); if [ "${WQ:-0}" = 3 ]; then positive+=(sk); negative+=(r2); fi
for t in "${positive[@]}"; do [ "$(cat "$out/$t.rc")" = 0 ] || ok=0; grep -q "PASS HGI_QDQ_WIDE_TPUT" "$out/$t.log" || ok=0; done
for t in "${negative[@]}"; do [ "$(cat "$out/$t.rc")" != 0 ] || ok=0; grep -q "PASS HGI_QDQ_WIDE_TPUT" "$out/$t.log" && ok=0; grep -qE "FATAL|MISMATCH" "$out/$t.log" || ok=0; done   # a mutant must FAIL in simulation, not in the build
[ $ok = 1 ] && echo "QDQ_WIDE_TPUT GATE PASS (positive cases PASS, negative cases FAIL)" | tee "$out/gate" || { echo "QDQ_WIDE_TPUT GATE FAIL" | tee "$out/gate"; exit 1; }
