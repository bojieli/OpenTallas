#!/usr/bin/env bash
# usage: OUT
# KV-CAL15 10-20: the die-composed embedding calendar (kv_static_programme cal_deltas + kvjc3_pc_chain.emb_calendar with
# per-stack down / return relays) played on the real root -> 4 x 32 stations -> es merges -> return trains -> join4_cal
# RTL with the route-A die relay lines, the fan-root/join start skew and join4_cal PIPE_JOIN (tb_kvcal15_emb_die.sv).
# Positives (every join word at the compiled edge, exact data, no fault):
#   p_die   GEN9 i13a relays + HROOT_LAND (+1 chain / +1 return) + skew 1 + PIPE_JOIN 1  (the admitted die point)
#   p_land  HROOT_LAND alone (down 1 / return 1 on every stack, skew 0, PJ 0)             (Codex 740bde993 law)
#   p_base  GEN9 i13a relays, unlanded, PJ 0
# Mutants on p_die (must FAIL): m1 no skew, m2 return relays not compiled (LAND return missed), m3 PIPE_JOIN edge not
# priced, m4 es_cfg at relays 0 (today's production image on this die).
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --version > "$out/verilator.txt"
E=rtl/qwen_sys/static_embedding_20261014;S=rtl/qwen_sys/static_kv_20261014;T=rtl/test/qwen_static_kv
src=(rtl/lib/ot_rst_relay.sv $S/qkd_kv_es_fan_root.sv $E/qkd_kv_pc_chain_station.sv $E/qkd_embedding_static_map.sv
     $E/qkd_static_kv_pc_es_merge.sv $E/qkd_embedding_static_return_head.sv $E/qkd_embedding_static_return_hop.sv
     $E/qkd_embedding_static_join.sv $E/qkd_embedding_static_join4.sv $E/qkd_embedding_static_join4_cal.sv $T/tb_kvcal15_emb_die.sv)
DIE_DN=83,25,72,16; DIE_RT=67,21,77,32          # WS WN ES EN: i13a relay_stages + HROOT_LAND (see README)
run(){ # name mut down ret skew pj
 local n=$1 m=$2 d=$3 r=$4 k=$5 p=$6 md="$out/$1"
 python3 tools/qwen_kv_die/kvcal15_emb_die_model.py --down $d --ret $r --skew $k --pj $p --mut $m --out "$md" > "$md.model.log" 2>&1
 "$v" --binary --timing -O1 -Wno-fatal --top-module tb_kvcal15_emb_die -I"$md" -DOT_KC15_DIR=\"$md\" \
   --Mdir "$md/obj" "${src[@]}" > "$md/build.log" 2>&1 || { echo "FAIL build $n" > "$out/$n.log"; return; }
 "$md/obj/Vtb_kvcal15_emb_die" > "$out/$n.log" 2>&1 || true
 rm -rf "$md/obj"; }
run p_die 0 $DIE_DN $DIE_RT 1 1 &
run p_land 0 1,1,1,1 1,1,1,1 0 0 &
run p_base 0 82,24,71,15 66,20,76,31 1 0 &
for m in 1 2 3 4; do run m$m $m $DIE_DN $DIE_RT 1 1 & done
wait
ok=1
for n in p_die p_land p_base; do echo "== $n: $(grep -E '^(PASS|FAIL)' "$out/$n.log" | tail -1)"; grep -q '^PASS' "$out/$n.log" && ! grep -q '^FAIL' "$out/$n.log" || ok=0; done
for n in m1 m2 m3 m4; do echo "== $n: $(grep -E '^FAIL' "$out/$n.log" | tail -1)"; grep -q '^FAIL' "$out/$n.log" || ok=0; done
[[ $ok == 1 ]] || { echo FAIL KVCAL15_EMB_DIE; exit 1; }
echo PASS KVCAL15_EMB_DIE_LAND_PJ_SKEW_DIE_RELAYS_EXACT_MUTANTS_FAIL
