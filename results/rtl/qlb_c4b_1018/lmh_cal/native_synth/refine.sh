#!/bin/bash
set -eu
cp results/rtl/qlb_c4b_1018/lmh_cal/native_synth/audit.py native_synth_out/segcal/work/orfs/audit.py
cd native_synth_out/segcal/work/orfs
python3 audit.py
sha256sum 1_2_yosys.raw.v flat.json > native_input.sha256
