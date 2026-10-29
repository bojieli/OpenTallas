#!/bin/bash
# TOK-HEAD-LAND-2 step 2b: die-spine vehicle (TOK-ALL-15 recipe) on the LANDED HEAD top (DIE-HEAD-17 gate CA bind, strap form)
# Same substitutions as TOK-15: ctl LEAF -> ctl_core_drv.sv, ot_s81hd_bundle_native -> measured view LB 8419 (bstub),
# off-path leaves -> header stubs.  NEW: every wrapper = landed generated wrapper (rings ot_dp_clk_landing_cas, strap
# ties, start/origin), region clocks driven at their routed TT tap arrival (mk_tb_land.py).
set -eu
W=/srv/opentallas-scratch2/claude/wt/tok-head-land-2; R=/srv/opentallas-scratch2/claude/tok-head-land-2; L=$R/land; S=$W/results/token_pass/head_die_spine_1027/src
F=/srv/opentallas-scratch2/claude/tok14-head-fw
cd $W
python3 $S/mkstubs.py $W $R/stubs.sv
python3 $S/mkbstub.py $W $F/img/golden.json $F/per_tile.json $R/bstub.sv 8419
cp $R/ctl_core_drv_lat.sv $R/ctl_core_drv.sv
cp /srv/opentallas-scratch2/claude/tok15-head-die/ot_rom_4096x274_m8_scope.v $R/
python3 $R/mk_tb_land.py $L/gen/s81_head_top.sv $L/tap_TT.json $L/regions_strap.json $R/tb_TT.sv --stages $R/start_stages.sv
python3 $R/mk_tb_land.py $L/gen/s81_head_top.sv $L/tap_FF.json $L/regions_strap.json $R/tb_FF.sv --stages $R/start_stages.sv
python3 $R/mk_tb_land.py $L/gen/s81_head_top.sv $L/tap_TT.json $L/regions_strap.json $R/tb_zero.sv --zero --stages $R/start_stages.sv
mk_f () {  # $1 = tb file
cat <<EOF
+define+OT_COLL_NATIVE32
+define+OT_COLL_NATIVE32_OFF
+incdir+physical/asap7_memory_macros_v2/ot_rom_4096x274_m8
+incdir+results/token_pass/head_native_1351/partition_native
+incdir+results/token_pass/head_native_1351/partition_sources
+incdir+rtl/common
+incdir+rtl/dsrom_sys/s81_head
+incdir+rtl/hdc
+incdir+rtl/v41rom
rtl/common/ot_prefix.sv
rtl/v41rom/ot_v41_fadd.sv
rtl/v41rom/ot_v41_bmul2.sv
rtl/v41rom/ot_dsrom_bmul3.sv
$R/ot_rom_4096x274_m8_scope.v
rtl/hdc/ot_hdc_delay.sv
rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_native.sv
rtl/dsrom_sys/s81_head/ot_s81hd_elem.sv
$R/bstub.sv
rtl/dsrom_sys/s81_head/ot_s81hd_tile_native.sv
rtl/dsrom_sys/s81_head/ot_s81hd_oreg.sv
rtl/common/ot_meso_fifo.sv
rtl/common/ot_dp_clk_landing.sv
rtl/common/ot_dp_clk_landing_ca.sv
$R/start_stages.sv
EOF
for f in $L/gen/*.sv; do echo $f; done
cat <<EOF
rtl/dsrom_sys/s81_head/ot_s81hd_spo.sv
rtl/dsrom_sys/s81_head/ot_s81hd_spr.sv
$R/stubs.sv
$R/ctl_core_drv.sv
$1
EOF
}
mk_f $R/tb_TT.sv > $R/die_TT.f
mk_f $R/tb_FF.sv > $R/die_FF.f
mk_f $R/tb_zero.sv > $R/die_zero.f
sha256sum $L/gen/*.sv $R/stubs.sv $R/bstub.sv $R/ctl_core_drv.sv $R/start_stages.sv $R/tb_*.sv > $R/gen_sha256.txt
echo SETUP_OK
