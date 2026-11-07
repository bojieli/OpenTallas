#!/bin/bash
# $0 PACKET: build the prepared nst4 age packet, then run TT and FF.
set -u
cd "$1"
export CCACHE_DISABLE=1
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --assert -Wno-fatal --top-module head_guard_tb --output-groups 4 -j 4 \
  -CFLAGS '-O1 -fno-var-tracking' -Mdir obj tb.sv controls.sv start_stages.sv ot_dp_cells.sv \
  ot_dp_clk_landing.sv ot_dp_clk_landing_ca.sv ot_meso_fifo.sv > build.log 2>&1
rc=$?; echo "$rc" > build.rc; [ "$rc" -eq 0 ] || exit "$rc"
for c in TT FF; do
  arg=''; [ "$c" = FF ] && arg=+FF
  obj/Vhead_guard_tb $arg > "$c.log" 2>&1; echo $? > "$c.rc"
done
grep -h '^AGE\|^GUARD_FINAL\|^FIRST_GUARD' TT.log | sed 's/^/TT /'
grep -h '^AGE\|^GUARD_FINAL\|^FIRST_GUARD' FF.log | sed 's/^/FF /'
