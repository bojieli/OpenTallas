#!/usr/bin/env python3
"""S81-DIE6 (10-18): bind_table_p4l.json = bind_table_p4k.json + the RTL built since S81-DIE5 (claude/rtl-build-s81-1018):
end-slice link endpoints lepw / lepe (tx / rx 514 {st, rx}, host plane on s_7N), seq_host per-half svc ports, svc_rs
st_rg producer (up faces 16 b, entry st_rg -> jd lanes), mix4 deleted (in-slice Engram path), worktree slice RTL (Engram ENG
leaves) instead of the 57bc4ad / 1dcaa1b20 pins, newly CLOSED child views.  rtl_widths re-read from the worktree RTL."""
import copy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as D
B = ROOT / 'results/arch/s81_dv_1016/bind'
T = json.load(open(B / 'bind_table_p4k.json'))
M = T['masters']
M.pop('dsfd_engram_mix4_half')
for ref in ('57bc4ad63f81e29f35a758ec36e4827265047874', '1dcaa1b20e0a536f1413c9e9b2c397414c3262e1'):
    T['rtl_refs'].pop(ref)
T['prefer'] = [p for p in T['prefer'] if not p.startswith('claude_s81slice-1017/')]
# ---- end-slice endpoints
lep = M.pop('dsdv_slice_lep')
# S81-LEPV (10-18): host plane only on s_7N -> host-less masters (HOST_EN 0, no host ports, no tied pads):
#   dsdv_slice_lepw (s_0S / s_0N), dsdv_slice_lepe_nh (s_7S); dsdv_slice_lepe (s_7N) keeps the host plane
LEPS = (('w', 'ot_s81sl_slice_lepw', False), ('e', 'ot_s81sl_slice_lepe', True), ('e_nh', 'ot_s81sl_slice_lepe_nh', False))
for side, mod, host in LEPS:
    m = copy.deepcopy(lep)
    m['module'] = mod; m.pop('ref', None); m.pop('plan_only_ports', None)
    m['view_note'] = ('cluster not hardened; leaf ' + ('ot_s81sl_lep kit s81sl_lep' if host else 'ot_s81sl_lep_nh kit s81sl_lepnh (HOST_EN 0)')
                      + ' (critical gate under review), lane tiles dsfd_coll_lane_w/e')
    m['mode_unused'] = [u for u in m['mode_unused'] if u['port'] not in ('ri_w', 'ri_e')]
    m['straps'] = m.get('straps', []) + ['ch_b']
    m['strap_values'] = dict(m.get('strap_values', {}), ch_b="1'b0")
    for k in '01':
        m['ports'][f'tx{k}.o'] = {'port': f'tx{k}', 'lane': 512}
        m['ports'][f'rx{k}.i'] = {'lanes': [{'split': [[f'rx{k}', 0, 0, 514]]}], 'land': True}
    if not host:
        m['port_note'] = ('p4l: tx 512 -> PHY tx; rx 514 = {PHY st 2, rx 512} on a 562 lane (landed); NO host plane (HOST_EN 0: '
                          'the master has no t_host / t_kd / f_host / f_lf / f_ks ports); ch_b strap 0 (UCIe basis)')
        M[f'dsdv_slice_lep{side}'] = m
        continue
    m['ports']['hf.o'] = {'lanes': [{'split': [['f_host', 0, 0, 276]]}, {'split': [['f_host', 276, 0, 239], ['f_lf', 0, 239, 4], ['f_ks', 0, 243, 33]]}, {'split': [['f_ks', 33, 0, 20]]}]}   # 3 x 276 lanes (closed 276 relays in all directions)
    m['ports']['ht.i'] = {'land': True, 'lanes': [{'split': [['t_host', 0, 0, 77], ['t_kd', 0, 77, 54]]}]}
    m['port_note'] = ('p4l: tx 512 -> PHY tx; rx 514 = {PHY st 2, rx 512} on a 562 lane (landed); host plane hf (572 b on 3 x 276 -> seqhost '
                      'f_host / f_lf / f_ks) / ht (131 b <- seqhost t_host / t_kd) only on s_7N; ch_b strap 0 (UCIe basis)')
    M[f'dsdv_slice_lep{side}'] = m
for ph in ('ot_pdie_ucie', 'ot_pdie_serdes'):
    M[ph]['ports']['rx.o'] = {'lanes': [{'split': [['rx', 0, 0, 512], ['st', 0, 512, 2]]}]}
# ---- seq_host per-half + host plane
sh = M['dsdv_seq_host']
sh['ref'] = 'claude/rtl-build-s81-1018'
sh['ports']['jw.o'] = {'lanes': [{'split': [['s_j', 0, 0, 33], ['s_hw_e', 0, 33, 243]]}, {'split': [['s_hw_e', 243, 0, 49]]},
                                 {'split': [['=s_j', 0, 0, 33], ['s_hw_w', 0, 33, 243]]}, {'split': [['s_hw_w', 243, 0, 49]]}]}
sh['ports']['jd.i'] = {'land': True, 'lanes': [{'split': [['s_jd_e', 0, 0, 2], ['s_hc_e', 0, 2, 9], ['st_rg_e', 0, 11, 2]]},
                                               {'split': [['s_jd_w', 0, 0, 2], ['s_hc_w', 0, 2, 9], ['st_rg_w', 0, 11, 2]]}]}
