#!/usr/bin/env bash
# usage: OUT
# KVJ-C3: the static PC chain against its join model (tools/qwen_kv_die/kvjc3_pc_chain.py).
#  (1) writer lane -> 128-PC fan-out: real native writer -> root -> 4 x 32 stations -> es merges -> controller intake
#      check copy; exact PC / edge / bits.  Mutants 1 (pc alias), 2 (lanes 2/3 dropped), 5 (context not lagged) FAIL.
#  (2) embedding slot player: root -> stations -> es merges -> fixed-latency controller model -> real return trains ->
#      join4_cal; every join word at the model's edge with exact data.  Mutants 3 (late transfer), 4 (scale home
#      ignores the stack), 6 (beat calendar one short) FAIL.
#  (3) the pc_path successor parent elaborates with every pc_path source.
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
E=rtl/qwen_sys/static_embedding_20261014;S=rtl/qwen_sys/static_kv_20261014;T=rtl/test/qwen_static_kv
python3 tools/qwen_kv_die/kvjc3_pc_chain.py --ctrl-lat 92 --out "$out/model"
fan=(rtl/lib/ot_rst_relay.sv $S/qkd_kv_static_writer.sv rtl/physical/ot_qkd_kv_static_writer_native.sv $S/qkd_kv_es_fan_root.sv
     $E/qkd_kv_pc_chain_station.sv $E/qkd_embedding_static_map.sv $E/qkd_static_kv_pc_es_merge.sv $T/tb_kvjc3_es_fanout.sv)
emb=($S/qkd_kv_es_fan_root.sv $E/qkd_kv_pc_chain_station.sv $E/qkd_embedding_static_map.sv $E/qkd_static_kv_pc_es_merge.sv
     $E/qkd_embedding_static_return_head.sv $E/qkd_embedding_static_return_hop.sv $E/qkd_embedding_static_join.sv
     $E/qkd_embedding_static_join4.sv $E/qkd_embedding_static_join4_cal.sv $T/tb_kvjc3_emb_player.sv)
run(){ # name top mut sources...
 local n=$1 top=$2 m=$3;shift 3
 "$v" --binary --timing -O1 -Wno-fatal --top-module $top -DOT_KVJC3_MUT=$m -DOT_KVJC3_DIR=\"$out/model\" \
   --Mdir "$out/$n$m-obj" "$@" > "$out/$n$m-build.log" 2>&1
 "$out/$n$m-obj/V$top" > "$out/$n$m.log" 2>&1 || true
 rm -rf "$out/$n$m-obj"; }
for m in 0 1 2 5;do run fan tb_kvjc3_es_fanout $m "${fan[@]}" & done
for m in 0 3 4 6;do run emb tb_kvjc3_emb_player $m "${emb[@]}" & done
wait
ok=1
for n in fan0 emb0;do echo "== $n: $(grep -E '^(PASS|FAIL)' "$out/$n.log" | tail -1)";grep -q '^PASS' "$out/$n.log"&&! grep -q '^FAIL' "$out/$n.log"||ok=0;done
for n in fan1 fan2 fan5 emb3 emb4 emb6;do echo "== $n: $(grep -E '^FAIL' "$out/$n.log" | tail -1)";grep -q '^FAIL' "$out/$n.log"||ok=0;done
pcs=$(python3 -c "import sys;sys.path.insert(0,'tools/qwen_kv_die');from static_pc_path_sources import SOURCES;print(' '.join(SOURCES))")
"$v" --lint-only -Wno-fatal -Wno-lint -Wno-style --top-module qkd_static_kv_pc_path_fan $pcs $E/qkd_embedding_static_map.sv \
  $E/qkd_static_kv_pc_es_merge.sv $E/qkd_static_kv_pc_path_emb.sv $E/qkd_kv_pc_chain_station.sv $E/qkd_static_kv_pc_path_fan.sv \
  > "$out/parent-lint.log" 2>&1 || ok=0
grep -qE '%Error|PINMISSING|PINNOTFOUND' "$out/parent-lint.log"&&ok=0
[[ $ok == 1 ]]||{ echo FAIL KVJC3_PC_CHAIN;exit 1;}
echo PASS KVJC3_PC_CHAIN_FANOUT_PLAYER_EXACT_OBSERVED_MUTANTS_PARENT_ELABORATES
