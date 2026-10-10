#!/usr/bin/env bash
# Minimum full-capacity SRAM vehicle plus shortened-code exhaustive single/double errors.
set -euo pipefail
wd=$1
mkdir -p "$wd"
for mut in 0 1; do
  iverilog -g2012 -s tb_qfd_prompt_sram -P tb_qfd_prompt_sram.MUT=$mut -o "$wd/p$mut" rtl/test/qwen_system/tb_qfd_prompt_sram.sv rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
  vvp "$wd/p$mut" > "$wd/p$mut.log"
done
grep -q '^PROMPT_SRAM_PASS' "$wd/p0.log"
grep -q '^PROMPT_SRAM_FAIL.*ecc_bad=[1-9]' "$wd/p1.log"
cat "$wd/p0.log" "$wd/p1.log"
echo PROMPT_CAMPAIGN_PASS
