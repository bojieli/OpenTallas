import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import hbm_accel_die_fp as H


def test_full_shape_identity_and_legality():
    baseline = H.build(H.R24W, geometry_only=True)
    candidate = H.build(H.R24SM3, geometry_only=True)
    before = {i.name: i for i in baseline['insts'] if i.kind == 'sm'}
    after = {i.name: i for i in candidate['insts'] if i.kind == 'sm'}
    assert set(after) == set(before) == {f'sm{i}' for i in range(32)}
    for name, sm in after.items():
        assert (sm.w, sm.h) == (3075.84, 1131.84)
        assert sm.orient == before[name].orient
        assert {k: sm.sm[k] for k in ('stack', 'row', 'col')} == before[name].sm
    for group in candidate['groups'].values():
        assert {(i.sm['physical_row'], i.sm['physical_col']) for i in group['sms']} == {
            (r, c) for r in range(3) for c in range(3)} - {(2, 2)}
    result = H.legality(candidate)
    assert result['overlaps'] == result['outside'] == 0
    assert candidate['geo']['W'] <= 33000 and candidate['geo']['H'] <= 26000


def test_network_fail_closed_and_clock_partition():
    with pytest.raises(ValueError, match='network paths and latency'):
        H.build(H.R24SM3)
    m = H.build(H.R24SM3, geometry_only=True)
    regions = [r for r in H.clock_regions(m) if r['name'].startswith('G')]
    assert len(regions) == 12
    assert sorted(s for r in regions for s in r['sms']) == sorted(f'sm{i}' for i in range(32))
    for a, r in enumerate(regions):
        x0, y0, x1, y1 = r['rect']
        for t in regions[a+1:]:
            a0, b0, a1, b1 = t['rect']
            assert x1 <= a0 or a1 <= x0 or y1 <= b0 or b1 <= y0
    assert not m['buses'] and not m['paths']
