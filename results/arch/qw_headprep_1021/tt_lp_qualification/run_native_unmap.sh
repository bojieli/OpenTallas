#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys -Q -T -p 'read_json generic_hp.json; dffunmap; write_json generic_hp_unmapped.json' > native_unmap.log 2>&1
python3 tools/qwen_dv/ctlm6_bound_macro.py generic_hp_unmapped.json --top qfd_tt_ctlm_dv_lpf_hp_lp --name qfd_tt_ctlm_dv_hp_h16z_native32 --out hp_native32.v --helpers hp_native32_helpers.sv --record hp_native32_record.json --macro-contracts native_macro_contracts.json --fuse-ao --retain-mux --transparent-inverters > native_construct2.log 2>&1
echo HP_NATIVE_CONSTRUCTION_DONE
