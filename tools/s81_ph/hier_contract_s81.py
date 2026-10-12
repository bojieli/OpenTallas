#!/usr/bin/env python3
"""S81 (DeepSeek ROM layer-1 die) top-down hierarchy contract builder (s81die-1011, 2026-10-11).

Writes results/arch/hier_contract_1011/s81.json (schema tools/hier_contract/contract.schema.json) from
  * the die-fit plan of the recipe (results/physical/s81_gen_20261011/s81_layer1_full_efs_suhc_v2b.opts): hub slab
    outlines / die origins / die pins, as emitted by tools/s81_ph/slab_contracts.py --tag layer1v2b (--contracts DIR),
  * the per-slot assembly decision (GLUE PLACEMENT rule: tiles placed directly by the die, or one hardened cluster),
  * the tile lists the element owners published (SU composition json, HC split outline, cb tile row); slots whose tile
    list is still pending carry assembly 'pending_owner' and only their slab outline.

Layer contract (all S81 tiles placed by the die): signals M1-M6, PG = full-length VDD/VSS stripes on M7 (the tile's
top layer), die straps M8 (+ M9), M8/M9 belong to the die top only.  A hardened cluster's own children: signals <= M5,
PG M6, cluster straps M7 = cluster PG pins.

    python3 tools/s81_ph/hier_contract_s81.py --contracts physical/s81_ph_views/contracts_1011 [--out results/arch/hier_contract_1011/s81.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = 833.333
DIE = (33000.0, 26000.0)
TILE_L = dict(pg_layer='M7', strap_layer='M8', signal_max_layer='M6')
CLUS_CHILD_L = dict(pg_layer='M6', strap_layer='M7', signal_max_layer='M5')
IO = dict(in_delay_frac=0.2, out_delay_frac=0.2, registered_in=True, registered_out=True)
TINS = 250.0   # provisional target clock insertion at each tile clock pin (ps): the closed cb tiles measure 217-302 ps (TT lib);
               # re-budgeted per slot from each closed route's lib (child_lint (g))
# contract v3 (s81die-1011): >= 20-um channels at every column boundary of an abutted array whose tiles carry W/E-face pins
# (43.2 = 4 x the 10.8 M7 PG pitch, on the 0.064 M7 / 0.096 M5 / 0.054 site grids); SU 86.4 for its spine jogs
SU_CH, HC_CH, VM_CH = 86.4, 43.2, 43.2
MEAS_INS = dict(dsfd_coll_cbr=297.0, dsfd_coll_cbf=217.0, dsfd_coll_cbq0=291.0, dsfd_coll_cbq=302.0)   # child_lint 2026-10-11 c2e836720-p2


def slot(name, parent, cell, kind, w, h, x, y, orient='R0', pins=None, ck=('ck', 'N', 'M4'), layers=TILE_L, **kw):
    s = dict(name=name, cell=cell, kind=kind, parent=parent, outline=dict(w=round(w, 3), h=round(h, 3)),
             origin=dict(x=round(x, 3), y=round(y, 3), orient=orient), io_budget=dict(IO),
             clock_entry=dict(pin=ck[0], face=ck[1], layer=ck[2]), target_insertion_ps=MEAS_INS.get(cell, TINS), version=1, **layers)
    if pins is not None:
        s['pins'] = pins
    s.update(kw)
    return s


def die_pins(inst):
    out = []
    for n, p in sorted(inst['pins'].items()):
        a, b = p['span_um']
        out.append(dict(name='%s[%d:0]' % (n, p['bits'] - 1) if p['bits'] > 1 else n, face=p['face'], layer=p['layer'],
                        offset=round((a + b) / 2, 3), width=round(max(b - a, 0.024), 3)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contracts', type=Path, required=True, help='slab_contracts.py --tag layer1v2b output dir')
    ap.add_argument('--out', type=Path, default=ROOT / 'results/arch/hier_contract_1011/s81.json')
    a = ap.parse_args()
    slabs = {}
    for f in sorted(a.contracts.glob('*.layer1v2b.json')):
        for i in json.loads(f.read_text())['instances']:
            slabs[i['instance']] = i
    S = [dict(name='s81_layer1', cell='dsrom_s81_layer1_die', kind='die', parent=None, outline=dict(w=DIE[0], h=DIE[1]),
              origin=dict(x=0.0, y=0.0, orient='R0'), io_budget=dict(IO), clock_entry=dict(pin='refclk', face='W', layer='M8'),
              version=1, pg_layer='M9', strap_layer='M9', signal_max_layer='M9',
              notes='die top: routed per region (seams, relays, clock spine to every tile clock entry, M8/M9 straps) with '
                    'tiles/clusters as fixed macros; signed off TT setup / FF hold / DRC 0 (AMENDMENT item 2)')]

    def hub(inst, assembly, owner, note=''):
        i = slabs[inst]
        S.append(slot(inst, 's81_layer1', i['master'], 'element', i['outline_um'][0], i['outline_um'][1],
                      i['die_origin_um'][0], i['die_origin_um'][1], i.get('orient', 'R0'), pins=die_pins(i),
                      assembly=assembly, owner=owner, notes=note))
        return i

    # ---- SU: one instance on the die -> tiles placed directly (29 tiles, 3 x 572.4 columns)
    hub('sp_su_s', 'tiles_direct', 'el1011 s81 suhc-hier (claude/s81-suhc-hier-1011-su)',
        'tiles from physical/s81_ph_views/su_hier/su_slab_composition.json; the slab outline is the die region they fill')
    su = json.loads((ROOT / 'physical/s81_ph_views/su_hier/su_slab_composition.json').read_text())
    for t in su['tiles']:
        S.append(slot('sp_su_s/' + t['inst'], 'sp_su_s', t['master'], 'tile', t['w'], t['h'], t['col'] * (t['w'] + SU_CH), t['y']))
    S[-len(su['tiles']) - 1]['outline']['w'] = round(3 * 572.4 + 2 * SU_CH, 4)
    # ---- HC: one instance -> tiles direct, N-S split variant (HALF=1 CSPLIT=1, crooty closed 5b78b9d3b), H_half 400
    i = hub('sp_hc_s', 'tiles_direct', 'el1011 s81 suhc-hier (claude/s81-suhc-hier-1011-hc)',
            'split variant outline 1,727.976 x (22 H_half + 840), H_half 400 -> 9,640; roots on the N edge')
    h, cw, hh = i['outline_um'][1], 575.992, 400.0
    S[-1]['outline']['w'] = round(3 * cw + 2 * HC_CH, 4)
    cw_ = cw + HC_CH   # column pitch
    for nm, ms, x, y, w, th in (('crooty_c0', 'ot_s81_hc_crooty', 0, h - 200, cw, 200), ('crootr_c0', 'ot_s81_hc_crootr', 0, h - 840, cw, 640),
                                ('cpin', 'ot_s81_hc_cpin', cw_, h - 200, cw, 200), ('comb', 'ot_s81_hc_comb', cw_, h - 840, cw, 640),
                                ('crooty_c2', 'ot_s81_hc_crooty', 2 * cw_, h - 200, cw, 200), ('crootr_c2', 'ot_s81_hc_crootr', 2 * cw_, h - 840, cw, 640)):
        S.append(slot('sp_hc_s/' + nm, 'sp_hc_s', ms, 'tile', w, th, x, y))
    for c, (lo, hi) in enumerate(((0, 22), (22, 42), (42, 64))):
        for p in range(hi - lo):
            S.append(slot('sp_hc_s/ctile_%d' % (lo + p), 'sp_hc_s', 'ot_s81_hc_ctile_half', 'tile', cw, hh, c * cw_, h - 840 - hh * (p + 1)))
    # ---- collective: lane tiles W (8 x 345.6 x 340.2 stacked), core column x 367.2..1,727.976 = 1,360.776:
    #      cb tiles direct (no glue) at the S of the core column, ce region above (tile list pending), ct at the N
    i = hub('sp_collective', 'tiles_direct', 'el1011-ds-coll',
            'v1 slab 1,727.976 x 2,721.576 (free W-column height): lanes W stacked, core column 1,360.776 wide; '
            'cb = 8 tiles direct (cbh parent route not iterated: GLUE PLACEMENT); ce tiles to fill (367.2, 444.96)-(1,727.976, 2,359.776) '
            'at 50-60% with >= 20 um channels -> owner posts the tile list; ct 1,036.776 x 340.2 at the N')
    H = i['outline_um'][1]
    for k in range(8):
        S.append(slot('sp_collective/lane%d' % k, 'sp_collective', 'dsfd_coll_lane_w', 'tile', 345.6, 340.2, 0.0, 340.2 * k))
    cx = 367.2 + (1360.776 - 972.432) / 2
    for nm, ms, x, w, o in (('cb_rw', 'dsfd_coll_cbr', 40.176, 113.4, 'R0'), ('cb_f', 'dsfd_coll_cbf', 183.6, 64.8, 'R0'),
                            ('cb_q0', 'dsfd_coll_cbq0', 278.64, 77.76, 'R0'), ('cb_q1', 'dsfd_coll_cbq', 386.64, 77.76, 'R0'),
                            ('cb_q2', 'dsfd_coll_cbq', 494.64, 77.76, 'R0'), ('cb_q3', 'dsfd_coll_cbq', 602.64, 77.76, 'R0'),
                            ('cb_q4', 'dsfd_coll_cbq', 710.64, 77.76, 'R0'), ('cb_re', 'dsfd_coll_cbr', 818.64, 113.4, 'MY')):
        S.append(slot('sp_collective/' + nm, 'sp_collective', ms, 'tile', w, 340.2, cx + x, 41.04, o))
    S.append(slot('sp_collective/ct', 'sp_collective', 'dsfd_coll_ct', 'tile', 1036.776, 340.2, 367.2 + (1360.776 - 1036.776) / 2, H - 340.2))
    # ---- VM: slab 1,520.184 x 2,609.256 (FE v4 + BE 136.08); be slices / fe lane tiles / bgq: owner decides tiles vs cluster
    hub('sp_vm', 'pending_owner', 'el1011-ds-vm',
        'BE S-face contract v3 (P2 READY-LATENCY 4: consumer dsfd_vm_p2_ep rebuilt s81die-1011 377e1ff10); tile list (be slices, fe '
        'lane tiles, be hub logic folded into tiles) to be posted by the owner; clt6 LEF fails M7/pin access (re-route)')
    hub('sp_capture', 'element', 'el1011 s81 ctrl', 'single hard element (dsfd_sp_capture_c)')
    hub('sp_gather', 'element', 'el1011 s81 ctrl', 'single hard element (dsfd_sp_gather_c)')
    hub('sp_wfc', 'element', 'el1011-ds-wfc', 'WFC kit stage (dsfd_wfc_stg)')
    for nm, ms, n_, own in (('rep/q_elem', 'ot_v41_rom_elem_q_*', '1,898', 'ds-1010'), ('rep/bf', 'dsfd_bf', '519', 'el1011-ds-bf'),
                            ('rep/pqc', 'dsfd_sp_pq / pqc tiles', 'per stage', 'el1011-ds-misc'),
                            ('rep/hrow', 'dsfd_mtp_hrow banks', 'per die role', 'el1011-ds-mtp'),
                            ('rep/engram_c', 'engram_c tiles', '1 (unique)', 'el1011-ds-misc')):
        S.append(dict(name=nm, cell=ms, kind='element', parent='s81_layer1', outline=dict(w=0, h=0), origin=dict(x=0, y=0),
                      io_budget=dict(IO), clock_entry=dict(pin='ck', face='N', layer='M4'), version=1, **TILE_L,
                      assembly='cluster' if nm in ('rep/q_elem', 'rep/bf') else 'pending_owner', owner=own,
                      notes='instances %s: positions in the plan floorplan.def; replicated >= 4 -> hardened once and stepped'
                            % n_ if nm in ('rep/q_elem', 'rep/bf') else 'owner decides tiles_direct vs cluster (GLUE PLACEMENT)'))
    doc = dict(schema='opentallas.hier_contract.v1', die='ds_rom_s81_layer1', version=1, owner='s81die-1011',
               updated='2026-10-11T21:45-07:00', clock_period_ps=T, layer_defaults=TILE_L,
               cluster_child_layers=CLUS_CHILD_L,
               recipe=dict(opts='results/physical/s81_gen_20261011/s81_layer1_full_efs_suhc_v2b.opts',
                           die_fit='plan d221bdf05 (EPYC1tb): 59,495 instances, overlaps 0, outside 0, generated pin clashes 0'),
               seam_rules=dict(
                   registered='every tile-to-tile seam registered on both sides (pin flop in, flop out; child_lint io flags)',
                   reach_um_per_stage=500.0, relays='longer seams get die-top relay stations (last segment <= ~100 um at a die pin)',
                   io_budget='0.2 T in / 0.2 T out per tile; the die top owns the remaining 0.6 T per seam stage',
                   clock='each tile clock pin balanced to target_insertion_ps (provisional 120 ps; re-budget from routed CTS)',
                   check=('die closure, not element closure: die-region routes (tiles as fixed macros, relays/stations only logic, '
                          'M8/M9 straps) signed off TT setup >= 0 / FF hold >= 0 / DRC 0; prerequisite: tools/hier_contract/'
                          'child_lint.py PASS on every placed tile')),
               changelog=[dict(version=1, when='2026-10-11 21:45 PT',
                               change='v1 from die-fit v2b: VM slab 2,609.28 (BE 136.08 + FE v4), collective 1,727.976 x 2,721.576 '
                                      '(lanes W, core column 1,360.8, cb 8 tiles direct 972.4-wide row, ce region pending), SU 29 tiles '
                                      'direct, cb clock targets from measured TT libs (217-302 ps), '
                                      'direct, HC split variant tiles direct, P2 ready-latency 4 consumer, layer contract M7 PG / M8 straps')],
               slots=S)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc, indent=1) + '\n')
    print(a.out, len(S), 'slots')


if __name__ == '__main__':
    main()
