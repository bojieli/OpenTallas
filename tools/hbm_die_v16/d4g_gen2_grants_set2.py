#!/usr/bin/env python3
"""H-D4G GEN2 / SET2 (HANDOFF 0gl, 10-18): rebind SET 2 slot changes (results/arch/hbm_die_d4g/gen2_rebind/rebind_set2.json)
+ cij in all 4 quadrants, applied to results/arch/hbm_die_d4g/grants_d4g.json.  Idempotent (absolute values, re-run safe).

  hb_dbk_SW/NW    604.8 x 540 -> 606.96 x 542.16 (kit hv16_dbk_cpl), origin kept (MY); wd banks 0-3 S face, 4-7 N face.
  idx_sel         clock entry clk_ctl E face, mid-face (stale offset 581.304 > the 450-um face); faces + synth_pin_bind =
                  kit hidx_sel_g4 (W in/ctl, E clocks + selected_line, S out_line).
  idx_q           clock entry W face (kit hidx_q_r4: every pin on W); synth_pin_bind faces W.
  vmh_SW/NW       NEW die slots 777.6 x 1555.2 (VM-GLUE hfd_hgi_vms_glue_{sw,nw}_t) on the W edge of the vmh plan block (same
                  distance to the banks / centre channel as the 480-um block), ring face E toward the centre channel.  SW
                  centred on the block; NW top 20 um under calendar_NW (which overhangs the block's W edge).
  quant_NW_dec    NEW planning slot (cluster, 3 closed tiles qw_dxl/dbq/daq 120.96^2/120.96^2/129.6^2) on the N face of
                  quant_NW_xp at its E end: the E face itself is 21.6 um from su_NW1 (no room).  hb_quant_NW is one soft
                  instance in the GEN contract, so die_case does not consume it (records the decoder home for the parent kit).
  cij_<q>         NOT here: l5b_cij4 homes cij_<q> in the coll_<q> region (as cij_SW today), beside hb_coll_<q> and short to
                  hb_idx__link (2,180-b IDX tree); the band cij_<q> slots (SFUPLAN) stay unused stand-ins.
NOT applied (open): vmks_<q><k> 432 x 388.8 own slots.  The PC box (1036.8 x 637.2) holds the 4 ctl leaves (155.52^2 at the
PHY edge) and svg_<q><k> (explicit home at the SM-side edge, SYNTH size not known here) -> a 388.8-um tile fits only if
svg is <= ~38 um tall; outside the box there is 100 um between boxes and 200 um to the SM row (link path).  The vmks stay
in their pc_<q><k> shared region (die_case nearest free fit, OVERFLOW reported in the manifest homes).
    d4g_gen2_grants_set2.py [--check]
"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'results/arch/hbm_die_d4g'
GRANTS = D / 'grants_d4g.json'
TAG = 'GEN2 SET2 (HANDOFF 0gl)'
CLR = 20.0


def rect(s):
    w, h = s['outline']['w'], s['outline']['h']
    if s['origin'].get('orient', 'R0') in ('R90', 'R270'):
        w, h = h, w
    return s['origin']['x'], s['origin']['y'], w, h


def gap(a, b):
    dx = max(b[0] - (a[0] + a[2]), a[0] - (b[0] + b[2]))
    dy = max(b[1] - (a[1] + a[3]), a[1] - (b[1] + b[3]))
    return max(dx, dy)


def note(s, t):
    if TAG not in s.get('notes', ''):
        s['notes'] = (s.get('notes', '') + f' | {TAG}: {t}').lstrip(' |')


def tile(name, cell, kind, x, y, w, h, ck, faces, nt, **kw):
    return dict(name=name, cell=cell, kind=kind, parent='die', outline=dict(w=w, h=h), origin=dict(x=x, y=y, orient='R0'),
                clock_entry=ck, pg_layer='M7', strap_layer='M8', signal_max_layer='M7', version=1, faces=faces, notes=f'{TAG}: {nt}',
                pins=[], pin_status='FACES_ONLY', **kw)


def apply(G):
    S = {s['name']: s for s in G['slots']}
    ch = []
    for q in ('SW', 'NW'):
        s = S[f'hb_dbk_{q}']
        s['outline'] = dict(w=606.96, h=542.16); s['cell'] = 'ot_hgi_dma_back_static_vp4_banks_cp'
        s['faces'] = dict(S='wd banks 0-3', N='wd banks 4-7', E=s.get('faces', {}).get('E', 'clk') if isinstance(s.get('faces'), dict) else 'clk')
        note(s, 'outline 606.96 x 542.16 (kit hv16_dbk_cpl, OWNERS-HBM/STK); wd banks 0-3 S / 4-7 N (wires only, 0 cycles)'); ch.append(s['name'])
    s = S['idx_sel']; h = s['outline']['h']
    s['clock_entry'] = dict(pin='clk_ctl', face='E', layer='M4', offset=round(h / 2, 3))
    kit = {'W': ['op', 'pass', 'addr', 'k', 'in_line', 'out_v', 'threshold_observe', 'selected_v', 'selected_observe', 'fault'],
           'E': ['clk_ctl', 'clk_q', 'clk_mem', 'rst_n', 'selected_line'], 'S': ['out_line']}
    s['faces'] = {f: ', '.join(v) for f, v in kit.items()}
    s['synth_pin_bind'] = dict(source='kit hidx_sel_g4 floorplan.json pins (claude/hbm-idx-small-1018)',
                               faces={p: f for f, v in kit.items() for p in v})
    note(s, 'clock clk_ctl E mid-face (stale offset 581.304 was outside the 450-um face); faces = kit hidx_sel_g4'); ch.append('idx_sel')
    s = S['idx_q']
    s['clock_entry'] = dict(pin='clk', face='W', layer='M4', offset=round(s['outline']['h'] / 2, 3))
    s['faces'] = dict(W='all pins (kit hidx_q_r4)')
    note(s, 'clock W face (kit hidx_q_r4 has every pin incl. clk on W; was E offset 224.3)'); ch.append('idx_q')
    # vmh tiles
    for q, (x, y) in {'SW': (8756.592, 10033.6), 'NW': (8945.712, 19561.464)}.items():
        nm = f'vmh_{q}'
        new = tile(nm, f'hfd_hgi_vms_glue_{q.lower()}_t', 'tile', x, y, 777.6, 1555.2,
                   dict(pin='clk', face='E', layer='M4', offset=777.6),
                   dict(E='ring face 8,896 b toward the centre channel; clock mid-face', W='banks 0-3 (far face)',
                        N='banks 4,5 + cq', S='banks 6,7 + cr / control'),
                   'VM-GLUE quadrant VM tile (hb_vms_{0} rebound in GEN1 l5); kit outline from vms_glue_kit_specs.py; W edge = '
                   'vmh plan block W edge'.format(q), rtl_owner='VM-GLUE (claude/vm-glue-1018)')
        if nm in S:
            S[nm].update({k: v for k, v in new.items() if k not in ('notes',)}); note(S[nm], 'outline 777.6 x 1555.2')
        else:
            G['slots'].append(new); S[nm] = new
        ch.append(nm)
    # qdq decoder planning slot
    xp = rect(S['quant_NW_xp'])
    w_ = 120.96 + 120.96 + 129.6 + 2 * 21.6
    new = tile('quant_NW_dec', None, 'cluster', round(xp[0] + xp[2] - w_, 3), round(xp[1] + xp[3] + CLR, 3), round(w_, 3), 129.6,
               dict(pin='clk', face='S', layer='M5'),
               dict(S='dec_x 1024 b out / y 512 b back to quant_NW_xp (N face of the transport)'),
               'qdq decoders u_dxl/u_dbq/u_daq (closed views qw_{dxl,dbq,daq}_ref) inside hb_quant_NW (soft split); planning home: '
               'N face of quant_NW_xp at its E end (E face is 21.6 um from su_NW1); not consumed by die_case (one soft instance)')
    if 'quant_NW_dec' in S:
        S['quant_NW_dec'].update({k: v for k, v in new.items()})
    else:
        G['slots'].append(new); S['quant_NW_dec'] = new
    ch.append('quant_NW_dec')
    return ch


def check(G, names, G0=None):
    S = {s['name']: rect(s) for s in G['slots'] if s.get('parent') == 'die' and s.get('origin') and s['kind'] != 'die'}
    S0 = {s['name']: rect(s) for s in (G0 or G)['slots'] if s.get('parent') == 'die' and s.get('origin') and s['kind'] != 'die'}
    bad = []
    rep = {}
    for n in names:
        if n not in S:
            continue
        near = sorted((round(gap(S[n], S[m]), 2), m) for m in S if m != n)
        rep[n] = near[:3]
        unchanged = lambda m: n in S0 and m in S0 and S0[n] == S[n] and S0[m] == S[m]
        bad += [(n, m, d) for d, m in near if d < CLR - 1e-3 and not unchanged(m)]
    return rep, bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true', help='apply in memory and report only')
    a = ap.parse_args()
    G0 = json.loads(GRANTS.read_text())
    G = json.loads(GRANTS.read_text())
    ch = apply(G)
    rep, bad = check(G, ch, G0)
    print(json.dumps(dict(changed=ch, clearance=rep, violations=bad), indent=1))
    if not a.check:
        GRANTS.write_text(json.dumps(G, indent=1) + '\n')
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
