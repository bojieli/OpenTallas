from pathlib import Path
import json,hashlib
b=Path('/work');d=json.loads((b/'SC_MM_ROLE_PROFILE.json').read_text())
for n,want in d['inputs'].items():
 actual=hashlib.sha256((b/n).read_bytes()).hexdigest()
 if actual!=want:raise SystemExit('SC_MM_EXACT_INPUT_CHANGED '+n)
print('SC_MM_EXACT_INPUT_GUARD_PASS truthful_PLACE_ODB_SDC_no_CTS_credit')
