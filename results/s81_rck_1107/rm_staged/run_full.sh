#!/bin/bash
cd $(dirname $(readlink -f $0))
run() { name=$1; shift; iverilog -g2012 -o $name.vvp -DOT_S81_RM_STAGED "$@" tb.sv rm_gold.sv rm_new.sv 2>&1 | head -5; vvp $name.vvp | tail -3 | sed "s/^/$name: /"; rm -f $name.vvp; }
run fullw1 -Ptb.TW=560.0 -Ptb.TR=833.0 -Ptb.SEED=3
run fullw2 -Ptb.TW=420.0 -Ptb.TR=833.0 -Ptb.SEED=5
run fullw3 -Ptb.TW=700.0 -Ptb.TR=833.0 -Ptb.SEED=11
