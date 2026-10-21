#!/bin/bash
set -eu
O="$PWD/results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv"
(cd "$O" && python3 normalize_namespace.py)
printf 'read_json /out/namespace_sources.json\nequiv_make gold gate equiv\nwrite_json /out/miter_namespace.json\n' > "$O/make_namespace.ys"
docker run --rm -v "$O:/out" openroad/orfs:latest yosys -s /out/make_namespace.ys > "$O/make_namespace.log" 2>&1
(cd "$O" && python3 cut_macros.py miter_namespace.json namespace_macro_cut.json namespace_macro_certificate.json)
printf 'read_json /out/namespace_macro_cut.json\nhierarchy -check -top equiv\nasync2sync\nopt_clean\nequiv_simple -seq 4\nequiv_induct -seq 8\nequiv_status -assert\n' > "$O/prove_namespace.ys"
docker run --rm -v "$O:/out" openroad/orfs:latest yosys -s /out/prove_namespace.ys > "$O/yosys_namespace.log" 2>&1
