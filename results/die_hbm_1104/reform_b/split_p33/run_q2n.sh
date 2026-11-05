#!/bin/bash
# run_q2n.sh TREE_WITH_q2n_src GEN_DIR OUT: lockstep flat qslots against tile; PASS modes, MUT must FAIL.
set -u; S=$1; G=$2; OUT=$3; mkdir -p $OUT; R=/srv/opentallas-scratch3/claude/hbm-reform-b3/wt
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; P=$S/rtl/hbm_accel/generic/collective/p2p; rc=0
python3 $R/physical/die_plan/hbm/over_cap_split/reform_1103/facewrap.py --no-hier --clk-re clk --rst-re rst --top ot_q2nf_qout --pass-param MUT --out $OUT/t.fs.sv -- $G/ot_q2nf_split.sv > $OUT/fw.log 2>&1 || { echo FW FAIL; tail -3 $OUT/fw.log; exit 3; }
python3 -I - $G/q2n_tilebus.json $OUT/q2n_refmap.svh <<'P'
import json,sys
print(*[f"  ref_pd[{o}+:{c}]=f_d_o[{d*545+k*32}+:{c}];" for k,d,o,c in json.load(open(sys.argv[1]))],sep="\n",file=open(sys.argv[2],"w"))
P
cat > $OUT/face_reg.sv <<'V'
module ot_hbm_face_reg #(parameter integer W=1)(input wire clk, input wire [W-1:0] d, output reg [W-1:0] q); always @(posedge clk) q<=d; endmodule
V
one(){ n=$1;e=$2;shift 2;d=$OUT/obj_$n
 $VL --binary --timing -O1 -j 6 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DCYC=${CYC:-3000} -I$OUT --top-module tb_q2n "$@" -Mdir $d -o sim $G/tb_q2n.sv $OUT/t.fs.sv $OUT/face_reg.sv $G/ot_q2nf_split.sv $P/ot_hgi_coll_qslots.sv $P/ot_hgi_coll_qslots_capture_pin_v2.sv > $d.build.log 2>&1 || { echo "$n BUILD FAIL"; grep -m6 %Error $d.build.log | cut -c1-220; rc=1; return; }
 timeout 900 $d/sim > $d.run.log 2>&1; r=$?; g=PASS; [ $r != 0 ] && g=FAIL; v=BAD; [ $g = $e ] && v=OK; [ $v = OK ] || rc=1
 echo "$n expect=$e got=$g $v | $(grep -E '^Q2N|^pin|^link|^fault|^dest|^cap' $d.run.log | head -2 | tr '\n' ' ' | cut -c1-180)"; }
for sp in ${RUNS:-m0:PASS: bs:PASS:-GBAD=2 bu:PASS:-GBAD=1 bc:PASS:-GBAD=3 s1:FAIL:-GMUT=1 s2:FAIL:-GMUT=2 s3:FAIL:-GMUT=3,-GBAD=1}; do IFS=: read n e f <<<"$sp"; one $n $e ${f//,/ }; done
echo EQ_EXIT $rc; exit $rc
