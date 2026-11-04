#!/bin/bash
# Prove the r3 exp default (TQ=0) elaborates identical to r2 (d793df3308b), per v41x_exp parameter set used by any user.
# equiv_make (flop names) + equiv_simple/equiv_induct; where generate names moved, a SAT miter with temporal induction.
set -u; W=/home/ubuntu/scratch-root/claude/die-hbm-61-rtl-tailx; D=${OUT:-/tmp/dh61_c12eq_tq}; rm -rf $D; mkdir -p $D/old $D/new
C=rtl/hbm_accel/integrated_20261006/sfu_c12_selected
FILES="$C/00_ot_hdc_fastfp_lat_c12.sv $C/01_ot_hdc_fp32_f12.sv $C/02_ot_hdc_prefix.sv $C/03_ot_dsrom_su_add6.sv $C/04_ot_dsrom_su_f12.sv $C/06_ot_hdc_v41x_sfu_c12.sv $C/08_ot_hdc_delay.sv $C/09_ot_hdc_sfu.sv $C/14_ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv"
cd $W
for f in $FILES; do mkdir -p $D/old/$(dirname $f) $D/new/$(dirname $f); git show d793df3308b:$f > $D/old/$f; cp $f $D/new/$f; done
CFGS="v41x_exp:LM=3,LA=3 v41x_exp:LM=4,LA=4 v41x_exp:LM=5,LA=4 v41x_exp:LM=5,LA=5 v41x_exp:LM=6,LA=6 v41x_exp:LM=6,LA=7,L7X=1,NREP=8"
for cfg in $CFGS; do
  m=ot_hbm_selected_c12__ot_hdc_${cfg%%:*}; p=${cfg#*:}; tag=$(echo $cfg | tr ':,=' '___')
  pp=$(echo "$p" | sed -E 's/([A-Z0-9]+)=([0-9]+)/.\1(\2)/g')
  if [ "${cfg%%:*}" = qadd_lat ]; then
    echo "module eqtop(input wire clk, rst_n, v, input wire [31:0] a, b, output wire [31:0] y, output wire fault); $m #($pp) u(clk, rst_n, v, a, b, y, fault); endmodule" > $D/$tag.top.sv
  else
    echo "module eqtop(input wire clk, rst_n, v, input wire [31:0] x, output wire [31:0] y, output wire vo, fault); $m #($pp) u(.clk(clk), .rst_n(rst_n), .v(v), .x(x), .y(y), .vo(vo), .fault(fault)); endmodule" > $D/$tag.top.sv
  fi
  for side in old new; do
    echo "read_verilog -sv -DSYNTHESIS $FILES $D/$tag.top.sv; hierarchy -top eqtop; proc; flatten; memory; opt_clean; async2sync; hierarchy -top eqtop; opt_clean; rename -top $side; write_rtlil $D/$tag.$side.il" > $D/$tag.$side.ys
  done
  printf 'read_rtlil %s\nread_rtlil %s\nequiv_make old new eq\nhierarchy -top eq\nequiv_struct\nequiv_simple -undef\nequiv_induct -undef\nequiv_status -assert\n' $D/$tag.old.il $D/$tag.new.il > $D/$tag.eq.ys
  printf 'read_rtlil %s\nread_rtlil %s\nmiter -equiv -flatten -make_assert old new miter\nhierarchy -top miter\nsat -verify -prove-asserts -tempinduct -set-init-zero -seq 1 -maxsteps 40 miter\n' $D/$tag.old.il $D/$tag.new.il > $D/$tag.sat.ys
done
cat > $D/run_in.sh <<'EOS'
set -u; D=$1; cd $D; fail=0
for e in *.eq.ys; do t=${e%.eq.ys}
  (cd old && yosys -q -s ../$t.old.ys > ../$t.old.log 2>&1) && (cd new && yosys -q -s ../$t.new.ys > ../$t.new.log 2>&1) || { echo "$t ELAB_FAIL"; fail=1; continue; }
  if timeout 1500 yosys -q -s $e > $t.eq.log 2>&1; then echo "$t EQUIV (equiv_make/struct/simple/induct)";
  elif timeout 3000 yosys -q -s $t.sat.ys > $t.sat.log 2>&1; then echo "$t EQUIV (SAT miter, temporal induction)";
  else echo "$t NOT_PROVEN"; tail -n 3 $t.sat.log; fail=1; fi
done; echo "C12_TQ_DEFAULT_EQUIV fail=$fail"
EOS
docker run --rm --name dh61_c12eq_tq --cpus=6 --memory=16g --memory-swap=16g -v $D:$D openroad/orfs:asap7lock bash $D/run_in.sh $D
