#!/bin/bash
# TOK-FUNC-S81 (10-21) step 1: RTL-ONLY source assembly of the S81 72-frame release die (no physical views, no GEN).
#   assemble_rtl72.sh <ref> <workdir>
# <ref> = a commit of claude/tokfunc-s81-1021 (= G7 die plan/RTL claude/s81-die72-g7-1021 + main + S81-FIX2 eng640
# d5e45464e + xgt_xo 6aac44322 + link5 xdie / cap contract / tok4 bench tools).  Runs the G7 die chain
# (tools/s81_dv/release72/run_die72_g7.sh) up to and including the STRICT bind (dv_diecase --bind real ->
# die_port_bind), and stops: no rvcase / GRT / STA.  Output <workdir>/bind/bind/{die.v, port_bind.json, ...},
# <workdir>/plan_routed_g7.json, <workdir>/land_plan_g7.json, <workdir>/src (the archived sources = the RTL of record).
# At die closure the token script takes the GEN netlist instead (run_tokfunc_s81.sh --die-v).
set -euo pipefail
REF=${1:?ref}; W=$(realpath -m ${2:?workdir})
FRAME=f04198934d9a1fdacc81b9501a9ccb5c632ba2ea; LPREF=21b97190eba0b3b306026f23a2408867cd099726
G=${OT_GIT_DIR:-/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git}
export OT_GIT_DIR=$G OT_DIE_REPAIR_CORRIDOR=1
mkdir -p "$W/src"; S=$W/steps.log
for r in "$REF" "$FRAME" "$LPREF"; do git --git-dir="$G" cat-file -e "$r^{commit}" 2>/dev/null || git --git-dir="$G" fetch -q origin "$r" || git --git-dir="$G" fetch -q origin claude/tokfunc-s81-1021; done
REF=$(git --git-dir="$G" rev-parse "$REF^{commit}")
BASE=results/arch/s81_dv_1016
printf 'REF %s\nFRAME %s\nLP %s\n' "$REF" "$FRAME" "$LPREF" > "$W/snapshot.refs"
git --git-dir="$G" archive "$REF" tools rtl "$BASE" physical/rom_host_ingest results/arch/die_reach_1016.json results/arch/accepted_cost_ledger_1013.json results/arch/mu_s81_1018 results/arch/s81_die72_1021 physical/ref_tile/s81_mu72_assembly | tar -xf - -C "$W/src"
git --git-dir="$G" ls-tree -r --name-only "$REF" physical | grep -E '(\.v|\.sv|\.vh|/spec\.json)$' | grep -v '^physical/rom_host_ingest' > "$W/phys.lst"
mapfile -t PF < "$W/phys.lst"; git --git-dir="$G" archive "$REF" -- "${PF[@]}" | tar -xf - -C "$W/src"
git --git-dir="$G" show "$FRAME:tools/s81_dv/frame_bind.py" > "$W/src/tools/s81_dv/frame_bind.py"
cd "$W/src"
if ! grep -q 'from frame_bind import' tools/s81_dv/dv_bind.py; then patch --batch -p1 < tools/s81_dv/release72/frame_bind.patch; fi
export GIT_DIR=$G
R72=results/arch/s81_die72_1021
python3 tools/s81_dv/dv_route72.py "$R72/g7/plan_unrouted_g7.json" "$W/plan_routed_g7_raw.json" > "$W/route72.log" 2>&1
python3 - "$W/plan_routed_g7_raw.json" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]));f=p['facts']['physical72']
assert not f['routing_failures'],f['routing_failures'][:5]
print('ROUTE72_OK links',len(p['links']),'stations',f['relay_station_count'])
PY
echo "ROUTE_RC 0 $(date)" >> "$S"
python3 tools/s81_dv/dv_station_dirs72.py "$W/plan_routed_g7_raw.json" "$R72/relay_bodies.json" "$W/plan_routed_g7.json" > "$W/station_dirs.log" 2>&1
P=$W/plan_routed_g7.json; T=$W/bind_table72.json; LAND=$W/land_plan_g7.json
python3 tools/s81_dv/release72/mk_land_plan_g7.py "$BASE/landing/p4l3/land_plan.json" "$P" "$LAND" > "$W/land_plan_g7.log" 2>&1
python3 tools/s81_dv/frame_bind.py --plan "$P" --table "$BASE/bind/bind_table_p4l3_mu.json" --out "$T" --source-ref "$LPREF" > "$W/frame_table.log" 2>&1
python3 tools/s81_dv/recovery_idx4_1021/apply_overlay.py "$T"
python3 tools/s81_dv/rtlgap_idx_1021/apply_rst_fix.py "$T" > "$W/idx_rst_fix.log" 2>&1
python3 tools/s81_dv/l20split_1021/apply_overlay.py "$T" > "$W/l20_overlay.log" 2>&1
python3 tools/s81_dv/release72/apply_mu72_overlay.py "$T" > "$W/mu72_overlay.log" 2>&1
python3 tools/s81_dv/release72/apply_eng_overlay_g7.py "$T" > "$W/eng_overlay.log" 2>&1
echo "OVERLAYS_RC 0 $(date)" >> "$S"
set +e
python3 tools/s81_dv/dv_diecase.py --plan "$P" --out "$W/bind" --bind real --bind-table "$T" --land-plan "$LAND" > "$W/bind.log" 2>&1
RC=$?; echo "BIND_RC $RC $(date)" >> "$S"
sha256sum "$W/bind/bind/die.v" >> "$S" 2>/dev/null
exit $RC
