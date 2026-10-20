#!/bin/bash
set -euo pipefail
# HBM-H9BIND 10-20 lookup fix: src/ is a plain file snapshot (no .git), so die_bind_unread_manifest's
# `git show <review.source_commit>:<path>` failed for EVERY selected source ('historical source missing ...ot_hbm_obs_leaf.sv'
# was just the first). Point git at a bare snapshot repo holding the review's exact source_commit (59576ab0f, an ancestor of
# the pushed codex/hbm-die11-portage-1020@20200bdc2). No tool change, no waiver: every selected source is still compared
# byte-for-byte against that commit and against the review pins.
export GIT_DIR=$PWD/h9bind_snap.git
rev=$(python3 -c "import json;print(json.load(open('fallback_unread/review_h9bind.json'))['source_commit'])")
git cat-file -e "$rev^{commit}"; echo "HISTORICAL_SOURCE_COMMIT $(git rev-parse $rev)"
cd src
C=../fallback_contract.json; O=../fallback_bind; U=../fallback_unread
EXTRA=$(python3 - <<'PY'
import json
c=json.load(open('../fallback_contract.json'))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+(i.get('rtl_deps') or []) if f.startswith('rtl/hbm_accel/die_glue/scoped_d4g/') or not (f.startswith('rtl/') or '/rtl/' in f)})))
PY
)
python3 tools/die_port_bind.py $O/die.v --top hbm_v16_die $EXTRA --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb --rtl-root rtl --rtl-root physical/hbm_mtp/rtl --rtl-root physical/hbm_accel_die_views/common --rtl-root physical/hbm_accel_die_views/quant/rtl --rtl-root physical/hbm_generic/argmax18/rtl --rtl-root physical/hbm_xp_aq_tree13_1014 --lib-root physical/asap7_memory_macros --lib-root physical/asap7_memory_macros_v2 --define OT_SMH_FC_HIER --strap-file $O/straps.json --pad-file $O/die.v.pads.json --unread-review $U/review_h9bind.json --unread-contract $C --unread-proposal-out $U/manifest_proposal_h9bind.json --out $U/proposal_bind_h9bind.json > $U/proposal_h9bind.log 2>&1
sha=$(sha256sum $U/manifest_proposal_h9bind.json | cut -d' ' -f1)
echo "FALLBACK_UNREAD_PROPOSAL_SHA $sha"
bash tools/hbm_die_v16/d4g_layers/l21_strict_replay.sh $C $U/replay_h9bind $U/review_h9bind.json $U/manifest_proposal_h9bind.json $sha
echo FALLBACK_STRICT_REPLAY_PASS_PROPOSAL_DIGEST_ADMISSION_OWED
