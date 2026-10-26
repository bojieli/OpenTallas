#!/bin/bash
# S81-QNTKEEP 10-18: the QNT_CB lockstep bench (tb_qnt_cb: CB256 / CB32 / CB16 candidates against the immutable
# 69c124e5d reference, all 4305 output bits every cycle) run straight from a non-git source export, as the closure
# loop runs benches.  tools/s81_suhc/qnt_cb_gate.py is the git-pinned form of the same bench.
# usage: run_direct.sh OUT_DIR MUT   (MUT 0 = exact, must print PASS QNT_CB; MUT 6 = one copied offset bit flipped,
# must print FAIL QNT_CB active_data=1)
set -o pipefail
for v in /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin; do [ -x "$v/verilator" ] && export PATH="$v:$PATH"; done
O=$1; M=${2:-0}; mkdir -p "$O"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_qnt_cb -GMUT="$M" --Mdir "$O/obj" \
  --output-split 20000 --output-split-cfuncs 200 tests/rtl/s81su_qnt_cb/reference_69c124e5d.sv \
  rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_qn.sv tests/rtl/s81su_qnt_cb/tb_qnt_cb.sv > "$O/build.log" 2>&1 \
  || { echo "QNT_CB BUILD_FAIL"; tail -20 "$O/build.log"; exit 3; }
"$O/obj/Vtb_qnt_cb" 2>&1 | tee "$O/run.log" | grep -a "QNT_CB" | cut -c1-240
