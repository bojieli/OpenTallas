#!/bin/bash
# STW-S81d-GEN 10-22: cap31 = pin_cap30.sh with the plan step g9f_cap31_plan.py (cap30 moves + s_0S/s_0N +172.8 N, s_7N +216 N,
# lk_WN3/lk_WN1 +172.8 E) and optional ROUTE_ARGS; everything else (binds, force_landing incl. 0-stage xring, case flags) unchanged.
# STW-S81c-DIE3-C28 10-22: cap28 = pin_cap26.sh (same cap24+cap26 plans, same binds, same route) + the structural die-clock
# fix, no interface / port / latency change: dv_rvcase.py (this branch) --dieclk-pin-split (sub-root bisection + anchors
# on the REAL sink clock-pin positions) --dieclk-split-um 1500 (sub-roots <= ~1.5 mm, same balance group, same die clock
# port) --dieclk-ckr-reserve (obstacle-free reserved FIRM entry-buffer sites at the region anchors, placed before ties/rfw)
# --dieclk-iters ${DIECLK_ITERS:-6}.  usage: C24=main|fb C26=A|B|C CAP28_TOOLS=dir pin_cap28.sh NAME RUN_DIR
# STW-S81c-DIE2-C25 10-22: cap26 = pin_cap25.sh (all cap25 binds: lnland, kit_reset_landing, hop-max 340) on a cap26
# floorplan: g9f_cap24_plan.py --variant $C24 then g9f_cap26_plan.py --variant $C26 (rigid col6 re-stack / E centre).
# usage: C24=main|fb C26=A|B|C|Ae|Be|Ce pin_cap26.sh NAME RUN_DIR
# STW-S81c-DIE2-C25 10-22: cap25 = pin_cap24.sh (same plan, same flags) + three additions, nothing else:
#  (1) MU72 end tops with lane landing (STW-S81c-COLLA2 08:36 BIND, ot_s81_mu72_lnland @ main 370e06603 incl. showahead
#      fix 893432491 + CRED12 lane sources a19178766): RTL/tools swapped file by file from 370e06603 (sha256 in
#      cap25_swap.sha256), table step cap25_table.py (current main mu72_overlay.json + apply_ep_clock_g8, plain lep_mu_ab,
#      r4l UNBOUND, s_0N keeps its HOST(b) HBC as ot_s81sl_slice_lepw_mab_hbc_prod_mu_72);
#  (2) kit_reset_landing_stages ctrl_rg3 +2: dv_bind.py = 528fc3c9f + the 5c27c09ce hunk (claude/s81c-die2-rdepth-1022);
#  (3) dv_route72c --hop-max 340 (cap24 MAIN W1: one 462-um ret hop r_f_0R03).
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
printf 'cap31 (STW-S81d-GEN: cap30 + s_0S/s_0N +172.8 N, s_7N +216 N, lk_WN3/WN1 +172.8 E, g9f_cap31_plan.py; ROUTE_ARGS=${ROUTE_ARGS:-}) %s (cap24 %s, cap26 %s) + C28 dieclk pin-split 1500 / ckr-reserve / iters on 528fc3c9f (cap18 inputs) + 370e06603 lnland + 5c27c09ce kit_rl, branch claude/s81c-cap28-1022 CLK2=%s %s\n' "$V" "${C24:?}" "${C26:?}" "${CLK2:-0}" "$(date -Is)" > "$W/start.identity"
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
CAP24_TOOLS=${CAP25_TOOLS:?dir with g9f_cap24_plan.py + dv_rvcase.py (cap23) + cap25_table.py}
cp "$CAP24_TOOLS/g9f_cap24_plan.py" "$CAP24_TOOLS/g9f_cap26_plan.py" "$W/src/tools/s81_dv/release72/" || exit 4
if [ "${CLK2:-0}" = 1 ]; then
 cp "$I/tools/clk2/dv_rvcase.py" "$W/src/tools/s81_dv/dv_rvcase.py" && cp "$I/tools/clk2/land_xhead_clk2.py" "$W/src/tools/s81_dv/release72/" || exit 4
