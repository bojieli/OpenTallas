#!/bin/bash
set -eu
O="$PWD/results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv"
printf 'read_json /out/miter_macro_cut.json\nhierarchy -check -top equiv\nasync2sync\nopt_clean\nequiv_simple -seq 4\nequiv_induct -seq 8\nequiv_status -assert\n' > "$O/prove_macro_cut_direct.ys"
docker run --rm -v "$O:/out" openroad/orfs:latest yosys -s /out/prove_macro_cut_direct.ys > "$O/yosys_macro_cut_direct.log" 2>&1
