#!/usr/bin/env python3
"""Replay original real HWIN occupancy witnesses; never modify the old gate."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[2]
sys.path.insert(0, str(root / 'tools/ref_tile'))
from measured_band_fill import measured_band_fill

binding = json.loads((here / 'review_source_binding.json').read_text())
for rel, expected in binding['tools'].items():
    assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == expected, rel
spec = json.loads((here / 'original_spec.json').read_text())
floorplan = json.loads(gzip.decompress((here / 'floorplan.json.gz').read_bytes()))
for tag in ('placed', 'cts'):
    placed = json.loads(gzip.decompress((here / (tag + '.json.gz')).read_bytes()))
    result = measured_band_fill(spec, floorplan, placed)
    assert not result['valid'], result
    assert 'unapproved standard cell outside full-width band' in result['errors'], result
    assert result['outside_area_um2'] > 6000, result
    print(tag, json.dumps(result, sort_keys=True))
print('ACTUAL_OLD_HWIN_FILL_REFUSAL_PASS')
