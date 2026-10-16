#!/usr/bin/env python3
"""Grants v5 (H-DIE r3, 2026-10-15): real slots for every compact660_v5 plan block that had only a plan box or a
request box (SM, SU slices + cores, SFU leaves, HC + HC engine, QUANT groups, SerDes lk, endpoint ep), homes for the
off-die boundaries (host UCIe), the registered relay stations, and the disposition of the v14 masters with no v15 home.

    window_grants.py [--grants results/arch/hier_contract_1015/hbm_v15.json]   (rewrites it as version 5)

A window slot is a full grant: cell (the owner's current RTL master, or null + rtl_pending when the master is being
split), outline / origin / orient = the plan block, layer caps, clock-entry face and PIN WINDOWS = per die link of the
v5 pin plan (results/arch/hbm_die_v15/compact660_v5/pins/compact660_v5.pins.json): face, layer, offset/span in the
slot's R0 frame, bits, peer block and traffic class.  The owner maps RTL ports into the windows (bits within the
window's span at 0.096 um/bit); slot_fit checks outline, faces/layers and clock entry; die tools re-pin from the RTL
port list when the master lands (top-down pin assignment).  Hard macros (SerDes, UCIe) keep their LEF pins.
"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'results/arch/hbm_die_v15/compact660_v5/compact.P.json'
PINS = ROOT / 'results/arch/hbm_die_v15/compact660_v5/pins/compact660_v5.pins.json'
RFP = ROOT / 'results/arch/hbm_die_v15/compact660_v5/su_rf_route_pins.json'
FACE_LAYER = dict(N='M5', S='M5', E='M4', W='M4')
KINDS = {  # kind -> (cell, rtl_pending/owner, cluster?, note)
    'sm': ('hfd_sm', 'H-ELEM-A', True, 'SM frame 11.316 mm2 (x-load static 9515de0c6 + attention on SM); owner confirms '
           'the static v15 master name, slot stays'),
    'su': (None, 'H-ELEM-B: ot_hbm_su_static_pgslice (slice g at bank pair {2g,2g+1})', True,
           'whole static SU slice; reserve a 40 um feedthrough relay column at x = w/2 (band through-traffic)'),
    'sucore': (None, 'H-ELEM-B: ot_hbm_su_static_qcore', False, 'SU core (RF replica + reducer); RF pins = su_rf_route_pins'),
    'sfu': (None, 'H-ELEM-B / HBM-V15-HARDEN: SFU bank-pair leaf (4 per quadrant, LG roots f94fb79fd/80d1f4413)', False,
            'SFU port-group leaf 0.40 mm2'),
    'hc': ('hfd_hc', 'HC owner', False, 'HC combined shell 500x500; owner confirms the static master'),
    'hc_eng': (None, 'HC owner: HC engine', False, 'HC engine 1.0 mm2 estimate'),
    'quant': (None, 'H-ATTQ: ot_hgi_qdq_host_static split into 4 bank-pair groups (one host master cannot meet the '
              '<=500 um fixed return to 4 bank pairs)', False, 'QUANT group 245x245 estimate'),
    'lk': ('ot_pdie_serdes', 'SerDes owner (hard macro, LEF pins fixed)', False,
           'die-to-die SerDes link macro; off-die boundary: elastic/credit flow control allowed (owner 0az)'),
    'ep': (None, 'H-COLL: ot_hgi_coll_static_link_capture group', False,
           'endpoint = link capture + elastic boundary buffer (off-die, 0az)'),
}
HOST = dict(name='host_N', cell='ot_pdie_ucie', w=260.766, h=1652.4,
            note='host UCIe-A shoreline macro (off-die boundary, elastic/credit at the boundary only, owner 0az); '
                 'N edge of the centre column east of the endpoints')
HOST_CP = dict(name='host_cp', w=432.0, h=432.0,
               note='static host ingress + programme loader (successor of v14 hfd_cmdproc): host packets -> on-die '
                    'programme/config memories at block-ready, no on-die credits; RTL pending')
RELAYS = [dict(cell='hfd_stn_v15_cc2224', bits=2224), dict(cell='hfd_stn_v15_cc2248', bits=2248)]
RETIRE = {
    'hfd_hgi_am': 'v14 single-CP ARGMAX die master (credit dispatch via hfd_cmdproc); superseded by ot_hbm_argmax_static '
                  '(contract instance hb_argmax, static calendar client)',
    'hfd_cmdproc': 'v14 HGI command processor with per-unit dispatch credits and legacy SM launch tree: violates the '
                   'static on-die schedule (owner 10-14/0az); its host/loader role moves to slot host_cp (static successor)',
    'hfd_serdes_slab': 'v14 reservation slab beside the SerDes pin macros; v15 places the real ot_pdie_serdes macros '
                       'as lk_* blocks (no slab: the macro is the block)',
    'hfd_host_slab': 'v14 host reservation slab; v15 places the real ot_pdie_ucie macro as host_N + host_cp logic',
}


def kind_of(b):
    if b == 'hc_eng':
        return 'hc_eng'
    if b.startswith('sucore'):
        return 'sucore'
    return b.split('_')[0]


def overlap(a, b):
    return a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w'] and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grants', default=str(ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'))
    ap.add_argument('--pcrow', help='view_case.py --pc-align manifest: adopt PHY orients + PC homes (variant B)')
    a = ap.parse_args()
    G = json.loads(Path(a.grants).read_text()); P = json.loads(PLAN.read_text()); PP = json.loads(PINS.read_text())
    rf = json.loads(RFP.read_text())
    W, H = G['floorplan']['die_um']
    have = {s['name'] for s in G['slots']}
    new = []
    for b, box in sorted(P.items()):
        k = kind_of(b)
        if k not in KINDS or b in have:
            continue
        cell, owner, cluster, note = KINDS[k]
        wins = []
        for f, fx in PP['blocks'].get(b, {}).get('faces', {}).items():
            for p in fx['pins']:
                peer = [x for x in p['link'].split(':')[0].split('>') if x != b]
                wins.append(dict(face=f, layer=FACE_LAYER[f], offset=round(p['offset_um'], 3),
                                 span_um=round(p['span_um'], 3), bits=p['bits'], peer=peer[0] if peer else None,
                                 cls=p['link'].split(':')[-1], link=p['link']))
        if k == 'sucore':
            for r in (rf.get('pins') or {}).get(b, []) if isinstance(rf.get('pins'), dict) else []:
                wins.append(dict(r, cls='SU_RF'))
        ctl = max(wins, key=lambda w: w['bits'])['face'] if wins else 'N'
        s = dict(name=b, cell=cell, kind='hard_macro' if k == 'lk' else ('cluster' if cluster else 'tile'), parent='die',
                 outline=dict(w=box['w'], h=box['h']), origin=dict(x=box['x'], y=box['y'], orient=box['orient']),
                 clock_entry=None if k == 'lk' else dict(pin='clk', face=ctl, layer=FACE_LAYER[ctl]),
                 pg_layer='M7' if cluster else 'M5', strap_layer='M8' if cluster else 'M6',
                 signal_max_layer='M6' if cluster else 'M5', layer_cap='M6' if cluster else 'M5',
                 io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2), version=5, grant='window',
                 rtl_owner=owner, notes=note, pin_windows=wins)
        if cell is None:
            s['rtl_pending'] = owner
        new.append(s)
    # host UCIe + host_cp: N edge east of the endpoints, first free spot scanning east
    occ = [dict(x=v['x'], y=v['y'], w=v['w'], h=v['h']) for v in P.values()]
    occ += [dict(x=s['origin']['x'], y=s['origin']['y'], w=s['outline']['w'], h=s['outline']['h']) for s in G['slots']
            if s['name'] != 'die']
    epx = max(P[k]['x'] + P[k]['w'] for k in P if k.startswith('ep_N'))
    homes = {}

    def scan(x, blk):
        while True:
            r = dict(x=round(x, 3), y=round(H - 20.0 - blk['h'], 3), w=blk['w'], h=blk['h'])
            if not any(overlap(r, o) for o in occ):
                assert r['x'] + r['w'] < W, blk['name']
                return r
            x += 21.6
    homes['host_N'] = scan(epx + 21.6, HOST); occ.append(homes['host_N'])
    homes['host_cp'] = scan(homes['host_N']['x'] + HOST['w'] + 21.6, HOST_CP); occ.append(homes['host_cp'])
    new.append(dict(name='host_N', cell=HOST['cell'], kind='hard_macro', parent='die',
                    outline=dict(w=HOST['w'], h=HOST['h']), origin=dict(x=homes['host_N']['x'], y=homes['host_N']['y'],
                                                                         orient='MX'),
                    version=5, grant='hard_macro', notes=HOST['note'], flow_control='elastic (off-die boundary, 0az)'))
    new.append(dict(name='host_cp', cell=None, rtl_pending='H-DIE requests owner (coordinator to assign): static host '
                    'ingress + programme loader', kind='tile', parent='die',
                    outline=dict(w=HOST_CP['w'], h=HOST_CP['h']),
                    origin=dict(x=homes['host_cp']['x'], y=homes['host_cp']['y'], orient='R0'),
                    clock_entry=dict(pin='clk', face='W', layer='M4'), pg_layer='M5', strap_layer='M6',
                    signal_max_layer='M5', layer_cap='M5', version=5, grant='window', notes=HOST_CP['note'],
                    pin_windows=[dict(face='W', layer='M4', offset=round(HOST_CP['h'] / 2, 3), span_um=98.4, bits=1024,
                                      peer='host_N', cls='HOST_FLIT')]))
    # relay station templates: homes are the relay rows / channels of the lane plan, instanced by the die relay planner
    rel = []
    for r in RELAYS:
        span = r['bits'] * 0.096
        h = round(-(-(span / 0.6) // 2.16) * 2.16, 3)
        rel.append(dict(cell=r['cell'], outline=dict(w=43.2, h=h), pins=dict(input='W', output='E', layer='M4',
                                                                            span_um=round(span, 3)),
                        clock_entry=dict(pin='clk', face='N', layer='M5'),
                        homes='relay rows / 0.6 mm channels / 40 um feedthrough columns per '
                              'results/arch/hbm_die_v15/compact660_v5/lanes2.json (die relay planner instances them)',
                        latency_cycles=1, version=5))
    if a.pcrow:
        M = json.loads(Path(a.pcrow).read_text())
        assert M.get('variant') == 'B_pc_align', M.get('variant')
        for l, v in sorted(M['placement'].items()):
            if v['master'].startswith('ot_hbm3e_phy') and l not in have:
                new.append(dict(name=l, cell=v['master'], kind='hard_macro', parent='die', outline=dict(w=v['w'], h=v['h']),
                                origin=dict(x=v['x'], y=v['y'], orient=v['orient']), version=5, grant='hard_macro',
                                notes=v.get('note', ''), flow_control='HBM PHY/controller boundary (0az)'))
        G['pc_homes'] = dict(
            rule='bands are SOFT die-level groups (wires only); every ot_hbm_svc_static_pc is placed directly over its '
                 'own PHY channel pin window, 10.8 um from the PHY edge (die GRT+STA on real views, H-DIE r3: overflow 0, '
                 'TT +167.29 ps, FF +57.25 ps, max PHY-PC hop 127 um); answers HBM-V15-HARDEN request (2) of 10:33',
            homes={l: dict(x=v['x'], y=v['y'], orient=v['orient'], band=v['of']) for l, v in sorted(M['placement'].items())
                   if v['master'] == 'ot_hbm_svc_static_pc'})
        for s in G['slots']:
            if s['name'].startswith('svc_'):
                s['kind'] = 'soft_group'; s['version'] = 5
                s['notes'] = (s.get('notes') or '') + ' | v5: soft group, PCs at pc_homes (no band hardening)'
    G['slots'] += new
    G['relay_templates'] = rel
    G['retired_masters'] = RETIRE
    rq = {s['name'] for s in new if s.get('rtl_pending')}
    G['request_slots'] = [r for r in G.get('request_slots', [])]
    G['request_slots_superseded_by_v5'] = 'SU/SFU request boxes are now window slots su_<q><k>, sucore_<q>, sfu_<q><k>'
    G['version'] = 5
    G['owner'] = 'H-DIE'
    G['updated'] = '2026-10-15 H-DIE r3: window slots for every plan block, host_N/host_cp, relay templates, retirements'
    Path(a.grants).write_text(json.dumps(G, indent=1))
    from collections import Counter
    print(json.dumps(dict(new_slots=len(new), by_kind=dict(Counter(kind_of(s['name']) for s in new)),
                          pending_rtl=len(rq), host=homes, relays=[r['outline'] for r in rel])))


if __name__ == '__main__':
    main()
