#!/bin/bash
# HBM-HCROOT8 pipe2: reuse mapped_k2.json (per-module map of SKCE1 child) -> bound_fanout_clone --tag sk_=g_skce.sink. ->
# retained re-synth -> native32 census (plain + retained) -> compact -> native lockstep.
set -u
d=$(pwd); n=k2t; top=ot_hbm_hc_tail_child_static
rm -rf $d/s_$n; mkdir -p $d/s_$n && cd $d/s_$n && tar xzf $d/src2.tgz
L=/srv/opentallas-scratch/claude/codex-sm9-native-north-1020/libs
LIBS="$L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib $L/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
RL=""; AL=""; for f in $LIBS; do RL="$RL
read_liberty -lib $f"; AL="$AL -liberty $f"; done
libs=""; for f in $L/*.lib; do libs="$libs --liberty $f"; done
python3 tools/ref_tile/native_census.py --netlist $d/mapped_k2.v --top $top --out $d/census_p_$n.json $libs > $d/census_p_$n.log 2>&1; python3 $d/summ.py $d/census_p_$n.json > $d/summ_p_$n.txt 2>&1
python3 tools/hbm_hc/bound_fanout_clone.py $d/mapped_k2.json --top $top --name ${top}_bfc --out $d/native_$n.v --limit 24 --tag sk_=g_skce.sink. > $d/clone_$n.log 2>&1; echo "CLONE_RC rc=$?" >> $d/clone_$n.log
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
yosys -q -l $d/b_$n.log b.ys > /dev/null 2>&1; echo "RETAIN_RC rc=$?" >> $d/b_$n.log
python3 tools/ref_tile/native_census.py --netlist $d/retained_$n.v --top ${top}_bfc --out $d/census_r_$n.json $libs > $d/census_r_$n.log 2>&1; python3 $d/summ.py $d/census_r_$n.json > $d/summ_r_$n.txt 2>&1
python3 tools/hbm_hc/compact_netlist.py $d/retained_$n.v $d/tailc_$n.v --top $top --header "HBM-HCROOT8 10-20: GATE-LEVEL native netlist of ot_hbm_hc_tail_child_static SKCE 1 (Sinkhorn on clk + step enable). Cells sk_c<i> = the Sinkhorn (ot_hdc_sinkhorn_ce) of the declared SDIV multicycle (physical/hbm_hc_tail_child/tailc_skmcp.sdc).
RTL @HBM-HCROOT8 -> per-module ABC map (ASAP7 RVT TT) -> tools/hbm_hc/bound_fanout_clone.py --limit 24 --tag sk_=g_skce.sink. -> retained re-synth -> tools/hbm_hc/compact_netlist.py.  Do not edit by hand: regenerate from the RTL." > $d/compact_$n.log 2>&1
grep -c ' sk_c' $d/tailc_$n.v > $d/sk_count_$n.txt; grep -E '^\s+DFF\w+ sk_c' $d/tailc_$n.v | wc -l >> $d/sk_count_$n.txt; grep -o '\.CLK([^)]*)' $d/tailc_$n.v | sort | uniq -c > $d/clk_nets_$n.txt
zcat $d/cells.v.gz > $d/cells_$n.v
BUILD_JOBS=16 bash rtl/test/run_hbm_hc_tail_child_eq.sh $d/out_$n 0 48 1 $d/tailc_$n.v $d/cells_$n.v > $d/bench_nat_$n.log 2>&1; echo "BENCH_RC nat rc=$?" >> $d/bench_nat_$n.log
cp $d/out_$n/run.log $d/run_nat_$n.log 2>/dev/null; cd $d && rm -rf $d/s_$n
