# HBM-BIND-2: manifest = HBM-BIND-1 B1s (Codex SU ownership r3 + native cones + reset carriers + strap_lane_id ID strap)
# + extra whole-cell map parts (landing homes).  usage: mk_h.py OUTDIR HOMES_JSON
import json,sys
from pathlib import Path
P=Path('/srv/opentallas-scratch2/claude/hbm-bind-1-1029'); R=Path(sys.argv[1]); R.mkdir(exist_ok=True)
a=json.loads((P/'b1s/asbuilt_b.json').read_text())
m=json.loads((P/'b1/map_b.json').read_text()); n0=len(m['parts'])
h=json.loads(Path(sys.argv[2]).read_text())['parts']
clash=[k for k in h if k in m['parts']]; assert not clash, clash[:5]
m['parts'].update(h)
(R/'map_b.json').write_text(json.dumps(m))
a['map_file']=str(R/'map_b.json'); a['note']='HBM-BIND-2 landing homes '+Path(sys.argv[2]).name+' | '+a['note']
(R/'asbuilt_b.json').write_text(json.dumps(a,indent=1))
print('map parts',n0,'->',len(m['parts']),'compose',a['compose'])
