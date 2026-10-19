#!/bin/bash
# KV-CTL mu2 10-19: lockstep of the registered-timing variants bound in the MU release qkd_kvs_ctl
# (ownership calendar PIPE=1, boot dispatcher SRQ=2).  Verilator 5.050 (the closure daemon's version).
#   usage: run_kv_ctl_mu2.sh ROOT OUT CASE      CASE: tb_kv_ctl_mu2_lockstep | c1 | c2 | c3 (mutants, must FAIL)
# Every file a case reads is in lists/tb_kv_ctl_mu2_lockstep.f.
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
O_=rtl/qwen_sys/static_kv_20261014/qkd_static_kv_ownership.sv
B_=rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_dispatch.sv
TB=tb_kv_ctl_mu2_lockstep; MF=""; FROM=""; TO=""
case "$CASE" in
 tb_kv_ctl_mu2_lockstep) ;;
 # PIPE drain stage reduces one group only (a dropped group drain is missed at enter / leave)
 c1) MF=$O_; FROM='drained_all_q <= &drained_q;'; TO='drained_all_q <= drained_q[0];';;
 # PIPE enter offset not captured (native mode enters one edge late)
 c2) MF=$O_; FROM="enter_m <= data_q - ((MUT == 1) ? 32'd2 : 32'd1);"; TO='enter_m <= data_q;';;
 # SRQ one stage short (setup_ready 1 edge after the term, not 2)
 c3) MF=$B_; FROM='assign setup_ready=sr_q;'; TO='assign setup_ready=sr_int_q&&sr_ext_q;';;
 *) echo "KV_CTL_MU2 $CASE: unknown case"; exit 2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$TB.f"
if [ -n "$MF" ]; then
  python3 - "$W/$MF" "$FROM" "$TO" <<'PY' || { echo "KV_CTL_MU2 $CASE: mutation did not apply"; exit 2; }
import sys
p, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
assert s.count(a) == 1, (a, s.count(a))
open(p, "w").write(s.replace(a, b))
PY
fi
cd "$W"
"$V" --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH \
  --top-module "$TB" -Mdir obj -j 4 -o sim $(cat "$L/$TB.f") > "$OUT/$CASE.build" 2>&1 \
  || { echo "KV_CTL_MU2 $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim > "$OUT/$CASE.log" 2>&1; rc=$?
r=$(grep -E '^(PASS|FAIL)|^%Error|Fatal|fatal' "$OUT/$CASE.log" | tail -1)
echo "KV_CTL_MU2 $CASE rc=$rc: $r"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
