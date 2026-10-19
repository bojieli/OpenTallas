#!/bin/bash
# MU-ADOPT-KV 10-19: KV die per-user row (R6) wired into the parents.  Verilator 5.050 (the closure daemon's version).
#   usage: run_mu_kv.sh ROOT OUT CASE
#   CASE: tb_mu_kv_writer_rows | tb_mu_kv_pc_path_rows | lint_mu_kv_tiles | a mutant id below (must FAIL)
# Every file a case reads is in lists/<tb>.f (+ the compiled calendar image for the read bench).
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
W_=rtl/qwen_sys/mu_qwen_20261018/qkd_kv_static_writer_native_mu.sv
P_=rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv
IMG=results/arch/qwen_kv_static_programme_1017/die/target6.hex   # stack 0 (PCs 0..31)
TB=$CASE; MF=""; FROM=""; TO=""
case "$CASE" in
 # write wrapper: user not inserted into the es rows (users alias)
 mw1) TB=tb_mu_kv_writer_rows; MF=$W_; FROM='u_mu_es (.user(identity[44:43])'; TO='u_mu_es (.user(2'"'"'b00)';;
 # write wrapper: expected address keeps today's row (PC native check would see the wrong row)
 mw2) TB=tb_mu_kv_writer_rows; MF=$W_; FROM='u_mu_xa (.user(expected_identity[44:43])'; TO='u_mu_xa (.user(2'"'"'b00)';;
 # write wrapper: user from the wrong TAG bits (stage field, not epoch[1:0])
 mw3) TB=tb_mu_kv_writer_rows; MF=$W_; FROM='u_mu_es (.user(identity[44:43])'; TO='u_mu_es (.user(identity[38:37])';;
 # read parent: user not inserted into the KV descriptor row
 mk1) TB=tb_mu_kv_pc_path_rows; MF=$P_; FROM='static_cmd[10:9] | (mu_kv ? static_epoch[1:0] : 2'"'"'d0)'; TO='static_cmd[10:9]';;
 # read parent: user from the wrong epoch bits
 mk2) TB=tb_mu_kv_pc_path_rows; MF=$P_; FROM='(mu_kv ? static_epoch[1:0]'; TO='(mu_kv ? static_epoch[2:1]';;
 # read parent: user taken from the live calendar epoch pin, not the epoch latched at the go (not stage-latched)
 mk3) TB=tb_mu_kv_pc_path_rows; MF=$P_; FROM='(mu_kv ? static_epoch[1:0]'; TO='(mu_kv ? cal_epoch[1:0]';;
esac
[ -f "$L/$TB.f" ] || { echo "MU_KV $CASE: no list $TB"; exit 2; }
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$TB.f"
mkdir -p "$W/$(dirname $IMG)"; cp "$ROOT/$IMG" "$W/$IMG"
if [ -n "$MF" ]; then
  python3 - "$W/$MF" "$FROM" "$TO" <<'PY' || { echo "MU_KV $CASE: mutation did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
PY
fi
cd "$W"
if [ "$TB" = lint_mu_kv_tiles ]; then
  rc=0
  for top in qkd_kvs_ctl qkd_kvs_pc qkd_kvs_pc_h; do
    "$V" --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --top-module $top \
      $(cat "$L/$TB.f") > "$OUT/$CASE.$top.log" 2>&1 || rc=1
    if grep -qE '%Error|PINMISSING|PINNOTFOUND|PINCONNECTEMPTY' "$OUT/$CASE.$top.log"; then rc=1; fi
    echo "lint $top rc=$rc"
  done > "$OUT/$CASE.log"
  [ $rc = 0 ] && echo "PASS LINT_MU_KV_TILES qkd_kvs_ctl qkd_kvs_pc qkd_kvs_pc_h (tile file qkd_kvs_tiles_hroot_ff_k_mu.sv)" >> "$OUT/$CASE.log" \
    || echo "FAIL LINT_MU_KV_TILES" >> "$OUT/$CASE.log"
  echo "MU_KV $CASE: $(tail -1 "$OUT/$CASE.log")"; [ $rc = 0 ]; exit
fi
PA=""
if [ "$TB" = tb_mu_kv_pc_path_rows ]; then   # PC 13 of stack 0: its 16 x 128-b calendar words (as kvplan_ci_nc_gate.sh)
  python3 - "$W/$IMG" 13 "$W/image13.hex" <<'PY'
import sys
t, l, o = sys.argv[1], int(sys.argv[2]), sys.argv[3]
w = [int(x, 16) for x in open(t).read().split()][32 * l:32 * l + 32]
open(o, 'w').write(''.join(f'{w[n] | (w[16 + n] << 64):032x}\n' for n in range(16)))
PY
  PA="+IMAGE=$W/image13.hex +PC=13"
fi
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j 8 -o sim $(cat "$L/$TB.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "MU_KV $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim $PA > "$OUT/$CASE.log" 2>&1; rc=$?
r=$(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' "$OUT/$CASE.log" | tail -1)
echo "MU_KV $CASE rc=$rc: $r"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
