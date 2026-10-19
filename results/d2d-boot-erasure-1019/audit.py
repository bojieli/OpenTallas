"""Bounded source/image inventory; not RTL simulation or startup equivalence."""
from pathlib import Path
import hashlib, json, re

base = Path(__file__).resolve().parent
binding = json.loads((base / 'frozen_binding.json').read_text())
assert all(x['manifest_sha256'] == x['actual_sha256'] for x in binding['dependencies'])
image = (base / 'input/d2d_cal_image_mu.svh').read_text()
events = {}
for side in ('TX', 'RX'):
    packed = int(re.search(r'D2D_CAL_K_' + side + r"_IMG = 1024'h([0-9a-f]+)", image)[1], 16)
    for seg in (0, 1, 2):
        start = 0 if seg == 0 else int(re.search(r'D2D_CAL_K_' + side + '_SEG' + str(seg) + r" = 32'h([0-9a-f]+)", image)[1], 16)
        t, rows = 0, []
        for i in range(start, 32):
            w = (packed >> (32*i)) & 0xffffffff
            dt, last, port, kind, beat, rep = w >> 18, (w >> 17) & 1, (w >> 14) & 7, (w >> 10) & 15, (w >> 5) & 31, w & 31
            assert dt and beat + rep <= 31
            t += dt
            rows.append(dict(entry=i, calendar_edge_offset=t, port=port, kind=kind, first_beat=beat, extra_beats=rep, last=bool(last)))
            t += rep
            if last:
                break
        assert rows[-1]['last']
        events[f'{side}_segment{seg}'] = rows

# Exact target-11 dispatch addressing. This inventory proves complete EMISSION
# coverage if all 66 words pass dispatch; it does not prove calendar acceptance.
dispatch = [dict(word=a, side=('RX' if a & 1 else 'TX'), address=(a >> 1 if a < 64 else 32)) for a in range(66)]
for side in ('TX', 'RX'):
    assert sorted(x['address'] for x in dispatch if x['side'] == side) == list(range(33))

manifest = {str(p.relative_to(base)): dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size) for p in sorted((base/'input').iterdir())}
result = dict(status='HOLD_UNCONDITIONAL_ERASURE_NOT_PROVEN', qualification='Static source and image inventory only; no simulation, constructor, source integration or EDA', certified_clone_partition=[], dispatcher_emission_coverage=dispatch, calendar_events=events, inputs=manifest, prerequisite_status=dict(full_emission='Source supports 66 ordered words', actual_acceptance='OPEN: stopped/reset/write frontier not established', no_early_start='OPEN: BC EARLY faults but does not suppress start', full_macro_noninterference='OPEN: stale memory must be dominated by real written ownership and age bypass', first_authoritative_boundary='OPEN: FRAME D2D has no native binding; absolute reset/phase composition missing'))
(base/'audit.json').write_text(json.dumps(result, indent=2)+'\n')
print('SOURCE_INVENTORY PASS: 66 emitted-address coverage, six image segments, frozen dependency hashes match; startup equivalence HOLD')