sh['ports']['hf.i'] = {'land': True, 'lanes': [{'split': [['f_host', 0, 0, 276]]}, {'split': [['f_host', 276, 0, 239], ['f_lf', 0, 239, 4], ['f_ks', 0, 243, 33]]}, {'split': [['f_ks', 33, 0, 20]]}]}
sh['ports']['ht.o'] = {'lanes': [{'split': [['t_host', 0, 0, 77], ['t_kd', 0, 77, 54]]}]}
sh.pop('mode_unused', None)
sh['port_note'] = ('p4l: cw; per-half job jw_E (s_j + s_hw_e) / jw_W (s_j copied + s_hw_w); jd_E / jd_W {jd, hc, st_rg} per '
                   'half (landed); host plane hf / ht to end slice s_7N (landed)')
# ---- svc_rs: up faces 16 (st_rg fold), entry st_rg -> jd lane bits 11..12
sv = M['dsdv_svc_rs']
sv['ref'] = 'claude/rtl-build-s81-1018'
for f in 'NESW':
    for d in 'oi':
        sv['ports'][f'up{f}.{d}']['lane'] = 16
sv['ports']['jd.o'] = {'lanes': [{'split': [['jd', 0, 0, 2], ['hc', 0, 2, 9], ['st_rg', 0, 11, 2]]}]}
# ---- jd lanes order: the plan names jd_E / jd_W; dv_bind orders lanes of one port by link name -> E first, W second
# ---- widths from the worktree RTL
mods = {}
for p in (ROOT / 'rtl').rglob('*.sv'):
    try:
        for md in D.parse_modules(p.read_text(errors='replace'), str(p)):
            mods.setdefault(md.name, md)
    except Exception:
        pass
for mod in list(T['rtl_widths']) + [mod for _, mod, _ in LEPS]:
    md = mods.get(mod)
    if md is None:
        print('no module', mod); continue
    w, env = {}, md.env()
    for pn in md.ports:
        try:
            w[pn] = md.width(pn, env)
        except Exception:
            w[pn] = None
    T['rtl_widths'][mod] = {k: v for k, v in w.items() if v} or T['rtl_widths'].get(mod, {})
T['rtl_widths'] = {k: v for k, v in T['rtl_widths'].items() if k != 'dsfd_engram_mix4_half'}
# ---- views
cv = T['child_views']
new = {'dsdv_gunit_l1': ('dsdv_gunit_l1-gl1-ecad968d3', 'dsdv_gunit'), 'dsdv_gunit_l1c': ('dsdv_gunit_l1c-gl1-ecad968d3', 'dsdv_gunit'),
       'dsdv_gunit_l4': ('dsdv_gunit_l4-nf3-14b48ae73', 'dsdv_gunit'), 'dsdv_sh_vc': ('dsdv_sh_vc-nf3bt-ce989b78c', 'dsdv_seq_host'),
       'ot_s81sl_vq': ('s81sl_vq-n3-8eea202c0', 'ot_s81sl_slice'), 'ot_s81sl_cap_tr': ('s81sl_cap_tr-s81sl_cap_tr-0ecc0c258', 'ot_s81sl_slice (capture root)'),
       'ot_s81sl_hcpl': ('s81sl_hcpl-s81sl_hcpl-31155b373', 'ot_s81sl_vp (16 x hcpl)'), 'dsdv_bk_cm': ('s81dvbk_cm-m1-8c2850345', 'dsfd_bk_collector'),
       'ot_s81sl_xfin': ('s81dv_xfin-x5-06cb91161', 'ot_s81sl_slice'), 'ot_s81_rate_match': ('s81lk_rate_match-ec1-bc3912b42', 'ot_pdie_ucie / serdes')}
for k, (job, par) in new.items():
    cv[k] = {'view': f'{job} (CLOSED, closure_loop state 10-18)', 'parent': par}
T['child_views_owed'] = {k: v for k, v in T['child_views_owed'].items() if k not in new}
T['child_views_owed'].update({'ot_s81sl_lep': 'kit s81sl_lep critical gate under coordinator review (03afd8c1a)',
                              'ot_s81sl_lep_nh': 'kit s81sl_lepnh (HOST_EN 0 leaf of s_0S / s_0N / s_7S, S81-LEPV) critical gate',
                              'dsfd_dvland_pvrd': 'hardened view owed (S81-DIE5)', 'ot_s81sl_eg': 's81sl_eg-v1-fbb651e33 routing',
                              'ot_s81sl_vs': 's81sl_vs regate/submit pending', 'ot_s81sl_ve': 'gate pending'})
T['plan'] = 'S81-DV p4l (results/arch/s81_dv_1016/p4l/plan.json)'
T['note'] = ('S81-DIE6 (10-18) p4l bind table = p4k + lepw/lepe endpoints (tx 512, rx 514 {st, rx} on 562 lanes, host plane '
             'on s_7N only; S81-LEPV: s_0S / s_0N / s_7S host-less masters, no tied host pads), seq_host per-half jw/jd + host plane, svc_rs up 16 + entry st_rg, mix4 deleted, worktree slice RTL; '
             'generated by results/arch/s81_dv_1016/bind6/mk_table_p4l.py')
json.dump(T, open(B / 'bind_table_p4l.json', 'w'), indent=1)
print('ok', len(M))
