#!/bin/bash
# S81-FIX2/XG fleet round (cwd = staging dir with src/ = worktree copy): lint, native census (xgt_xo, rstopt_xo), benches.
set -u; S=$(pwd); SL=rtl/dsrom_sys/s81_dv/slice; B=$S/bench; mkdir -p $B
MB="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1_bb.v"
XS="rtl/lib/ot_rst_relay.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv $SL/ot_s81sl_rstopt_xo.sv $SL/ot_s81sl_xs4.sv $SL/ot_s81sl_xgt_xo.sv"
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
( cd src && printf '%s\n' 'module ot_lint_top; ot_s81sl_xgt_xo u_top (); endmodule' > $B/ot_lint_top.sv && $V --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top $B/ot_lint_top.sv $XS $MB > $B/lint.log 2>&1 && echo LINT_OK || { echo LINT_FAIL; head -20 $B/lint.log; } )
[ "${ONLY_LINT:-0}" = 1 ] && exit 0
cp src/results/rtl/s81_xgtxo_1021/scripts/census.sh src/results/rtl/s81_xgtxo_1021/scripts/dontuse.txt $S/
( ./census.sh xgtxo ot_s81sl_xgt_xo - $XS $MB > c_xgtxo.log 2>&1 ) &
( ./census.sh rstoptxo ot_s81sl_rstopt_xo - rtl/lib/ot_rst_relay.sv $SL/ot_s81sl_rstopt_xo.sv > c_rstoptxo.log 2>&1 ) &
cd src
for m in none xooff xoall xonoflag tiercol; do ( J=4 bash tools/s81_slice/rstopt_xo_bench.sh $B/rstopt_xo $m > $B/rstopt_xo_$m.log 2>&1; echo "rc $?" >> $B/rstopt_xo_$m.log ) & done
( J=16 bash tools/s81_slice/xgtxo_bench.sh $B/xgtxo > $B/xgtxo_bench.log 2>&1; echo "rc $?" >> $B/xgtxo_bench.log ) &
( J=8 bash tools/s81_slice/xs4_equiv.sh $B/xs4_equiv > $B/xs4_equiv_base.log 2>&1; echo "rc $?" >> $B/xs4_equiv_base.log ) &
for m in bank off qswap wcopy tpar exp; do ( J=4 bash tools/s81_slice/xs4_equiv.sh $B/xs4_equiv_$m $m > $B/xs4_equiv_$m.log 2>&1; echo "rc $?" >> $B/xs4_equiv_$m.log ) & done
wait
cd $S; for f in c_*.log; do echo "== $f"; grep -E "^CENSUS|^   [0-9]|^DONE|Chip area" $f | head -20; done
for f in $B/*.log; do echo "== $(basename $f): $(tail -n 2 $f | tr '\n' ' ')"; done
echo ROUND_DONE
