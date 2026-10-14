#!/bin/bash
set -euo pipefail
base=$(pwd)
out="$base/${VM_PRODUCER_TOP:-tb_qfd_vm_producer_row}-out"
mkdir -p "$out"
vp="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
top=${VM_PRODUCER_TOP:-tb_qfd_vm_producer_row}
p=rtl/qwen_sys/vm_plane_20261013
s=rtl/qwen_sys/vm_die_split_20261012
src=("$p/$top.sv" "$p/ot_qfd_vm_producer_lease.sv" "$p/ot_qfd_vm_region_leaf.sv" "$s/ot_qfd_vm_region_quarter.sv" "$s/ot_qfd_vm_answer_tiles.sv" "$s/ot_qfd_vm_xfifo8_t.sv" rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv "$p/ot_qfd_vm_xplane.sv" rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qwen_tree_delay.sv rtl/physical/ot_qwen_tree_delay_tiles.sv)
for mut in 0 1; do
 "$vp" --binary --timing -O1 -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT --output-split 20000 --output-split-cfuncs 2000 --top-module "$top" -GMUT=$mut --Mdir "$out/m$mut" "${src[@]}" > "$out/m$mut.build.log" 2>&1
 set +e
 "$out/m$mut/V$top" > "$out/m$mut.run.log" 2>&1
 code=$?
 set -e
 cat "$out/m$mut.run.log"
 if [ "$mut" = 0 ] && [ "$code" != 0 ]; then exit 2; fi
 if [ "$mut" != 0 ] && [ "$code" = 0 ]; then exit 3; fi
 printf 'GATE mutant=%s exit=%s expected\n' "$mut" "$code"
done
