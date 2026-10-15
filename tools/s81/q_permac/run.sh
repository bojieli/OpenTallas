#!/bin/bash
# S81 Q element per-mac container mapping (mac0 | ctl | mac1), source graph 7602 (sha a695f611 uncompressed), die lead 10-14
set -eu
B=/srv/opentallas-scratch/claude/s81-qpermac; cd $B
LIB=/srv/opentallas-scratch/codex/qcg-graph-7602/libs/merged.lib
IMG=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
zcat source_graph.json.gz > source_graph.json
python3 q_native_partition_graph.py source_graph.json part --per-mac > part.log 2>&1
cat > generic.ys <<YS
read_json $B/part/partitioned.json
synth -top ot_v41_rom_elem_q_qxpq_w10 -flatten -noabc
stat
write_json $B/generic.json
YS
cat > mapped.ys <<YS
read_json $B/generic.json
dffunmap
dfflibmap -liberty $LIB
abc -liberty $LIB
stat -liberty $LIB
write_json $B/mapped.json
YS
docker run --rm -v $B:$B -v /srv/opentallas-scratch/codex/qcg-graph-7602/libs:/srv/opentallas-scratch/codex/qcg-graph-7602/libs $IMG /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -s $B/generic.ys > generic.log 2>&1
docker run --rm -v $B:$B -v /srv/opentallas-scratch/codex/qcg-graph-7602/libs:/srv/opentallas-scratch/codex/qcg-graph-7602/libs $IMG /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -s $B/mapped.ys > mapped.log 2>&1
python3 census.py > census.json
echo QPERMAC_DONE
