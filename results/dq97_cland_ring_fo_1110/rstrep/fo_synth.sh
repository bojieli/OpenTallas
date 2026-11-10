#!/bin/bash
# DIE-QC-97 RSTREP-1: generic yosys synth (hierarchy kept) of lec_gold / lec_gate, then sink-pin count of the cas reset
# port bits (rst_n, rst_xn[j]) inside the synthesized cas module.  usage: fo_synth.sh RTLDIR OUT
R=$1; O=$2; mkdir -p $O; H=$(cd $(dirname $0) && pwd)
docker run --rm --memory=8g --name dq97fos_$$ --user $(id -u):$(id -g) -v $R:/rtl:ro -v $H:/h:ro -v $O:/o openroad/orfs:asap7lock bash -lc "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /o
for t in lec_gold lec_gate; do
yosys -q -l synth_\$t.log -p \"read_slang --keep-hierarchy -D SYNTHESIS --top \$t /rtl/ot_dp_clk_landing_ca.sv /rtl/ot_meso_fifo.sv /rtl/ot_dp_clk_landing.sv /h/tops_rs.sv; hierarchy -top \$t; synth -top \$t; opt_clean -purge; write_json \$t.json\"
done
python3 /h/fo_count.py lec_gold.json lec_gate.json" 2>&1 | tail -12
