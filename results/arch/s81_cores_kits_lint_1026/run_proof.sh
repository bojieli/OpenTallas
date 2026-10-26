#!/bin/bash
# old-vs-new lockstep + candidate-only mutants + Yosys lint/equiv; run from repo WT via ot-run
set -u
WT=$1; R=$WT/results/arch/s81_cores_kits_lint_1026; B=$R/build; rm -rf $B; mkdir -p $B
V="docker run --rm -e CCACHE_DISABLE=1 -e HOME=/tmp --user $(id -u):$(id -g) -v $WT:$WT -w $B verilator/verilator:v5.032"
VR="docker run --rm --entrypoint= --user $(id -u):$(id -g) -v $WT:$WT -w $B verilator/verilator:v5.032"
Y="docker run --rm --user $(id -u):$(id -g) -v $WT:$WT -w $B openroad/orfs:asap7lock"
sed -e 's/\bot_s81_cfg7_seq/old_ot_s81_cfg7_seq/g' -e 's/OT_S81_CFG7_MUT/OLD_OT_S81_CFG7_MUT/g' $R/old/ot_s81_cfg7_seq.sv > $B/old_cfg7_seq.sv
sed -e 's/\bot_s81_cfg7_seq/old_ot_s81_cfg7_seq/g' -e 's/OT_S81_CFG7_MUT/OLD_OT_S81_CFG7_MUT/g' $WT/rtl/v41die/ot_s81_cfg7_seq_bfp.sv > $B/old_cfg7_seq_bfp.sv
sed -e 's/\bot_hdc_sk_/old_ot_hdc_sk_/g' $R/old/ot_hdc_sk_arith.sv > $B/old_sk_arith.sv
# candidate-only mutants (bench copies, never committed RTL)
sed -e 's/assign pend_ph = ph_q;/assign pend_ph = cfg_ph;/' $WT/rtl/v41die/ot_s81_cfg7_seq.sv > $B/mut_pend_cfg7_seq.sv
sed -e 's/always @(posedge clk\[0\]) if (rst_c \&\& cfg_go \&\& !ld_ok)/always @(posedge clk[0]) if (cfg_go \&\& !ld_ok)/' $WT/rtl/v41die/ot_s81_cfg7_seq.sv > $B/mut_rst_cfg7_seq.sv
sed -e 's/assign c = v_last\[W +: W\];/assign c = v_last[0 +: W];/' $WT/rtl/hdc/v41/ot_hdc_sk_arith.sv > $B/mut_c_sk_arith.sv
for f in mut_pend_cfg7_seq.sv mut_rst_cfg7_seq.sv mut_c_sk_arith.sv; do cmp -s $B/$f $WT/rtl/v41die/ot_s81_cfg7_seq.sv && echo "MUTANT $f NOT APPLIED"; done
cmp -s $B/mut_c_sk_arith.sv $WT/rtl/hdc/v41/ot_hdc_sk_arith.sv && echo "MUTANT mut_c NOT APPLIED"
COMMON="-Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --binary --timing -j 8 -I$WT/rtl/v41die"
CFG_SHARED="$WT/rtl/dsrom_sys/s81_die_bind/ot_s81_bf_prog_seq.sv $WT/rtl/lib/ot_rst_relay.sv"
build_cfg () { # name seqfile
  $V $COMMON --top-module tb -Mdir $B/obj_$1 $B/tb_cfg7_lockstep.sv $B/old_cfg7_seq.sv $B/old_cfg7_seq_bfp.sv $2 $WT/rtl/v41die/ot_s81_cfg7_seq_bfp.sv $CFG_SHARED $3 > $B/$1.build.log 2>&1 || { echo "BUILD FAIL $1"; tail -20 $B/$1.build.log; }
  $VR $B/obj_$1/Vtb +ncyc=${4:-300000} > $B/$1.sim.log 2>&1; grep -h "CFG7_LOCKSTEP\|MISMATCH" $B/$1.sim.log | head -3 | sed "s/^/$1: /"
}
cp $(dirname $0)/tb_*.sv $B/
build_cfg cfg7_new $WT/rtl/v41die/ot_s81_cfg7_seq.sv "" 300000
build_cfg cfg7_mut_pend $B/mut_pend_cfg7_seq.sv "" 300000
build_cfg cfg7_mut_nohold $WT/rtl/v41die/ot_s81_cfg7_seq.sv "+define+OT_S81_CFG7_MUT_NOHOLD" 300000
build_csa () {
  $V $COMMON --top-module tb -Mdir $B/obj_$1 $B/tb_csa_lockstep.sv $B/old_sk_arith.sv $2 > $B/$1.build.log 2>&1 || { echo "BUILD FAIL $1"; tail -20 $B/$1.build.log; }
  $VR $B/obj_$1/Vtb +nv=50000 > $B/$1.sim.log 2>&1; grep -h "CSA_LOCKSTEP\|MISMATCH" $B/$1.sim.log | head -3 | sed "s/^/$1: /"
}
build_csa csa_new $WT/rtl/hdc/v41/ot_hdc_sk_arith.sv
build_csa csa_mut_c $B/mut_c_sk_arith.sv
# Yosys: formal equiv where both elaborate (cfg7 PQ 1 and PQ 0 local, bfp kit params; csa old vs new), new-only check -assert
RELAY=$WT/rtl/lib/ot_rst_relay.sv
eqv () { # name top params oldfiles newfiles [hide]
  # hide: PQ 0 only -- un-name the dead pending-store values (old: undriven -> free anyseq; new: alias of cfg_ph/cfg_np) so
  # equiv_make does not pair them; every port and every register is still paired and must be proven
  HIDE=""; [ "${6:-}" = hide ] && HIDE='rename -hide w:*pend_ph w:*pend_np w:*.sph w:*.sph_m'
  cat > $B/$1.ys <<YS
read_verilog -sv -DSYNTHESIS $4
hierarchy -top $2 $3
proc; flatten; opt_clean; rename $2 gold; design -stash gold
read_verilog -sv -DSYNTHESIS $5
hierarchy -top $2 $3
proc; flatten; opt_clean; check -assert; rename $2 gate; design -stash gate
design -copy-from gold -as gold gold; design -copy-from gate -as gate gate
setundef -undriven -anyseq gold
$HIDE
equiv_make gold gate equiv; hierarchy -top equiv; async2sync
equiv_simple -seq 5; equiv_induct -seq 5; equiv_status -assert
YS
  $Y yosys -q -l $B/$1.yosys.log $B/$1.ys > /dev/null 2>&1 && echo "$1: YOSYS_EQUIV PASS ($(grep -h 'Found .* \$equiv cells\|proven' $B/$1.yosys.log | tail -1))" || echo "$1: YOSYS_EQUIV FAIL ($(grep -h 'ERROR\|unproven' $B/$1.yosys.log | head -2 | tr '\n' ' '))"
}
NEWCFG="$WT/rtl/v41die/ot_s81_cfg7_seq.sv $WT/rtl/v41die/ot_s81_cfg7_seq_bfp.sv $WT/rtl/dsrom_sys/s81_die_bind/ot_s81_bf_prog_seq.sv $RELAY"
OLDCFG="$R/old/ot_s81_cfg7_seq.sv $WT/rtl/v41die/ot_s81_cfg7_seq_bfp.sv $WT/rtl/dsrom_sys/s81_die_bind/ot_s81_bf_prog_seq.sv $RELAY"
eqv eq_bfp_l1p1 ot_s81_cfg7_seq_bfp "-chparam LAYOUT 1 -chparam PINREG 1" "$OLDCFG" "$NEWCFG" hide
eqv eq_loc_pq0_l1p1 ot_s81_cfg7_seq_local "-chparam PQ 0 -chparam LAYOUT 1 -chparam PINREG 1 -chparam LOCAL_COPY 1" "$OLDCFG" "$NEWCFG" hide
eqv eq_bfl_l1p1 ot_s81_cfg7_seq_bf_local "-chparam LAYOUT 1 -chparam PINREG 1 -chparam LOCAL_COPY 1" "$OLDCFG" "$NEWCFG" hide
eqv eq_loc_pq1_l1p1 ot_s81_cfg7_seq_local "-chparam PQ 1 -chparam LAYOUT 1 -chparam PINREG 1 -chparam LOCAL_COPY 1" "$OLDCFG" "$NEWCFG"
eqv eq_loc_pq1_l0p0 ot_s81_cfg7_seq_local "-chparam PQ 1" "$OLDCFG" "$NEWCFG"
for nw in "3 8" "13 30" "29 49" "2 8" "1 8"; do set -- $nw
  eqv eq_csa_n$1_w$2 ot_hdc_sk_csa "-chparam N $1 -chparam W $2" "$R/old/ot_hdc_sk_arith.sv" "$WT/rtl/hdc/v41/ot_hdc_sk_arith.sv"
done
echo DONE
