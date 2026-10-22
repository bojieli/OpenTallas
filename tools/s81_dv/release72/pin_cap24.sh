#!/bin/bash
# STW-S81c-DIE 10-22: cap24 = pin_cap19.sh with the cap24 floorplan (g9f_cap19_plan.py --variant fb, then
# g9f_cap24_plan.py --variant V: open W col6 street, wider centre/lower channels) and the cap23 case flags
# (dv_rvcase 177f3d55f: --rfw --hold-eco --dieclk --fck-out-pin --rs-chain-place --rs-repair --dieclk-split-um 2000),
# forced landings on the 3 u_irg_02 -> u_irg_03 crossings (cap23 FB, same HBM row). Original cap19 notes follow.
# STW-S81c-DIE-CAP 10-22: cap19 = cap18 (528fc3c9f, Codex pin_cap18.sh) with a re-slotted floorplan and a fresh route.
# Exactly the cap17 -> cap18 generation, with two replaced steps:
#   cap17 plan (pool body reserved) -> g9f_cap19_plan.py --variant V (rigid re-slots, no resize / interface change)
#   -> dv_route72c.py --iter 16 --hop-max 380 (every station arc <= 380 um) -> dv_station_dirs72.py
#   -> cap17 finish step (g9f_functional finish + select_native_local_source4 + land stages) -> cap18 table/land tweak
#   [-> CLK2 land_xhead_clk2.py when CLK2=1] -> dv_diecase --bind real -> dv_rvcase (cap18 flags).
# usage: pin_cap19.sh VARIANT RUN_DIR   (env: I = dir with cap17_input.tar.gz + pin_cap18.sh + tools/, SRC_TAR, CLK2=0|1)
set -uo pipefail
V=${1:?variant}; W=${2:?run dir}
I=${I:-/srv/opentallas-scratch2/claude/stw-s81c-cap19-1022/in}
SRC_TAR=${SRC_TAR:-/home/ubuntu/ot-scratch/claude/codex-s81-g9e-probe-2022-1021/inputs/source.tar.gz}
G=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
export OT_GIT_DIR=$G GIT_DIR=$G OT_DIE_REPAIR_CORRIDOR=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$(dirname "$W")"; mkdir "$W" || exit 2
trap 'rc=$?; echo "EXIT_RC $rc $(date -Is)" > "$W/run.exit"' EXIT
printf 'cap24 %s on 528fc3c9f (cap18 inputs) branch claude/s81c-cap24-1022 CLK2=%s %s\n' "$V" "${CLK2:-0}" "$(date -Is)" > "$W/start.identity"
tar -xzf "$I/cap17_input.tar.gz" -C "$W" || exit 4
tar -xzf "$SRC_TAR" -C "$W" || exit 4
sha256sum "$I/cap17_input.tar.gz" "$SRC_TAR" > "$W/archives.sha256"
for file in tools/s81_dv/ctrl_corner.tcl tools/s81_dv/dv_bind.py tools/s81_dv/dv_spare_out.py tools/s81_dv/dv_rvcase.py tools/s81_dv/geo_clock.py tools/die_repeaters/step.py tools/die_repeaters/fclk_audit.tcl tools/s81_dv/release72/g9f_functional.py rtl/dsrom_sys/s81_dv/land/dsdv_pv_local_land.sv tools/s81_dv/dv_station_dirs72.py; do
 git --git-dir="$G" show "528fc3c9f:$file" > "$W/src/$file" || exit 4
done
# STEWARD 00:14: one XS4 selector in strict bind and GEN = 50485a59 (claude/s81-rtlgap-g9-xs4-1022 357b79673 == f5f35855d == table prefer 8a495768f)
git --git-dir="$G" cat-file -e 357b79673 2>/dev/null || git --git-dir="$G" fetch -q origin claude/s81-rtlgap-g9-xs4-1022 || exit 4
git --git-dir="$G" show 357b79673:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv > "$W/src/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv" || exit 4
echo "50485a59b26517eb34e2ae4c0918f8480ae0c5e0c96f6246b93c30c6b7970808  $W/src/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv" | sha256sum -c >> "$W/steps.log" || exit 4
cp "$I/tools/dv_route72c.py" "$W/src/tools/s81_dv/dv_route72c.py" && cp "$I/tools/g9f_cap19_plan.py" "$W/src/tools/s81_dv/release72/" || exit 4
cp "${CAP24_TOOLS:?dir with g9f_cap24_plan.py + dv_rvcase.py (cap23)}/g9f_cap24_plan.py" "$W/src/tools/s81_dv/release72/" || exit 4
if [ "${CLK2:-0}" = 1 ]; then
 cp "$I/tools/clk2/dv_rvcase.py" "$W/src/tools/s81_dv/dv_rvcase.py" && cp "$I/tools/clk2/land_xhead_clk2.py" "$W/src/tools/s81_dv/release72/" || exit 4
fi
cp "$CAP24_TOOLS/dv_rvcase.py" "$W/src/tools/s81_dv/dv_rvcase.py" || exit 4
sha256sum "$W"/src/tools/s81_dv/dv_route72c.py "$W"/src/tools/s81_dv/release72/g9f_cap19_plan.py "$W"/src/tools/s81_dv/release72/g9f_cap24_plan.py "$W"/src/tools/s81_dv/dv_rvcase.py > "$W/tools.sha256"
cd "$W/src"
python3 - "$W/plan.json" "$W/plan_unrouted0.json" <<'PY' || exit 5
import json,sys
p=json.load(open(sys.argv[1]))
for l in p['links']:
 for k in ('h','sp','s','L','station_dirs'):l.pop(k,None)
