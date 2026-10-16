#!/usr/bin/env bash
# H-NETLIST/COLL-LANE 1045: ot_hgi_coll_tkm_buffer bench = the static TKM engine (tb_hgi_coll_tkm_static, actual
# tkm_static + 32 tkm tiles + THIS buffer with both real 1024x256 SRAMs) on the synthetic production-shaped and edge
# vectors of tools/hgi_coll_tkm_vectors.py (golden = tools/hgi_sim u_coll_topk_merge).
#   run_tkbuf_bench.sh OUT pos      every case PASS            -> TKBUF_BENCH_PASS cases<n> words<w>
#   run_tkbuf_bench.sh OUT bufmut   buffer MUT=1 (read address bit 0 flipped) built instead -> exit 1 TKBUF_MUTANT_REJECTED
set -euo pipefail
OUT=$(realpath -m "${1:?out}"); MODE=${2:-pos}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
C=rtl/hbm_accel/generic/collective
python3 tools/hgi_coll_tkm_vectors.py --out "$OUT/vec" > "$OUT/vec.log" 2>&1 || { tail "$OUT/vec.log"; exit 2; }
BUF=$C/tkm/ot_hgi_coll_tkm_buffer.sv
if [ "$MODE" = bufmut ]; then sed 's/parameter integer MUT=0/parameter integer MUT=1/' "$BUF" > "$OUT/buf_mut.sv"; BUF=$OUT/buf_mut.sv
 grep -q 'parameter integer MUT=1' "$BUF" || { echo "mutant not applied"; exit 2; }; fi
"$V" --binary --timing --hierarchical -j "${JOBS:-8}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT \
 --top-module tb_hgi_coll_tkm_static -Mdir "$OUT/obj" "$C/p2p/qtkm_hier.vlt" "$C/tkm/tb_hgi_coll_tkm_static.sv" \
 "$C/tkm/ot_hgi_coll_tkm_static.sv" "$C/tkm/ot_hgi_coll_tkm.sv" "$BUF" rtl/lib/ot_rst_relay.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$OUT/build.log" 2>&1 \
 || { tail -30 "$OUT/build.log"; exit 2; }
n=0; bad=0; words=0
for d in "$OUT"/vec/*/; do c=$(basename "$d"); [ -f "$d/cfg.hex" ] || continue
 set +e; "$OUT/obj/Vtb_hgi_coll_tkm_static" +DIR="$d" > "$OUT/$c.log" 2>&1; rc=$?; set -e
 n=$((n+1)); l=$(grep -E 'TKM_STATIC (PASS|FAIL)' "$OUT/$c.log" | tail -1 || true); echo "$c rc$rc $l"
 if [ $rc = 0 ] && [[ "$l" == "TKM_STATIC PASS"* ]]; then w=$(sed -n 's/.*words=\([0-9]*\).*/\1/p' <<<"$l"); words=$((words+${w:-0})); else bad=$((bad+1)); fi
done
[ $n -gt 0 ] || { echo "no vectors"; exit 2; }
if [ "$MODE" = bufmut ]; then [ $bad -gt 0 ] && { echo "TKBUF_MUTANT_REJECTED failed$bad/$n"; exit 1; } || { echo "TKBUF_MUTANT_SURVIVED"; exit 0; }; fi
[ $bad = 0 ] && echo "TKBUF_BENCH_PASS cases$n words$words" || { echo "TKBUF_BENCH_FAIL bad$bad/$n"; exit 1; }
