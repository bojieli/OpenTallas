#!/bin/bash
set -eu
O="$PWD/results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv"
printf 'read_rtlil /out/fullrtl_miter.il\nwrite_json /out/miter.json\n' > "$O/miter_json.ys"
docker run --rm -v "$O:/out" openroad/orfs:latest yosys -s /out/miter_json.ys > "$O/miter_json.log" 2>&1
(cd "$O" && python3 cut_macros.py)
printf 'read_json /out/miter_macro_cut.json\nhierarchy -check -top equiv\nasync2sync\nopt_clean\nequiv_struct -icells\nequiv_simple -seq 4\nequiv_induct -seq 8\nequiv_status -assert\n' > "$O/prove_macro_cut.ys"
docker run --rm -v "$O:/out" openroad/orfs:latest yosys -s /out/prove_macro_cut.ys > "$O/yosys_macro_cut.log" 2>&1
