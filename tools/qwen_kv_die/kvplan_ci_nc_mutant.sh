#!/usr/bin/env bash
# usage: OUT M   (KV-NC-KITS 2026-10-17) one mutant of tools/qwen_kv_die/kvplan_ci_nc_gate.sh, run alone so each nc kit has
# its own expect=fail bench + committed witness: the variant with mutant M against the original qkd_static_kv_pc_path
# (ci held 0) in tb_kvplan_ci_nc_lockstep, PC 45 calendar image, jitter 0, no pre-ownership traffic.  Must print FAIL LOCKSTEP.
#   1 sched_nc: owner-mode kc command check dropped    2 front_mc_nc: front word shifted
#   3 return_slots_mc_nc: ring data field shifted        4 port_child_nc: PHY read data captured one bit low
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};m=${2:?mutant};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-verilator}
S=rtl/qwen_sys/static_kv_20261014;T=rtl/test/qwen_static_kv;P=results/arch/qwen_kv_static_programme_1017/die
pcs=$(python3 -c "import sys;sys.path.insert(0,'tools/qwen_kv_die');from static_pc_path_sources import SOURCES;print(' '.join(SOURCES))")
python3 - "$P" 45 "$out/image45.hex" <<'PY'
import sys
d,pc,o=sys.argv[1],int(sys.argv[2]),sys.argv[3];s,l=divmod(pc,32)
w=[int(x,16) for x in open(f'{d}/target{6+s}.hex').read().split()][32*l:32*l+32]
open(o,'w').write(''.join(f'{w[n]|(w[16+n]<<64):032x}\n' for n in range(16)))
PY
mkdir -p "$out/src"; cp $S/qkd_ctrl_pc_nc.sv $S/qkd_static_kv_pc_path_nc.sv "$out/src/"
case $m in
 1) f=qkd_ctrl_pc_nc.sv; o='if((static_owner_q&&tc_v)||'; n='if((1'"'"'b0&&tc_v)||';;
 2) f=qkd_static_kv_pc_path_nc.sv; o='assign co_out = {out_q[280:0], put_q};'; n='assign co_out = {out_q[279:0], 1'"'"'b0, put_q};';;
 3) f=qkd_static_kv_pc_path_nc.sv; o='controller_co[7:1],controller_co[281:26]}'; n='controller_co[7:1],controller_co[280:25]}';;
 4) f=qkd_ctrl_pc_nc.sv; o='rd_q <= pi[288:1];'; n='rd_q <= {pi[287:1], 1'"'"'b0};';;
 *) echo "unknown mutant $m"; exit 2;;
esac
python3 - "$out/src/$f" "$o" "$n" <<'PY'
import sys
p,o,n=sys.argv[1:];t=open(p).read();assert t.count(o)==1,o;open(p,'w').write(t.replace(o,n))
PY
"$v" --binary --timing -O2 -Wno-fatal -j 4 --top-module tb_kvplan_ci_nc_lockstep --Mdir "$out/obj" $pcs \
   "$out/src/qkd_ctrl_pc_nc.sv" "$out/src/qkd_static_kv_pc_path_nc.sv" $T/tb_kvplan_ci_nc_lockstep.sv > "$out/build.log" 2>&1 \
   || { tail -20 "$out/build.log"; echo "BUILD_FAIL mutant $m"; exit 3; }
"$out/obj/Vtb_kvplan_ci_nc_lockstep" +IMAGE="$out/image45.hex" +PC=13 +JIT=0 +PRE=0 > "$out/run.log" 2>&1 || true
rm -rf "$out/obj"
echo "== kvplan_ci_nc mutant $m ($f)"; grep -E '^(PASS|FAIL)' "$out/run.log" | head -5
grep -q '^FAIL LOCKSTEP' "$out/run.log" && exit 1
exit 0
