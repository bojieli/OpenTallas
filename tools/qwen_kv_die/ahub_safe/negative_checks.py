#!/usr/bin/env python3
import copy,json,subprocess,sys
from pathlib import Path
b=Path('..').resolve();j=json.loads((b/'distributed/reparsed.json').read_text());m=j['modules']['qkd_ahub_static_dw_safe_native'];out=b/'negatives';out.mkdir(exist_ok=True)
base=[sys.executable,'tools/qwen_kv_die/ahub_safe/verify.py',str(b/'synth/safe2.mapped.json')]
ff=next(n for n,c in m['cells'].items()if c['type'].startswith('DFFASR'))
pins=m['cells'][ff]['connections'];print('state mutant target',ff,pins)
for key in ['D','CLK','RESETN','SETN']:
 if key not in pins:continue
 q=copy.deepcopy(j);q['modules']['qkd_ahub_static_dw_safe_native']['cells'][ff]['connections'][key]=['0']
 path=out/f'mut_{key}.json';path.write_text(json.dumps(q))
 r=subprocess.run(base+[str(path),str(b/'distributed/distribution.json')],capture_output=True,text=True)
 (out/f'mut_{key}.log').write_text(r.stdout+r.stderr)
 assert r.returncode and 'input/state/reset/clock relation' in r.stderr,(key,r.returncode,r.stderr)
 print('EXPECTED_FAIL',key)
# Unsupported parameter profile must be rejected before output generation.
r=subprocess.run([sys.executable,'tools/qwen_kv_die/ahub_safe/distribute.py',str(b/'synth/safe2.mapped.json'),str(out/'unsupported'),'--profile','historical_a7'],capture_output=True,text=True)
(out/'unsupported.log').write_text(r.stdout+r.stderr);assert r.returncode and 'unsupported AHUB native parameter profile' in r.stderr
print('EXPECTED_FAIL unsupported_profile')
bad=out/'wrong_source.json';bad.write_text('{}')
r=subprocess.run([sys.executable,'tools/qwen_kv_die/ahub_safe/distribute.py',str(bad),str(out/'unsupported_source'),'--profile','GEN7_AP_-40_-40_-38_-39_FR_-7'],capture_output=True,text=True)
(out/'wrong_source.log').write_text(r.stdout+r.stderr);assert r.returncode and 'unsupported AHUB mapped source/profile hash' in r.stderr
print('EXPECTED_FAIL wrong_source_hash')
s=(b/'distributed/qkd_ahub_static_dw_safe_native.v').read_text();needle='  assign \\fr_rz = '
assert s.count(needle)==1;s=s.replace(needle,needle+'~',1)
(out/'native_payload_invert.v').write_text(s)
print('NEGATIVE_CHECKS_PASS')
