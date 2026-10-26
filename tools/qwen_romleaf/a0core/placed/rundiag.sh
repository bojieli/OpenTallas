#!/bin/bash
# rundiag.sh nk|nl regions.tcl label [extra]
K=$1; R=$2; L=$3; shift 3
Q=/srv/opentallas-scratch2/claude/qc/a0v8; W=/srv/opentallas-scratch2/claude/wt/qc-a0v8
B=$(ls -d /srv/opentallas-scratch2/claude/qc/synthprobe/$K/fp_$K/work/orfs/results/asap7/*/base)
cd /srv/opentallas-scratch2/claude/qc/a0v8place
(ulimit -v 30000000; nice python3 diag.py --netlist $B/1_2_yosys.v --top qfd_tile_${K}_a0c --macro-pins $Q/probe/macro_pins.json --place ${PLACE:-$Q/place_${K}_eMY.tcl} --regions $R --pins $W/tools/qwen_romleaf/a0core/qfd_tile_${K}_a0c8_pins.tcl --v7pos ${V7POS:-$Q/probe/$K.inst.tsv} --cache $Q/${K}_graph.pkl --label $L --out out/$L "$@")
