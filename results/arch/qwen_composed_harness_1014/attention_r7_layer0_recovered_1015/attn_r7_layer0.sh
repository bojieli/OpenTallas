#!/usr/bin/env bash
# attn_r7_layer0.sh <name> <plan>: seeded layer0, LV6 G3072 RTL-FP core + r7 RTL-FP attention service.
set -uo pipefail
S=/srv/opentallas-scratch/claude/qwen-wholetoken-1014; Q=$S/qfunc_rtlfp_2328
B=/srv/opentallas-scratch/codex/qwen-native-fulltoken-1014/banks/oracle
export OT_SEED_X=$B/cold_token0_first2/layer0/vm_x_fp32.hex
export LV6_OBJ=$S/lv6_hier/g3072_rtlfp_O3/obj LV6_HIER=1 PROBE_OBJ=$Q/probe_no_pch/core_instruction_probe.o
export KERNEL_SO_DIR=$S/lv6_hier/attn_rtlfp_r7_shim ATTN_RTL_ONLY=1
out=$Q/$1; bash $S/attn_r7_stage/src/run_whole_token.sh $S/attn_r7_stage "$2" $out > $out.outer.log 2>&1
rc=$?; echo $rc > $out.outer_exit.txt; exit $rc
