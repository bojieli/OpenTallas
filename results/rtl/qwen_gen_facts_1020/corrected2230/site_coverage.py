"""Check actual relay/reset frame footprints against emitted vacant row envelope."""
import json,hashlib
from pathlib import Path
s=Path('/srv/opentallas-scratch/claude/codex-qw-reset-inputs2230')
f=json.loads((s/'out/case/gen_safety_facts.json').read_text())
m=json.loads((s/'out/rom_tp8b.json').read_text())
frames=[i for i in m['insts'] if i['m'].startswith(('qfd_rly','qfd_land','qfd_rst_rep'))]
miss=[]
for i in frames:
 x0,y0,x1,y1=i['x'],i['y'],i['x']+i['w'],i['y']+i['h']
 area=(x1-x0)*(y1-y0)
 covered=sum(max(0.,min(x1,c)-max(x0,a))*max(0.,min(y1,d)-max(y0,b)) for a,b,c,d in f['channels'] if a<x1 and x0<c and b<y1 and y0<d)
 if area-covered>1e-5:
  miss.append(dict(inst=i['n'],master=i['m'],rect=[x0,y0,x1,y1],area_um2=area,uncovered_um2=area-covered))
r=dict(scope='Actual allocated relay/reset frame footprint coverage by declared hard-block/keepout-free channel rectangles; does not substitute for detailed cell/via occupancy',gen=str(s),frames=len(frames),channels=len(f['channels']),uncovered_frames=len(miss),examples=miss[:40],facts_sha256=hashlib.sha256((s/'out/case/gen_safety_facts.json').read_bytes()).hexdigest(),rom_sha256=hashlib.sha256((s/'out/rom_tp8b.json').read_bytes()).hexdigest())
Path('station_site_coverage.json').write_text(json.dumps(r,indent=1)+'\n')
print('FRAME_SITE_COVERAGE frames',len(frames),'uncovered',len(miss))
