#!/bin/bash
# run.sh: positives at 5 clock ratios, then mutants (each must FAIL)
cd $(dirname $(readlink -f $0))
K=/srv/opentallas-scratch2/claude/s81-rck-3/vE/serdes__t4/gen/serdes__t4/rtl
python3 -I gen.py ot_pdie_serdes.orig.sv rm_new.vh ot_pdie_serdes.new.sv || exit 1
# rate-match module alone, from the new file
awk '/^module ot_s81_rate_match/,/^endmodule/' ot_pdie_serdes.new.sv > rm_new.sv
run() { name=$1; shift; iverilog -g2012 -o $name.vvp -DOT_S81_RM_STAGED "$@" tb.sv rm_gold.sv rm_new.sv 2>&1 | grep -v 'sorry' | head -5; vvp $name.vvp | tail -3 | sed "s/^/$name: /"; rm -f $name.vvp; }
run same   -Ptb.TW=833.0 -Ptb.TR=833.0
run ppm_p  -Ptb.TW=833.0 -Ptb.TR=833.25
run ppm_m  -Ptb.TW=833.25 -Ptb.TR=833.0
run fastw  -Ptb.TW=770.0 -Ptb.TR=833.0
run fastr  -Ptb.TW=833.0 -Ptb.TR=770.0 -Ptb.SEED=7
run fast2  -Ptb.TW=833.0 -Ptb.TR=620.0 -Ptb.SEED=9
for m in NOSTAGE; do run mut_$m -DRMMUT_$m -Ptb.TW=833.0 -Ptb.TR=833.25; done
# text mutants of the new form (must fail)
mut() { name=$1; expr=$2; sed "$expr" rm_new.sv > rm_mut.sv; cmp -s rm_new.sv rm_mut.sv && { echo "$name: MUTATION DID NOT APPLY"; return; }; iverilog -g2012 -o $name.vvp -DOT_S81_RM_STAGED -Ptb.TW=833.0 -Ptb.TR=833.25 tb.sv rm_gold.sv rm_mut.sv 2>&1 | head -3; vvp $name.vvp | tail -2 | sed "s/^/$name: /"; rm -f $name.vvp; }
mut mut_slice 's/rm_i < RM_NS; rm_i = rm_i + 1)$/rm_i < RM_NS-1; rm_i = rm_i + 1)/'
mut mut_wa    's/(8.d1 << wp\[2:0\])/(8'"'"'d1 << (wp[2:0]+3'"'"'d1))/'
mut mut_data  's/w_dq <= w_d;/w_dq <= {w_d[511:1],~w_d[0]};/'
mut mut_idle  "s/r_m <= empty ? 512'd2/r_m <= empty ? 512'd0/"
