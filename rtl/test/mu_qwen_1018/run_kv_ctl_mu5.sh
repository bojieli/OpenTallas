#!/bin/bash
# KV-GRP-CTL/MU5 10-19: lockstep benches of the mu5 structural successors (Verilator 5.050, the closure daemon's version).
#   usage: run_kv_ctl_mu5.sh ROOT OUT CASE
#   CASE: lprg  (PASS: qkd_static_kv_layer_programme_mus == qkd_static_kv_layer_programme_mu MU 1, every output, every edge)
#         wprg  (PASS: qkd_kv_native_programme SRAM 1 / RCOPIES 3 == SRAM 0, every output, every edge)
#         mutants (must FAIL with 'FAIL KV_(LPRG|WPRG)_MU5_LOCKSTEP mismatches[1-9]'):
#           l_off  rows store r - 1 instead of r - 2 (event flags one edge late)
#           l_row  a wait-expiry begin reads the row of c_stage, not c_stage - 1 (wrong stage row after a gap)
#           l_gap  every context takes user 0's next-gap field from the row
#           l_wx   the registered wait expiry predicts c_cnt == 1 instead of 2 (stage begins one edge late)
#           w_row  wprg root row read at selected_stage, not selected_stage - 1
# Every file a case reads is in lists/<tb>.f.
set -u
ROOT=$(cd "${1:?root}" && pwd); OUT=${2:?out}; CASE=${3:?case}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
L=$(dirname "$(readlink -f "$0")")/lists
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
LP=rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_layer_programme_mus.sv
WP=rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv
TB=tb_kv_lprg_mu5_lockstep; MF=""; FROM=""; TO=""
case "$CASE" in
 lprg) ;;
 wprg) TB=tb_kv_wprg_mu5_lockstep;;
 l_off) MF=$LP; FROM="w_data<=row_acc?(data_q[31:0]-32'd2)"; TO="w_data<=row_acc?(data_q[31:0]-32'd1)";;
 l_row) MF=$LP; FROM="(f_wx[k]?c_stage[k]-6'd1:c_stage[k])"; TO="(f_wx[k]?c_stage[k]:c_stage[k])";;
 l_gap) MF=$LP; FROM="ng[k]<=rowb[32+32*k+:32];ngz[k]<=rowb[160+k];ngone[k]<=rowb[164+k];"; TO="ng[k]<=rowb[32+:32];ngz[k]<=rowb[160];ngone[k]<=rowb[164];";;
 l_wx) MF=$LP; FROM="if(c_wait[k])f_wx[k]<=c_cnt[k]==2;"; TO="if(c_wait[k])f_wx[k]<=c_cnt[k]==1;";;
 w_row) TB=tb_kv_wprg_mu5_lockstep; MF=$WP; FROM=".r_addr_in({1'b0,selected_stage-6'd1})"; TO=".r_addr_in({1'b0,selected_stage})";;
 *) echo "MU5 $CASE: unknown case"; exit 2;;
esac
W="$OUT/src_$CASE"; rm -rf "$W"; mkdir -p "$W"
while read -r f; do mkdir -p "$W/$(dirname "$f")"; cp "$ROOT/$f" "$W/$f"; done < "$L/$TB.f"
if [ -n "$MF" ]; then
  python3 - "$W/$MF" "$FROM" "$TO" <<'PY' || { echo "MU5 $CASE: mutation did not apply"; exit 2; }
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
  || { echo "MU5 $CASE: BUILD-ERR"; tail -20 "$OUT/$CASE.build"; exit 1; }
./obj/sim +verilator+seed+$((0x5eed)) > "$OUT/$CASE.log" 2>&1; rc=$?
cat "$OUT/$CASE.log"
rm -rf "$W/obj"
[ $rc = 0 ] && grep -q '^PASS' "$OUT/$CASE.log"
