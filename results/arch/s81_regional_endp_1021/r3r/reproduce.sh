#!/bin/bash
set -euo pipefail
python3 tools/s81_dv/dv_endp_regional_e2_1021.py --parent-rtl parent_input.sv --land-lef dsdv_mu_land.lef --writer-stat map/w.stat.json --reader-stat map/r.stat.json --variant main --per-root-endpoint-reset --out-dir ../hier_current
python3 - <<'PY'
from pathlib import Path
p=Path('sources.f');s=p.read_text();new='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_lep_mu_ab_regional_r3r.sv'
Path('../hier_current/sources.f').write_text(s+new+'\n')
PY
sha256sum $(cat ../hier_current/sources.f) tools/s81_dv/dv_endp_regional_e2_1021.py > ../hier_current/sources.sha256
verilator --lint-only --timing -Wno-fatal -DSYNTHESIS -DOT_S81SL_HARD -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF --top-module ot_s81sl_slice_lepw_mab_mu_regional_e2_lp -f ../hier_current/sources.f > ../hier_current/lint.log 2>&1
