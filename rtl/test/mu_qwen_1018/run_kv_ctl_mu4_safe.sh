#!/bin/bash
set -eu
ROOT=$(cd "${1:?}" && pwd); OUT=${2:?}; CASE=${3:?}; mkdir -p "$OUT";OUT=$(cd "$OUT" && pwd)
W="$OUT/src_$CASE";mkdir -p "$W"; cd "$W"
cp "$ROOT/rtl/qwen_sys/static_kv_20261014/qkd_static_kv_ownership.sv" original.sv
cp "$ROOT/rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_ownership_calendar_mu.sv" mu.sv
cp "$ROOT/rtl/test/mu_qwen_1018/tb_kv_ctl_mu4_safe.sv" tb.sv
python3 - "$CASE" <<'PY'
import sys
p='mu.sv';s=open(p).read();c=sys.argv[1]
a,b={'exact':('',''),'guard':("enter_guard <= data_q - 32'd2;","enter_guard <= data_q - 32'd1;"),'group':('bad_q <= bad;','bad_q <= bad & 8\'hdf;'),'copy':('halt_q[1] <= ft || (|bad);','halt_q[1] <= 0;')}[c]
if a: assert s.count(a)==1;s=s.replace(a,b)
open(p,'w').write(s)
PY
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary --timing -O2 -Wno-fatal --top-module tb_kv_ctl_mu4_safe -j 4 -Mdir obj -o sim original.sv mu.sv tb.sv > "$OUT/$CASE.build" 2>&1
set +e
./obj/sim > "$OUT/$CASE.log" 2>&1
rc=$?
cat "$OUT/$CASE.log"
exit "$rc"
