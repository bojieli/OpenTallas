#!/bin/bash
# One immutable available-view diagnostic chain. Original G8 inputs/jobs untouched.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
PREP=7ec9b5e2faeb9d7caec112470701f59a70777f94
RTL_BASE=553741303923ab6bab36d67d17f914b1f11896c5
TOOLS=1a872af33c8d10d8123f8d4c69198e09cc04fd43
CREF=12c132d60a8f0300056abb216d48ff9588e7f620
G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
W=$D/die72-g9-selected
[ ! -e "$W" ] || { echo 'REFUSE: immutable G9 output directory already exists'; exit 2; }
mkdir -p "$W/src"
export OT_GIT_DIR=$G OT_DIE_REPAIR_CORRIDOR=1 GIT_DIR=$G
for r in "$PREP" "$RTL_BASE" "$TOOLS" "$CREF"; do
 git --git-dir="$G" cat-file -e "$r^{commit}" 2>/dev/null || git --git-dir="$G" fetch -q origin "$r"
done
printf 'PREP %s\nRTL_BASE %s\nTOOLS %s\nCREF %s\n' "$PREP" "$RTL_BASE" "$TOOLS" "$CREF" > "$W/snapshot.refs"
BASE=results/arch/s81_dv_1016
# Preserve the original G8 RTL/spec census; apply only explicit pinned table refs.
git --git-dir="$G" archive "$RTL_BASE" tools rtl "$BASE" physical/rom_host_ingest results/arch/die_reach_1016.json results/arch/accepted_cost_ledger_1013.json results/arch/mu_s81_1018 | tar -xf - -C "$W/src"
git --git-dir="$G" ls-tree -r --name-only "$RTL_BASE" physical | grep -E '(\.v|\.sv|\.vh|/spec\.json)$' | grep -v '^physical/rom_host_ingest' > "$W/phys.lst"
mapfile -t PF < "$W/phys.lst"
git --git-dir="$G" archive "$RTL_BASE" -- "${PF[@]}" | tar -xf - -C "$W/src"
# Published helpers are independently pinned; never copy candidate-era shared helpers.
git --git-dir="$G" archive "$TOOLS" tools | tar -xf - -C "$W/src"
git --git-dir="$G" archive "$PREP" results/arch/s81_die72_1021/g9_assembly/pre_gen | tar -xf - -C "$W/src"
cd "$W/src"
cp results/arch/s81_die72_1021/g9_assembly/pre_gen/plan_unrouted_g9.json "$W/plan_unrouted_g9.json"
cp results/arch/s81_die72_1021/g9_assembly/pre_gen/bind_table_g9.json "$W/bind_table_g9.json"
python3 - "$W/bind_table_g9.json" "$G" <<'PY'
import json,subprocess,sys
for ref in json.load(open(sys.argv[1]))['rtl_refs']:
 if subprocess.run(['git','--git-dir='+sys.argv[2],'cat-file','-e',ref+'^{commit}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  subprocess.run(['git','--git-dir='+sys.argv[2],'fetch','-q','origin',ref],check=True)
PY
find . -type f -print0 | sort -z | xargs -0 sha256sum > "$W/materialized_inputs.sha256"
python3 tools/s81_dv/dv_route72.py "$W/plan_unrouted_g9.json" "$W/plan_routed_g9_raw.json" > "$W/route72.log" 2>&1
python3 - "$W/plan_routed_g9_raw.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]));assert not p['facts']['physical72']['routing_failures'];assert len(p['links'])==819
print('G9_ROUTE819 nominal paths only; exact relay-body legalization/actual-pin projection remain required')
PY
printf 'ROUTE_RC 0 %s\n' "$(date -Is)" >> "$W/steps.log"
python3 tools/s81_dv/dv_station_dirs72.py "$W/plan_routed_g9_raw.json" results/arch/s81_die72_1021/relay_bodies.json "$W/plan_routed_g9.json" > "$W/station_dirs.log" 2>&1
P=$W/plan_routed_g9.json
T=$W/bind_table_g9.json
LAND=$W/land_plan_g9.json
python3 tools/s81_dv/release72/mk_land_plan_g7.py "$BASE/landing/p4l3/land_plan.json" "$P" "$LAND" > "$W/land_plan.log" 2>&1
# These are explicit landing MODELS; no inherited stage-map/calendar dates are qualified.
python3 tools/s81_dv/dv_diecase.py --plan "$P" --out "$W/bind" --bind real --bind-table "$T" --land-plan "$LAND" > "$W/bind.log" 2>&1
printf 'BIND_RC 0 %s\n' "$(date -Is)" >> "$W/steps.log"
python3 tools/s81_dv/dv_rvcase.py --plan "$P" --bind-dir "$W/bind/bind" --bind-table "$T" --land-plan "$LAND" --out "$W/case" --view-refs "$CREF" "$RTL_BASE" "$PREP" --die-repair --dieflow-ref "$TOOLS" --dcc-ref "$TOOLS" --corners tt ff ss --macro-views --signal-top-layer M8 --gen-safety-diag 'G9 selected available-view diagnostic: exact configured CTRL16/QF1/TAP16 CLOSED views; W6 children beneath unhardened MU parents; unique KV512 master and all other unqualified parents remain explicit stand-ins. No whole-die physical, full programme, token, stage-map or calendar qualification.' > "$W/case_gen.log" 2>&1
printf 'CASE_RC 0 %s\n' "$(date -Is)" >> "$W/steps.log"
CPUS=16 MEMG_GRT=96 MEMG_STA=64 bash "$W/case/run_all.sh" > "$W/chain.log" 2>&1
printf 'CHAIN_RC 0 %s\n' "$(date -Is)" >> "$W/steps.log"
