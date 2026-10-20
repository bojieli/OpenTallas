#!/bin/bash
set -eu
R=$PWD
E=$R/results/rtl/kv_ectl_h15_1020/ab_complete_graph
mkdir -p "$E"
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
python3 - "$R" "$E" <<'INNER'
from pathlib import Path
import sys,json,hashlib
r,e=map(Path,sys.argv[1:]);src=['rtl/qwen_sys/static_kv_20261014/qkd_static_ectla_kiss.sv','rtl/qwen_sys/static_kv_20261014/qkd_static_k_issuer.sv','rtl/qwen_sys/split_20261014/qkd_ectl_a_tp8_epoch_direct.sv','rtl/qwen_sys/split_20261014/qkd_ectl_native_direct_tp8.sv','rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv','rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv','rtl/hdc/ot_hdc_delay.sv','rtl/lib/ot_rst_relay.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v']
for top in ['qkd_static_ectla_kiss','qkd_ectl_b_tp8_direct']:
 for age in [13,15]:
  args=f'-set HXK {age} -set QK_ISSUE_AGE 91 '+('-set RESPONSE_LAT 80' if top=='qkd_static_ectla_kiss' else '-set STATIC_QK 1 -set ROW_RETURN_LAT 87')
  cmd=['read_verilog -defer -sv -DSYNTHESIS '+' '.join(str(r/x) for x in src),f'chparam {args} {top}',f'prep -flatten -top {top}','opt_clean',f'write_json {e}/{top}_{age}.json']
  (e/f'{top}_{age}.ys').write_text('\n'.join(cmd)+'\n')
(e/'source_manifest.json').write_text(json.dumps({'sources':{x:hashlib.sha256((r/x).read_bytes()).hexdigest() for x in src},'root_approved_method':'strict full elaborated graph with actual SRAM BB retained; stateful macro lemma separate, no cold/physical admission'},indent=2)+'\n')
INNER
failed=0
for top in qkd_static_ectla_kiss qkd_ectl_b_tp8_direct;do
 for age in 13 15;do "$Y" -s "$E/${top}_${age}.ys" > "$E/${top}_${age}.log" 2>&1;done
 python3 results/rtl/kv_ectl_h15_1020/compare_ab_graphs.py "$top" "$E/${top}_13.json" "$E/${top}_15.json" "$E/${top}.comparison.json" || failed=1
done
exit "$failed"
