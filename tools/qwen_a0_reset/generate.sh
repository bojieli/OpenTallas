#!/bin/bash
set -euo pipefail
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work -e A0_ODB=/work/input.odb -e A0_OUT=/work/native openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -python /work/native_reset.py
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work -e A0_ODB=/work/native/candidate.odb -e A0_CENSUS=/work/native/census.json openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -python /work/audit_odb.py
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -T -p "read_liberty -ignore_miss_func /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT*.lib*; write_verilog -noattr /work/native/native_cells.v"' > native/cells.log