fi
cp "$CAP24_TOOLS/dv_rvcase.py" "$W/src/tools/s81_dv/dv_rvcase.py" || exit 4
cp "${CAP28_TOOLS:?dir with the cap28 dv_rvcase.py}/dv_rvcase.py" "$W/src/tools/s81_dv/dv_rvcase.py" || exit 4
# cap25 (2): dv_bind = 528fc3c9f + 5c27c09ce kit_reset_landing_stages hunk (its test_port_clock_bind case: 18/18 PASS on 528fc3c9f + hunk, C25 08:5x)
git --git-dir="$G" show 5c27c09ce -- tools/s81_dv/dv_bind.py > "$W/kit_rl.patch" || exit 4
patch -p1 -d "$W/src" < "$W/kit_rl.patch" > "$W/kit_rl_patch.log" 2>&1 || exit 4
echo "b35c2a50a431b7e4a1fde73a48a19cb96fd2fc83c66e6a980164cc1ba1ae0d0f  $W/src/tools/s81_dv/dv_bind.py" | sha256sum -c >> "$W/steps.log" || exit 4
# cap25 (1): lnland MU72 tops + tools from main 370e06603, file by file
LN=370e06603
for file in rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_lnland.sv rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81sl_slice_lepw_mu_72.sv \
  rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81sl_slice_lepw_mab_mu_72.sv rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81sl_slice_lepw_mab_hbc_prod_mu_72.sv \
  rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81sl_slice_lepe_mu_72.sv rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81sl_slice_lepe_nh_mu_72.sv \
  rtl/lib/ot_sram_showahead_1r1w.sv rtl/common/ot_link_credit_rx_b64.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv \
  tools/s81_dv/release72/apply_mu72_overlay.py tools/s81_dv/release72/mu72_overlay.json tools/s81_dv/release72/apply_ep_clock_g8.py; do
 (test -f "$W/src/$file" && sha256sum "$W/src/$file" || echo "absent  $W/src/$file") >> "$W/cap25_swap_before.sha256"
 mkdir -p "$(dirname "$W/src/$file")"; git --git-dir="$G" show "$LN:$file" > "$W/src/$file" || exit 4
 sha256sum "$W/src/$file" >> "$W/cap25_swap.sha256"
done
cp "$CAP24_TOOLS/cap25_table.py" "$W/src/tools/s81_dv/release72/" || exit 4
sha256sum "$W"/src/tools/s81_dv/dv_bind.py "$W"/src/tools/s81_dv/release72/cap25_table.py "$W"/src/tools/s81_dv/dv_route72c.py "$W"/src/tools/s81_dv/release72/g9f_cap19_plan.py "$W"/src/tools/s81_dv/release72/g9f_cap24_plan.py "$W"/src/tools/s81_dv/release72/g9f_cap26_plan.py "$W"/src/tools/s81_dv/dv_rvcase.py > "$W/tools.sha256"
cd "$W/src"
python3 - "$W/plan.json" "$W/plan_unrouted0.json" <<'PY' || exit 5
import json,sys
p=json.load(open(sys.argv[1]))
for l in p['links']:
 for k in ('h','sp','s','L','station_dirs'):l.pop(k,None)
json.dump(p,open(sys.argv[2],'w'),indent=1)
PY
python3 tools/s81_dv/release72/g9f_cap19_plan.py "$W/plan_unrouted0.json" "$W/plan_cap19fb.json" --variant fb > "$W/cap19_plan.log" 2>&1 || exit 5
python3 tools/s81_dv/release72/g9f_cap24_plan.py "$W/plan_cap19fb.json" "$W/plan_cap24.json" --variant "$C24" > "$W/cap24_plan.log" 2>&1 || exit 5
python3 tools/s81_dv/release72/g9f_cap26_plan.py "$W/plan_cap24.json" "$W/plan_cap26.json" --variant "$C26" > "$W/cap26_plan.log" 2>&1 || exit 5
cp "$CAP28_TOOLS/g9f_cap31_plan.py" "$W/src/tools/s81_dv/release72/" && python3 tools/s81_dv/release72/g9f_cap31_plan.py "$W/plan_cap26.json" "$W/plan_unrouted.json" > "$W/cap31_plan.log" 2>&1 || exit 5
python3 tools/s81_dv/dv_route72c.py "$W/plan_unrouted.json" "$W/plan_routed.json" --iter 16 --hop-max 340 --dump "$W/route_hot.json" ${ROUTE_ARGS:-} > "$W/route.log" 2>&1 || exit 5
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
t['functional_successor']['cap26_floorplan']=p['facts']['physical72']['cap26']
t['functional_successor']['cap31_floorplan']=p['facts']['physical72']['cap31']
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
# STEWARD 06:4x / RTLGAP BIND 06:34: census-safe su_kv cmp.pool (same module + ports, drop-in) from claude/rtlgap-sukv-so-1022
# 28b04754d replaces 75c077ec9 ot_s81sl_cmp_pool.sv (native max 193) in u_s_3N's KV slice package: MAIN die -> pool_safe_main.sv,
# FB die -> pool_safe_alternate.sv (single-root variants; the regional ones need 8 pool lane regions). MU.S81.CAL: CP 391 -> 431.
POOL_REF=28b04754d; POOL_FILE=rtl/dsrom_sys/s81_dv/slice/pool_safe_$([ "$C24" = main ] && echo main || echo alternate).sv
git --git-dir="$G" cat-file -e "$POOL_REF^{commit}" 2>/dev/null || git --git-dir="$G" fetch -q origin claude/rtlgap-sukv-so-1022 || exit 6
git --git-dir="$G" cat-file -e "$POOL_REF:$POOL_FILE" || exit 6
python3 - "$W/table.json" "$POOL_REF" "$POOL_FILE" <<'PY' > "$W/pool_bind.log" 2>&1 || exit 6
import json, sys
p, ref, f = sys.argv[1:]; T = json.load(open(p)); old = 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cmp_pool.sv'
assert old in T['rtl_refs']['75c077ec9'], 'cmp_pool not in 75c077ec9 refs'
T['rtl_refs']['75c077ec9'].remove(old); T['rtl_refs'].setdefault(ref, []).append(f)
i = T['prefer'].index('75c077ec9/' + old); T['prefer'][i] = f'{ref}/{f}'
T['functional_successor']['sukv_pool'] = dict(ref=ref, file=f, replaces='75c077ec9/' + old, census='native PASS max 29 loads/driver (RTLGAP 06:34)',
                                              calendar='CP job kind 14: 391 -> 431 cycles (+40), MU.S81.CAL')
