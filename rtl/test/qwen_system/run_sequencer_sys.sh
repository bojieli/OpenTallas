#!/usr/bin/env bash
set -euo pipefail
wd=$1
mkdir -p "$wd"
src=(rtl/test/qwen_system/tb_qfd_sequencer_sys.sv rtl/qwen_sys/system_20261008/ot_qfd_sp_constants_sequencer_sys.sv rtl/qwen_sys/system_20261008/ot_qfd_dctl.sv rtl/qwen_sys/missing_masters_20261007/gen/ot_qfd_sp_constants_sequencer.sv rtl/qwen_sys/missing_masters_20261007/gen/ot_qwen_rom_core_ctrl.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv rtl/rom/ot_qwen_tp_seq_w12.sv rtl/rom/ot_qwen_tp_seq_w12_fs.sv rtl/hdc/ot_hdc_dyn_ttiles.sv rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/hdc/ot_hdc_cg.sv rtl/hdc/ot_hdc_delay.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv)
for mut in 0 1; do
 verilator --binary --timing -j 4 -Wno-fatal -Irtl/qwen_sys/system_20261008 -DSYS_MUT=$mut --top-module tb_qfd_sequencer_sys -Mdir "$wd/obj$mut" "${src[@]}" > "$wd/build$mut.log" 2>&1
 "$wd/obj$mut/Vtb_qfd_sequencer_sys" > "$wd/run$mut.log" 2>&1 || true
 if [ "$mut" = 0 ]; then grep -q '^SEQUENCER_SYS_RESULT pass=1' "$wd/run0.log"; else grep -q '^SEQUENCER_SYS_RESULT pass=0' "$wd/run1.log"; fi
 grep '^SEQUENCER_SYS_RESULT\|^SYS_CASE' "$wd/run$mut.log"
done
echo SEQUENCER_SYS_CAMPAIGN_PASS
