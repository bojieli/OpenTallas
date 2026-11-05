#!/bin/bash
# DIE-S81-56/IQKV (11-04): c2c5_lag.sh OUTDIR (repo root, on the fleet). capc5r tied vs capc2_w3 (tb_c2c5_lag.sv): one fixed capture lag.
# Exit 0 iff every CMUT 0 seed PASSES at lag 6 and the live-lane mutant FAILS.  env N (default 200000), SEEDS (default "1 2 3").
set -u; O=$1; mkdir -p "$O"; N=${N:-200000}; SEEDS=${SEEDS:-1 2 3}
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
S=rtl/dsrom_sys/s81_dv/slice; T=tools/s81_slice/cap_end
F="rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/hdc/ot_hdc_cg.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv
 $S/ot_s81sl_cap_tr.sv $S/ot_s81sl_cap_ld.sv $S/ot_s81sl_cap_ed.sv $S/ot_s81sl_cap_rt.sv $S/cap_end/ot_s81_retn_fwd.sv $S/cap_end/ot_s81sl_cap_trn.sv
 $S/cap_end/ot_s81sl_cap_rt_w.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_rst_copy.sv
 $S/lp/ot_s81sl_capc5r.sv $S/cap_end/ot_s81sl_capc2_w3.sv $S/cap_end/ot_s81sl_cap_end.sv"
rc=0
for s in $SEEDS; do for M in 0 1; do
  [ $M = 1 ] && [ "$s" != "${SEEDS%% *}" ] && continue
  B=$O/o_${s}_$M
  $V --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --build-jobs ${J:-4} -GN=$N -GSEED=$s -GCMUT=$M --top-module tb_c2c5_lag -Mdir "$B" $F $T/tb_c2c5_lag.sv > "$B.build.log" 2>&1 \
    || { echo "BUILD_FAILED $s $M"; grep -m6 "%Error" "$B.build.log"; exit 3; }
  "$B/Vtb_c2c5_lag" > "$O/run_${s}_$M.log" 2>&1
  l=$(grep -h C2C5_LAG "$O/run_${s}_$M.log"); echo "$l"
  if [ $M = 0 ]; then echo "$l" | grep -q " PASS .* lag 6 " || rc=1; else echo "$l" | grep -q " FAIL " || { echo MUTANT_NOT_CAUGHT; rc=1; }; fi
done; done
echo "C2C5_LAG_EXIT $rc"; exit $rc
