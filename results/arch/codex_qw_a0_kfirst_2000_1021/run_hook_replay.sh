#!/bin/bash
set -euo pipefail
sha256sum pre_gpl.odb local_request_decode_fixed.tcl check_local_request.tcl
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/work" -w /work openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/check_local_request.tcl
