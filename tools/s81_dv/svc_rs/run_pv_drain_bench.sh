#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "${1:?output directory}")
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$O"
python3 - "$O" <<'PYCODE'
import sys
from pathlib import Path
b=Path(sys.argv[1]);s=Path('rtl/dsrom_sys/s81_svc/ot_s81_svc_attn_s.sv').read_text();i=s.index('module ot_s81_svc_rt2_load_calendar');(b/'calendar.sv').write_text(s[i:s.index('endmodule',i)+9]+'\n')
s=Path('rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv').read_text();old="32'(p_i - 1)*H*32";assert s.count(old)==1;(b/'outer_body_swap.sv').write_text(s.replace(old,"32'((p_i == 1) ? 1 : (p_i == 2) ? 0 : p_i - 1)*H*32"))
PYCODE
for form in nominal nominal_macro body_swap;do
 src=rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv
 defs=(-DOT_SVC_MERGE_H4 -DOT_ATTN_HCORE -DOT_SVC_H8_REUSE_RT2 -DOT_SVC_NATIVE_RT2_CALENDAR)
 extras=();expect=0
 if [[ $form != nominal ]];then
  defs+=(-DOT_SVC_ATT_MEM_MACRO)
  extras+=(rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_ar.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_la.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_lr.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v physical/asap7_memory_macros_v2/ot_sram_1r1w_160x256_m1_r0c0/ot_sram_1r1w_160x256_m1_r0c0.v)
 fi
 if [[ $form == body_swap ]];then src="$O/outer_body_swap.sv";expect=1;fi
 "$VL" --binary --timing --top-module tb_svc_pv_drain -Mdir "$O/obj_$form" -j 2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD "${defs[@]}" "${extras[@]}" "$src" rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv "$O/calendar.sv" rtl/dsrom_sys/s81_dv/svc_rs/test/tb_svc_pv_drain.sv >"$O/build_$form.log" 2>&1
 "$O/obj_$form/Vtb_svc_pv_drain" +expect_mut=$expect >"$O/run_$form.log" 2>&1
 grep -E 'DRAIN_SUMMARY|PV_DRAIN ' "$O/run_$form.log"
 grep -q '^PV_DRAIN PASS' "$O/run_$form.log"
done
