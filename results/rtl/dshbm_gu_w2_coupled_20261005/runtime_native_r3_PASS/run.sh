#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
out=/srv/opentallas-scratch2/jobs/hubble-gu-w2-coupled-native-r3
src=/srv/opentallas/repos/hubble-gu-w2-native-8a48bc29a
cd "$src"
p="/srv/opentallas-scratch2/jobs/hubble-gu-w2-coupled-native-r2/inputs/srv/opentallas"
python3 tools/dshbm_gu_w2_coupled.py run --out "$out/actual" --inputs "$p/repos/hubble-expert-workgroup-90b8a03e8/results/rtl/dshbm_expert_workgroup_20261005/source_inputs" --router "$p/jobs-overflow/hubble-gu-w2-router-source-20261005" --gu "/srv/opentallas-scratch2/jobs/hubble-gu-w2-coupled-native-r2/inputs/srv/opentallas-scratch/jobs/hubble-expert-workgroup-actual-r2" --service "$p/jobs-overflow/hubble-wg-service-r2" --w2 "$p/jobs-overflow/hubble-expert-w2-source-20261005" --service-exe "$p/jobs-overflow/hubble-gu-w2-coupled-r1/service_accept" --w2-exe "$p/jobs-overflow/erdos-w2-paired-sm-r3/build/Vtb_hbm_accel_sm_w2_pair_seq" --swiglu-exe "$out/native_swiglu"
