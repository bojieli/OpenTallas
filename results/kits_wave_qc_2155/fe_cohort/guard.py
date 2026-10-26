#!/usr/bin/env python3
"""Match the live kit to the exact committed G3 source cohort, without modifying it."""
import hashlib,json,sys
from pathlib import Path
meta=json.loads(Path(__file__).with_name('cohort.json').read_text())
kit=Path(sys.argv[1]);bad=[]
for name,want in meta['expected_kit_sha256'].items():
 p=kit/name
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=want:bad.append(name)
print('FE_COHORT '+('FAIL '+','.join(bad) if bad else 'PASS '+str(len(meta['expected_kit_sha256']))+' input files'))
sys.exit(bool(bad))
