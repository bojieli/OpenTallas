#!/bin/bash
# d4f grants pipeline (H-DIE 10-16): plan dir -> grants_d4f.json (rehome + SM column pins + sfucore M7 + wq2 merge + calendar + reticle)
#   d4f_grants_build.sh PLAN_DIR OUT_GRANTS
set -euo pipefail
cd "$(dirname "$0")/../.."
N=$1; OUT=$2; D=results/arch/hbm_die_v16_d4f
python3 tools/hbm_die_v15/d4f_homes.py $N > $N/homes.json
python3 tools/hbm_die_v15/rehome_v6.py --plan $N --old results/arch/hbm_die_v15/core4_sfu2_b3624 --sm-carve 40.32 --sm-side-drop SE,NE \
  --drop-slots lk_S2,lk_S4,lk_N1,lk_N3,ep_S2,ep_S4,ep_N1,ep_N3 --drop-ghosts --sm-column --homes $N/homes.json \
  --adopted "H-DIE d4f gate-2 (coordinator d4f; HBM-ARRAY TP-192), UNQUALIFIED until GEN+GRT" --out $OUT | tail -1
python3 tools/hbm_die_v15/a2p_sm_column_grant.py $OUT $D/sm_column_pins_0cfed29dc.json --source-commit 0cfed29dc
python3 tools/hbm_die_v15/d4f_sfucore_grant.py $OUT
python3 tools/hbm_die_v15/d4f_wq2_merge_grant.py $OUT $N
python3 tools/hbm_die_v15/d4f_calendar_grant.py $OUT
python3 tools/hbm_die_v15/reticle.py $OUT
python3 tools/hbm_die_v15/d4f_coll_grant.py $OUT $N
