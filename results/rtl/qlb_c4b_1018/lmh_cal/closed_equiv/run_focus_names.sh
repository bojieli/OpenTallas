#!/bin/bash
set -eu
O="$PWD/results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv"
python3 "$O/prepare_focus.py"
docker run --rm -v "$PWD:/src:ro" -v "$O:/out" openroad/orfs:latest yosys -s /out/focus_prepare.ys > "$O/focus_prepare.log" 2>&1
(cd "$O" && python3 normalize_focus.py)
printf 'read_json /out/gold_focus.json\nread_json /out/gate_focus_names.json\nequiv_make gold gate equiv\nhierarchy -check -top equiv\nasync2sync\nopt_clean\nequiv_simple -seq 2\nequiv_induct -seq 4\nequiv_status -assert\n' > "$O/focus_names.ys"
docker run --rm -v "$O:/out" openroad/orfs:latest yosys -s /out/focus_names.ys > "$O/yosys_focus_names.log" 2>&1
