#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/sysctl-pb2-19699b86e
trap 'rc=$?; printf "{\"source\":\"19699b86e\",\"mutation\":\"remove_matching_host_wait\",\"rc\":%s}\n" "$rc" > alignment_terminal.json' EXIT
sed 's/\.PB_READ_PIPE(PROMPT_SRAM \&\& PROMPT_READ_STATION)/.PB_READ_PIPE(0)/' rtl/qwen_sys/system_20261008/ot_qfd_sysctl_pb2.sv > control/mut_read_core.sv
sha256sum control/mut_read_core.sv > alignment_source.sha256
src=(rtl/test/qwen_system/tb_qfd_ctl_stn_pb2.sv control/mut_read_core.sv rtl/qwen_sys/system_20261008/ot_qfd_sysctl_stn_pb2.sv rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram_pb2.sv rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv rtl/qwen_sys/system_20261008/ot_qfd_dctl.sv rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv rtl/qwen_sys/ot_qwen_sys_csr.sv rtl/qwen_sys/ot_qwen_sys_rst_seq.sv rtl/lib/ot_reset_sync.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-DECLFILENAME -Wno-PINCONNECTEMPTY -Wno-INITIALDLY -Wno-BLKSEQ -Icontrol/golden -DCL=40 -DWDOG=5000 -DPROMPT_SRAM=1 -DPROMPT_POISON=1 --top-module tb_qfd_ctl_stn_pb2 -Mdir control/align_obj "${src[@]}" > alignment_build.log 2>&1
control/align_obj/Vtb_qfd_ctl_stn_pb2 +SCEN=control/golden/scen_eos.hex > alignment_mutant.log 2>&1 || true
grep -q 'CTL_RESULT pass=0' alignment_mutant.log
grep 'TRACE_BAD\|CTL_RESULT' alignment_mutant.log
