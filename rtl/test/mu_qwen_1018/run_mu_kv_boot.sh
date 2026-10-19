#!/bin/bash
# MU-KV-BOOT 10-19: the KV boot path loads the compiled MU layer image into qkd_static_kv_layer_programme_mu inside the
# qkd_kvs_ctl _mu parent; 4 users run per the GAP table.  Verilator 5.050 (the closure daemon's version).
#   usage: run_mu_kv_boot.sh ROOT OUT CASE
#   CASE: tb_mu_kv_boot (PASS) | a mutant id below (must FAIL; fail regex beside it)
# Every RTL file is in lists/tb_mu_kv_boot.f; the data files are the compiler's (results/rtl/mu_qwen_1018/kvboot, emitted by
# tools/qwen_kv_die/kv_static_programme.py --mu-from results/arch/qwen_kv_static_programme_1017/die) + the die target2.hex.
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
K=results/rtl/mu_qwen_1018/kvboot
DATA="$K/target1.hex $K/target3.hex $K/bench_starts.txt $K/bench_events.txt $K/mut_u0gap.hex $K/mut_collide.hex $K/mut_sealwrong.hex results/arch/qwen_kv_static_programme_1017/die/target2.hex"
TF=rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu.sv
TB=tb_mu_kv_boot; IMG=$K/target1.hex; NW=471; MF=""; FROM=""; TO=""; PX=""
case "$CASE" in
 # the single-user image (seal at 326) on the MU boot path          FAIL: 'layer programme not configured .*lprg fault 04'
 kb_sealwrong) IMG=$K/mut_sealwrong.hex; NW=327;;
 # dispatcher wrapper does not forward the GAP block                  FAIL: 'layer programme not configured .*lprg fault 01'
 kb_gapnot) MF=$TF; FROM='.MU(1), .WMUT(0)'; TO='.MU(1), .WMUT(1)';;
 # a GAP table with user 0 gap[5] = 7 (not the compiler's)            FAIL: 'user 0 differs from MU 0'
 kb_u0gap) IMG=$K/mut_u0gap.hex;;
 # user 1 stage 1 moved onto a user-0 event edge (no list check: the RTL's own collision fault)
 #                                                                    FAIL: 'layer programme / dispatcher fault .*lprg fault 10'
 kb_collide) IMG=$K/mut_collide.hex; PX=+NOLIST;;
 # KV-SRAM-CTL 10-19: the same boot through the mu6b tile storage (CTLSRAM 2, 6 x 64x128 banks)  PASS expected
 kb_ctl2) MF=rtl/test/mu_qwen_1018/tb_mu_kv_boot.sv; FROM='qkd_kvs_ctl dut('; TO='qkd_kvs_ctl #(.CTLSRAM(2)) dut(';;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
for f in $(cat "$L/$TB.f") $DATA; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done
if [ -n "$MF" ]; then
  python3 - "$W/$MF" "$FROM" "$TO" <<'PY' || { echo "MU_KV_BOOT $CASE: mutation did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
PY
fi
cd "$W"
"$V" --version > "$OUT/verilator_version.txt"
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH -Wno-PINMISSING \
  --top-module "$TB" -Mdir obj -j 8 -o sim $(cat "$L/$TB.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "MU_KV_BOOT $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim +IMG=$IMG +NW=$NW +IMG2=results/arch/qwen_kv_static_programme_1017/die/target2.hex +IMG3=$K/target3.hex \
  +STARTS=$K/bench_starts.txt +EVENTS=$K/bench_events.txt $PX > "$OUT/$CASE.log" 2>&1; rc=$?
r=$(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' "$OUT/$CASE.log" | head -1)
echo "MU_KV_BOOT $CASE rc=$rc: $r"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
