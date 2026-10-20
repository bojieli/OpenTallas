#!/bin/bash
set -euo pipefail
mkdir -p native
# Actual Liberty semantics, including native inverting QN and async set/reset.
docker run --rm -v "$PWD:/work" --entrypoint bash openroad/orfs:asap7lock -lc 'source /OpenROAD-flow-scripts/env.sh; yosys -Q -T -p "read_liberty -ignore_miss_func /work/liberty/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib /work/liberty/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib /work/liberty/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib /work/liberty/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib /work/liberty/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib; write_verilog -noattr /work/native/models.v"' > native/models.log 2>&1
