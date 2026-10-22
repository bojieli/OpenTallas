#!/bin/bash
# S81-ELEM2-XGRING fleet round (cwd = staging dir with src/ = worktree copy): lint, native census (xgr2 MAIN / xgr FB,
# rstopr), benches (rstopr + 4 mutants, xgr lockstep both variants + mutants, xs5 equivalence + 6 mutants).
set -u; S=$(pwd); SL=rtl/dsrom_sys/s81_dv/slice; B=$S/bench; mkdir -p $B
MB="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1_bb.v"
XS="rtl/lib/ot_rst_relay.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv $SL/ot_s81sl_rstopr.sv $SL/ot_s81sl_xs4.sv $SL/ot_s81sl_xs5.sv $SL/ot_s81sl_xgr.sv"
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
for T in ot_s81sl_xgr ot_s81sl_xgr2; do
( cd src && printf '%s\n' "module ot_lint_top; $T u_top (); endmodule" > $B/ot_lint_top_$T.sv && $V --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top $B/ot_lint_top_$T.sv $XS $MB > $B/lint_$T.log 2>&1 && echo LINT_OK $T || { echo LINT_FAIL $T; grep -m20 Error $B/lint_$T.log; } ); done
[ "${ONLY_LINT:-0}" = 1 ] && exit 0
cp src/results/rtl/s81_xgring_1021/scripts/census.sh src/results/rtl/s81_xgring_1021/scripts/dontuse.txt $S/
( ./census.sh xgr_fb ot_s81sl_xgr - $XS $MB > c_xgr_fb.log 2>&1 ) &
( ./census.sh xgr2_main ot_s81sl_xgr2 - $XS $MB > c_xgr2_main.log 2>&1 ) &
( ./census.sh rstopr ot_s81sl_rstopr - rtl/lib/ot_rst_relay.sv $SL/ot_s81sl_rstopr.sv > c_rstopr.log 2>&1 ) &
cd src
for m in none xooff xoall xonoflag tiercol; do ( J=4 bash tools/s81_slice/rstopr_bench.sh $B/rstopr $m > $B/rstopr_$m.log 2>&1; echo "rc $?" >> $B/rstopr_$m.log ) & done
( J=16 bash tools/s81_slice/xgr_bench.sh $B/xgr_fb > $B/xgr_fb_bench.log 2>&1; echo "rc $?" >> $B/xgr_fb_bench.log ) &
( XGR_TOP=ot_s81sl_xgr2 J=16 bash tools/s81_slice/xgr_bench.sh $B/xgr2_main > $B/xgr2_main_bench.log 2>&1; echo "rc $?" >> $B/xgr2_main_bench.log ) &
( J=8 bash tools/s81_slice/xs5_equiv.sh $B/xs5_equiv > $B/xs5_equiv_base.log 2>&1; echo "rc $?" >> $B/xs5_equiv_base.log ) &
for m in bank off qswap wcopy tpar exp; do ( J=4 bash tools/s81_slice/xs5_equiv.sh $B/xs5_equiv_$m $m > $B/xs5_equiv_$m.log 2>&1; echo "rc $?" >> $B/xs5_equiv_$m.log ) & done
wait
cd $S; for f in c_*.log; do echo "== $f"; grep -E "^CENSUS|^   [0-9]|^DONE|Chip area" $f | head -20; done
for f in $B/*.log; do echo "== $(basename $f): $(tail -n 2 $f | tr '\n' ' ')"; done
echo ROUND_DONE
