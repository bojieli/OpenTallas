#!/usr/bin/env bash
set -euo pipefail
r=/srv/opentallas-scratch/codex/s81-norm-physical-1015/ctnl2-surplus-v2
cd "$r/src"
python3 tools/ref_tile/ref_tile.py export --orfs-dir "$r/orfs" --kit physical/ref_tile/s81hc_ctnl_l2_native_ref --out "$r/views/ot_s81_hc_ctnl_l2" > "$r/export.log" 2>&1
