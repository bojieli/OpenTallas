#!/usr/bin/env bash
# HBM-BIND B2 (lane hbm-bind-idx 2026-10-24): umbrella gate for the IDX / ARGMAX root 2-quadrant straps.
#   rootctl SID/NQ/NL (run_idx_rootctl_nq.sh), selector NL (run_idx_selector_nl.sh), top-k link NL (run_idx_link_nl.sh),
#   argmax SID (../hbm_netlist_v16/run_argmax_r2_sid.sh). References are the as-built r18h5 sources (mk_idx_b2_refs.sh).
# usage: run_idx_b2_bind.sh OUT [REFDIR]   (run from the repo root; without REFDIR the refs are extracted with git)
set -uo pipefail
out=${1:?out}; refs=${2:-}; mkdir -p "$out"; fail=0
if [ -z "$refs" ]; then refs="$out/refs"; bash rtl/test/hbm_idx_static/mk_idx_b2_refs.sh "$refs" || exit 2; fi
bash rtl/test/hbm_idx_static/run_idx_rootctl_nq.sh "$out/rootctl" "$refs" | tee "$out/rootctl.txt" | tail -1; grep -q 'GATE PASS' "$out/rootctl.txt" || fail=1
bash rtl/test/hbm_idx_static/run_idx_selector_nl.sh "$out/selector" "$refs" | tee "$out/selector.txt" | tail -1; grep -q 'GATE PASS' "$out/selector.txt" || fail=1
bash rtl/test/hbm_idx_static/run_idx_link_nl.sh "$out/link" "$refs" | tee "$out/link.txt" | tail -1; grep -q 'GATE PASS' "$out/link.txt" || fail=1
bash rtl/test/hbm_netlist_v16/run_argmax_r2_sid.sh "$out/argmax" "$refs" | tee "$out/argmax.txt" | tail -1; grep -q 'GATE PASS' "$out/argmax.txt" || fail=1
[ $fail = 0 ] && echo "IDX_B2_BIND_GATE PASS" || { echo "IDX_B2_BIND_GATE FAIL"; exit 1; }
