#!/usr/bin/env bash
# usage: OUT
# RTL-BUILD-KV/BOOT 2026-10-18 (results/arch/qwen_kv_boot_path_1018/note.md): the static KV die's boot paths into HBM.
#  (1) tb_kv_boot_lockstep: runtime unchanged -- the boot-capable chain (root2_b, fan_stack_b, station_b, es merge _b)
#      equals the current chain bit for bit every edge with the boot face idle (4 x 32 PCs); boot / writer collision
#      faults; clean boot words reach exactly their station.  Mutants 7 (stack strap), 1 (root: no collision fault),
#      6 (station: pc[3:0] tap) FAIL.
#  (2) tb_kv_boot_pc: end to end on one stack with the 32 REAL HOST slices: cold boot, HOST KV writes, embedding image
#      load via the gateway / chain / slice landing source, est ready, run-phase reads find the boot data, re-load,
#      run-phase host word and wrong checksum fault.  Mutants 11..17 FAIL.
#  (3) the per-PC parent successor qkd_static_kv_pc_path_fan_nc_b elaborates with every pc_path source.
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
E=rtl/qwen_sys/static_embedding_20261014;S=rtl/qwen_sys/static_kv_20261014;D=rtl/qwen_sys/static_kv_die_20261017
P=rtl/qwen_sys/split_20261014;H=rtl/qwen_sys/host_20261013;T=rtl/test/qwen_static_kv
PK=rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv
lock=($D/qkd_kv_ctl_half_root.sv $D/qkd_kv_ctl_half_root_b.sv $E/qkd_kv_pc_chain_station.sv $E/qkd_kv_pc_chain_station_b.sv
      $E/qkd_embedding_static_map.sv $E/qkd_static_kv_pc_es_merge.sv $E/qkd_static_kv_pc_es_merge_b.sv $T/tb_kv_boot_lockstep.sv)
pcb=($PK $E/qkd_embgw_boot_s.sv $D/qkd_kv_ctl_half_root_b.sv $E/qkd_kv_pc_chain_station_b.sv $E/qkd_embedding_static_map.sv
     $E/qkd_static_kv_pc_es_merge.sv $E/qkd_static_kv_pc_es_merge_b.sv $P/qkd_host_pc_slice_die.sv $P/qkd_host_pc_slice.sv
     $H/qkd_host_ingest_station.sv $H/qkd_host_static_pc_emback.sv $P/qkd_hbm_boot_static_completion.sv
     $P/qkd_hbm_boot_static.sv $P/qkd_hbm_boot_pc.sv $P/qkd_static_completion_ownerdemux.sv $T/tb_kv_boot_pc.sv)
run(){ # name top mut sources...
 local n=$1 top=$2 m=$3;shift 3
 "$v" --binary -j 4 --timing -O1 -Wno-fatal --top-module $top -DOT_BOOT_MUT=$m \
   --Mdir "$out/$n$m-obj" "$@" > "$out/$n$m-build.log" 2>&1 || { echo "BUILD FAIL $n$m" > "$out/$n$m.log"; return; }
 "$out/$n$m-obj/V$top" > "$out/$n$m.log" 2>&1 || true
 rm -rf "$out/$n$m-obj"; }
LM=${LM:-0 7 1 6};PM=${PM:-0 11 12 13 14 15 16 17}
for m in $LM;do run lock tb_kv_boot_lockstep $m "${lock[@]}" & done
for m in $PM;do run pc tb_kv_boot_pc $m "${pcb[@]}" & done
wait
[[ -n ${SMOKE:-} ]]&&{ for f in "$out"/*.log;do echo "== $f: $(grep -E '^(PASS|FAIL|BUILD)' $f|tail -1)";done;exit 0;}
ok=1
for n in lock0 pc0;do echo "== $n: $(grep -E '^(PASS|FAIL|BUILD)' "$out/$n.log" | tail -1)";grep -q '^PASS' "$out/$n.log"&&! grep -q '^FAIL' "$out/$n.log"||ok=0;done
for n in lock7 lock1 lock6 pc11 pc12 pc13 pc14 pc15 pc16 pc17;do echo "== $n: $(grep -E '^(FAIL|PASS|BUILD)' "$out/$n.log" | tail -1)";grep -q '^FAIL' "$out/$n.log"||ok=0;done
pcs=$(python3 -c "import sys;sys.path.insert(0,'tools/qwen_kv_die');from static_pc_path_sources import SOURCES;print(' '.join(SOURCES))")
"$v" --lint-only -Wno-fatal -Wno-lint -Wno-style --top-module qkd_static_kv_pc_path_fan_nc_b $pcs $S/qkd_ctrl_pc_nc.sv \
  $S/qkd_static_kv_pc_path_nc.sv $E/qkd_embedding_static_map.sv $E/qkd_static_kv_pc_es_merge.sv $E/qkd_static_kv_pc_es_merge_b.sv \
  $E/qkd_kv_pc_chain_station_b.sv $E/qkd_static_kv_pc_path_fan_nc_b.sv > "$out/parent-lint.log" 2>&1 || ok=0
grep -qE '%Error|PINMISSING|PINNOTFOUND|PINCONNECTEMPTY' "$out/parent-lint.log"&&ok=0
echo "== parent lint: $(grep -cE '%Error' "$out/parent-lint.log" || true) errors"
[[ $ok == 1 ]]||{ echo FAIL KV_BOOT_GATE;exit 1;}
echo PASS KV_BOOT_GATE_LOCKSTEP_RUNTIME_UNCHANGED_BOOT_END_TO_END_MUTANTS_OBSERVED_PARENT_ELABORATES
