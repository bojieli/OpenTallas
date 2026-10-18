#!/bin/bash
# Re-run the KVJ-A item-2 benches from a worktree root ($1) into the current directory.
W=${1:?worktree}; E=$(dirname $(readlink -f $0)); D=$W/rtl/qwen_sys/static_kv_20261014
for m in 0 4; do
 iverilog -g2012 -s tb_static_boot_dispatch_lockstep -Ptb_static_boot_dispatch_lockstep.MUT_B=$m -o l$m.sim $E/base_dispatch.sv $D/qkd_static_kv_boot_dispatch.sv $W/rtl/test/qwen_static_kv/tb_static_boot_dispatch_lockstep.sv && vvp -n l$m.sim > lockstep_m$m.log
 iverilog -g2012 -s tb_static_boot_dispatch_cdc -Ptb_static_boot_dispatch_cdc.MUT=$m -o c$m.sim $W/rtl/lib/ot_reset_sync.sv $W/rtl/lib/ot_async_fifo.sv $D/qkd_static_kv_boot_cdc.sv $D/qkd_static_kv_boot_dispatch.sv $W/rtl/test/qwen_static_kv/tb_static_boot_dispatch_cdc.sv && vvp -n c$m.sim > cdc_m$m.log
done; rm -f *.sim; python3 $W/tools/qwen_static_kv/run_boot_dispatch.py --out unit >/dev/null && echo unit PASS
