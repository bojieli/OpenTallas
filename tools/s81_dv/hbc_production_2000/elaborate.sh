#!/usr/bin/env bash
# Full production-top hierarchy/port elaboration. Child body semantics belong
# to their pinned sources; -lib loads actual child interfaces, never fake RTL.
set -euo pipefail
[ -f prior/LIBRARIES.txt ] || python3 -I tools/s81_dv/hbc_production_2000/prepare_prior.py prior
out=${1:?output};top=${2:-ot_s81sl_slice_lepw_mab_hbc_prod_mu_72};mkdir -p "$out"
python3 - "$out" "$top" <<'PY'
from pathlib import Path
import sys
out=Path(sys.argv[1]);libs=Path('prior/LIBRARIES.txt').read_text().splitlines()
lines=['read_verilog -sv -lib prior/'+p for p in libs]
H='rtl/dsrom_sys/s81_dv/hostb/'
actual=['rtl/lib/ot_reset_sync.sv']+[H+n+'.sv' for n in ['dsdv_hostb_hold','dsdv_hostb_crc512','dsdv_hostb_rx','dsdv_hostb_tx','dsdv_hostb_stage','dsdv_hbc1_loader','dsdv_hbc1_affine_book','dsdv_hostb_return','dsdv_hostb_stage_hbc']]
lines+=['read_verilog -sv '+p for p in actual]
top=sys.argv[2]
assert top in ['ot_s81sl_slice_lepw_mab_hbc_prod_mu_72','ot_s81sl_slice_lepw_mab_hbc_r4d_mu_72']
lines+=['read_verilog -sv rtl/dsrom_sys/s81_dv/slice/mu72/'+top+'.sv',
 'chparam -set HBC_LOCAL_STAGE 1 -set HBC_LOCAL_RANK 0 -set HBC_PHASE_BOUND 1 -set HBC_CLOCK_RESET_ID 4133 -set HBC_BOOT_HEADER_EDGE 20 -set HBC_BOOT_COMMIT_EDGE 30 -set HBC_RETURN_ARRIVAL_DEADLINE 8100 '+top,
 'hierarchy -check -top '+top,'proc','opt_clean','check','write_json '+str(out/'top.json')]
(out/'elaborate.ys').write_text('\n'.join(lines)+'\n')
PY
yosys -s "$out/elaborate.ys" >"$out/elaborate.log" 2>&1
python3 - "$out" "$top" <<'PY'
from pathlib import Path
import json,sys
p=Path(sys.argv[1]);d=json.loads((p/'top.json').read_text());top=d['modules'][sys.argv[2]]
# All child interface parameters and actual HBC RTL were elaborated in the
# selected bounded test profile. This is a structural check, not a physical view.
print('HBC_PROD_TOP ELAB_PASS',len(top['ports']),'ports',len(top['cells']),'direct cells')
(p/'receipt.json').write_text(json.dumps(dict(kind='full_top_hierarchy_ports',verdict='PASS',prior_source='82add93fc',profile='explicit_component_TEST_NOT_PRODUCTION',ports=len(top['ports']),cells=len(top['cells']),physical_qualified=False),indent=2)+'\n')
PY
