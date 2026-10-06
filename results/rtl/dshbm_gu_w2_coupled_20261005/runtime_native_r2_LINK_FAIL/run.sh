#!/bin/bash
set -euo pipefail
export TMPDIR=/srv/opentallas-scratch2/jobs/hubble-gu-w2-coupled-native-r2/tmp
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
out=/srv/opentallas-scratch2/jobs/hubble-gu-w2-coupled-native-r2
src=/srv/opentallas/repos/hubble-gu-w2-native-8a48bc29a
lib=/srv/opentallas-scratch/claude/dsrom-suchains/swiglu/work4/obj_swiglu_W64_ROUTED1_NIN33_NOUT23_LM5_LA4_QLAT5_rtl
vhome=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
mkdir -p "$TMPDIR"
g++ -std=c++20 -fcoroutines -O2 -pthread -I"$lib" -I"$vhome/include" -I"$vhome/include/vltstd" -c "$src/rtl/test/hbm_accel/retained_swiglu_accept.cpp" -o "$out/swiglu.o"
g++ "$out/swiglu.o" "$lib/Vtb_dsrom_su_swiglu__ALL.a" "$lib/verilated.o" "$lib/verilated_timing.o" "$lib/verilated_threads.o" -pthread -latomic -o "$out/native_swiglu"
cd "$src"
p="$out/inputs/srv/opentallas"
python3 tools/dshbm_gu_w2_coupled.py run --out "$out/actual" --inputs "$p/repos/hubble-expert-workgroup-90b8a03e8/results/rtl/dshbm_expert_workgroup_20261005/source_inputs" --router "$p/jobs-overflow/hubble-gu-w2-router-source-20261005" --gu "$out/inputs/srv/opentallas-scratch/jobs/hubble-expert-workgroup-actual-r2" --service "$p/jobs-overflow/hubble-wg-service-r2" --w2 "$p/jobs-overflow/hubble-expert-w2-source-20261005" --service-exe "$p/jobs-overflow/hubble-gu-w2-coupled-r1/service_accept" --w2-exe "$p/jobs-overflow/erdos-w2-paired-sm-r3/build/Vtb_hbm_accel_sm_w2_pair_seq" --swiglu-exe "$out/native_swiglu"
