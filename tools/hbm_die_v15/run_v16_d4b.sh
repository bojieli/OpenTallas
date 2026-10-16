#!/bin/bash
# HBM die v16 + d4b relay stations (H-NETLIST/H-ELEM 2026-10-16): regenerate the revision layer from the H-DIE station
# list (needs the frozen case dir), build contract + die.v with the layer, strict port-bind.
#   run_v16_d4b.sh [OUT] [CASE_DIR CASE_CONTRACT]   (case args only to regenerate the layer)
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=${1:-results/arch/hbm_die_v16_d4b}; mkdir -p $OUT
LAYER=tools/hbm_die_v15/v16_relays/relays_d4b.json.gz
if [ $# -ge 3 ]; then
  python3 tools/hbm_die_v15/relay_contract_d4b.py --stations results/arch/hbm_die_v16/d4b_relay_stations_450.json.gz \
    --case "$2" --case-contract "$3" --out /tmp/relays_d4b.$$.json --report $OUT/relays_d4b_report.json || exit 2
  gzip -c /tmp/relays_d4b.$$.json > $LAYER && rm -f /tmp/relays_d4b.$$.json
fi
python3 tools/hbm_die_v15/full_die_v16.py --out $OUT --extra-spec $LAYER > $OUT/gen.log 2>&1 || { tail $OUT/gen.log; exit 2; }
EXTRA=$(python3 -c "
import json; c=json.load(open('$OUT/contract.json'))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+i.get('rtl_deps',[])
      if not (f.startswith('rtl/') or '/rtl/' in f)})))")
bind_rc=0
python3 tools/die_port_bind.py $OUT/die.v --top hbm_v16_die $EXTRA --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb \
  --define OT_SMH_FC_HIER --strap-file $OUT/straps.json --out $OUT/port_bind.json > $OUT/port_bind.log 2>&1 || bind_rc=$?
tail -1 $OUT/port_bind.log
gzip -f $OUT/contract.json $OUT/die.v
exit "$bind_rc"
