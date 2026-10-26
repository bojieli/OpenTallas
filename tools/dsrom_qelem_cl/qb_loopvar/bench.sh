#!/bin/bash
# S81-CORE-LAT-R2/LV bench: tb_qxpq_loopvar (q element NEW RTL vs OLD RTL renamed *_old), Verilator 5.050.
#   bench.sh REPO OLD_SHA NEW_ROOT WORK      REPO = git repo holding OLD_SHA; NEW_ROOT = source tree (rtl/, tools/) at the new sha
# Runs: S81 die params x seeds 1 2 3 4 (60k-cycle-class runs each), and the negative control (TB_MUT, must FAIL).  BENCH_RC 0 = all OK.
set -u
R=$(cd "$1" && pwd); OLD=$2; S=$(cd "$3" && pwd); W=$4; mkdir -p "$W"; W=$(cd "$W" && pwd)
D=$(cd "$(dirname "$0")" && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$D/mk_old.sh" "$R" "$OLD" "$W/old" || exit 2
L=$(cat "$D/rtl_list.txt"); F=""; FO=""
for f in $L; do F="$F $S/$f"; FO="$FO $W/old/$f"; done
TB=$D/tb_qxpq_loopvar.sv
"$V" --version
build() { local n=$1; shift
  "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_qxpq_loopvar --Mdir "$W/$n" -j 16 -CFLAGS -O1 \
    "$@" $F $FO "$TB" > "$W/$n.build.log" 2>&1 || { echo "BUILD_FAIL $n"; tail -20 "$W/$n.build.log"; return 1; }
}
run() { # name expect seed
  "$W/$1/Vtb_qxpq_loopvar" +seed=$3 > "$W/$1_s$3.log" 2>&1
  local v=$(grep -o "QXPQ_LV \(PASS\|FAIL\)" "$W/$1_s$3.log" | tail -1)
  local ok=0; [ "$v" = "QXPQ_LV PASS" ] && [ "$2" = pass ] && ok=1; [ "$v" = "QXPQ_LV FAIL" ] && [ "$2" = fail ] && ok=1
  echo "$1 seed $3 expect $2 -> ${v:-NO_VERDICT} $([ $ok = 1 ] && echo OK || echo BAD)"
  grep '^QXPQ_LV cycles' "$W/$1_s$3.log"
  [ $ok = 1 ]
}
build pass || exit 2; build mut +define+TB_MUT || exit 2
rc=0
for s in 1 2 3 4; do run pass pass $s || rc=1; done
run mut fail 1 || rc=1
echo "BENCH_RC $rc"; exit $rc
