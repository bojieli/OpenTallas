#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 tools/hbm_static_attention/prepare_QP_front.py --out "$out/vectors"
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_QP_fields_host_front --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_physical_host_program_front_fields.sv rtl/hdc/v41x/static/ot_hbm_attn_physical_program_query_front_fields.sv \
 rtl/hdc/v41x/static/ot_hbm_attn_physical_program_consumer.sv rtl/hdc/v41x/static/ot_hbm_attn_physical_event_program.sv rtl/hdc/v41x/static/ot_hbm_attn_query_prefetch.sv rtl/hdc/v41x/static/ot_hbm_attn_p_prefetch_fields.sv \
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_calendar_host_static.sv \
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_static.sv \
 rtl/hbm_accel/generic/loader/ot_hgi_loader_cp.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
 rtl/test/hbm_accel/generic/tb_hbm_attn_QP_fields_host_front.sv > "$out/build.log" 2>&1
for profile in 0 1 2 3;do
 "$out/obj/sim" +DIR="$out/vectors" +MUT=0 +PROFILE=$profile > "$out/profile$profile.log" 2>&1
 grep -q "PASS ATT_QP_HOST_PROGRAM_FRONT" "$out/profile$profile.log"
done
for m in 1 2 3;do
 set +e;"$out/obj/sim" +DIR="$out/vectors" +MUT=$m +PROFILE=0 > "$out/m$m.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/m$m.rc"
 grep -qE 'ATT_FRONT (source/calendar fault|wrong actual event profile|actual NE calendar/request mismatch)' "$out/m$m.log"
done
echo 'PASS actual AXI host/loaderCP/target49/resident programme/query producer +3 mutations' > "$out/gate"

for m in 4 5 6;do
 set +e;"$out/obj/sim" +DIR="$out/vectors" +MUT=$m +PROFILE=1 > "$out/m$m.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/m$m.rc"
 grep -qE 'ATT_FRONT (source/calendar fault|wrong actual P gather|bank fault)' "$out/m$m.log"
done
