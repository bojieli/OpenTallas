#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch/codex/ds-control
P=/srv/opentallas-scratch/mtp-die-prefixpath1fc92139a
O=$D/prefix-shared-binding-r2
cd "$O"
cp "$P/inputs.hex" .
python3 prefix_shared_vectors.py
S=("$P/ot_mtp_p2_ordered_rows.sv" "$P/ot_mtp_p2_prefix.sv" "$P/ot_mtp_p2_prefix_native.sv" "$P/ot_mtp_p2_prefix_path.sv"
 "$P/ot_v41_fadd.sv" "$P/rtl/common/ot_prefix.sv" "$P/rtl/common/ot_secded.sv"
 "$P/rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv"
 "$D/coll-native-src/rtl/hdc/ot_hdc_fastfp.sv" "$D/coll-native-src/rtl/hdc/ot_hdc_prefix.sv" "$D/ot_hdc_fp32_add_lat.sv"
 "$D/adapter-src/rtl/lib/ot_reset_sync.sv" "$D/adapter-src/rtl/lib/ot_async_fifo.sv"
 "$D/adapter-src/rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv"
 "$D/ot_s81_secded.sv" "$D/ot_sram_1r1w_256x256_m2_r2c2.v"
 "$O/ot_dsrom_mtp_shared_secded_pipe.sv" "$O/ot_s81_primary_shared_last.sv"
 "$O/ot_s81_shared_publisher_plain.sv" "$O/tb_s81_prefix_shared_path.sv" "$O/ot_s81_prefix_shared_binding.sv")
sha256sum "${S[@]}" "$P/rtl/common/ot_secded_cols.svh" hdc_golden.py inputs.hex shared.hex final.hex > source.sha256
/usr/bin/time -v iverilog -g2012 -DBINDING_DUT -I"$P/rtl/common" -s tb_s81_prefix_shared_path -o base.vvp "${S[@]}" > build.log 2>&1
/usr/bin/time -v vvp base.vvp > base.log 2>&1
/usr/bin/time -v iverilog -g2012 -DBINDING_DUT -DP2_MUT_PRE_ROUND -I"$P/rtl/common" -s tb_s81_prefix_shared_path -o mut.vvp "${S[@]}" > mut.build.log 2>&1
if vvp mut.vvp > mut.log 2>&1;then echo MUTANT_UNEXPECTED_PASS;exit 1;fi
grep -q 'COMPOSE numerical' mut.log
printf 'COMPOSE positivePASS premature-prefix-roundingEXPECTED_FAIL\n' > terminal.log
