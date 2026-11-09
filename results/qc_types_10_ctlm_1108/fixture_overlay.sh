#!/bin/bash
# on intel2: write fixture overlay tar for realcalendar_native lockstep (sha-checked later against INPUTS lists)
set -e; H=/home/ubuntu/OpenTallas; O=$1; rm -rf $O; mkdir -p $O/calr $O/calr10 $O/calr10a $O/calr10n $O/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1
g(){ git -C $H show "$1:$2" > "$3"; }
for d in calr10 calr10a calr10n; do for f in $(git -C $H ls-tree --name-only d2c8e45a7 results/rtl/qw_tlprod_1020/images/$d/); do g d2c8e45a7 $f $O/$d/$(basename $f); done; done
g d2c8e45a7 results/rtl/qw_calr_1020/ctlm9c/ot_rom_4096x266_m8_calrbench.v $O/calr/ot_rom_4096x266_m8_calrbench.v
g d2c8e45a7 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v $O/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
R=results/arch/qw_headprep_1021/rrloc_projection/realcalendar_native
g c303af45e5b $R/native_compare.f $O/native_compare.f; g c303af45e5b $R/tb_hp13_native.sv $O/tb_hp13_native.sv
g c303af45e5b results/arch/qdie5_hp13_1022/run_native_compare.sh $O/run_native_compare.sh
cd $O && sha256sum calr/* calr10/* physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/*.v native_compare.f tb_hp13_native.sv
