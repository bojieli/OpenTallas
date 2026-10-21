#!/bin/bash
# KV-PEER13 10-21: Yosys declare-before-use check of the MU g_mu blocks.  usage: yosys_dbu.sh ROOT OUT
# Per module: read_verilog -defer -sv -DSYNTHESIS <its file>; hierarchy -top <module> -chparam MU 1; proc
# (elaborates g_mu; a use before declaration fails "Failed to detect width of signal access g_mu.x" or similar).
# Then the whole MU 1 qkd_hr_core_peer (lists/lint_peer_mu.f) with hierarchy -check.
# Prints "YOSYS_DBU PASS <module>" / "YOSYS_DBU FAIL <module>" per module and a final "YOSYS_DBU ALL PASS|FAIL n".
set -u
R=$(cd "${1:?root}" && pwd); O=${2:?out}; mkdir -p "$O"; O=$(cd "$O" && pwd); cd "$R"
Y=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}; [ -x "$Y" ] || Y=$(command -v yosys)
M=rtl/qwen_sys/mu_qwen_20261018; fails=0
"$Y" -V
for f in $(grep -l 'begin *: *g_mu' $M/*.sv); do
  for mod in $(grep -oE '^module +[A-Za-z0-9_]+' "$f" | awk '{print $2}'); do
    "$Y" -q -l "$O/$mod.log" -p "read_verilog -defer -sv -DSYNTHESIS $f; hierarchy -top $mod -chparam MU 1; proc" >/dev/null 2>&1; rc=$?
    # a module without an MU parameter (helpers in the same file): elaborate at its defaults
    grep -q "MU.*not found\|no parameter.*MU\|does not have a parameter" "$O/$mod.log" && \
      "$Y" -q -l "$O/$mod.log" -p "read_verilog -defer -sv -DSYNTHESIS $f; hierarchy -top $mod; proc" >/dev/null 2>&1 && rc=0
    if [ $rc = 0 ]; then echo "YOSYS_DBU PASS $mod"; else echo "YOSYS_DBU FAIL $mod: $(grep -m1 -E 'ERROR' "$O/$mod.log")"; fails=$((fails+1)); fi
  done
done
L=rtl/test/mu_qwen_1018/lists/lint_peer_mu.f
"$Y" -q -l "$O/qkd_hr_core_peer.log" -p "read_verilog -defer -sv -DSYNTHESIS $(grep -v '^#' $L | grep -v '_bb.v$' | tr '\n' ' '); hierarchy -top qkd_hr_core_peer; proc" >/dev/null 2>&1
if [ $? = 0 ]; then echo "YOSYS_DBU PASS qkd_hr_core_peer (MU 1, lint_peer_mu.f)"; else echo "YOSYS_DBU FAIL qkd_hr_core_peer: $(grep -m1 -E 'ERROR' "$O/qkd_hr_core_peer.log")"; fails=$((fails+1)); fi
[ $fails = 0 ] && echo "YOSYS_DBU ALL PASS" || echo "YOSYS_DBU ALL FAIL $fails"
