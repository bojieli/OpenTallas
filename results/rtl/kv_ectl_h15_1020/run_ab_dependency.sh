#!/bin/bash
set -eu
R=$PWD
E=$R/results/rtl/kv_ectl_h15_1020
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
for top in qkd_static_ectla_kiss qkd_ectl_b_tp8_direct;do
 script="$E/${top}_dependency.ys"
 python3 - "$R" "$top" "$script" <<'INNER'
from pathlib import Path
import sys
r=Path(sys.argv[1]);top=sys.argv[2];out=Path(sys.argv[3])
src=['rtl/qwen_sys/static_kv_20261014/qkd_static_ectla_kiss.sv','rtl/qwen_sys/static_kv_20261014/qkd_static_k_issuer.sv','rtl/qwen_sys/split_20261014/qkd_ectl_a_tp8_epoch_direct.sv','rtl/qwen_sys/split_20261014/qkd_ectl_native_direct_tp8.sv','rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv','rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv','rtl/hdc/ot_hdc_delay.sv','rtl/lib/ot_rst_relay.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
cmd=[]
for age in [13,15]:
 cmd+=['read_verilog -sv -DSYNTHESIS '+' '.join(str(r/x) for x in src)]
 args=f'-set HXK {age} -set QK_ISSUE_AGE 91 '+('-set RESPONSE_LAT 80' if top=='qkd_static_ectla_kiss' else '-set STATIC_QK 1 -set ROW_RETURN_LAT 87')
 cmd += [f'chparam {args} {top}',f'prep -flatten -top {top}','opt_clean',f'design -stash h{age}']
cmd += [f'design -copy-from h13 -as gold {top}',f'design -copy-from h15 -as gate {top}','equiv_make gold gate eq','hierarchy -top eq','equiv_simple','equiv_status -assert']
out.write_text('\n'.join(cmd)+'\n')
INNER
 "$Y" -s "$script" > "$E/${top}_dependency.log" 2>&1
 tail -n 5 "$E/${top}_dependency.log"
done
