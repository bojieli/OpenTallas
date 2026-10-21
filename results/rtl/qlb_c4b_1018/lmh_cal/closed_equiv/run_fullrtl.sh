#!/bin/bash
set -eu
O="$PWD/results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv"
docker run --rm -v "$PWD:/src:ro" -v "$PWD/closed_ae6b:/old:ro" -v "$O:/out" openroad/orfs:latest yosys -s /out/default_off_fullrtl.ys > "$O/yosys_fullrtl.log" 2>&1
