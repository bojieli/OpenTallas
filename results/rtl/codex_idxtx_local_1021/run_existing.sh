#!/usr/bin/env bash
set -euo pipefail
O=$1; M=$2
mkdir -p "$O/case"
cp results/rtl/codex_idxtx_local_1021/fixture/args.txt "$O/case/"
gzip -dc results/rtl/codex_idxtx_local_1021/fixture/stim.txt.gz > "$O/case/stim.txt"
cp results/rtl/codex_idxtx_local_1021/fixture/exp.json "$O/case/exp.json"
DIEM=1 TXS=1 J=${J:-16} bash tools/s81_dv/layer_prog/bk/run_idx_tree.sh "$O/build" "$M" "$O/case"
