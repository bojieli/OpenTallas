#!/bin/bash
# FAM-HBM-B/HCTAIL 10-21: gate-level cloned netlist of ot_hbm_hc_tail_child_static at chosen parameters + native census +
# native lockstep.  usage: nl.sh NAME SDIV TPIPE SKP OFF GAP
# = results/rtl/hbm_hc_root_safe_1020/tail_child_hc8/clone_h.sh (per-module ABC map, flatten after mapping) with chparam,
#   then bound_fanout_clone --limit 24 --tag sk_=g_skce.sink., retained re-synth, census, compact, native lockstep (5.050).
set -u
d=$(pwd); n=$1; sdiv=$2; tp=$3; skp=$4; off=$5; gap=$6; top=ot_hbm_hc_tail_child_static
rm -rf $d/s_$n; mkdir -p $d/s_$n && cd $d/s_$n && tar xzf $d/src.tgz
L=$d/libs
LIBS="$L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib $L/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
RL=""; AL=""; for f in $LIBS; do RL="$RL
read_liberty -lib $f"; AL="$AL -liberty $f"; done
H=rtl/hbm_accel/generic/peers/static_hc
src="$H/ot_hbm_hc_tail_child_static.sv $H/ot_hgi_hc_tail_os_static.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sinkhorn_ce.sv rtl/hdc/v41/ot_hdc_sinkhorn_cp.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_arith_cp.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/lib/ot_rst_relay.sv"
cat > a.ys <<YS
read_verilog -sv -DSYNTHESIS -DOT_FP_DATA_NORST $src
chparam -set SDIV $sdiv -set TPIPE $tp -set SKP $skp $top
hierarchy -check -top $top
tcl physical/common_flow/ot_keep_regs.tcl
synth -top $top -noshare
dfflibmap -liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
abc $AL
opt_clean -purge
$RL
flatten
opt_clean -purge
hierarchy -check -top $top
write_json $d/mapped_$n.json
write_verilog -noattr $d/mapped_$n.v
tee -o $d/stat0_$n.txt stat
YS
date > $d/t_$n.txt
yosys -q -l $d/a_$n.log a.ys > /dev/null 2>&1; echo "SYNTH_RC rc=$?" >> $d/a_$n.log; date >> $d/t_$n.txt
libs=""; for f in $L/*.lib; do libs="$libs --liberty $f"; done
python3 tools/ref_tile/native_census.py --netlist $d/mapped_$n.v --top $top --out $d/census_p_$n.json $libs > $d/census_p_$n.log 2>&1; python3 $d/summ.py $d/census_p_$n.json > $d/summ_p_$n.txt 2>&1
python3 tools/hbm_hc/bound_fanout_clone.py $d/mapped_$n.json --top $top --name ${top}_bfc --out $d/native_$n.v --limit 24 --tag sk_=g_skce.sink. > $d/clone_$n.log 2>&1; echo "CLONE_RC rc=$?" >> $d/clone_$n.log; date >> $d/t_$n.txt
cat > b.ys <<YS
$RL
read_verilog $d/native_$n.v
hierarchy -check -top ${top}_bfc
tcl physical/common_flow/ot_keep_regs.tcl
synth -top ${top}_bfc -flatten -noshare
abc $AL
opt_clean
write_verilog -noattr $d/retained_$n.v
tee -o $d/stat1_$n.txt stat
YS
yosys -q -l $d/b_$n.log b.ys > /dev/null 2>&1; echo "RETAIN_RC rc=$?" >> $d/b_$n.log; date >> $d/t_$n.txt
python3 tools/ref_tile/native_census.py --netlist $d/retained_$n.v --top ${top}_bfc --out $d/census_r_$n.json $libs > $d/census_r_$n.log 2>&1; python3 $d/summ.py $d/census_r_$n.json > $d/summ_r_$n.txt 2>&1
python3 tools/hbm_hc/compact_netlist.py $d/retained_$n.v $d/tailc_$n.v --top $top --header "FAM-HBM-B/HCTAIL 10-21: GATE-LEVEL native netlist of ot_hbm_hc_tail_child_static SDIV $sdiv TPIPE $tp SKP $skp (SKCE 1). Cells sk_c<i> = the Sinkhorn (u_tail.g_skce.sink).
RTL @HCTAIL -> per-module ABC map (ASAP7 RVT TT) -> tools/hbm_hc/bound_fanout_clone.py --limit 24 --tag sk_=g_skce.sink. -> retained re-synth -> tools/hbm_hc/compact_netlist.py.  Do not edit by hand: regenerate from the RTL." > $d/compact_$n.log 2>&1
grep -c ' sk_c' $d/tailc_$n.v > $d/sk_count_$n.txt; grep -E '^\s+DFF\w+ sk_c' $d/tailc_$n.v | wc -l >> $d/sk_count_$n.txt; grep -o '\.CLK([^)]*)' $d/tailc_$n.v | sort | uniq -c > $d/clk_nets_$n.txt
zcat results/rtl/fp32_add_native_clone_1020/final_packet/cells.v.gz > $d/cells_$n.v
TC_OFF=$off TC_GAP=$gap BUILD_JOBS=16 bash rtl/test/run_hbm_hc_tail_child_eq.sh $d/out_nat_$n 0 48 1 $d/tailc_$n.v $d/cells_$n.v > $d/bench_nat_$n.log 2>&1; echo "BENCH_RC nat rc=$?" >> $d/bench_nat_$n.log
cp $d/out_nat_$n/run.log $d/run_nat_$n.log 2>/dev/null; date >> $d/t_$n.txt; cd $d && rm -rf $d/s_$n $d/out_nat_$n; gzip -f $d/mapped_$n.json
