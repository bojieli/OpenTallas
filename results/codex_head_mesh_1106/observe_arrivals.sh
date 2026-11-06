#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/codex-head-mesh-1106
O=$R/mesh_rbl_bq8_proof/obj_m0
V=$HOME/.local/opentallas-tools/verilator-5.050/share/verilator/include
g++ -std=c++20 -O0 -I$O -I$V -I$V/vltstd $R/observe_arrivals.cpp $O/verilated.o $O/verilated_timing.o $O/verilated_threads.o $O/Vtb_s81hd_mesh_ep__ALL.a -Wl,--allow-multiple-definition -pthread -o $R/observe_arrivals
$R/observe_arrivals > $R/arrivals.log
