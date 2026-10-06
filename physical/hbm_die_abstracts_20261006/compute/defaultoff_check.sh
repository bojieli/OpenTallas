#!/bin/bash
set -euo pipefail
# Cheap syntax check of OFF branches only; does not claim enabled exactness.
iverilog -g2012 -tnull -s ot_hbm_sfu_quarter physical/hbm_die_abstracts_20261006/compute/ot_hbm_sfu_quarter.sv
iverilog -g2012 -tnull -s ot_hbm_hc_quarter physical/hbm_die_abstracts_20261006/compute/ot_hbm_hc_quarter.sv
