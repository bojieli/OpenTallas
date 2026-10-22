#!/usr/bin/env python3
"""S81 DIE72 G9e bind table (STW-S81-DIE-PLAN 10-21) = G9d table (bind_table_g9d.json: G9 + frame_bind 675c6815b R-frame
orientations, unchanged) + the G9e plan deltas only:

  * masters dsdv_slice_c1x / dsdv_slice_c3x = the dsdv_slice row (same plan-port -> RTL-port rules, landings, straps,
    mode_unused) on the PARAMETER-FREE wrappers ot_s81sl_slice_c1x/c3x_k8_cap5r_w (claude/s81-slicep-k8c-1021 @6ff783251,
    kits k8c|k8d / k8e|k8f): no HB parameter (c1x = HB0, c3x = HB1 fixed by the wrapper), 10 regional clock inputs
    ck_C, ck_L0, ck_L1, ck_L3, ck_L4, ck_CAP_RT/CW/CE/RN/RS instead of clk.  RTL: the two wrappers + the c3x lp from
    6ff783251 (rtl_refs + prefer); every other file of the kit source list is byte-identical in the G9 RTL base 553741303
    (c1x lp differs by 5 comment lines only).
  * instance_clock_ports: each of the 10 wrapper instances drives every regional clock port from its own declared die-top
    root ck_sl_<inst>_<region> (landed-regions standard, as the frames' ck_r0/1/2 and the end parents' ck_ep_*);
    clock_domains rows seeded at the kit pin (E face, kit pin_ranges).
  * end-parent clock seeds (ck_ep_*) re-seeded on the moved s_0* / s_7* slots (same formula as apply_ep_clock_g8.py).
  * child_views: owed -> bound records (exact record + source), see CHILD below.
Usage: g9e_table.py BIND_TABLE_G9D PLAN_ROUTED_G9E SPEC_K8C SPEC_K8E OUT LOGICAL_PLAN_G9
"""
import copy, json, sys
from pathlib import Path

WREF = '6ff783251ab208a90632ee4ac180d7d529126676'
WFILES = ['rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_w.sv',
          'rtl/dsrom_sys/s81_dv/slice/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_w.sv',
          'rtl/dsrom_sys/s81_dv/slice/landed/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_lp.sv']
CKP = ['ck_C', 'ck_L0', 'ck_L1', 'ck_L3', 'ck_L4', 'ck_CAP_RT', 'ck_CAP_CW', 'ck_CAP_CE', 'ck_CAP_RN', 'ck_CAP_RS']
WRAP = {'dsdv_slice_c1x': ('ot_s81sl_slice_c1x_k8_cap5r_w', 'k8c (MAIN 1252.8 x 6868.8) / k8d (FB 1296 x 6868.8)'),
        'dsdv_slice_c3x': ('ot_s81sl_slice_c3x_k8_cap5r_w', 'k8e (MAIN 1468.8 x 6868.8) / k8f (FB 1512 x 6868.8)')}