json.dump(T, open(p, 'w'), indent=1)
print('POOL_BIND', ref, f)
PY
python3 - "$W/land.json" <<'PY' > "$W/force_landing.log" 2>&1 || exit 6
import json, sys
p = sys.argv[1]; L = json.load(open(p)); n = 0
for r in L['links']:
    if r['link'] in ('iq_02_03_l0', 'iq_02_03_l1', 'is_02_03'):
        r['force_landing'] = True; n += 1
        r['K_source'] = r.get('K_source', '') + ' | cap24 (as C23 FB): force_landing on the u_irg_02 -> u_irg_03 region crossing; E/K unchanged'
# cap30 (DIE4): the street re-slots shorten some xring lanes to 0 route stages; a region crossing keeps its landing ring.
x = 0
for r in L['links']:
    if r.get('cls') == 'xring' and r.get('stages') == 0 and not r.get('force_landing'):
        r['force_landing'] = True; x += 1
        r['K_source'] = r.get('K_source', '') + ' | cap30: force_landing (street re-slot left 0 route stages on this xring crossing); E/K unchanged'
print('FORCE_LANDING_XRING', x)
assert n == 3, n
json.dump(L, open(p, 'w'), indent=1)
print('FORCE_LANDING', n)
PY
python3 tools/s81_dv/release72/cap25_table.py "$W/table.json" "$W/plan.json" > "$W/cap25_table.log" 2>&1 || exit 6
sha256sum "$W/plan.json" "$W/table.json" "$W/land.json" > "$W/input.sha256"
python3 tools/s81_dv/dv_diecase.py --plan "$W/plan.json" --out "$W/bind" --bind real --bind-table "$W/table.json" --land-plan "$W/land.json" > "$W/bind.log" 2>&1
rc=$?; echo "BIND_RC $rc $(date -Is)" >> "$W/steps.log"; test "$rc" = 0 || exit "$rc"
sha256sum "$W/bind/bind/die.v" > "$W/die.sha256"
python3 tools/s81_dv/dv_rvcase.py --plan "$W/plan.json" --bind-dir "$W/bind/bind" --bind-table "$W/table.json" --land-plan "$W/land.json" --out "$W/case" --view-refs 12c132d60a8f0300056abb216d48ff9588e7f620 553741303923ab6bab36d67d17f914b1f11896c5 c4d1047c20506ef133b4ec683d1b04aedcf4030a 6ff783251ab208a90632ee4ac180d7d529126676 --die-repair --dieflow-ref 33432c494a461c70406ffe5623fabae9548f6293 --dcc-ref 1a872af33c8d10d8123f8d4c69198e09cc04fd43 --corners tt ff ss --macro-views --signal-top-layer ${SIGTOP:-M9} --m9-pg-reserve 0 --upper-adj ${UPPER_ADJ:-0.10} --congestion-iterations ${CONG_IT:-0} --rfw --hold-eco --dieclk --fck-out-pin --rs-chain-place --rs-repair --dieclk-split-um 1500 --dieclk-pin-split --dieclk-ckr-reserve --dieclk-iters ${DIECLK_ITERS:-6} --gen-safety-diag "cap31 $V (STW-S81d-GEN: cap30 + 5 rigid re-slots g9f_cap31_plan.py) on cap28 $V (STW-S81c-DIE3-C28): die clock fix = sub-roots split on real sink-pin positions at 1500 um (same balance group / die clock port) + reserved FIRM obstacle-free CKR sites at region anchors + dieclk iters ${DIECLK_ITERS:-6}; on cap26 $V (STW-S81c-DIE2-C25): cap24 $C24 + cap26 $C26 rigid re-slot (g9f_cap26_plan.py) + cap25 binds: lnland MU72 end tops (370e06603, lane regions ck_N*, CRED12) + kit_reset_landing ctrl_rg3 +2 + hop-max 340; cap24 $V: cap19 FB + cap24 open W col6 street / wider centre+lower channels (g9f_cap24_plan.py), cap23 case flags, irg_02/03 landings; CLK2=${CLK2:-0}. Diagnostic while stand-ins remain." > "$W/case_gen.log" 2>&1
rc=$?; echo "CASE_RC $rc $(date -Is)" >> "$W/steps.log"; exit "$rc"
