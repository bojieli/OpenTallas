#!/bin/bash
# KV-CTL3 10-20 (fork S32-D2): lockstep of qkd_static_kv_boot_dispatch_mu_s32 (+ qkd_static_kv_boot_dispatch_s32) vs the
# unchanged qkd_static_kv_boot_dispatch_mu (tile params), every output every edge (tb_kv_s32_boot_lockstep).  Verilator 5.050.
#   usage: run_kv_ctl_s32_d2.sh ROOT OUT CASE
#   PASS cases: d2 (seed 7), d2s (seed 1234)
#   mutants (must FAIL, regex 'FAIL KV_S32_BOOT_LOCKSTEP mismatches[1-9]'):
#     m_cw    controller_we group 3 selects the wrong addr[9] half
#     m_hold  writer data slice 2 latches on the layer-target accept
#     m_gap   MU layer-bus slice 1: g_we select arms swapped
#     m_fl    front_last groups drop the addr % 6 == 5 term
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
F=rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_s32_boot.sv
TB=tb_kv_s32_boot_lockstep; MF=""; FROM=""; TO=""; SEED=7
case "$CASE" in
 d2) ;; d2s) SEED=1234;;
 m_cw) MF=$F; FROM=".s(acc_t[T]&&addr[9]==H&&rs_s[(46+gi_)%RS])"; TO=".s(acc_t[T]&&addr[9]==((gi_==3)?!H:H)&&rs_s[(46+gi_)%RS])";;
 m_hold) MF=$F; FROM=".s((acc_t[2])&&rs_s[(5+gi_)%RS])"; TO=".s(((gi_==2)?acc_t[1]:acc_t[2])&&rs_s[(5+gi_)%RS])";;
 m_gap) MF=$F; FROM=".a(gq[LO+:W]),.b(lo_b[LO+:W])"; TO=".a((gs==1)?lo_b[LO+:W]:gq[LO+:W]),.b((gs==1)?gq[LO+:W]:lo_b[LO+:W])";;
 m_fl) MF=$F; FROM=".s(acc_t[5]&&l5&&gix[4]==gi_"; TO=".s(acc_t[5]&&gix[4]==gi_";;
 *) echo "S32D2 $CASE: unknown case"; exit 2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$TB.f"
if [ -n "$MF" ]; then python3 - "$W/$MF" "$FROM" "$TO" <<'PY' || { echo "S32D2 $CASE: substitution did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
PY
fi
cd "$W"
"$V" --version > "$OUT/verilator_version.txt"
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j 4 -o sim $(cat "$L/$TB.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "S32D2 $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim +seed=$SEED > "$OUT/$CASE.log" 2>&1; rc=$?
cat "$OUT/$CASE.log"
rm -rf "$W/obj"
