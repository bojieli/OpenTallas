#!/bin/bash
# run_es_cfg_boot.sh OUT (KVJ-SMALL b2 2026-10-17, KVJ-C3 open): the shared boot bus of the PC chain root
# (qkd_kv_es_fan_root) and join4_cal (qkd_embedding_static_join4_cal) boot-loaded through qkd_static_kv_boot_dispatch
# ESCFG=1 (image targets 12 = 1024 PC player words, 13 = 8 beat segments; order 1..9, [11,] 12, 13, 0).
#   image: tools/qwen_kv_die/kv_static_programme.es_cfg_words (= kvjc3_pc_chain.boot_words, ctrl_lat 92, relays 0)
#   (1) tb_kv_es_cfg_boot (iverilog), must PASS: SCN 0 (stream == kvjc3 boot.memh + 6 empty segments, setup_ready),
#       1 (no 12/13 refused), 2 / 3 / 5 (malformed words refused, code 5), 4 (ESCFG=0 refuses 12), 6 (with LINKCFG=1);
#       must FAIL: MUT 7 (pc/reg swapped address), MUT 8 (segment 1 dropped)
#   (2) the KVJ-C3 embedding player bench (tb_kvjc3_emb_player, full shape, verilator) fed by the dispatcher
#       (OT_KVJC3_DISP): DMUT 0 PASS (5 tokens x 65 words exact edges/data), DMUT 7 / 8 FAIL
#   (3) regressions at ESCFG=0: run_link_cfg_boot.sh (LINKCFG + KVJ-F DIECFG + KVJ-A lockstep/CDC/unit) and the
#       unchanged KVJ-C3 gate (kvjc3_pc_chain_gate.sh, direct bus)
set -u
O=$(readlink -f "$1"); mkdir -p "$O"; cd "$(dirname "$0")/../.."
S=rtl/qwen_sys/static_kv_20261014; E=rtl/qwen_sys/static_embedding_20261014; T=rtl/test/qwen_static_kv
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
rc=0
python3 tools/qwen_kv_die/kvjc3_pc_chain.py --ctrl-lat 92 --out "$O/model" > "$O/model.log" || { echo "FAIL model"; exit 1; }
python3 -c "
import sys;sys.path.insert(0,'tools/qwen_kv_die')
import kv_static_programme as P
pc,beat=P.es_cfg_words()
open('$O/model/target12.hex','w').write(''.join(f'{x:016x}\n' for x in pc))
open('$O/model/target13.hex','w').write(''.join(f'{x:016x}\n' for x in beat))" || { echo "FAIL image"; exit 1; }
run(){ # tag scn mut expect
  iverilog -g2012 -o "$O/$1" -s tb_kv_es_cfg_boot -P tb_kv_es_cfg_boot.SCN=$2 -P tb_kv_es_cfg_boot.MUT=$3 \
    $S/qkd_static_kv_boot_dispatch.sv $T/tb_kv_es_cfg_boot.sv > "$O/$1.build.log" 2>&1 || { echo "BUILD FAIL $1"; rc=1; return; }
  l=$( (cd "$O/model" && vvp -n "$O/$1") 2>&1 | tee "$O/$1.log" | grep -E '^(PASS|FAIL) kv_es_cfg_boot' | tail -1)
  echo "$1 (must $4): ${l:-no result line}"
  case "$l" in $4*) ;; *) rc=1;; esac
}
for s in 0 1 2 3 4 5 6; do run scn$s $s 0 PASS; done
run mut7 0 7 FAIL; run mut8 0 8 FAIL
emb=($S/qkd_static_kv_boot_dispatch.sv $S/qkd_kv_es_fan_root.sv $E/qkd_kv_pc_chain_station.sv $E/qkd_embedding_static_map.sv
     $E/qkd_static_kv_pc_es_merge.sv $E/qkd_embedding_static_return_head.sv $E/qkd_embedding_static_return_hop.sv
     $E/qkd_embedding_static_join.sv $E/qkd_embedding_static_join4.sv $E/qkd_embedding_static_join4_cal.sv $T/tb_kvjc3_emb_player.sv)
emb_run(){ # dmut expect
  "$v" --binary --timing -O1 -Wno-fatal --top-module tb_kvjc3_emb_player -DOT_KVJC3_MUT=0 -DOT_KVJC3_DISP -DOT_KVJC3_DMUT=$1 \
    -DOT_KVJC3_DIR=\"$O/model\" -DOT_KVJC3_DISP_DIR=\"$O/model\" --Mdir "$O/emb$1-obj" "${emb[@]}" > "$O/emb$1-build.log" 2>&1 \
    || { echo "BUILD FAIL emb$1"; echo 0 > "$O/emb$1.ok"; return; }
  "$O/emb$1-obj/Vtb_kvjc3_emb_player" > "$O/emb$1.log" 2>&1; rm -rf "$O/emb$1-obj"
  l=$(grep -E '^(PASS|FAIL)' "$O/emb$1.log" | tail -1)
  echo "emb_player via dispatcher DMUT $1 (must $2): ${l:-no result line}"
  ok=1
  if [ "$2" = PASS ]; then grep -q '^FAIL' "$O/emb$1.log" && ok=0; case "$l" in PASS*) ;; *) ok=0;; esac
  else grep -q '^FAIL' "$O/emb$1.log" || ok=0; fi
  echo $ok > "$O/emb$1.ok"
}
emb_run 0 PASS & emb_run 7 FAIL & emb_run 8 FAIL & wait
for d in 0 7 8; do [ "$(cat "$O/emb$d.ok" 2>/dev/null)" = 1 ] || rc=1; done
bash tools/qwen_static_kv/run_link_cfg_boot.sh "$O/regress_link" > "$O/regress_link.log" 2>&1 \
  && echo "regression (ESCFG=0): $(tail -1 "$O/regress_link.log")" || { echo "regression FAIL (see $O/regress_link.log)"; rc=1; }
bash tools/qwen_kv_die/kvjc3_pc_chain_gate.sh "$O/regress_c3" > "$O/regress_c3.log" 2>&1 \
  && echo "regression (C3 direct bus): $(tail -1 "$O/regress_c3.log")" || { echo "regression FAIL (see $O/regress_c3.log)"; rc=1; }
[ $rc = 0 ] && echo "PASS es_cfg_boot: 7 scenarios, mutants 7/8 caught (unit + C3 player), C3 player exact via the dispatcher, LINKCFG/DIECFG/KVJ-A/C3 regressions unchanged" || echo "FAIL es_cfg_boot"
exit $rc
