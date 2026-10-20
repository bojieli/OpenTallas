#!/bin/bash
# L2H-PAD l21 2026-10-19: strict unread replay of a d4g contract with an admitted review/manifest (run from the repo root).
#   l21_strict_replay.sh CONTRACT OUTDIR REVIEW MANIFEST SHA256      -> OUTDIR/port_bind.json + strict_replay.log
# Exit 0 only for DIE_PORT_BIND PASS (structural 0 AND unread 0 after the manifest). Same RTL roots / straps / pads as
# l1_bind_check.sh (the chain's bind2), plus --unread-review/--unread-contract/--unread-manifest/--unread-manifest-sha256.
set -o pipefail
C=$1; O=$2; R=$3; M=$4; H=$5; mkdir -p $O
bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $C $O > /dev/null 2>&1
EXTRA=$(python3 -c "
import json,gzip; p='$C'; c=json.load(gzip.open(p,'rt') if p.endswith('.gz') else open(p))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+(i.get('rtl_deps') or [])
      if f.startswith('rtl/hbm_accel/die_glue/scoped_d4g/') or not (f.startswith('rtl/') or '/rtl/' in f)})))")
python3 tools/die_port_bind.py $O/die.v --top hbm_v16_die $EXTRA --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb \
  --rtl-root rtl --rtl-root physical/hbm_mtp/rtl --rtl-root physical/hbm_accel_die_views/common --rtl-root physical/hbm_accel_die_views/quant/rtl \
  --rtl-root physical/hbm_generic/argmax18/rtl --rtl-root physical/hbm_xp_aq_tree13_1014 --lib-root physical/asap7_memory_macros --lib-root physical/asap7_memory_macros_v2 \
  --define OT_SMH_FC_HIER --strap-file $O/straps.json --pad-file $O/die.v.pads.json \
  --unread-review $R --unread-contract $C --unread-manifest $M --unread-manifest-sha256 $H \
  --out $O/port_bind.json > $O/strict_replay.log 2>&1
tail -1 $O/strict_replay.log
grep -q "^DIE_PORT_BIND PASS" $O/strict_replay.log
