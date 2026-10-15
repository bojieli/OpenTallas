#!/usr/bin/env python3
"""Propose static collective IO geometry without inventing physical link views.

Preserve the complete historical combined PHY/codec envelopes. These are
reservations, not evidence of licensed PHY dimensions or static codec fit.
Use the actual S2 assigned face ranges, with explicit missing remote pins.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from placement_repack import gap, validate, relays

ORDER = ('io_serdes_2', 'io_serdes_1', 'io_collective', 'io_serdes', 'io_ucie')
RETIRED = ('io_xfifo',)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def propose(dump, spec, die):
    original = copy.deepcopy(dump['insts'])
    by = {i['n']: i for i in original}
    if spec['top'] != 'qfd_io_collective_static' or spec['outline'] != dict(w=864.0, h=950.4):
        raise ValueError('proposal requires exact static S2 ABI and 864 x 950.4 outline')
    for name in ORDER+RETIRED:
        if name not in by:
            raise ValueError(f'missing historical envelope: {name}')
    x = min(by[n]['x'] for n in ORDER)
    y = by['io_collective']['y']
    placements = []
    for name in ORDER:
        rect = copy.deepcopy(by[name])
        rect.update(x=round(x, 4), y=y, o='R0')
        if name == 'io_collective':
            rect.update(m=spec['top'], w=spec['outline']['w'], h=spec['outline']['h'])
        placements.append(rect)
        x = math.ceil(round((x+rect['w']+4.32)/.216, 8))*.216
    remaining = [i for i in original if i['n'] not in ORDER+RETIRED]
    final = remaining+placements
    if not die:
        raise ValueError('explicit authoritative die outline required')
    errors = validate(final, die)
    if errors:
        raise ValueError(f'proposed IO placement invalid: {errors[:8]}')
    after = {i['n']: i for i in placements}
    distances = {}
    for name in ('io_serdes', 'io_serdes_1', 'io_serdes_2', 'io_ucie'):
        distances[name] = dict(before_gap_um=round(gap(by['io_collective'], by[name]), 4),
                               after_gap_um=round(gap(after['io_collective'], after[name]), 4),
                               before_geometric_relays=relays(by['io_collective'], by[name]),
                               after_geometric_relays=relays(after['io_collective'], after[name]))
    ports = []
    coll = after['io_collective']
    for face in ('W', 'E', 'N'):
        for port in spec['pins'][face]:
            if port.startswith(('clk', 'fault')) or port in ('rst_n', 'pkg_s', 'die_ps'):
                continue
            lo, hi = spec['pin_ranges'][port]
            segment = ([coll['x'], coll['y']+lo, coll['x'], coll['y']+hi] if face == 'W' else
                       [coll['x']+coll['w'], coll['y']+lo, coll['x']+coll['w'], coll['y']+hi] if face == 'E' else
                       [coll['x']+lo, coll['y']+coll['h'], coll['x']+hi, coll['y']+coll['h']])
            ports.append(dict(port=port, face=face, assigned_global_segment=segment,
                              remote_physical_endpoint=None))
    graph = []
    for prefix, width, face in [('up',546,'E'), ('ur',514,'E'), ('sx0',546,'E'), ('sx1',546,'W'), ('sx2',546,'W')]:
        rx = {'up':'dp', 'ur':'dr', 'sx0':'sr0', 'sx1':'sr1', 'sx2':'sr2'}[prefix]
        graph.append(dict(tx=prefix, rx=rx, record_bits=width, collective_face=face,
            tx_chain=[f'collective.{prefix}_rec/valid/token', 'fixed equal-age relays',
                      'qfd_static_ch546 (TX write1/read3)',
                      'static slot codec', 'licensed PHY'],
            rx_chain=['licensed PHY', 'static slot codec',
                      'qfd_static_ch546 (RX write1/read3)', 'fixed equal-age relays', f'collective.{rx}_rec/valid'],
            calendar_controls=['ot_coll_lcal_tx: CDC write/read and codec write/read fixed slots',
                               'ot_coll_lcal_rx: codec expectation and CDC write/read fixed slots'],
            physical_homes='OPEN: CDC leaf views exist, but per-face children and calendar/codec slot joins missing',
            codec_phy_frame_bits=width+51))
    return dict(schema='opentallas.qwen.static-io-placement-proposal.v1', die=die,
        scope='full-global legal rectangles with exact collective assigned-face segments; not native qualification',
        placements=placements, retired_legacy_envelopes=list(RETIRED),
        envelope_semantics='SerDes/UCIe reservations preserve historical combined sizes. Licensed PHY-only outline, pin/clock views and static codec fit remain unproven.',
        global_geometry=dict(instances=len(final), overlaps=0, outside=0),
        distances=distances, actual_collective_face_assignments=ports, static_graph=graph,
        cut_diagnostic=dict(legacy_bits=2053, legacy_tracks=2438, legacy_util=2053/2438,
            native_serdes_pair_bits=1095, pair_only_same_tracks_util=1095/2438,
            two_pairs_same_tracks_util=2190/2438, ucie_both_pairs_bits=2126,
            qualification=False,
            condition='1095/2438 is conditional bookkeeping only; no claim that routes use these tracks. Separate W SerDes1/2 windows and E UCIe P/R windows, reserve exact track capacity and physical relay sites.'),
        missing=['Per-face static codec/calendar children and assigned physical pins.',
                 'Licensed PHY-only envelopes, FDI pins, source views and UCIe P/R concurrent capacity.',
                 'Seq/cq CDC homes and epoch/reset/static slot producers.',
                 'Exact pin-to-pin paths, real relay count/equal ages, cuts <=0.60 and routed TT/FF/DRC.'])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('dump',type=Path)
    p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--die',type=Path,required=True,help='JSON containing authoritative die key')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=propose(json.loads(a.dump.read_text()),json.loads(a.spec.read_text()),json.loads(a.die.read_text())['die'])
    result['inputs']={str(f):digest(f) for f in (a.dump,a.spec,a.die)}
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(geometry=result['global_geometry'],distances=result['distances'])))


if __name__=='__main__':
    main()
