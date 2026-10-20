#!/bin/bash
# KV-CTL3 10-20: whole-tile lockstep qkd_kvs_ctl (mu6 members) vs qkd_kvs_ctl_s32 (tb_kv_ctl_s32_tile, every output every
# edge).  Verilator 5.050.   usage: run_kv_ctl_s32_tile.sh ROOT OUT CASE
#   PASS cases: tile0 (zero-initialised flops), first (FIRST USE: --x-initial unique + +verilator+rand+reset+2, every
#               flop / kept copy / SRAM word of both tiles starts random; 3 seeds: first, first2, first3)
#   mutants (must FAIL, regex 'FAIL KV_CTL_S32_TILE mismatches[1-9]'):
#     m_tl  layer programme: row-landing slice 7 latches the slice-8 source bits
#     m_sl  writer: es high-half slice 3 never loads
#     m_ub  fan root: the early use_b copies ignore the ph1 term
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
TB=tb_kv_ctl_s32_tile; XI=""; RR=""; SEED=$((0x5eed))
MF=""; FROM=""; TO=""
LP=rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_layer_programme_s32.sv
WR=rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_s32_writer.sv
MS=rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_s32_misc.sv
case "$CASE" in
 tile0) ;;
 first) XI="--x-initial unique"; RR="+verilator+rand+reset+2";;
 first2) XI="--x-initial unique"; RR="+verilator+rand+reset+2"; SEED=12345;;
 first3) XI="--x-initial unique"; RR="+verilator+rand+reset+2"; SEED=777;;
 m_tl) MF=$LP; FROM=".a(lsrc[LO+:W])"; TO=".a((gs==7)?lsrc[LO+16+:W]:lsrc[LO+:W])";;
 m_sl) MF=$WR; FROM="else if (hs_hi[k]) es_data[128 + LO +: W]"; TO="else if (hs_hi[k] && k != 3) es_data[128 + LO +: W]";;
 m_ub) MF=$MS; FROM="(ub_base && !(evn[(k < 10) ? 1 : 2] && MUT != 2))"; TO="(ub_base)";;
 *) echo "S32T $CASE: unknown case"; exit 2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$TB.f"
if [ -n "$MF" ]; then python3 - "$W/$MF" "$FROM" "$TO" <<'PY' || { echo "S32T $CASE: substitution did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
PY
fi
cd "$W"
"$V" --version > "$OUT/verilator_version.txt"
"$V" --binary --timing -O2 $XI -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j 8 -o sim $(cat "$L/$TB.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "S32T $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim +verilator+seed+$SEED $RR > "$OUT/$CASE.log" 2>&1; rc=$?
cat "$OUT/$CASE.log"
rm -rf "$W/obj"