CHILD = {
    'dsdv_bksel_q': dict(view='s81dvbk_sq_hk2l-hk2l-f9753ee14 (CLOSED TT +37.37 / FF +5.16, DRC 0; record 0d4ba50ed; source + kits on '
                              'main edae62d7b; view physical/ref_tile/s81dvbk_sq_hq3/views/dsdv_bksel_q; defines of kit s81dvbk_sq_hk2l)',
                         parent='dsdv_bk_sel_vmtx successor (PlanA dsdv_bk_sel_pa_n32_lp u_q0..3), STW-S81-TOPK', source='f9753ee14', record='0d4ba50ed'),
    'dsdv_gunit_l5_n32': dict(view='dsdv_gunit_l5_n32-n32-1766568f0 (CLOSED TT +49.93 / FF +13.78, DRC 0; record a13792409; define OT_S81_VE_LOADSAFE5)',
                              parent='dsdv_gunit (u_l5; parent binding 127356adf STW-S81-COLLA-GUNIT)', source='1766568f0', record='a13792409',
                              source_check='1766568f0 is NOT an ancestor of main: dsdv_gunit_l5.sv dac0785b (main b21f0a4c, 312cb42b6 51ee22f8), '
                                           'dsdv_gunit_tail.sv / tail_fs / ot_rst_region16 / hdc sinkhorn+predecode differ or are absent on main '
                                           'and at 312cb42b6 (an l1f census commit 10-20, not an L5 successor); 127356adf carries the 1766568f0 '
                                           'sources byte-identical -> bind L5 only with the 1766568f0 / 127356adf sources'),
    'dsdv_sh_lk': dict(view='dsdv_sh_lk_s10hq-dsdv_sh_lk_s10hq-649101c0d (CLOSED TT +33.16 / FF +17.42, DRC 0; record a1e3102cd)',
                       parent='dsdv_seq_host_mux successor dsdv_seq_host_h/hw (ba140fd98 S81-ELEM2-SEQ)', source='649101c0d', record='a1e3102cd'),
    'dsfd_coll_lane_e_safe8_ntf': dict(view='dscoll_lane_e_s8ng-s8ng-ba18b20b1 (CLOSED TT +0.25 / FF +2.81, DRC 0; record 7db6d6351)',
                                       parent='ot_s81sl_slice / MU end parents (CRED8 E; configured_coll_g9 keeps its exact binding)', source='ba18b20b1', record='7db6d6351'),
    'dsfd_coll_lane_w_safe8_ntf': dict(view='dscoll_lane_w_s8ng-s8ng-8151c3923 (CLOSED TT +9.95 / FF +6.81, DRC 0; record 89182bf29)',
                                       parent='ot_s81sl_slice / MU end parents (CRED8 W; configured_coll_g9 keeps its exact binding)', source='8151c3923', record='89182bf29'),
    'ot_s81sl_vs': dict(view='s81sl_vs_n32f-n32f-71ac7943d (CLOSED TT +12.98 / FF +12.28, DRC 0; record 0905c20ff, auto-merge 53fde0f26; 216 x 237.6)',
                        parent='ot_s81sl_slice_c1x/c3x_k8_cap5r_lp u_vs x5 (k8 kits still carry the 172.8 stand-in; slot grows to 216, STW-S81-COLLA 19:19)',
                        source='71ac7943d', record='0905c20ff'),
}


