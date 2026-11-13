#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "${1:?output dir}")
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$O"
python3 - "$O/calendar_exact.sv" <<'PY'
import sys
s=open('rtl/dsrom_sys/s81_svc/ot_s81_svc_attn_s.sv').read();i=s.index('module ot_s81_svc_rt2_load_calendar');open(sys.argv[1],'w').write(s[i:s.index('endmodule',i)+9]+'\n')
PY
for form in nominal nominal_macro malformed;do
 defs=(-DOT_SVC_MERGE_H4 -DOT_ATTN_HCORE)
 mut=1
 if [[ $form != malformed ]];then defs+=(-DOT_SVC_H8_REUSE_RT2);mut=0;fi
 extras=()
 if [[ $form == nominal_macro ]];then
  defs+=(-DOT_SVC_ATT_MEM_MACRO)
  extras+=(rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_ar.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_la.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_lr.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v physical/asap7_memory_macros_v2/ot_sram_1r1w_160x256_m1_r0c0/ot_sram_1r1w_160x256_m1_r0c0.v)
 fi
 "$VL" --binary --timing --top-module tb_svc_static_producer -Mdir "$O/obj_$form" -j 2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD "${defs[@]}" "${extras[@]}" \
 rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv "$O/calendar_exact.sv" \
 rtl/dsrom_sys/s81_dv/svc_rs/test/tb_svc_static_producer.sv >"$O/build_$form.log" 2>&1
 "$O/obj_$form/Vtb_svc_static_producer" +mut=$mut >"$O/run_$form.log" 2>&1
 cat "$O/run_$form.log"
 grep -q '^STATIC_PRODUCER PASS' "$O/run_$form.log"
done
