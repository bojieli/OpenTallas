#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
python3 tools/hbm_static_attention/prepare_QP_front.py --out "$out/vectors"
python3 - "$out/tb_mutant.sv" <<'PY'
import sys
from pathlib import Path
s=Path('rtl/test/hbm_accel/generic/tb_hbm_attn_QP_fields_host_front.sv').read_text().replace('module tb_hbm_attn_QP_fields_host_front;','module tb_hbm_attn_QP_fields_host_front_mutant;')
s=s.replace('endmodule', 'defparam dut.u_front.u_p.MUT_FIELD=2;\nendmodule')
Path(sys.argv[1]).write_text(s)
PY
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_QP_fields_host_front_mutant --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_physical_host_program_front_fields.sv rtl/hdc/v41x/static/ot_hbm_attn_physical_program_query_front_fields.sv \
 rtl/hdc/v41x/static/ot_hbm_attn_physical_program_consumer.sv rtl/hdc/v41x/static/ot_hbm_attn_physical_event_program.sv rtl/hdc/v41x/static/ot_hbm_attn_query_prefetch.sv rtl/hdc/v41x/static/ot_hbm_attn_p_prefetch_fields.sv \
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_calendar_host_static.sv \
 rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_static.sv \
 rtl/hbm_accel/generic/loader/ot_hgi_loader_cp.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
 "$out/tb_mutant.sv" > "$out/build.log" 2>&1
set +e;"$out/obj/sim" +DIR="$out/vectors" +MUT=0 +PROFILE=1 > "$out/mutant.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/mutant.rc"
if [ "$rc" = 0 ];then echo 'FAIL actual Pfield2 DUT mutant survived';exit 1;fi
grep -q 'ATT_FRONT wrong actual P field gather field2' "$out/mutant.log"
echo 'PASS actualPfield2 bankpayloadassociation DUTmutation rejected under actualhost/currentbank/NEprogramme' > "$out/gate"