json.dump(p,open(sys.argv[2],'w'),indent=1)
PY
python3 tools/s81_dv/release72/g9f_cap19_plan.py "$W/plan_unrouted0.json" "$W/plan_cap19fb.json" --variant fb > "$W/cap19_plan.log" 2>&1 || exit 5
python3 tools/s81_dv/release72/g9f_cap24_plan.py "$W/plan_cap19fb.json" "$W/plan_unrouted.json" --variant "$V" > "$W/cap24_plan.log" 2>&1 || exit 5
python3 tools/s81_dv/dv_route72c.py "$W/plan_unrouted.json" "$W/plan_routed.json" --iter 16 --hop-max 380 --dump "$W/route_hot.json" ${ROUTE_ARGS:-} > "$W/route.log" 2>&1 || exit 5
grep -q 'ROUTE_DONE failed 0 ' "$W/route.log" || exit 5
python3 tools/s81_dv/dv_station_dirs72.py "$W/plan_routed.json" results/arch/s81_die72_1021/relay_bodies.json "$W/plan.json" > "$W/station_dirs.log" 2>&1 || exit 5
# cap17 finish step (pin_cap17.sh PYP), source ref 528fc3c9f
python3 - "$W" <<'PYP' > "$W/finish.log" 2>&1 || exit 6
import sys,json
from pathlib import Path
sys.path.insert(0,'tools/s81_dv/release72')
from g9f_functional import finish,select_native_local_source4
r=Path(sys.argv[1]);p=json.load(open(r/'plan.json'));t=json.load(open(r/'table.json'));l=json.load(open(r/'land.json'))
finish(p,l);select_native_local_source4(t,l,'528fc3c9f')
for row in l['links']:
 link=next((x for x in p['links'] if x['i']==row['link']),None)
 if link:row['stages']=link['s']
t['functional_successor']['pool_body_growth']=p['facts']['pool_body_growth']
t['functional_successor']['cap19_floorplan']=p['facts']['physical72']['cap19']
t['functional_successor']['cap24_floorplan']=p['facts']['physical72']['cap24']
for name,obj in [('plan.json',p),('table.json',t),('land.json',l)]:json.dump(obj,open(r/name,'w'),indent=1)
PYP
# cap18 table/land tweak, verbatim from pin_cap18.sh
sed -n "/^python3 - \"\$W\/table.json\" <<'PY'$/,/^PY$/p" "$I/pin_cap18.sh" > "$W/cap18_tweak.sh"
test -s "$W/cap18_tweak.sh" || exit 6
W="$W" bash "$W/cap18_tweak.sh" > "$W/cap18_tweak.log" 2>&1 || exit 6
if [ "${CLK2:-0}" = 1 ]; then
 python3 tools/s81_dv/release72/land_xhead_clk2.py "$W/plan.json" "$W/land.json" "$W/land_x.json" ${CLK2_ARGS:-} > "$W/land_xhead.log" 2>&1 || exit 6
 mv "$W/land_x.json" "$W/land.json"
fi
python3 - "$W/land.json" <<'PY' > "$W/force_landing.log" 2>&1 || exit 6
import json, sys
p = sys.argv[1]; L = json.load(open(p)); n = 0
for r in L['links']:
    if r['link'] in ('iq_02_03_l0', 'iq_02_03_l1', 'is_02_03'):
        r['force_landing'] = True; n += 1
        r['K_source'] = r.get('K_source', '') + ' | cap24 (as C23 FB): force_landing on the u_irg_02 -> u_irg_03 region crossing; E/K unchanged'
assert n == 3, n
json.dump(L, open(p, 'w'), indent=1)
print('FORCE_LANDING', n)
PY
sha256sum "$W/plan.json" "$W/table.json" "$W/land.json" > "$W/input.sha256"
python3 tools/s81_dv/dv_diecase.py --plan "$W/plan.json" --out "$W/bind" --bind real --bind-table "$W/table.json" --land-plan "$W/land.json" > "$W/bind.log" 2>&1
rc=$?; echo "BIND_RC $rc $(date -Is)" >> "$W/steps.log"; test "$rc" = 0 || exit "$rc"
sha256sum "$W/bind/bind/die.v" > "$W/die.sha256"
python3 tools/s81_dv/dv_rvcase.py --plan "$W/plan.json" --bind-dir "$W/bind/bind" --bind-table "$W/table.json" --land-plan "$W/land.json" --out "$W/case" --view-refs 12c132d60a8f0300056abb216d48ff9588e7f620 553741303923ab6bab36d67d17f914b1f11896c5 c4d1047c20506ef133b4ec683d1b04aedcf4030a 6ff783251ab208a90632ee4ac180d7d529126676 --die-repair --dieflow-ref 33432c494a461c70406ffe5623fabae9548f6293 --dcc-ref 1a872af33c8d10d8123f8d4c69198e09cc04fd43 --corners tt ff ss --macro-views --signal-top-layer M8 --rfw --hold-eco --dieclk --fck-out-pin --rs-chain-place --rs-repair --dieclk-split-um 2000 --gen-safety-diag "cap24 $V (STW-S81c-DIE): cap19 FB + cap24 open W col6 street / wider centre+lower channels (g9f_cap24_plan.py), cap23 case flags, irg_02/03 landings; CLK2=${CLK2:-0}. Diagnostic while stand-ins remain." > "$W/case_gen.log" 2>&1
rc=$?; echo "CASE_RC $rc $(date -Is)" >> "$W/steps.log"; exit "$rc"
