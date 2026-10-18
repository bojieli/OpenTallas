#!/usr/bin/env bash
# usage: OUT N
# KV-NCKITS 2026-10-17: one mutant of the ci-less static PC path, run in lockstep against the original
# qkd_static_kv_pc_path (ci held 0) by rtl/test/qwen_static_kv/tb_kvplan_ci_nc_lockstep.sv, under the actual compiled
# die calendar image of PC 45 (jitter 0, no pre-ownership traffic).  The per-tile expect=fail bench of the *_nc tile
# kits; the positive bench is tools/qwen_kv_die/kvplan_ci_nc_gate.sh.  A caught mutant prints "FAIL LOCKSTEP".
#   N=1 qkd_ctrl_pc_sched_nc            owner-mode kc command check dropped
#   N=2 qkd_kv_hbm_elastic_front_mc_nc  front controller word shifted by one bit
#   N=3 qkd_static_kv_return_slots_mc_nc ring data field shifted by one bit
#   N=4 qkd_ctrl_pc_port_child_nc       PHY read data rotated by one bit at the port pin register
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};n=${2:?mutant};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/qwen_sys/static_kv_20261014;T=rtl/test/qwen_static_kv;P=results/arch/qwen_kv_static_programme_1017/die
pcs=$(python3 -c "import sys;sys.path.insert(0,'tools/qwen_kv_die');from static_pc_path_sources import SOURCES;print(' '.join(SOURCES))")
python3 - "$P" 45 "$out/image45.hex" <<'PY'
import sys
d,pc,o=sys.argv[1],int(sys.argv[2]),sys.argv[3];s,l=divmod(pc,32)
w=[int(x,16) for x in open(f'{d}/target{6+s}.hex').read().split()][32*l:32*l+32]
open(o,'w').write(''.join(f'{w[n]|(w[16+n]<<64):032x}\n' for n in range(16)))
PY
case $n in
 1) f=qkd_ctrl_pc_nc.sv;o='if((static_owner_q&&tc_v)||';r='if((1'"'"'b0&&tc_v)||';;
 2) f=qkd_static_kv_pc_path_nc.sv;o='assign co_out = {out_q[280:0], put_q};';r='assign co_out = {out_q[279:0], 1'"'"'b0, put_q};';;
 3) f=qkd_static_kv_pc_path_nc.sv;o='controller_co[7:1],controller_co[281:26]}';r='controller_co[7:1],controller_co[280:25]}';;
 4) f=qkd_ctrl_pc_nc.sv;o='.r_v(rv_q), .r_d(rd_q)';r='.r_v(rv_q), .r_d({rd_q[286:0], rd_q[287]})';;
 *) echo "unknown mutant $n";exit 2;;
esac
mkdir -p "$out/src";cp $S/qkd_ctrl_pc_nc.sv $S/qkd_static_kv_pc_path_nc.sv "$out/src/"
python3 - "$out/src/$f" "$o" "$r" <<'PY'
import sys
p,o,n=sys.argv[1:];t=open(p).read();assert t.count(o)==1,o;open(p,'w').write(t.replace(o,n))
PY
"$v" --binary --timing -O2 -Wno-fatal -j 2 --top-module tb_kvplan_ci_nc_lockstep --Mdir "$out/obj" $pcs \
  "$out/src/qkd_ctrl_pc_nc.sv" "$out/src/qkd_static_kv_pc_path_nc.sv" $T/tb_kvplan_ci_nc_lockstep.sv > "$out/build.log" 2>&1 \
  || { tail -20 "$out/build.log";echo "BUILD_FAILED mutant $n";exit 3;}
"$out/obj/Vtb_kvplan_ci_nc_lockstep" +IMAGE="$out/image45.hex" +PC=13 +JIT=0 +PRE=0 > "$out/run.log" 2>&1 || true
rm -rf "$out/obj"
grep -E '^(PASS|FAIL|MISMATCH)' "$out/run.log" | head -8
grep -q '^FAIL LOCKSTEP' "$out/run.log" && { echo "OBSERVED mutant $n";exit 1;}
echo "NOT_OBSERVED mutant $n";exit 0
