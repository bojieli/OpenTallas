#!/bin/bash
# HEAD-97 rp21 plan chain (COORD 11-13 rulings + REACH-TOOL-3 1a13fcec4a). hd_tile 8.64 / 43.2 / 25.92 (8.64 lattice,
# tile 717.12, die +190.08) -> sink bins -> per-pin strip relays -> reach_pairs x_q -> u_xo + fix --rules 2 ->
# hd_host_e legalize + lattice re-block -> hd_host_w centred re-layout -> reset references re-derived (remap_start,
# head_reset_exports with offset fallback) -> R-REACH-4 fwd_source fix -> pin de-dup -> sidecar regions + collector sync
set -euo pipefail; cd /
H=/srv/opentallas-scratch2/claude/head-97; N=/srv/opentallas-scratch2/claude/wt/head-97-rp20; cd $H
export WS=8.64 ES=25.92
python3 -I ev21.py pd/rp20a.json pd/rp21a.json g_b/ev21_rep.json | cut -c1-300
python3 -I bins21.py pd/rp21a.json $N physical/die_plan/s81_head/plan_of_record/sink_bins/hd_tile_rp21.json
(cd $N && python3 -I $H/pinreg.py $N $H/pd/rp21a.json $H/pd/rp21b.json | tail -1)
python3 -I -c "
import json
p=json.load(open('pd/rp21b.json')); t=p['partition_types']['hd_tile']
t['reach_pairs']=[{'name':'x_xo','from':'x_q','to':'u_xo/q','bits':512,'note':'HEAD-97 rp21 F1c (COORD 11-13): hd_tile x -> xo round elemB; stages realized in RTL (XO_HOP)'}]
json.dump(p,open('pd/rp21c.json','w'),indent=1); open('pd/rp21c.json','a').write('\n')"
(cd $N && python3 -I tools/die_plan/reach_rules.py fix $H/pd/rp21c.json --repo $N --rules 2 --types hd_tile --out-plan $H/pd/rp21d.json --report $H/g_b/rr_fix21.json | tail -1)
(cd $N && python3 -I tools/die_plan/street_rule.py legalize $H/pd/rp21d.json --die s81_head --types hd_host_e --repo $N --out $H/g_b/leg_he21.json --out-plan $H/pd/rp21e.json --event $H/g_b/leg_he21_event.json > $H/g_b/leg_he21.log 2>&1); grep -v "^#" g_b/leg_he21.log | tail -2 | head -1 | cut -c1-250
python3 -I he_reblock.py pd/rp21e.json pd/rp21f.json | tail -2
python3 -I hw_relayout.py pd/rp21f.json pd/rp21gw.json
python3 -I mesh_relayout.py pd/rp21gw.json pd/rp21gm.json
python3 -I ctl_relayout.py pd/rp21gm.json pd/rp21g.json
ONLY=hd_host_e python3 -I remap_start.py $N pd/rp21e.json pd/rp21g.json pd/rp21g1.json > g_b/remap21e.log 2>&1; tail -1 g_b/remap21e.log | cut -c1-300
SKIP=hd_host_e python3 -I remap_start.py $N pd/rp20a.json pd/rp21g1.json pd/rp21h0.json > g_b/remap21.log 2>&1; tail -1 g_b/remap21.log | cut -c1-300
grep "not in OLD" g_b/remap21e.log g_b/remap21.log && { echo REMAP_STALE; exit 4; } || true
(cd $N && cp $H/head_reset_exports_rp21.py tools/s81_head/_h97_hre.py && python3 -I tools/s81_head/_h97_hre.py fix $H/pd/rp20a.json $H/pd/rp21h0.json $H/pd/rp21h.json > $H/g_b/rexp21.log 2>&1; rc=$?; rm -f tools/s81_head/_h97_hre.py; exit $rc)
grep "OFFSET-FALLBACK" g_b/rexp21.log || true
(cd $N && python3 -I tools/die_plan/reach_rules.py fix $H/pd/rp21h.json --repo $N --rules 4 --out-plan $H/pd/rp21i.json --report $H/g_b/rr_fix21i.json | tail -1)
python3 -I pindedup.py pd/rp21i.json pd/rp21j.json
(cd $N && python3 -I tools/s81_head/head_reset_exports.py check $H/pd/rp21j.json | tail -1)
python3 -I side21.py pd/rp20a.json pd/rp21j.json pd/sidecar.json pd/sidecar_rp21m.json | head -1
(cd $N && python3 -I tools/die_plan/street_rule.py sidecar $H/pd/rp20a.json $H/pd/rp21j.json $H/pd/sidecar_rp21m.json $H/pd/sidecar_rp21.json)
python3 -I -c "
import json
d=json.load(open('pd/sidecar_rp21.json')); t=d['collector']['types']['hd_tile']
x,y=t['collector_root_xy']; t['collector_root_xy']=[round(x+8.64,4) if x>=691.2 else x,y]
json.dump(d,open('pd/sidecar_rp21.json','w'),separators=(',',':'))"
sha256sum pd/rp21j.json pd/sidecar_rp21.json | cut -c1-16
(cd $N && python3 -I tools/die_plan/street_rule.py check $H/pd/rp21j.json --die s81_head --repo $N --out $H/g_b/st3_rp21j.json > $H/g_b/st3_rp21j.log 2>&1; tail -1 $H/g_b/st3_rp21j.log)
(cd $N && python3 -I tools/die_plan/check.py $H/pd/rp21j.json --out $H/g_b/g0_rp21j --quiet > $H/g_b/g0_rp21j.log 2>&1 || true; tail -2 $H/g_b/g0_rp21j.log | cut -c1-200)
(cd $N && python3 -I tools/die_plan/reach_rules.py check $H/pd/rp21j.json --repo $N > $H/g_b/rr_rp21j.log 2>&1 || true; head -1 $H/g_b/rr_rp21j.log)
python3 -I xohop/xohop_delta.py pd/rp21j.json pd/rp21x.json --report g_b/xohop_rep.json | cut -c1-200
sha256sum pd/rp21x.json | cut -c1-16
PW=$H/prep21c PO=$H/kits21c PT=hd_ctl bash $H/prep21.sh > $H/prep21c.out 2>&1; grep -v "cp: warning" $H/prep21c.out | grep "rc \\|GEN\\|KITRTL" | cut -c1-200
echo BUILD21_DONE
