#!/bin/bash
# KV-CTL3 10-20: lockstep of qkd_static_kv_ownership_calendar_mu_s32 S32 1 vs qkd_static_kv_ownership_calendar_mu
# (MU 1 PIPE 1 SAFE 1 RCOPIES 12, the tile form): every output every edge (tb_kv_own_s32_lockstep).  Verilator 5.050.
#   usage: run_kv_ctl_s32_d.sh ROOT OUT CASE
#   PASS case: own
#   mutants (must FAIL, regex 'FAIL KV_OWN_S32_LOCKSTEP mismatches[1-9]'):
#     m_os1  leave bank slice 2 (leave_m low half) loads the inverted source
#     m_os2  deadline bank slice 2 (deadline_m low half) written on the leave-root write
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
MS=rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_s32_misc.sv; TB=tb_kv_own_s32_lockstep
MF=""; FROM=""; TO=""
case "$CASE" in
 own) ;;
 m_os1) MF=$MS; FROM=".a(s1[16*gs +: 16])"; TO=".a((gs == 2) ? ~s1[16*gs +: 16] : s1[16*gs +: 16])";;
 m_os2) MF=$MS; FROM=".s(en2 && rs_s[12+gs])"; TO=".s(((gs == 2) ? en1 : en2) && rs_s[12+gs])";;
 *) echo "S32D $CASE: unknown case"; exit 2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$TB.f"
if [ -n "$MF" ]; then python3 - "$W/$MF" "$FROM" "$TO" <<'PY' || { echo "S32D $CASE: substitution did not apply"; exit 2; }
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
  || { echo "S32D $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim +verilator+seed+$((0x5eed)) > "$OUT/$CASE.log" 2>&1; rc=$?
cat "$OUT/$CASE.log"
rm -rf "$W/obj"
