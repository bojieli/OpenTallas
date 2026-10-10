"""Bind immutable QS5 exact evidence to the actually retained native Q RTL."""
import argparse
import hashlib
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--source', type=Path, required=True)
ap.add_argument('--receipt', type=Path, required=True)
a = ap.parse_args()
raw = a.receipt.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '44f6c76d27d95b83e0e4bdb57241121c91672d4eb816de27f21038b3cbd4f33b'
gate = json.loads(raw)
assert gate['verdict'] == 'PASS' and gate['total_compared_cycles'] == 12775002
positive = [r for r in gate['runs'] if r['name'].startswith('pos')]
negative = [r for r in gate['runs'] if r['name'].startswith('neg')]
assert len(positive) == 5 and len(negative) == 3
assert all(r['returncode'] == 0 and r['coverage']['compared_cycles'] > 0 for r in positive)
assert all(r['returncode'] != 0 and r['caught'] for r in negative)
for filename, digest in gate['source_sha256'].items():
    assert hashlib.sha256((a.source / filename).read_bytes()).hexdigest() == digest, filename
print(f"QS5_GATE_BOUND_PASS sources={len(gate['source_sha256'])} positives=5 negatives=3 cycles=12775002")
