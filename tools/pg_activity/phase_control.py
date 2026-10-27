#!/usr/bin/env python3
"""Check exact net-labelled stripe locations after cropping, plus old-reset mutant."""
from kv_commensurate import local_stripe

def global_rows(row, origin, length):
    out = set()
    for i in range(-10000, 10000):
        x = row['offset_um'] + i * row['pitch_um']/2 - origin
        if -1e-6 <= x <= length+1e-6:
            out.add((round(x, 5), 'POWER' if i % 2 == 0 else 'GROUND'))
    return out

def local_rows(row, offset, first, length):
    out = set()
    i = 0
    while offset + i * row['pitch_um']/2 <= length+1e-6:
        net = first if i % 2 == 0 else ('GROUND' if first == 'POWER' else 'POWER')
        out.add((round(offset + i * row['pitch_um']/2, 5), net))
        i += 1
    return out

cases = [({'pitch_um':4.32, 'offset_um':2.16}, 6433.56),
         ({'pitch_um':39.96, 'offset_um':13.77},6433.56),
         ({'pitch_um':4.32, 'offset_um':2.16},6432.0),
         ({'pitch_um':39.96, 'offset_um':13.77},6420.0),
         ({'pitch_um':39.96, 'offset_um':13.77},0.0)]
for row, origin in cases:
    offset, first = local_stripe(row, origin)
    assert local_rows(row, offset, first, 200) == global_rows(row, origin, 200), (row,origin)
row, origin = cases[0]
assert local_rows(row,row['offset_um'],'POWER',200) != global_rows(row,origin,200)
row, origin = cases[2]
offset, first = local_stripe(row,origin)
assert first == 'GROUND'
assert local_rows(row,offset,'POWER',200) != global_rows(row,origin,200)
print('STRIPE_PHASE PASS 5 global-location/net controls; crop-reset and wrong-first-net mutants caught')
