#!/usr/bin/env python3
"""Corrupt the final released HC row and require source-aware rejection."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

root = pathlib.Path(sys.argv[1]).resolve()
source = root / 'output/payload.bin'
mutant = root / 'payload-last-row-mutant.bin'
if mutant.exists():
    raise SystemExit('refusing to overwrite previous mutant evidence')
if shutil.disk_usage(root).free - source.stat().st_size < 1 << 30:
    raise SystemExit('need 1GiB headroom after mutant allocation')
shutil.copyfile(source, mutant)
with mutant.open('r+b') as f:
    f.seek(-1, 2)
    offset = f.tell()
    value = f.read(1)
    f.seek(offset)
    f.write(bytes([value[0] ^ 1]))
command = [sys.executable, str(root / 'export_hbm_hc_checkpoint_image.py'),
           'verify', '--inputs', str(root / 'inputs'), '--out', str(root / 'output'),
           '--payload', str(mutant)]
result = subprocess.run(command, capture_output=True, text=True)
(root / 'payload-mutant.log').write_text(result.stdout + result.stderr)
if result.returncode == 0 or 'actual row payload mismatch ordinal2063' not in result.stderr:
    raise SystemExit('mutant did not fail at the final actual checkpoint row')
h = hashlib.sha256()
with mutant.open('rb') as f:
    for data in iter(lambda: f.read(1 << 20), b''):
        h.update(data)
receipt = {'status': 'EXPECTED_FAILURE_OBSERVED', 'changed_byte_offset': offset,
           'actual_row_ordinal': 2063, 'mutant_sha256': h.hexdigest(),
           'verifier_exit': result.returncode, 'command': command,
           'disk_free_after': shutil.disk_usage(root).free}
(root / 'payload-mutant.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('HC_FULL_IMAGE MUTANT PASS expected_failure=actual_row_payload_mismatch_ordinal2063')
