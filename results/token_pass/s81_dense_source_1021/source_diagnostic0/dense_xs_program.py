#!/usr/bin/env python3
"""Immutable single-frame producer stimulus from lower_xs checkpoint images.

This is a component driver, not a complete DENSE2 stage programme. Input
quantisation is the fixture oracle at the gather interface; no output or return
is driven by the oracle. Completion is observed in the actual frame/CAP RTL.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/s81_static_control')]
import numpy as np
import hdc_golden_v41 as G
from pq_calendar import action_word, viamap


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--vectors', type=Path, required=True)
    p.add_argument('--capture-map', type=Path, required=True)
    a = p.parse_args()
    v = a.vectors
    m = json.loads((v / 'meta.json').read_text())
    assert m['die_master'] == 'col_h9_l4_lp' and m['land_e'] == 2
    assert m['K'] == 5120 and m['phase']['index'] == 0 and not m['phase']['bf']
    cap = next(c for c in json.loads(a.capture_map.read_text())['halves']['B']['captures']
               if c['slice'] == m['slice'])
    assert next(f for f in cap['frames'] if f['frame'] == m['die_frame'])['rows'] == list(map(int, m['rows']))
    P = [int(x, 16) for x in (v / 'spine_phase.hex').read_text().split()]
    nb, sb = (P[0] >> 14) & 65535, (P[0] >> 30) & 65535
    rows = {}
    def ev(t, **kw):
        r = rows.setdefault(t, {})
        assert not set(r).intersection(kw)
        r.update(kw)
    ev(400, accept_tag=0)
    ev(420, cfg=1, cfg_tag=0)
    for j in range(nb):
        ev(460+j, stream_req=1, stream_tag=0, stream_pos=0, stream_fam=0,
           stream_lastpos=int(j == nb-1), stream_lastop=int(j == nb-1))
        ev(462+j, stream_addr=sb+j)
    launch = 460+nb+48
    ev(launch, launch=1, launch_tag=0)
    # Conservative fixed deadline, never advanced by a DUT completion signal.
    ev(launch+2000, retire_mask=1)
    ev(launch+2020, phase_end=1)
    packed = [(t << 75) | action_word(r, action_bits=75) for t, r in sorted(rows.items())]
    (v/'pq_calendar_action.viamap.hex').write_text(viamap([x & ((1<<72)-1) for x in packed]))
    (v/'pq_calendar_time.viamap.hex').write_text(viamap([x >> 72 for x in packed]))
    events = []
    def issuer(t, **kw):
        layout = dict(go=(0,1), ph=(1,10), np=(11,3), prime=(93,1), start=(94,1),
                      length=(107,13), gw=(120,1), off_we=(123,1), off=(124,8))
        w = 0
        for k, x in kw.items():
            lo, wd = layout[k]
            assert 0 <= x < 1 << wd
            w |= x << lo
        events.append((t, 0, w))
    issuer(40, off_we=1, off=37)
    issuer(60, prime=1, length=len(packed))
    issuer(80, start=1, length=len(packed))
    issuer(110, gw=1)
    issuer(80+3+400, go=1, ph=0, np=0)
    x = np.array([int(x, 16) for x in (v/'vm.hex').read_text().split()], dtype=np.uint32).view(np.float32)
    q, e = G.quant_fp8(x)
    # Canonical E4M3 encoding, signed ten-bit unbiased block exponents.
    codes = {float(f): i for i, f in enumerate(G.E4M3) if np.isfinite(f)}
    qb = [codes[float(f)] if f != 0 else 0 for f in q]
    for bt in range(80):
        data = 0
        for half in range(2):
            block = 2*bt+half
            word = sum(int(c) << (8*i) for i, c in enumerate(qb[32*block:32*block+32]))
            word |= (int(e[block]) & 1023) << 256
            data |= word << (266*half)
        # One already-gathered beat per edge at the real XS input boundary.
        events.append((200+bt, 1, (bt << 1024) | data))
    (v/'dense_stim.txt').write_text(''.join(f'{t} {k} {w:x}\n' for t,k,w in sorted(events)))
    (v/'capture.hex').write_text(cap['cfg_d']+'\n')
    out = dict(schema='opentallas.s81.dense_component_program.v1', scope='XS4_FRAME_CAP_COMPONENT_ONLY',
               full_stage=False, full_token=False, stream_words=nb, calendar_rows=len(packed),
               issuer_go=483, calendar_launch=launch, fixed_retire=launch+2000,
               off=37, cycles=80+37+launch+2200,
               input_boundary='golden-quantised actual checkpoint x at XS gather pins',
               meta_sha256=hashlib.sha256((v/'meta.json').read_bytes()).hexdigest(),
               capture_map_sha256=hashlib.sha256(a.capture_map.read_bytes()).hexdigest())
    (v/'dense_program.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
