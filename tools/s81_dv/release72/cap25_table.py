#!/usr/bin/env python3
"""S81 DIE72 cap25 bind-table step (STW-S81c-DIE2-C25 10-22): cap24 table + three additions, nothing else.

 (1) MU72 end tops with lane landing (STW-S81c-COLLA2 08:36 BIND, ot_s81_mu72_lnland, main 370e06603):
     a. tools/s81_dv/release72/apply_mu72_overlay.py with the CURRENT main mu72_overlay.json (lane_regions ck_N*,
        u_lep CRED/DR 12, lanes CORE_CRED 12; PLAIN ot_s81sl_lep_mu_ab, r4l UNBOUND: mu72_overlay_r4l.json NOT used).
     b. s_0N keeps its HOST(b) HBC unit (frozen host option (b)): cap24 bound s_0N to
        ot_s81sl_slice_lepw_mab_hbc_r4d_mu_72 (HBC + the r4l regional lep, now UNBOUND).  Its plain-lep lnland
        successor with the same HBC ports is ot_s81sl_slice_lepw_mab_hbc_prod_mu_72 (= lepw_mab_mu_72 + HBC,
        HBC_ENABLE 0 as cap24); the overlay's plain lepw_mab_mu_72 would drop the HBC, so s_0N's row takes hbc_prod.
     c. lane_regions -> port clocks: die ports tx<i>.o / rx<i>.i of each end parent are timed / landed on ck_N<i>
        (the lane region, overlay note 'die landing / pin side: the lane, not K'), as cap24 did for r4d's ck_KA/KB.
     d. rtl_widths of the five MU72 tops = their RTL ports at 370e06603 (overlay widths checked equal, + ck_N<i>, hb_*).
     e. per-region die clock roots: apply_ep_clock_g8.py re-run on the 4 end parents (ck_ep_<inst>_N<i> added,
        ck_ep_s_0N_KA/KB dropped); every root that existed in cap24 keeps its cap24 clock_domains row byte-identical.
     f. child_views of the u_ln* lanes: CRED12 coll lane views W dscoll_lane_w_s12h / E dscoll_lane_e_s12g (a19178766).
     g. the r4d file (and its r4l lep) leaves rtl_refs / prefer; the 3d16b87e2 hostb HBC sources stay.
 (2) kit_reset_landing_stages {dsfd_ctrl_rg3: 2, dsfd_ctrl_rg3_native32: 2} (dv_bind 5c27c09ce hunk).
Usage (cwd = GEN src): cap25_table.py TABLE PLAN
"""
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, 'tools')
import die_port_bind as D  # noqa: E402

EP = ('s_0S', 's_0N', 's_7S', 's_7N')
MU = 'rtl/dsrom_sys/s81_dv/slice/mu72'
HBC_PROD = 'ot_s81sl_slice_lepw_mab_hbc_prod_mu_72'
R4D = 'ot_s81sl_slice_lepw_mab_hbc_r4d_mu_72'
LNLAND_REF = '370e06603'
KIT_RL = {'dsfd_ctrl_rg3': 2, 'dsfd_ctrl_rg3_native32': 2}
CRED12_VIEWS = {
    'dsfd_coll_lane_w_safe8_ntf': dict(view='dscoll_lane_w_s12h-dscoll_lane_w_s12h-8eb663ae9 (CORE_CRED12 closure candidate, gate WARN)',
                                       kit='physical/ref_tile/dscoll_lane_w_s12h', source='8eb663ae9', record='a19178766'),
    'dsfd_coll_lane_e_safe8_ntf': dict(view='dscoll_lane_e_s12g-dscoll_lane_e_s12g-8eb663ae9 (CORE_CRED12 closure candidate, gate WARN)',
                                       kit='physical/ref_tile/dscoll_lane_e_s12g', source='8eb663ae9', record='a19178766'),
}

tp, pp = Path(sys.argv[1]), Path(sys.argv[2])
t0 = json.loads(tp.read_text()); plan = json.loads(pp.read_text())
blocks = {b['name']: b for b in plan['blocks']}
ep_master = {i: blocks[i]['master'] for i in EP}
old_icp = {i: dict(t0['instance_clock_ports'][i]) for i in EP}
old_dom = {n: t0['clock_domains'][n] for r in old_icp.values() for n in r.values()}
old_s0n = json.loads(json.dumps(t0['masters'][ep_master['s_0N']]))
assert old_s0n['module'] == R4D, old_s0n['module']

# (1a) the current main overlay, verbatim tool
r = subprocess.run([sys.executable, 'tools/s81_dv/release72/apply_mu72_overlay.py', str(tp)], capture_output=True, text=True)
print(r.stdout.strip()); assert r.returncode == 0, r.stderr
t = json.loads(tp.read_text())
ov = json.loads(Path('tools/s81_dv/release72/mu72_overlay.json').read_text())

# (1b) s_0N: HBC kept, plain lep + lnland lanes
s0n = t['masters'][ep_master['s_0N']]
assert s0n['module'] == 'ot_s81sl_slice_lepw_mab_mu_72', s0n['module']
for k in ('params', 'top_ports', 'mode_unused'):
    assert s0n.get(k) == old_s0n.get(k), k            # HBC row data untouched by the overlay
