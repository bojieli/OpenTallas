#!/bin/bash
# HBM die v16 full netlist (H-NETLIST 2026-10-15): generate contract + die.v, strict port-bind (die_port_bind v2), and
# Verilator lint (5.x on a fleet host).   run_v16.sh [OUT_DIR] [LINT_HOST]
set -u
cd "$(dirname "$0")/../.."
OUT=${1:-results/arch/hbm_die_v16}; HOST=${2:-ot-epyc1tb}
python3 tools/hbm_die_v15/full_die_v16.py --out $OUT > $OUT.gen.log 2>&1 || { cat $OUT.gen.log; exit 2; }
mv $OUT.gen.log $OUT/gen.log
# masters defined outside die_port_bind's default roots (rtl/, physical/**/rtl) enter as explicit RTL files
EXTRA=$(python3 -c "
import json,sys; c=json.load(open('$OUT/contract.json'))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+i.get('rtl_deps',[])
      if not (f.startswith('rtl/') or '/rtl/' in f)})))")
python3 tools/die_port_bind.py $OUT/die.v --top hbm_v16_die $EXTRA \
  --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb --define OT_SMH_FC_HIER \
  --strap-file $OUT/straps.json --out $OUT/port_bind.json > $OUT/port_bind.log 2>&1
tail -1 $OUT/port_bind.log
# Flat whole-die Verilator lint is OFF by default: measured 2026-10-15 22:27 at 364 GB RSS after 10 min on EPYC1 (killed,
# never admitted via ot-run). Connectivity is the strict port-bind above; per-master elaboration is each owner's bench.
if [ "${LINT:-0}" = 1 ]; then python3 tools/hbm_die_v15/lint_v16.py $OUT --remote $HOST | tee $OUT/lint_summary.txt; fi