def main():
    tp, pp, k8c, k8e, out, logical_plan = sys.argv[1:7]
    t = json.load(open(tp)); plan = json.load(open(pp)); spec = {'dsdv_slice_c1x': json.load(open(k8c)), 'dsdv_slice_c3x': json.load(open(k8e))}
    blocks = {b['name']: b for b in plan['blocks']}
    # Derive streamer identity from the original G9 logical placement, before
    # face projection or column moves. Never infer identity from new pin y.
    old = json.load(open(logical_plan)); oldb = old['blocks']; lanes = {}
    for link in old['links']:
        a, z = link['e']; b = oldb[a[0]]
        if a[1] != 'xf':
            continue
        peer = oldb[z[0]]['name']; side = 0 if peer[3] == 'L' else 1
        up = int(a[3] > b['y'] + b['h'] / 2)
        idx = (2 * up + side) * 4 + int(link['i'].rsplit('_l', 1)[1])
        assert 0 <= idx < 16, (link['i'], idx)
        lanes[link['i'].replace('-', '_')] = idx
    base = t['masters']['dsdv_slice']; bw = t['rtl_widths']['ot_s81sl_slice']
    for key, (mod, kits) in WRAP.items():
        m = copy.deepcopy(base)
        m.update(module=mod, ref=f'claude/s81-slicep-k8c-1021 {WREF[:9]} {WFILES[0 if key.endswith("c1x") else 1]}', view=None,
                 view_note=f'G9e: parameter-free k8_cap5r wrapper, kits {kits}; kits carry stand-in children (xgt_xo/xrt/vp/ve/xfin/vs) -> '
                           'no CLOSED parent view yet, the die binds the wrapper RTL (stand-in footprint = plan slot = kit outline)',
                 clk='ck_C', clock_ports=list(CKP))
        m['ports']['xf.o']['lane_by_link'] = dict(lanes)
        m.pop('hb_param', None); m.pop('clk_extra', None)
        if key.endswith('c3x'):                       # HB=1 by construction: band port B is used (s_4S pv landing)
            m['mode_unused'] = [r for r in m['mode_unused'] if not (r.get('port') == 'bi' and r.get('when') == 'hb0')]
        t['masters'][key] = m
        w = {k: v for k, v in bw.items() if k != 'clk'}; w.update({c: 1 for c in CKP})
        t['rtl_widths'][mod] = w
        assert spec[key]['outline']['exact'] and set(spec[key]['clock_ports']) == set(CKP)
    # Service bus rings are real RTL parents, intentionally not claimed CLOSED.
    # The exact source hash binds their no-extra-reset-stage contract.
    import hashlib
    bus_ref = '96d428dee'
    bus_path = 'rtl/dsrom_sys/s81_dv/land/dsdv_svc_busland.sv'
    bus_hash = '6761a57f2ed4239b9eb8a72d1757d59630bbcacc1eba0ead84835ad487cd33d1'
    t['rtl_refs'][bus_ref] = [bus_path]
    t.setdefault('landing_assemblies', {})
    for pre, width in (('dn',805),('up',16),('pr',514),('sg',2133),('ss',1077)):
        master = f'dsdv_svc_busland_{width}'
        t['landing_assemblies'][master] = dict(ref=bus_ref,path=bus_path,sha256=bus_hash,reset_stages=0,
            qualification='UNHARDENED_RTL_ASSEMBLY',slots=4,steady_words_per_cycle=1)
        t['rtl_widths'][master] = dict(ck_f=1,i=width,ck=1,rs=1,k=3,o=width,fault=1)
        t.setdefault('landing_reset_stages', {})[master] = 0
        for face in 'NESW':
            rule = t['masters']['dsdv_svc_rs']['ports'][f'{pre}{face}.i']
            rule.update(adapter=master,out_w=width,land=True)
    t['rtl_refs'][WREF] = list(WFILES)
    t['prefer'] = list(t['prefer']) + [f'{WREF}/{f}' for f in WFILES]
    for k in ('status_fault_masters',):
        t[k] = list(t[k]) + [m for m in WRAP if m not in t[k]]
    icp = t['instance_clock_ports']; doms = t['clock_domains']; n = 0
    for name, b in blocks.items():
        if b['master'] not in WRAP:
            continue
        rng = spec[b['master']]['pin_ranges']; row = {}
        assert name not in icp, name
        for p in CKP:
            net = f'ck_sl_{name}_{p[3:]}'; assert net not in doms, net
            lo, hi = rng[p]; row[p] = net
            doms[net] = dict(period_ps=833.333, asynchronous_to_core=False, relationship='same_pll_fixed_phase', source_kind='die_top_input',
                             receiver_instance=f'u_{name}', receiver_clock_port=p, receiver_region=p[3:],
                             receiver_pin_xy_um=[round(b['x'] + b['w'], 3), round(b['y'] + (lo + hi) / 2, 3)],
                             receiver_pin_source='S81 G9e plan seed: k8 kit pin_ranges, E face (regional clock tree per slice region)')
            n += 1
        icp[name] = row
    moved = 0
    for inst in ('s_0S', 's_0N', 's_7S', 's_7N'):
        b = blocks[inst]; m = t['masters'][b['master']]; ports = m.get('clock_ports') or [m['clk']] + list(m.get('clk_extra', []))
        for k, p in enumerate(ports):
            d = doms[icp[inst][p]]
            xy = [round(b['x'] + b['w'] / 2, 3), round(b['y'] + (k + 0.5) * b['h'] / 12, 3)]
            if d['receiver_pin_xy_um'] != xy:
                d['receiver_pin_xy_um'] = xy; moved += 1
    # An intact relocated frame keeps its native pin map/orientation and root names;
    # translate its three clock receiver seeds by the same physical body delta.
    logical_blocks = {b['name']: b for b in old['blocks']}
    for name, b in blocks.items():
        if not name.startswith('f_'):
            continue
        original = logical_blocks[name]
        dx, dy = b['x'] - original['x'], b['y'] - original['y']
        if not (dx or dy):
            continue
        for domain in doms.values():
            if domain.get('receiver_instance') == f'u_{name}':
                x, y = domain['receiver_pin_xy_um']
                domain['receiver_pin_xy_um'] = [round(x + dx, 4), round(y + dy, 4)]
                domain['receiver_pin_source'] = 'Exact native frame pin seed translated with intact moved body'
    cv = t['child_views']
    for k, v in CHILD.items():
        cv[k] = v
    t['g9e_note'] = ('STW-S81-DIE-PLAN 10-21 G9e: G9d table + slice wrappers c1x/c3x k8_cap5r_w (6ff783251) with 10 regional roots per '
                     f'slice ({n} roots), end-parent clock seeds re-seeded ({moved}), child_views owed->bound ({len(CHILD)}); plan '
                     'plan_routed_g9e.json (column order 0..7, centre channel 302.4, bk_sel 4449.6, gunit E inner column, dv_route72c)')
    Path(out).write_text(json.dumps(t, indent=1) + '\n')
    print('G9E_TABLE wrappers', sum(1 for b in blocks.values() if b['master'] in WRAP), 'roots', n, 'ep_reseeded', moved, 'child_views', len(CHILD))


if __name__ == '__main__':
    main()
