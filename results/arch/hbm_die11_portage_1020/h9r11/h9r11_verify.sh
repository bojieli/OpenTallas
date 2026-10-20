#!/bin/bash
# HBM-H9R11 10-20: verify the l25 h9c fallback swap + STRICT bind on a GEN2e4 r11 contract (default: S5 contract_pre.json).
#   h9r11_verify.sh A|B [CONTRACT_IN] [TAG]     (local; same commands as the chain's bind2 + strict_manifest)
set -o pipefail
PL=${1:?A|B}; W=/home/ubuntu/wt/hbm-die11-$PL; AR=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r11; A=$AR/plan$PL
CIN=${2:-$A/net/contract_pre.json}; T=${3:-S5H}; O=$A/h9r11/$T; mkdir -p $O $O/unread
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || exit 9; cd $W
H=$(git -C $W rev-parse --short=9 HEAD); REV0=$W/results/arch/hbm_unread_gen2e3_1019/l21/review_l21_candidate.json
python3 tools/hbm_die_v16/d4g_layers/l25_h9c_fallback.py swap $CIN $O/contract_h9c.json --report $O/swap_report.json || { echo ${T}_SWAP_FAIL; exit 2; }
bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $O/contract_h9c.json $O/pb > /dev/null; tail -1 $O/pb/port_bind.log
python3 tools/hbm_die_v16/d4g_functional_bind.py $O/contract_h9c.json --report $O/pb/functional_bind.json > $O/pb/functional_bind.log 2>&1; tail -1 $O/pb/functional_bind.log
U=$O/unread
python3 tools/hbm_die_v16/unread_l21_transfer.py $REV0 $O/pb/die.v $O/contract_h9c.json $O/pb/port_bind.json $H $U/review_transfer.json > $U/transfer.log 2>&1 || { echo ${T}_TRANSFER_REFUSED; tail -2 $U/transfer.log; exit 3; }
tail -1 $U/transfer.log
python3 tools/hbm_die_v16/d4g_layers/l25_h9c_fallback.py review $U/review_transfer.json $U/review.json || { echo ${T}_REVIEW_REFUSED; exit 4; }
X=$(python3 -c "
import json; c=json.load(open('$O/contract_h9c.json'))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+(i.get('rtl_deps') or [])
      if f.startswith('rtl/hbm_accel/die_glue/scoped_d4g/') or not (f.startswith('rtl/') or '/rtl/' in f)})))")
python3 tools/die_port_bind.py $O/pb/die.v --top hbm_v16_die $X --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb \
  --rtl-root rtl --rtl-root physical/hbm_mtp/rtl --rtl-root physical/hbm_accel_die_views/common --rtl-root physical/hbm_accel_die_views/quant/rtl \
  --rtl-root physical/hbm_generic/argmax18/rtl --rtl-root physical/hbm_xp_aq_tree13_1014 --lib-root physical/asap7_memory_macros --lib-root physical/asap7_memory_macros_v2 \
  --define OT_SMH_FC_HIER --strap-file $O/pb/straps.json --pad-file $O/pb/die.v.pads.json --unread-review $U/review.json --unread-contract $O/contract_h9c.json \
  --unread-proposal-out $U/manifest_proposal.json --out $U/proposal_bind.json > $U/proposal.log 2>&1 || { echo ${T}_PROPOSAL_REFUSED; tail -2 $U/proposal.log; exit 5; }
S=$(sha256sum $U/manifest_proposal.json | cut -d' ' -f1); echo "${T}_UNREAD_PROPOSAL $S"
bash tools/hbm_die_v16/d4g_layers/l21_strict_replay.sh $O/contract_h9c.json $U/replay $U/review.json $U/manifest_proposal.json $S > $U/replay.out 2>&1; rc=$?
tail -n 2 $U/replay.out; [ $rc = 0 ] && echo "${T}_STRICT_PASS $S (LEAD digest admission pending)" || echo "${T}_STRICT_FAIL $S"
exit $rc
