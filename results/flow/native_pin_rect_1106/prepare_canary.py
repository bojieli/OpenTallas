import copy,json
from pathlib import Path
from compact_coll_form import declare_clock_pin
p=Path('/work'); rows=json.loads(Path('/source/pins.json').read_text());(p/'baseline.json').write_text(json.dumps(rows));(p/'pins.json').write_text(json.dumps(rows));declare_clock_pin(p)
rows=json.loads((p/'pins.json').read_text());assert len(rows)==2143
for mode in ['declared','wrong_rectangle','wrong_layer','wrong_anchor','wrong_name']:
 out=copy.deepcopy(rows);pin=next(x for x in out if x['bus']=='ck' and x.get('bit')==0)
 if mode=='wrong_rectangle':pin['native_rects'][0][2]-=.001
 if mode=='wrong_layer':pin['layer']='M4'
 if mode=='wrong_anchor':pin['x']+=1
 if mode=='wrong_name':pin['bus']='ck_WRONG'
 (p/(mode+'.json')).write_text(json.dumps(out))
