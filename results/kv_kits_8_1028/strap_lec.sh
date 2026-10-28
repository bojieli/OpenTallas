#!/bin/bash
# KV-KITS-8 10-28: per-strap-variant equivalence of the STRAP_DIRECT / STRAP_SAMPLE leaves vs the unchanged (main) leaves.
# Each check: old leaf (main) and new leaf (param = 1) elaborated with the kit's params, the strap port tied to one used
# value (pin constraint), flattened, opt (constant-D no-init flops -> constants = LEC don't-care power-up), then
# equiv_make by register name + equiv_simple + equiv_induct; equiv_status -assert.  Mutants (old tie != new tie) must FAIL.
# frontq additionally ties rst_n = 1 (reset-inactive pin constraint): STRAP_SAMPLE differs only while rp = 0.
# Usage (inside openroad/orfs image): strap_lec.sh OUT LEAFDIR OLDDIR NEWDIR
set -u
OUT=$1; LEAF=$2; OLD=$3; NEW=$4
mkdir -p $OUT
LEAVES=$(for f in ${LEAF_FILES:-ot_rst_relay.sv ot_hdc_delay.sv ot_qwen_nearhbm_prod.sv ot_qwen_nearhbm_head_hs.sv ot_hdc_fp32_add_lat.sv ot_hdc_fp32_add_lat_nr.sv ot_hdc_fp32_mul_lat.sv ot_hdc_fastfp.sv ot_hdc_prefix.sv}; do printf "%s " $LEAF/$f; done)
one() {  # name module file_rel params tieport tieval_gold tieval_gate extra_newparam rst
  local name=$1 mod=$2 rel=$3 params=$4 port=$5 vg=$6 vn=$7 np=$8 rst=$9
  local ys=$OUT/$name.ys
  {
    for side in gold gate; do
      if [ $side = gold ]; then f=$OLD/$rel; v=$vg; p="$params"; else f=$NEW/$rel; v=$vn; p="$params -chparam $np 1"; fi
      echo "design -reset"
      echo "read_verilog -sv -DSYNTHESIS $LEAVES $f"
      echo "hierarchy -top $mod $p"
      echo "proc; setattr -mod -unset keep_hierarchy *; setattr -unset keep_hierarchy *; flatten; opt_clean"
      echo "rename -top $side"
      echo "delete -port $side/w:$port"
      echo "cd $side; connect -set $port $v; cd .."
      if [ "$rst" = 1 ]; then echo "delete -port $side/w:rst_n"; echo "cd $side; connect -set rst_n 1'b1; cd .."; fi
      echo "opt -full; opt_dff -sat; opt -full; opt_clean; async2sync"
      echo "stat"
      echo "design -stash $side"
    done
    echo "design -copy-from gold -as gold gold"
    echo "design -copy-from gate -as gate gate"
    echo "equiv_make gold gate eq; hierarchy -top eq"
    echo "equiv_simple -seq 3; equiv_induct -seq 3; equiv_status -assert"
  } > $ys
  yosys -q -l $OUT/$name.log $ys > /dev/null 2>&1; local rc=$?
  echo "$name rc=$rc $(grep -E 'Found [0-9]+ unproven|Equivalence successfully proven|unproven \$equiv' $OUT/$name.log | head -2 | tr '\n' ' ')" | tee -a $OUT/summary.txt
}
: > $OUT/summary.txt
L8=rtl/hdc/nearhbm/ot_qkh_subtiles.sv
FQ=rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4.sv
for s3 in 0 1; do for b in 00 01 10 11; do
  one lane8_s3c${s3}_bsel$b ot_qkh_lane8 $L8 "-chparam LT_COPY 1 -chparam ADD_LAT 7 -chparam LTW 12 -chparam S3_COPY $s3" bsel "2'b$b" "2'b$b" STRAP_DIRECT 0
done; done
for h in 00 01 10 11; do
  one frontq_hid$h ot_qkh_head_frontq_native $FQ "-chparam PORT_REGS 1 -chparam Q_FP32 1 -chparam MUT 0" hid "2'b$h" "2'b$h" STRAP_SAMPLE 1
done
# mutants: must NOT prove
one MUT_lane8_s3c1_bsel01_vs10 ot_qkh_lane8 $L8 "-chparam LT_COPY 1 -chparam ADD_LAT 7 -chparam LTW 12 -chparam S3_COPY 1" bsel "2'b01" "2'b10" STRAP_DIRECT 0
one MUT_frontq_hid01_vs11 ot_qkh_head_frontq_native $FQ "-chparam PORT_REGS 1 -chparam Q_FP32 1 -chparam MUT 0" hid "2'b01" "2'b11" STRAP_SAMPLE 1
# reset NOT constrained: STRAP_SAMPLE must show the reset-window difference (honesty check, expected unproven)
one RSTFREE_frontq_hid01 ot_qkh_head_frontq_native $FQ "-chparam PORT_REGS 1 -chparam Q_FP32 1 -chparam MUT 0" hid "2'b01" "2'b01" STRAP_SAMPLE 0
