#!/bin/bash
set -euo pipefail
cd src
C=../fallback_contract.json; O=../fallback_bind; U=../fallback_unread
EXTRA=$(python3 - <<'PY'
import json
c=json.load(open('../fallback_contract.json'))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+(i.get('rtl_deps') or []) if f.startswith('rtl/hbm_accel/die_glue/scoped_d4g/') or not (f.startswith('rtl/') or '/rtl/' in f)})))
PY
)
python3 tools/die_port_bind.py $O/die.v --top hbm_v16_die $EXTRA --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb --rtl-root rtl --rtl-root physical/hbm_mtp/rtl --rtl-root physical/hbm_accel_die_views/common --rtl-root physical/hbm_accel_die_views/quant/rtl --rtl-root physical/hbm_generic/argmax18/rtl --rtl-root physical/hbm_xp_aq_tree13_1014 --lib-root physical/asap7_memory_macros --lib-root physical/asap7_memory_macros_v2 --define OT_SMH_FC_HIER --strap-file $O/straps.json --pad-file $O/die.v.pads.json --unread-review $U/review.json --unread-contract $C --unread-proposal-out $U/manifest_proposal.json --out $U/proposal_bind.json > $U/proposal.log 2>&1
sha=$(sha256sum $U/manifest_proposal.json | cut -d' ' -f1)
echo "FALLBACK_UNREAD_PROPOSAL_SHA $sha"
bash tools/hbm_die_v16/d4g_layers/l21_strict_replay.sh $C $U/replay $U/review.json $U/manifest_proposal.json $sha
echo FALLBACK_STRICT_REPLAY_PASS_PROPOSAL_DIGEST_ADMISSION_OWED
