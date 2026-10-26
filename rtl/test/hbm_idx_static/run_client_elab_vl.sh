#!/usr/bin/env bash
# Full elaboration of ot_hbm_idx_client_static with a second tool (Verilator --lint-only, every real child, no
# blackboxes) and a third (yosys hierarchy -check). Same source list as run_client_elab.sh (iverilog, which ran >2 h).
# PASS requires: Verilator exit 0 with no %Error, no PINNOTFOUND/PINMISSING on any instance, and yosys hierarchy -check
# resolving every module of the top. Usage: run_client_elab_vl.sh OUT [vl|yosys|both]
set -u
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-client-vl}"); mode=${2:-both}; mkdir -p "$out"
src=$(sed -n '/^src=(/,/)$/p' rtl/test/hbm_idx_static/run_client_elab.sh | tr -d '()' | sed 's/^src=//' | tr '\n' ' ')
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
sha256sum $src > "$out/sources.sha256"; rc=0
if [ "$mode" != yosys ]; then
  /usr/bin/time -v "$vl" --lint-only -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM \
    -Wno-UNDRIVEN -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-PINCONNECTEMPTY -Wno-GENUNNAMED -Wno-VARHIDDEN \
    --top-module ot_hbm_idx_client_static $src > "$out/vl.log" 2>&1; vrc=$?
  nerr=$(grep -c '^%Error' "$out/vl.log"); npin=$(grep -cE '%Warning-(PINMISSING|PINNOTFOUND)' "$out/vl.log")
  grep -E '^%(Error|Warning-(PINMISSING|PINNOTFOUND|WIDTH|MULTIDRIVEN|IMPLICIT))' "$out/vl.log" | head -40
  grep 'Maximum resident' "$out/vl.log"
  echo "VL rc=$vrc errors=$nerr pin_missing_or_notfound=$npin"
  [ "$vrc" = 0 ] && [ "$nerr" = 0 ] && [ "$npin" = 0 ] && echo IDX_CLIENT_ELAB_VERILATOR PASS || { echo IDX_CLIENT_ELAB_VERILATOR FAIL; rc=1; }
fi
if [ "$mode" != vl ]; then
  /usr/bin/time -v yosys -q -l "$out/yosys.log" -p "read_verilog -sv -defer $src; hierarchy -check -top ot_hbm_idx_client_static; stat" \
    > "$out/yosys.out" 2>&1; yrc=$?
  grep -iE 'error|not part of the design|missing' "$out/yosys.log" | head -20; grep 'Maximum resident' "$out/yosys.out"
  echo "YOSYS rc=$yrc"; [ "$yrc" = 0 ] && echo IDX_CLIENT_ELAB_YOSYS PASS || { echo IDX_CLIENT_ELAB_YOSYS FAIL; rc=1; }
fi
exit $rc
