#!/usr/bin/env bash
# DIE-S81-51/RF-H 11-03 cell estimate: generic yosys synth (docker, memory-capped) of the old column and the two new
# core masters; ASAP7 cells = generic cells x (g48 ASAP7 synth 296,270 / old column generic cells).
# usage: est.sh <repo root> <out>
set -u; R=$1; O=$2; mkdir -p $O
P="-set NSEG 8 -set NCH 16 -set XF 8 -set LV 5 -set BF16 1 -set NCHB 8 -set NB 2 -set MTP 1 -set EARLY 1 -set CG 1 -set DRAIN 200 -set FAST 1 -set PP 1 -set BP 0 -set QTIMING_FIX 1 -set QPIPE 1 -set QP_XS 1 -set QP_CAP 0 -set QP_P1 1 -set QP_CSAM 10 -set QZ 1 -set QZ_NS 8 -set QZ_NE 4 -set QY 1 -set QX 10 -set QBF 2 -set QZE 1 -set TCG 1 -set GRADUAL_RNE 1 -set BXST 2 -set FXST 2 -set RCG 1 -set KEEP_XPOS 1"
SRC=$(python3 -c "import json;print(' '.join('/r/'+s for s in json.load(open('$R/physical/die_plan/s81/cores/legacy/specs/ot_v41_bf_col/spec.json'))['sources']))")
SRC="$SRC /r/rtl/v41rom/ot_v41_bf16_half.sv /r/rtl/v41rom/ot_v41_bf_col3_c.sv /r/results/rfh_1103/bf_col3/est_h_wrap.sv"
echo "module ICGx1_ASAP7_75t_R(input CLK, input ENA, input SE, output GCLK); endmodule" > $O/icg_stub.v
J=${JOBS_EST:-"old c h"}
for job in old:ot_v41_bf_col:"$P -set BRNECUT 0" c:ot_v41_bf_col3_c:"$P -set BRNECUT 1" h:est_h:""; do
  n=${job%%:*}; r=${job#*:}; top=${r%%:*}; pp=${r#*:}
  cat > $O/$n.ys <<YS
read_verilog -lib /o/icg_stub.v
read_verilog -DSYNTHESIS -sv $SRC
hierarchy -top $top ${pp//-set/-chparam}
synth -flatten -top $top
abc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX
tee -o /o/$n.stat stat
YS
  docker run -d --rm --name rfh3est_$n --memory 24g --cpus 4 -v $R:/r:ro -v $O:/o openroad/orfs:asap7lock yosys -q -l /o/$n.log /o/$n.ys
done
