#!/bin/bash
set -eu
B=/srv/opentallas-scratch/claude/s81-qpermac; cd $B
IMG=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
python3 report.py
for t in ot_s81_q_ctl_native_graph ot_s81_q_mac0_native_graph "\$paramod\\\\ot_s81_q_lane_pair_native\\\\TW=s32'00000000000000000000000000010001"; do :; done
for t in ctl mac0; do
cat > wv_$t.ys <<YS
read_json $B/containers.json
hierarchy -top ot_s81_q_${t}_native_graph
check
write_verilog -noattr $B/ot_s81_q_${t}_native_graph.v
YS
docker run --rm -v $B:$B $IMG /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -s $B/wv_$t.ys > wv_$t.log 2>&1 || { echo WV_FAIL $t; tail -5 wv_$t.log; }
done
ls -la *.v