s0n['module'] = HBC_PROD
s0n['ref'] = LNLAND_REF
s0n['view_note'] = (f'cap25 (STW-S81c-DIE2-C25 10-22): {HBC_PROD} @{LNLAND_REF} = the plain-lep (ot_s81sl_lep_mu_ab, r4l UNBOUND) '
                    'lnland successor of cap24 ' + R4D + ' with the same HOST(b) HBC ports, HBC_ENABLE 0; lanes u_ln0..3 in regions '
                    'N0..N3 (CORE_CRED12), every lep<->lane net landed +3 each way (ot_s81_mu72_lnland). Unhardened, no parent view. '
                    'cap24 note: ' + old_s0n.get('view_note', ''))

# (1c) lane-region port clocks, (1d) RTL widths
modules = {}
for i in EP:
    m = t['masters'][ep_master[i]]
    lr = m.get('lane_regions')
    assert lr, (i, ep_master[i])
    n = 0
    for ck, row in lr.items():
        assert ck in m['clk_extra'], (i, ck)
        for p in row['ports']:
            key = f"{p}.{'o' if p.startswith('tx') else 'i'}"
            assert key in m['ports'], (i, key)
            m['ports'][key]['clock_port'] = ck; n += 1
    assert not any(c in ('ck_KA', 'ck_KB') for c in m['clk_extra']), i
    modules[m['module']] = i
    print('LANE_REGION_PORTS', i, ep_master[i], m['module'], len(lr), 'regions', n, 'ports')
for mod in modules:
    src = Path(f'{MU}/{mod}.sv')
    md = [x for x in D.parse_modules(src.read_text(), str(src)) if x.name == mod]
    assert len(md) == 1, mod
    md = md[0]; env = dict(md.params)
    w = {p: md.width(p, env) for p in md.ports}
    for k, v in ov['rtl_widths'].get(mod, {}).items():
        assert w.get(k) == v, (mod, k, w.get(k), v)
    t['rtl_widths'][mod] = w
    for i in EP:
        m = t['masters'][ep_master[i]]
        if m['module'] == mod:
            for c in [m['clk']] + m['clk_extra']:
                assert w.get(c) == 1, (mod, c)
t['rtl_widths'].pop(R4D, None)

# (1e) per-region roots: drop the cap24 EP rows, re-run the G8 tool, restore every cap24 row that still exists
for i in EP:
    for net in t['instance_clock_ports'].pop(i).values():
        t['clock_domains'].pop(net)
tp.write_text(json.dumps(t, indent=1) + '\n')
r = subprocess.run([sys.executable, 'tools/s81_dv/release72/apply_ep_clock_g8.py', str(tp), str(pp)], capture_output=True, text=True)
print(r.stdout.strip()); assert r.returncode == 0, r.stderr
t = json.loads(tp.read_text())
kept, new, dropped = 0, [], []
for i in EP:
    for p, net in t['instance_clock_ports'][i].items():
        if net in old_dom:
            t['clock_domains'][net] = old_dom[net]; kept += 1
        else:
            new.append(net)
    dropped += [n for n in old_icp[i].values() if n not in t['instance_clock_ports'][i].values()]
assert all('_N' in n for n in new), new
print('EP_ROOTS kept', kept, 'new', len(new), new, 'dropped', dropped)

# (1f) CRED12 lane views, (1g) r4d / r4l out of the RTL closure
for m, v in CRED12_VIEWS.items():
    t['child_views'][m] = dict(v, parent='MU72 end parents u_ln* (lanes #(.CORE_CRED(12)), lnland 370e06603)',
                               replaces=t['child_views'][m]['view'])
r4d_path = f'{MU}/{R4D}.sv'
t['rtl_refs']['3d16b87e2'] = [p for p in t['rtl_refs']['3d16b87e2'] if p != r4d_path]
t['prefer'] = [p for p in t['prefer'] if p != f'3d16b87e2/{r4d_path}']
assert not any('lepw_mab_hbc_r4d' in p for p in t['prefer'])

# (2) block-kit reset landing
t['kit_reset_landing_stages'] = dict(KIT_RL)
hbc = t['functional_successor'].get('hbc')
if hbc:
    hbc['cap24_master'] = hbc['master']; hbc['master'] = HBC_PROD; hbc['source_ref'] = LNLAND_REF
t['functional_successor']['cap25'] = dict(
    lnland=dict(source_ref=LNLAND_REF, bind='STW-S81c-COLLA2 08:36', overlay='tools/s81_dv/release72/mu72_overlay.json @370e06603',
                masters={i: [ep_master[i], t['masters'][ep_master[i]]['module']] for i in EP},
                lane_region_roots=new, dropped_roots=dropped, r4l='UNBOUND (mu72_overlay_r4l.json not used)'),
    kit_reset_landing_stages=KIT_RL, route_hop_max_um=340)
tp.write_text(json.dumps(t, indent=1) + '\n')
print('CAP25_TABLE OK modules', sorted(modules), 'kit_reset_landing_stages', KIT_RL)
