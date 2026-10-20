cd /census
P=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
L=$(ls $P/*RVT_TT*.lib* $P/*LVT_TT*.lib* $P/*SLVT_TT*.lib* 2>/dev/null | grep -v FAKE | sort -u)
echo "nlibs: $(echo $L | wc -w)"
args=""; for l in $L /src/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_tt.lib /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_tt.lib /src/physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr_tt.lib; do args="$args --liberty $l"; done
python3 t/tools/ref_tile/native_census.py --netlist /base/1_2_yosys.v --top qfd_tt_ctlm_dv_lpf_lp --out /census/safe5_census.json $args
