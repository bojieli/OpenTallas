#!/usr/bin/env bash
# usage: OUT [REF_COMMIT]
# KV-TOK B 2026-10-24: lockstep proof of the controller BOOT WINDOW (qkd_ctrl_pc_sched_nc boot_win -> u_ctl boot_window
# -> ot_qkd_static_kv_timing boot_static_col; col_boot -> expected_sr / boot_raw).  The per-PC static path as now in the
# repo (u_b) runs against the ORIGINAL path (u_a: ot_qkd_static_kv_timing / ot_qkd_static_ctrl_pc_emb / qkd_ctrl_pc_nc /
# qkd_static_kv_pc_path_nc at REF_COMMIT, default b1131f6fa = the parent of the change, every module renamed *_ref) in
# rtl/test/qwen_static_kv/tb_kv_boot_window_lockstep.sv: every output every 0.1 ns, under the actual compiled die
# calendar images (PCs 0 / 45 / 127, PHY jitter 0 / 16) and random stress.
#   EQ   : random pre-ownership traffic WITHOUT static words, then the compiled calendar, then stress with static words
#          (window closed): zero mismatches in every phase (window inert when unused; post-ownership behaviour unchanged).
#   DIS  : the window disabled (reset value 0, source edit) with random pre-ownership static words: zero mismatches in
#          every phase (the window is the ONLY behavioural change).
#   ACT  : the window as built with random pre-ownership static words: boot columns issue in phase P (activity only).
#   MUT1 : the window never closes (source edit): must FAIL LOCKSTEP (boot columns after ownership).
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};ref=${2:-b1131f6fa};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
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
# reference: the original sources, every module they define renamed *_ref (instances inside them follow)
mkdir -p "$out/ref"
for f in ot_qkd_static_kv_timing.sv ot_qkd_static_ctrl_pc_emb.sv qkd_ctrl_pc_nc.sv qkd_static_kv_pc_path_nc.sv;do
 git show "$ref:$S/$f" > "$out/ref/$f";done
python3 - "$out/ref" <<'PY'
import sys,re,glob
fs=sorted(glob.glob(sys.argv[1]+'/*.sv'));txt={f:open(f).read() for f in fs}
mods=sorted({m for t in txt.values() for m in re.findall(r'^\s*module\s+(\w+)',t,re.M)},key=len,reverse=True)
for f,t in txt.items():
  for m in mods:t=re.sub(r'\b'+m+r'\b',m+'_ref',t)
  open(f,'w').write(t)
print('REF modules renamed:',len(mods))
PY
mkdir -p "$out/src0";cp $S/qkd_ctrl_pc_nc.sv "$out/src0/"
mut(){ # n old new (qkd_ctrl_pc_nc.sv)
 mkdir -p "$out/src$1";cp "$out/src0/"*.sv "$out/src$1/"
 python3 - "$out/src$1/qkd_ctrl_pc_nc.sv" "$2" "$3" <<'PY'
import sys
p,o,n=sys.argv[1:];t=open(p).read();assert t.count(o)==1,o;open(p,'w').write(t.replace(o,n))
PY
}
mut 1 'else if (static_owner_q) boot_win <= 1'"'"'b0;' 'else if (1'"'"'b0) boot_win <= 1'"'"'b0;'   # never closes
mut 2 'if (!h_rn) boot_win <= 1'"'"'b1;' 'if (!h_rn) boot_win <= 1'"'"'b0;'                         # disabled
build(){ "$v" --binary --timing -O2 -Wno-fatal -j 4 --top-module tb_kv_boot_window_lockstep --Mdir "$out/obj$1" $pcs \
   "$out/src$1/qkd_ctrl_pc_nc.sv" $S/qkd_static_kv_pc_path_nc.sv "$out"/ref/*.sv $T/tb_kv_boot_window_lockstep.sv \
   > "$out/build$1.log" 2>&1; }
for m in 0 1 2;do build $m & done;wait
for m in 0 1 2;do [[ -x "$out/obj$m/Vtb_kv_boot_window_lockstep" ]]||{ tail -20 "$out/build$m.log";echo FAIL build$m;exit 1;};done
run(){ # tag model pc jit args...
 local tag=$1 m=$2 pc=$3 j=$4;shift 4
 "$out/obj$m/Vtb_kv_boot_window_lockstep" +IMAGE="$out/image$pc.hex" +PC=$(( pc % 32 )) +JIT=$j "$@" > "$out/run_${tag}.log" 2>&1||true; }
for pc in 0 45 127;do for j in 0 16;do
 run eq_pc${pc}_j${j}_p0 0 $pc $j +PRE=0 +PRE_ES=0 +PRE_STRICT=1 &
 run eq_pc${pc}_j${j}_p3000 0 $pc $j +PRE=3000 +PRE_ES=0 +PRE_STRICT=1 &
done;done
run dis_pc45 2 45 0 +PRE=3000 +PRE_ES=1 +PRE_STRICT=1 &
run dis_pc0_j16 2 0 16 +PRE=3000 +PRE_ES=1 +PRE_STRICT=1 &
run act_pc45 0 45 0 +PRE=3000 +PRE_ES=1 +CMP_POST=0 &
run mut1_pc45 1 45 0 +PRE=0 +PRE_ES=0 &
wait
ok=1
for f in "$out"/run_eq_*.log "$out"/run_dis_*.log;do r=$(grep -E '^(PASS|FAIL)' "$f"|tail -1);p=$(grep '^PHASE_P' "$f"||true)
 echo "== $(basename $f .log): $r | $p";grep -q '^PASS KV_BOOT_WINDOW_LOCKSTEP' "$f"&&! grep -q '^FAIL' "$f"||ok=0;done
f="$out/run_act_pc45.log";p=$(grep '^PHASE_P' "$f"||true);echo "== act_pc45 (window activity): $p"
bc=$(sed -n 's/.*boot_cols_pre=\([0-9]*\).*/\1/p' <<<"$p");[[ ${bc:-0} -gt 0 ]]||{ echo "window issued no boot column";ok=0;}
f="$out/run_mut1_pc45.log";echo "== mutant 1 (window never closes): $(grep -E '^(PASS|FAIL)' "$f"|tail -1)";grep -q '^FAIL LOCKSTEP' "$f"||ok=0
"$v" --lint-only -Wno-fatal -Wno-lint -Wno-style --top-module qkd_static_kv_pc_path_fan_nc $pcs $S/qkd_ctrl_pc_nc.sv \
  $S/qkd_static_kv_pc_path_nc.sv $E/qkd_embedding_static_map.sv $E/qkd_static_kv_pc_es_merge.sv $E/qkd_kv_pc_chain_station.sv \
  $E/qkd_static_kv_pc_path_fan_nc.sv > "$out/parent-lint.log" 2>&1 || ok=0
grep -qE '%Error|PINMISSING|PINNOTFOUND|PINCONNECTEMPTY' "$out/parent-lint.log"&&{ grep -m5 -E '%Error|PIN' "$out/parent-lint.log";ok=0;}
rm -rf "$out"/obj*
[[ $ok == 1 ]]||{ echo FAIL KV_BOOT_WINDOW;exit 1;}
echo PASS KV_BOOT_WINDOW_LOCKSTEP_EQ_DIS_ACTIVE_MUTANT_OBSERVED_PARENT_ELABORATES
