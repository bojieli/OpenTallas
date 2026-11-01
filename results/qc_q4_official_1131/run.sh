#!/bin/bash
set -eu
export OT_LEC_RESET_CYCLES=64
export OT_LEC_HINTS_PRESEED=1
export OT_LEC_EARLY_COMPARE=1
B=$(pwd)
exec python3 kit/lec.py "$B/kit" --netlist "$B/kit/run/results/asap7/dp_sle_st_b_v1/base/1_2_yosys.v" --out "$B/out" --reuse --hints "$B/cache_profile_plus6.json" --mem 16 --jobs 2
