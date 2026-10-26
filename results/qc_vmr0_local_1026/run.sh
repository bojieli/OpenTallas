set -euo pipefail
for mut in 0 1 2;do
 def=;[ "$mut" != 1 ] || def=+define+OT_QC_VMR0_MUT_COLL;[ "$mut" != 2 ] || def=+define+OT_QC_VMR0_MUT_EDGE
 "$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --x-assign 0 --x-initial 0 $def --top-module tb rtl/test/qwen_dv/s5/sram_models_nofatal.sv rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv results/qc_vmr0_local_1026/gold.sv results/qc_vmr0_local_1026/tb.sv -Mdir out/m$mut >out/build$mut.log 2>&1
 set +e
 out/m$mut/Vtb >out/run$mut.log 2>&1
 rc=$?
 set -e
 cat out/run$mut.log
 if [ "$mut" = 0 ];then test "$rc" = 0;grep -q 'VMR0_LOCAL PASS' out/run$mut.log;else test "$rc" != 0;grep -q 'VMR MISMATCH' out/run$mut.log;fi
done
