#!/bin/bash
# TOK-DS-4 T7 canary3: canary2 inputs (exact current selected 141-source export) with the T7 bound replaced by the
# UNAPPLIED memory closure bound (PMEM+PVQ+LAND data cuts + staging SRAM_MACRO=1, sha 12605dc2) and its 3 children;
# gen tools = kit-wave-15-s81b tools + claude/tok-ds-3-1102 gen_phys/rom_declared_logic patch. Opt-in canary only.
set -euo pipefail
K=/srv/opentallas-scratch2/claude/tok-ds-4-t7canary3
S=/srv/opentallas-scratch2/claude/wt/kit-wave-15-s81b
C2=/srv/opentallas-scratch2/claude/codex-flow-s81-source-2055/t7_current_canary2
rm -rf "$K/rtl" "$K/gen"
cp -a "$C2/rtl" "$K/rtl"
python3 - "$K" "$C2" <<'PY'
from pathlib import Path
import sys, json
K = Path(sys.argv[1]); old = sys.argv[2]; root = K / 'rtl'
for f in root.rglob('*'):
    if f.is_file() and f.suffix in ('.f', '.json', '.sv', '.v'):
        f.write_text(f.read_text().replace(old, str(K)))
bound = root / 's81p_svc_lo_dsdv_svc_rs__t7_bound.sv'
bound.write_text((K / 'closure_bound.sv').read_text())
kids = [str(K / 'children' / f'ot_t7_{c}_capture_candidate.sv') for c in ('pmem', 'pvq', 'land')]
for fl in ('kit_rtl.f', 'kit_rtl_sim.f'):
    p = root / fl; L = p.read_text().split('\n'); i = L.index(str(bound)); L[i+1:i+1] = kids; p.write_text('\n'.join(L))
j = json.loads((root / 'kit_rtl.json').read_text())
i = j['files'].index(str(bound)); j['files'][i+1:i+1] = kids
(root / 'kit_rtl.json').write_text(json.dumps(j, indent=1))
(root / 'CANARY_SCOPE.json').write_text(json.dumps(dict(scope='TOK-DS-4 opt-in T7 canary3: canary2 inputs + UNAPPLIED memory closure bound 12605dc2 (PMEM+PVQ+LAND cuts, staging SRAM_MACRO=1) + 3 children', base='codex t7_current_canary2 (bound 61c902f1)'), indent=1))
PY
cd "$K/src"
python3 tools/die_plan/gen.py phys physical/die_plan/s81/plan_h2_2249.json --out "$K/gen" --types svc_lo_dsdv_svc_rs__t7 --rtl-root "$S" --kit-rtl svc_lo_dsdv_svc_rs__t7="$K/rtl/kit_rtl.f" --hold-ff-margin 0 --max-wire-um 100 --clock-landing "$S/physical/die_plan/s81/h2_2249/landed_sidecar_h2.json" > "$K/gen.log" 2>&1
set +e
python3 tools/die_plan/kit_gen_lint.py "$K/gen/svc_lo_dsdv_svc_rs__t7" --plan-dir "$S/physical/die_plan/s81" --mem 8 > "$K/gen_lint.log" 2>&1
echo "gen_lint rc=$?" > "$K/summary.txt"
python3 tools/die_plan/kit_preflight.py "$K/gen/svc_lo_dsdv_svc_rs__t7" --plan-dir "$S/physical/die_plan/s81" --out "$K/preflight.json" > "$K/preflight.log" 2>&1
echo "preflight rc=$?" >> "$K/summary.txt"
cat "$K/summary.txt"
