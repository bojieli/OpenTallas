#!/usr/bin/env bash
# usage: OUT
# KV-PLAN-CI 2026-10-17: the ci-less static controller path (qkd_static_kv_pc_path_nc and its children
# qkd_ctrl_pc_host_static_nc / qkd_ctrl_pc_sched_nc / qkd_ctrl_pc_port_child_nc / ot_qfd_emb_pcport_nkw /
# qkd_kv_hbm_elastic_front_mc_nc / qkd_static_kv_return_slots_mc_nc) against the original qkd_static_kv_pc_path with
# ci held 0, in lockstep (rtl/test/qwen_static_kv/tb_kvplan_ci_nc_lockstep.sv: every output every 0.1 ns) under the
# actual compiled die calendar images (PCs 0 / 45 / 127, jitter 0 / 16, with and without random pre-ownership traffic)
# plus random stress.  Three mutants of the variant (owner-mode kc command check dropped; front word shifted; ring data
# field shifted) must be observed (FAIL LOCKSTEP).  The wires-only parents qkd_static_kv_pc_path_fan_nc / _emb_nc must
# elaborate without PINMISSING / PINNOTFOUND.
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
E=rtl/qwen_sys/static_embedding_20261014;S=rtl/qwen_sys/static_kv_20261014;T=rtl/test/qwen_static_kv
P=results/arch/qwen_kv_static_programme_1017/die
pcs=$(python3 -c "import sys;sys.path.insert(0,'tools/qwen_kv_die');from static_pc_path_sources import SOURCES;print(' '.join(SOURCES))")
for pc in 0 45 127;do python3 - "$P" "$pc" "$out/image$pc.hex" <<'PY'
import sys
d,pc,o=sys.argv[1],int(sys.argv[2]),sys.argv[3];s,l=divmod(pc,32)
w=[int(x,16) for x in open(f'{d}/target{6+s}.hex').read().split()][32*l:32*l+32]
open(o,'w').write(''.join(f'{w[n]|(w[16+n]<<64):032x}\n' for n in range(16)))
PY
done
mkdir -p "$out/src0"; cp $S/qkd_ctrl_pc_nc.sv $S/qkd_static_kv_pc_path_nc.sv "$out/src0/"
mut(){ # n file old new
 mkdir -p "$out/src$1";cp "$out/src0/"*.sv "$out/src$1/"
 python3 - "$out/src$1/$2" "$3" "$4" <<'PY'
import sys
p,o,n=sys.argv[1:];t=open(p).read();assert t.count(o)==1,o;open(p,'w').write(t.replace(o,n))
PY
}
mut 1 qkd_ctrl_pc_nc.sv 'if((static_owner_q&&tc_v)||' 'if((1'"'"'b0&&tc_v)||'
mut 2 qkd_static_kv_pc_path_nc.sv 'assign co_out = {out_q[280:0], put_q};' 'assign co_out = {out_q[279:0], 1'"'"'b0, put_q};'
mut 3 qkd_static_kv_pc_path_nc.sv 'controller_co[7:1],controller_co[281:26]}' 'controller_co[7:1],controller_co[280:25]}'
build(){ "$v" --binary --timing -O2 -Wno-fatal -j 4 --top-module tb_kvplan_ci_nc_lockstep --Mdir "$out/obj$1" $pcs \
   "$out/src$1/qkd_ctrl_pc_nc.sv" "$out/src$1/qkd_static_kv_pc_path_nc.sv" $T/tb_kvplan_ci_nc_lockstep.sv > "$out/build$1.log" 2>&1; }
for m in 0 1 2 3;do build $m & done;wait
for m in 0 1 2 3;do [[ -x "$out/obj$m/Vtb_kvplan_ci_nc_lockstep" ]]||{ tail -20 "$out/build$m.log";echo FAIL build$m;exit 1;};done
run(){ "$out/obj$1/Vtb_kvplan_ci_nc_lockstep" +IMAGE="$out/image$2.hex" +PC=$(( $2 % 32 )) +JIT=$3 +PRE=$4 > "$out/run$1_pc$2_j$3_p$4.log" 2>&1||true; }
for pc in 0 45 127;do for j in 0 16;do for pre in 0 3000;do run 0 $pc $j $pre & done;done;done
for m in 1 2 3;do run $m 45 0 0 & done
wait
ok=1
for f in "$out"/run0_*.log;do r=$(grep -E '^(PASS|FAIL)' "$f"|tail -1);a=$(grep '^PHASE_A' "$f"||true);echo "== $(basename $f): $r | $a"
 grep -q '^PASS KVPLAN_CI_NC_LOCKSTEP' "$f"&&! grep -q '^FAIL' "$f"||ok=0;done
for m in 1 2 3;do f="$out/run${m}_pc45_j0_p0.log";echo "== mutant $m: $(grep -E '^(PASS|FAIL)' "$f"|tail -1)";grep -q '^FAIL LOCKSTEP' "$f"||ok=0;done
"$v" --lint-only -Wno-fatal -Wno-lint -Wno-style --top-module qkd_static_kv_pc_path_fan_nc $pcs $S/qkd_ctrl_pc_nc.sv \
  $S/qkd_static_kv_pc_path_nc.sv $E/qkd_embedding_static_map.sv $E/qkd_static_kv_pc_es_merge.sv $E/qkd_kv_pc_chain_station.sv \
  $E/qkd_static_kv_pc_path_fan_nc.sv > "$out/parent-lint.log" 2>&1 || ok=0
grep -qE '%Error|PINMISSING|PINNOTFOUND|PINCONNECTEMPTY' "$out/parent-lint.log"&&ok=0
rm -rf "$out"/obj*
[[ $ok == 1 ]]||{ echo FAIL KVPLAN_CI_NC;exit 1;}
echo PASS KVPLAN_CI_NC_LOCKSTEP_EXACT_OBSERVED_MUTANTS_PARENT_ELABORATES
