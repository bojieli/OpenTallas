#!/bin/bash
# HBM-HC7-ROOT: root (SAFE1 TAILC1 PTFS1, tails black-boxed) hierarchical map (ABC per module, flatten after mapping)
# -> plain native32 census (+ attribution) -> bound_fanout_clone LIMIT -> retained re-synth -> native32 census.
# usage: sc.sh NAME LIMIT "chparam args"
set -u
d=$(pwd); n=$1; lim=$2; cp_args=$3; top=ot_hbm_hc_root_static
rm -rf $d/s_$n; mkdir -p $d/s_$n && cd $d/s_$n && tar xzf $d/src.tgz
L=/srv/opentallas-scratch/claude/codex-sm9-native-north-1020/libs
LIBS="$L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib $L/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
RL=""; AL=""; for f in $LIBS; do RL="$RL
read_liberty -lib $f"; AL="$AL -liberty $f"; done
H=rtl/hbm_accel/generic/peers/static_hc; M=physical/asap7_memory_macros_v2
src="$H/ot_hbm_hc_root_static.sv $H/ot_hbm_hc_eng_seq_static.sv $H/ot_hbm_hc_tail_unit_static.sv $H/ot_hbm_hc_tail_child_static.sv $H/ot_hgi_hc_tail_os_static.sv $H/ot_hdc_v41x_hcp_sys1_static.sv $H/ot_hgi_hc_tail_static.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target_fs.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/lib/ot_rst_relay.sv $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v"
cat > a.ys <<YS
read_verilog -sv -DSYNTHESIS -DOT_FP_DATA_NORST $src
blackbox ot_hbm_hc_tail_child_static
chparam $cp_args $top
hierarchy -check -top $top
tcl physical/common_flow/ot_keep_regs.tcl
synth -top $top -noshare
dfflibmap -liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
abc $AL
opt_clean -purge
$RL
setattr -mod -unset keep_hierarchy
flatten
opt_clean -purge
hierarchy -check -top $top
write_json $d/mapped_$n.json
write_verilog -noattr $d/mapped_$n.v
tee -o $d/stat0_$n.txt stat
YS
yosys -q -l $d/a_$n.log a.ys > /dev/null 2>&1; echo "SYNTH_RC rc=$?" >> $d/a_$n.log
libs=""; for f in $L/*.lib $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_tt.lib $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib $d/tail_child_stub_tt.lib; do libs="$libs --liberty $f"; done
if [ -f $d/mapped_$n.v ]; then
  python3 tools/ref_tile/native_census.py --netlist $d/mapped_$n.v --top $top --out $d/census_p_$n.json $libs > $d/census_p_$n.log 2>&1
  python3 $d/summ.py $d/census_p_$n.json > $d/summ_p_$n.txt 2>&1
  python3 $d/ep2.py $d/mapped_$n.v $top $d/census_p_$n.json > $d/ep_p_$n.log 2>&1
fi
python3 tools/hbm_hc/bound_fanout_clone.py $d/mapped_$n.json --top $top --name ${top}_bfc --out $d/native_$n.v --limit $lim > $d/clone_$n.log 2>&1; echo "CLONE_RC rc=$?" >> $d/clone_$n.log
cat > b.ys <<YS
$RL
read_verilog -sv $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v
read_verilog -sv -DSYNTHESIS $H/ot_hbm_hc_tail_child_static.sv
blackbox ot_hbm_hc_tail_child_static
read_verilog $d/native_$n.v
hierarchy -check -top ${top}_bfc
tcl physical/common_flow/ot_keep_regs.tcl
synth -top ${top}_bfc -flatten -noshare
abc $AL
opt_clean
write_verilog -noattr $d/retained_$n.v
tee -o $d/stat1_$n.txt stat
YS
[ -f $d/native_$n.v ] && { yosys -q -l $d/b_$n.log b.ys > /dev/null 2>&1; echo "RETAIN_RC rc=$?" >> $d/b_$n.log; }
[ -f $d/retained_$n.v ] && { python3 tools/ref_tile/native_census.py --netlist $d/retained_$n.v --top ${top}_bfc --out $d/census_r_$n.json $libs > $d/census_r_$n.log 2>&1; python3 $d/summ.py $d/census_r_$n.json > $d/summ_r_$n.txt 2>&1; }
cd $d && rm -rf $d/s_$n; gzip -f $d/mapped_$n.json
exit 0
