#!/bin/bash
# MU-KV-TOKLIST 10-19 (option b): the KV boot path loads the compiled TOKLIST layer image (per-token gap lists of the F 16
# KV-consistent frame) into qkd_static_kv_layer_programme_mu TOKLIST 1 inside the qkd_kvs_ctl _mu parent; 4 users play two
# frames.  Verilator 5.050 (the closure daemon's version).
#   usage: run_mu_kv_toklist.sh ROOT OUT CASE
#   CASE: tb_mu_kv_toklist (PASS) | a mutant id below (must FAIL; fail regex beside it)
# Every RTL file is in lists/tb_mu_kv_toklist.f; the data files are the compiler's (results/rtl/mu_qwen_1018/kvtoklist,
# emitted by tools/qwen_kv_die/kv_static_programme.py --mu-from results/arch/qwen_kv_static_programme_1017/die --toklist)
# + the die target2.hex.  TOKLIST is opt-in and the die generator does not emit it yet: this script sets it on the bench
# copy of the tile file (u_boot .TOKLIST(1), u_lprg .TOKLIST(1)); the committed tile file is unchanged.
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
K=${TL_DIR:-results/rtl/mu_qwen_1018/kvtoklist}     # TL_DIR=results/rtl/mu_qwen_1018/kvtoklist/f14: the F 14 image
DATA="$K/kv_toklist_receipt.json $K/target1.hex $K/target3.hex $K/bench_starts.txt $K/bench_events.txt $K/mut_u0hdr.hex $K/mut_collide.hex $K/mut_short.hex $K/mut_sealwrong.hex results/arch/qwen_kv_static_programme_1017/die/target2.hex"
TF=rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu.sv
TB=tb_mu_kv_toklist; IMG=$K/target1.hex; NW=$(wc -l < "$ROOT/$K/target1.hex"); H=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['frame']['H'])" "$ROOT/$K/kv_toklist_receipt.json"); WM=0; TM=0; PX=""
case "$CASE" in
 # the single-user image (seal at 326, taken as the list header)      FAIL: 'layer programme not configured .*lprg fault 04'
 kt_sealwrong) IMG=$K/mut_sealwrong.hex; NW=327;;
 # dispatcher wrapper does not forward the list words (WMUT 1)        FAIL: 'layer programme not configured .*lprg fault 01'
 kt_listnot) WM=1;;
 # header ntok0 = 1 (the latency user must have no list)              FAIL: 'layer programme not configured .*lprg fault 04'
 kt_u0hdr) IMG=$K/mut_u0hdr.hex;;
 # the last list word dropped: the seal arrives as a list word        FAIL: 'layer programme not configured .*lprg fault 04'
 kt_short) IMG=$K/mut_short.hex; NW=$((NW-1));;
 # user 1 token 0 stage 1 moved onto a user-0 event edge (no list check: the RTL's own collision fault)
 #                                                                    FAIL: 'layer programme / dispatcher fault .*lprg fault 10'
 kt_collide) IMG=$K/mut_collide.hex; PX=+NOLIST;;
 # list pointer does not wrap at the user's list end (TLMUT 1)        FAIL: 'event kinds differ from the compiled list'
 kt_nowrap) TM=1;;
 # lane select off by one (TLMUT 2)                                   FAIL: 'event kinds differ from the compiled list'
 kt_lane) TM=2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
for f in $(cat "$L/$TB.f") $DATA; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done
python3 - "$W/$TF" "$WM" "$TM" <<'PY' || { echo "MU_KV_TOKLIST $CASE: TOKLIST elaboration did not apply"; exit 2; }
import sys
p, wm, tm = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
for a, b in ((".MU(1), .WMUT(0)) u_boot", f".MU(1), .WMUT({wm}), .TOKLIST(1)) u_boot"),
             (".MU(1)) u_lprg", f".MU(1), .TOKLIST(1), .TLMUT({tm})) u_lprg")):
    assert s.count(a) == 1, (a, s.count(a))
    s = s.replace(a, b)
open(p, "w").write(s)
PY
cd "$W"
"$V" --version > "$OUT/verilator_version.txt"
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH -Wno-PINMISSING \
  --top-module "$TB" -Mdir obj -j 8 -o sim $(cat "$L/$TB.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "MU_KV_TOKLIST $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
# relative paths (cwd = $W): the bench's 128-character filename registers would truncate a long absolute path
./obj/sim +IMG=$IMG +NW=$NW +H=$H +IMG2=results/arch/qwen_kv_static_programme_1017/die/target2.hex +IMG3=$K/target3.hex \
  +STARTS=$K/bench_starts.txt +EVENTS=$K/bench_events.txt $PX > "$OUT/$CASE.log" 2>&1; rc=$?
r=$(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' "$OUT/$CASE.log" | head -1)
echo "MU_KV_TOKLIST $CASE rc=$rc: $r"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
