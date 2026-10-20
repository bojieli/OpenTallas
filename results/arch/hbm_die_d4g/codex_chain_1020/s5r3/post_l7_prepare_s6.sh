#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
B=/srv/opentallas-scratch/claude/codex-hbm-gen2e4r5-tailclasses-1020
H=27a01b34d
A=$B/artifacts
cd "$B/src_$H"
REV0=$PWD/results/arch/hbm_unread_gen2e3_1019/l21/review_l21_candidate.json

[ -f "$B/S5_STRICT_DONE" ] || { echo SOURCE_PREREQUISITE_NOT_READY; exit 10; }
python3 tools/hbm_die_v16/d4g_layers/l7_wire.py "$A/net/contract.json" "$A/net/contract_l7.json" --report "$A/net/l7_wire_post.json"
cp "$A/net/contract_l7.json" "$A/net/contract_pre.json"
rc=0
bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh "$A/net/contract_pre.json" "$A/pb5b" || rc=$?
if [ "$rc" != 0 ]; then
 python3 - "$A/pb5b/port_bind.json" <<'CHECK'
import json,sys
r=json.load(open(sys.argv[1]));print('S5B_STRUCTURAL_BIND',r.get('failing'))
sys.exit(0 if r.get('failing')==['unread_net_bits'] else 1)
CHECK
fi
python3 tools/hbm_die_v16/d4g_functional_bind.py "$A/net/contract_pre.json" --report "$A/pb5b/functional_bind.json" --lat warn
strict_manifest() {   # $1 contract  $2 bind dir (die.v + port_bind.json from bind2)  $3 tag -> transfer -> propose -> replay
  local U=$A/unread/$3; mkdir -p $U
  python3 tools/hbm_die_v16/unread_l21_transfer.py $REV0 $2/die.v $1 $2/port_bind.json $H $U/review.json > $U/transfer.log 2>&1 \
    || { echo "$3_UNREAD_TRANSFER_REFUSED"; tail -2 $U/transfer.log; return 1; }
  tail -1 $U/transfer.log
  local X=$(python3 -c "
import json,gzip; p='$1'; c=json.load(gzip.open(p,'rt') if p.endswith('.gz') else open(p))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+(i.get('rtl_deps') or [])
      if f.startswith('rtl/hbm_accel/die_glue/scoped_d4g/') or not (f.startswith('rtl/') or '/rtl/' in f)})))")
  python3 tools/die_port_bind.py $2/die.v --top hbm_v16_die $X --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb \
    --rtl-root rtl --rtl-root physical/hbm_mtp/rtl --rtl-root physical/hbm_accel_die_views/common --rtl-root physical/hbm_accel_die_views/quant/rtl \
    --rtl-root physical/hbm_generic/argmax18/rtl --rtl-root physical/hbm_xp_aq_tree13_1014 --lib-root physical/asap7_memory_macros --lib-root physical/asap7_memory_macros_v2 \
    --define OT_SMH_FC_HIER --strap-file $2/straps.json --pad-file $2/die.v.pads.json --unread-review $U/review.json --unread-contract $1 \
    --unread-proposal-out $U/manifest_proposal.json --out $U/proposal_bind.json > $U/proposal.log 2>&1 || { echo "$3_UNREAD_PROPOSAL_REFUSED"; tail -2 $U/proposal.log; return 1; }
  local S=$(sha256sum $U/manifest_proposal.json | cut -d' ' -f1); echo "$3_UNREAD_PROPOSAL $S"
  bash tools/hbm_die_v16/d4g_layers/l21_strict_replay.sh $1 $U/replay $U/review.json $U/manifest_proposal.json $S > $U/replay.out 2>&1; local rc=$?
  tail -1 $U/replay.out; [ $rc = 0 ] && echo "$3_STRICT_PASS_WITH_PROPOSAL $S (LEAD digest admission pending)" || echo "$3_STRICT_FAIL_WITH_PROPOSAL $S"
  return $rc
}


strict_manifest "$A/net/contract_pre.json" "$A/pb5b" S5B
mkdir -p "$A/vplan_prev"
ln -sfn /srv/opentallas-scratch/claude/hd4g/gen2e4/views/views.json "$A/vplan_prev/views.json"
ln -sfn /srv/opentallas-scratch/claude/hd4g/gen2e4/src_7b303c847/v16w "$A/vplan_prev/wrap"
python3 tools/hbm_die_v15/v16_views.py --out "$A/vplan_b" --contract "$A/net/contract_pre.json"
python3 tools/hbm_die_v16/synth_reuse_r8b.py --views "$A/vplan_b" --metas /srv/opentallas-scratch/claude/hd4g/gen2e4/views/synth --root "$PWD" --prev "$A/vplan_prev" --out "$A/reuse_b.json" > "$A/reuse_b.log"
tail -2 "$A/reuse_b.log"
touch "$B/S6_PLAN_DONE"
echo S5B_STRICT_S6_MODEL_DONE source27a01b34d
