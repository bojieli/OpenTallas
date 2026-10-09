#!/usr/bin/env bash
# Remote admission only:1thread/1GB component campaign; no physical verdict implied.
set -euo pipefail
wd=$1
mkdir -p "$wd"
for mut in 0 1;do
  iverilog -g2012 -s tb_qfd_prompt_sram_pb2_fault -P tb_qfd_prompt_sram_pb2_fault.MUT=$mut -o "$wd/p$mut" rtl/test/qwen_system/tb_qfd_prompt_sram_pb2_fault.sv rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram_pb2.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
  vvp "$wd/p$mut" > "$wd/p$mut.log"
done
grep -q '^PROMPT_FAULT_PASS' "$wd/p0.log"
grep -q '^PROMPT_FAULT_FAIL.*bad=[1-9]' "$wd/p1.log"
cat "$wd/p0.log" "$wd/p1.log"
echo PROMPT_FAULT_CAMPAIGN_PASS
