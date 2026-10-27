#!/bin/bash
# Run via ot-run with a staged source repository. One core, not a die simulation.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
O=${1:?new output directory required}
if [ -e "$O" ];then echo "refusing existing output $O" >&2;exit 2;fi
mkdir -p "$O"
T=rtl/dsrom_sys/s81_head
for n in ctl_core ctl_hsf0_static static_issue util beat_link host276 best64 mesh_ep_core ar_control_hsf0 rank_merge_hsf0 result_landing_hsf0 fault_state_hsf0;do cp "$ROOT/$T/ot_s81hd_$n.sv" "$O/";done
cp "$ROOT/$T/test/tb_s81hd_ctl_static.sv" "$ROOT/$T/test/tb_s81hd_static_issue.sv" "$O/"
cp "$ROOT/rtl/dsrom_sys/mtp/"{dsfd_mtp_tops,ot_dsrom_mtp_link_pair,ot_dsrom_mtp_seq}.sv "$O/"
cp "$ROOT/rtl/lib/ot_rst_relay_tree3.sv" "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" "$O/"
cd "$O";export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for mut in 0 1 2;do
 verilator --binary --timing --build-jobs 2 -O1 -Wno-fatal --top-module tb_s81hd_static_issue -GMUT=$mut -Mdir obj_static$mut ot_s81hd_static_issue.sv tb_s81hd_static_issue.sv > static_build$mut.log 2>&1
 if obj_static$mut/Vtb_s81hd_static_issue > static_run$mut.log 2>&1;then test "$mut" = 0;else test "$mut" != 0;fi
 if [ "$mut" = 0 ];then grep -q 'PASS static_issue' static_run$mut.log;else grep -q '%Fatal' static_run$mut.log;fi
done
verilator --lint-only --timing -Wno-fatal --top-module ot_s81hd_ctl_core *.sv *.v > ctl_lint.log 2>&1
for mut in 0 1;do
 verilator --binary --timing --build-jobs 2 -O1 -Wno-fatal --top-module tb_s81hd_ctl_static -GMUT=$mut -Mdir obj_ctl$mut *.sv *.v > ctl_build$mut.log 2>&1
 if obj_ctl$mut/Vtb_s81hd_ctl_static > ctl_run$mut.log 2>&1;then test "$mut" = 0;else test "$mut" != 0;fi
 if [ "$mut" = 0 ];then grep -q 'PASS hd_ctl_static' ctl_run$mut.log;else grep -q 'result miter full512-bit payload mismatch' ctl_run$mut.log;fi
done
echo 'PASS HEAD_CTL static lockstep+2mutants; 2-position full stream/rank/result/token miter+payload mutant; ROWS-only identity'
