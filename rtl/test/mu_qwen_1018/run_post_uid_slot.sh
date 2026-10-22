#!/bin/bash
# KV-HOST2 10-19: MU4 POST UID binding bench (tb_post_uid_slot) on Verilator 5.050 (the closure daemon's version).
# usage: run_post_uid_slot.sh ROOT OUT CASE
#   PASS : exact (UID_SLOT 1) | neg_slot4 | neg_poshi | neg_uidx (each must see the sticky fault)
#   FAIL : legacy_rawpos (UID_SLOT 0 = existing pos[17:16] decode on the real observer's raw positions: users 1-3 alias
#          user 0 -- the model 164138243 contract mismatch) | m2 (MUT 2 legacy decode in slot mode) | m3 (MUT 3 slot range
#          check removed, run on neg_slot4)
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
M=$ROOT/rtl/qwen_sys/mu_qwen_20261018; HI=$ROOT/rtl/qwen_sys/host_integrated_20261014
SRCS="$ROOT/rtl/test/mu_qwen_1018/tb_post_uid_slot.sv $M/qkd_host_post_collector_mu.sv $HI/qkd_host_post_collector.sv"
G="-GUID_SLOT=1 -GMUT=0"; PA=""
case "$CASE" in
 exact) ;;
 neg_slot4) PA=+NEG_SLOT4;; neg_poshi) PA=+NEG_POSHI;; neg_uidx) PA=+NEG_UIDX;;
 legacy_rawpos) G="-GUID_SLOT=0 -GMUT=0";;
 m2) G="-GUID_SLOT=1 -GMUT=2";;
 m3) G="-GUID_SLOT=1 -GMUT=3"; PA=+NEG_SLOT4;;
 *) echo "unknown case $CASE"; exit 2;;
esac
"$V" --version
"$V" --binary -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_post_uid_slot $G \
  --Mdir "$OUT/obj_$CASE" $SRCS > "$OUT/build_$CASE.log" 2>&1 || { tail -n 30 "$OUT/build_$CASE.log"; echo "POST_UID_SLOT FAIL build"; exit 1; }
"$OUT/obj_$CASE/Vtb_post_uid_slot" $PA | tee "$OUT/$CASE.log"
grep -q "POST_UID_SLOT PASS" "$OUT/$CASE.log"
