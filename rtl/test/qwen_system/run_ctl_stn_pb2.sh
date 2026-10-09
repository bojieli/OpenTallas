#!/usr/bin/env bash
set -euo pipefail
wd=$1
mkdir -p "$wd/golden"
python3 tools/qwen_system/ctl_golden.py --out "$wd/golden" > "$wd/golden.log"
src=(rtl/test/qwen_system/tb_qfd_ctl_stn_pb2.sv rtl/qwen_sys/system_20261008/ot_qfd_sysctl_pb2.sv rtl/qwen_sys/system_20261008/ot_qfd_sysctl_stn_pb2.sv rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram_pb2.sv rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv rtl/qwen_sys/system_20261008/ot_qfd_dctl.sv rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv rtl/qwen_sys/ot_qwen_sys_csr.sv rtl/qwen_sys/ot_qwen_sys_rst_seq.sv rtl/lib/ot_reset_sync.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-DECLFILENAME -Wno-PINCONNECTEMPTY -Wno-INITIALDLY -Wno-BLKSEQ -I"$wd/golden" -DCL=40 -DWDOG=5000 -DPROMPT_SRAM=1 -DPROMPT_POISON=1 --top-module tb_qfd_ctl_stn_pb2 -Mdir "$wd/obj" "${src[@]}" > "$wd/build.log" 2>&1
for scen in eos length badlen fullctx; do
 "$wd/obj/Vtb_qfd_ctl_stn_pb2" +SCEN="$wd/golden/scen_$scen.hex" > "$wd/$scen.log"
 grep -q 'CTL_RESULT pass=1' "$wd/$scen.log"
done
for kind in 1 2 3 4; do
 "$wd/obj/Vtb_qfd_ctl_stn_pb2" +SCEN="$wd/golden/scen_eos.hex" +FAULT_DIE=2 +FAULT_STEP=1 +FAULT_STAGE=17 +FAULT_KIND=$kind > "$wd/fault$kind.log"
 grep -q 'CTL_RESULT pass=1' "$wd/fault$kind.log"
done
"$wd/obj/Vtb_qfd_ctl_stn_pb2" +SCEN="$wd/golden/scen_eos.hex" +DISAGREE_STEP=2 > "$wd/disagree.log"
grep -q 'CTL_RESULT pass=1' "$wd/disagree.log"
grep 'CTL_RESULT' "$wd"/*.log
echo CTL_SRAM_CAMPAIGN_PASS

# Negative control: replay the prior unconditional-read mechanism on poisoned unwritten slots.
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-DECLFILENAME -Wno-PINCONNECTEMPTY -Wno-INITIALDLY -Wno-BLKSEQ -I"$wd/golden" -DCL=40 -DWDOG=5000 -DPROMPT_SRAM=1 -DPROMPT_POISON=1 -DPB_VALID_ONLY=0 --top-module tb_qfd_ctl_stn_pb2 -Mdir "$wd/mut_obj" "${src[@]}" > "$wd/mut_build.log" 2>&1
"$wd/mut_obj/Vtb_qfd_ctl_stn_pb2" +SCEN="$wd/golden/scen_eos.hex" > "$wd/unused_read_mutant.log" 2>&1 || true
grep -q 'CTL_RESULT pass=0' "$wd/unused_read_mutant.log"
grep 'CTL_RESULT' "$wd/unused_read_mutant.log"
echo CTL_STATION_POISON_PASS
