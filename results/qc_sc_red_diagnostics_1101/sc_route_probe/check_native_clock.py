import re,json,sys
from pathlib import Path
text=Path('probe.log').read_text(errors='replace');counts=[int(x) for x in re.findall(r'Found\s+(\d+)\s+clock nets',text)]
j=dict(scope='NATIVE_ROUTER_CLOCK_RECOGNITION_NOT_STA',expected=2390,observed_clock_net_counts=counts,verdict='PASS' if counts and counts[-1]==2390 else 'FAIL')
Path('native_clock_recognition.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j))
if j['verdict']!='PASS':raise SystemExit(1)
