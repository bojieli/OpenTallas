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
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/s81_static_control'),
               str(ROOT / 'tools/s81_dv/layer_prog')]
import numpy as np
import hdc_golden_v41 as G
from pq_calendar import viamap
import xs_calendar as XC


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
    # The frame cfg7 sequencer's operation tag is independent of the XS
    # streamer's live-slot tag. Keep the calibrated compiler's tag/parity0.
    tag = int(cap['flags'])
    assert tag in range(4) and ((cap['cfg']['rbase'] >> 14) & 3) == tag
    assert next(f for f in cap['frames'] if f['frame'] == m['die_frame'])['rows'] == list(map(int, m['rows']))
    P = [int(x, 16) for x in (v / 'spine_phase.hex').read_text().split()]
    S = [int(x, 16) for x in (v / 'spine_stream.hex').read_text().split()]
    c = XC.compile_phase(P, S, 0, m['slice_index'])
    packed = c['packed']
    (v/'pq_calendar_action.viamap.hex').write_text(viamap([x & ((1<<72)-1) for x in packed]))
    (v/'pq_calendar_time.viamap.hex').write_text(viamap([x >> 72 for x in packed]))
    events = [(t, 0, w) for t, w in c['iss'].items()]
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
               full_stage=False, full_token=False, stream_words=c['nb'], calendar_rows=len(packed),
               issuer_go=XC.TS+XC.GO_LAT+XC.ACC, calendar_launch=c['tg'],
               fixed_retire=next(t for t,r in c['rows'].items() if r.get('retire_mask')),
               off=XC.OFF, xs_tag=0, frame_operation_tag=tag, gather_parity=0,
               cycles=max(2905,c['end_iter']), calibrated_common_shift_model=c['D'],
               calendar_compiler_sha256=hashlib.sha256(Path(XC.__file__).read_bytes()).hexdigest(),
               stream_stall_edges=c['stall_edges'],
               input_boundary='golden-quantised actual checkpoint x at XS gather pins',
               meta_sha256=hashlib.sha256((v/'meta.json').read_bytes()).hexdigest(),
               capture_map_sha256=hashlib.sha256(a.capture_map.read_bytes()).hexdigest())
    (v/'dense_program.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
