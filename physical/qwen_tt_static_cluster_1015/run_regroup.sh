#!/bin/bash
# usage: run_regroup.sh MUT NCYC [CMD_A CMD_B RET_A RET_B]
#   MUT=1 swaps tree-return bits RET_A/RET_B, MUT=2 swaps tree-command bits CMD_A/CMD_B in the dut.
#   r14 defaults (measured c3ba6466d, 8 programme runs + 60k random): cmd[0]/cmd[1] = tree GO (differs 32x, mutant
#   214,461 output mismatches), ret[0]/ret[94] = tree done/fault (differs 1,363x, 285 mismatches). Swaps of
#   descriptor/data bits (cmd 67/68, 70/71, 261/262; ret 0/2, 1/2, 3/4, 85/90) were exercised but NOT observed at the
#   parent outputs by this bench: they remain covered only by the formal equivalence (equiv.sh).
#   r14: the seam pair indices are chosen from measured seam activity (m0 SEAM_* report) and the bench
#   refuses a vacuous pass (REGROUP_UNSENSITIZED) when either pair never differs.
set -e
# --converge-limit 5000: the directed PW programme phase (tasks with zero-delay blocking input updates) exceeds
# Verilator 5.032 default active-region iteration limit 100; it is a scheduler iteration bound, not a semantic change.
MUT=${1:-0}; N=${2:-100000}; CA=${3:-0}; CB=${4:-1}; RA=${5:-0}; RB=${6:-94}; MINP=${MIN_PAIR:-16}
P=physical/qwen_tt_static_cluster_1015
NEW=rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_static_parent.sv
swap(){ python3 - "$1" "$2" "$3" "$4" "$5" <<'PY'
import sys
src,kind,a,b,dst=sys.argv[1:];a=int(a);b=int(b);t=open(src).read()
W={'ret':95,'cmd':380}[kind]
bits=[f'{"rom_ret" if kind=="ret" else "rom_cmd"}[{i}]' for i in range(W)]
bits[a],bits[b]=bits[b],bits[a]
cat='{'+','.join(reversed(bits))+'}'
old={'ret':'.rom_ret_i(rom_ret),','cmd':'.cmd(rom_cmd),.ret(rom_ret));'}[kind]
new={'ret':f'.rom_ret_i({cat}),','cmd':f'.cmd({cat}),.ret(rom_ret));'}[kind]
assert t.count(old)==1,old
open(dst,'w').write(t.replace(old,new))
PY
}
case $MUT in
 1) swap $NEW ret $RA $RB /tmp/rg_m$$.sv; NEW=/tmp/rg_m$$.sv;;
 2) swap $NEW cmd $CA $CB /tmp/rg_m$$.sv; NEW=/tmp/rg_m$$.sv;;
esac
SR=$(sed 's#_bb\.v#.v#g' $P/srcs.txt)
O=${RG_OBJ:-/tmp/rg_obj_${MUT}_$$}
verilator --binary --timing --converge-limit 5000 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DNCYC=$N -DCMD_A=$CA -DCMD_B=$CB -DRET_A=$RA -DRET_B=$RB -DMIN_PAIR=$MINP -DRUNS=${RUNS:-8} --top-module tb_tt_static_regroup -Mdir $O \
  $SR rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_static_hr.sv $NEW $P/ot_qfd_tt_ctlm_static_parent_ref.sv $P/tb_tt_static_regroup.sv > $O.build.log 2>&1 || { tail -20 $O.build.log; exit 2; }
$O/Vtb_tt_static_regroup +PROGRAM=results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/head_program_rank7.hex
