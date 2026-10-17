#!/bin/bash
# Full core A2P: only SE/NE SM-side hardware and four physical SerDes peers are removed.
# d4c reset geometry is deliberately not reused; rebuild against the d4f placement.
set -euo pipefail
cd "$(dirname "$0")/../.."
LAYER=none IDSTRAPS=1 PCH8=1 DROPSM=SE,NE \
DROPI=ep_S2,lk_S2,ep_S4,lk_S4,ep_N1,lk_N1,ep_N3,lk_N3 \
EXTRA_LAYERS=tools/hbm_die_v15/v16_layers/xql_d4c.json \
bash tools/hbm_die_v15/run_v16_d4b.sh "${1:-results/arch/hbm_die_v16_d4f}"
