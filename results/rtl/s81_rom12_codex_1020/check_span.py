import json,pickle,sys
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
import xs_field_calendar as F
D=Path('/srv/opentallas-scratch/codex/s81-rom12-1020');r=pickle.loads((D/'out/pack_real/L0.pickle').read_bytes())
old=next(c for c in r['cals'] if c['op']=='attn.wq_b')
new=F.op_calendar('attn.wq_b',r['phase'],r['stream'],[p['phase'] for p in old['phases']])
assert old['packed']==new['packed'] and old['iss']==new['iss']
assert old['predicted_span']==1105 and new['predicted_span']==1189
assert new['span_tail']==307
(D/'out/span_correction.json').write_text(json.dumps(dict(PASS=True,old_predicted=1105,new_measured=1189,added_edges=84,origin='u_sp.go at63 -> last frame-root RET at1252',same_ROM_actions_and_issuer=True,new_record=F.record(new)),indent=1)+'\n')
print('SPAN_CORRECTION PASS1189=7*126+307; ROM/action/issuer bytes unchanged',flush=True)
