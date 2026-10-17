#!/bin/bash
# HBM die v16 + d4b relay stations (H-NETLIST/H-ELEM 2026-10-16): regenerate the revision layer from the H-DIE station
# list (needs the frozen case dir), build contract + die.v with the layer, strict port-bind.
#   run_v16_d4b.sh [OUT] [CASE_DIR CASE_CONTRACT]   (case args only to regenerate the layer)
#   LAYER=none: no relay layer (d4c netlist before routed stations); EXTRA_LAYERS='a.json b.json': more revision layers
#   IDSTRAPS=1: full_die_v16.py --identity-straps (H-NETLIST 1815 alias reduction: identity parameters -> strap pins)
#   STATIONS=<list> LAYER=<layer.json.gz>: another station list / layer (d4b-r: d4br_relay_stations_r20.json.gz -> relays_d4br.json.gz)
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=${1:-results/arch/hbm_die_v16_d4b}; mkdir -p $OUT
LAYER=${LAYER:-tools/hbm_die_v15/v16_relays/relays_d4b.json.gz}
STATIONS=${STATIONS:-results/arch/hbm_die_v16/d4b_relay_stations_450.json.gz}
if [ $# -ge 3 ]; then
  python3 tools/hbm_die_v15/relay_contract_d4b.py --stations $STATIONS \
    --case "$2" --case-contract "$3" --out /tmp/relays_d4b.$$.json --report $OUT/relays_d4b_report.json || exit 2
  gzip -c /tmp/relays_d4b.$$.json > $LAYER && rm -f /tmp/relays_d4b.$$.json
fi
XS=(); [ "$LAYER" = none ] || XS=(--extra-spec $LAYER); for L in ${EXTRA_LAYERS:-}; do XS+=(--extra-spec $L); done
python3 tools/hbm_die_v15/full_die_v16.py --out $OUT "${XS[@]}" ${IDSTRAPS:+--identity-straps} ${PCH8:+--pc-h8} ${PCH9B:+--pc-h9b} ${KEEPQ:+--keep-quadrants $KEEPQ} ${DROPSM:+--drop-sm-side $DROPSM} ${DROPI:+--drop-instances $DROPI} > $OUT/gen.log 2>&1 || { tail $OUT/gen.log; exit 2; }
EXTRA=$(python3 -c "
import json; c=json.load(open('$OUT/contract.json'))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+i.get('rtl_deps',[])
      if not (f.startswith('rtl/') or '/rtl/' in f)})))")
# H-NETLIST (H-DIE 10-17): every instance source / rtl_dep must exist in THIS tree; a missing non-rtl/ dep (e.g.
# physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv under ot_hbm_xp_aq_tree13_fmt) would otherwise bind as a STUB.
python3 -c "
import json,os,sys; c=json.load(open('$OUT/contract.json'))
miss=sorted({f for i in c['instances'].values() for f in [i['source']]+i.get('rtl_deps',[]) if not os.path.isfile(f)})
print('CONTRACT_SOURCES_PRESENT', 'PASS' if not miss else 'FAIL missing='+','.join(miss)); sys.exit(1 if miss else 0)" || exit 4
bind_rc=0
python3 tools/die_port_bind.py $OUT/die.v --top hbm_v16_die $EXTRA --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb \
  --define OT_SMH_FC_HIER --strap-file $OUT/straps.json --out $OUT/port_bind.json > $OUT/port_bind.log 2>&1 || bind_rc=$?
tail -1 $OUT/port_bind.log
gzip -f $OUT/contract.json $OUT/die.v
exit "$bind_rc"
