#!/bin/bash
set -euo pipefail
cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib seq.lib
yosys -Q -s model.ys > model.log 2>&1
