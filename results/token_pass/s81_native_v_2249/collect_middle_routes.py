"""Export exact current bound descriptions of missing middle V transport.

Raw $buf boundaries are kept as boundaries; no alias or wire-age fallback.
"""
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from bound_die import object_items

root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
report=json.loads((root/'bind_report.json').read_text())
if report.get('n_errors')!=0 or report.get('errors') or report.get('type_splits'):
    raise ValueError('current bind stage is not clean')
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
pin=re.compile(r'^(.+)\.(vi_s|vi_n|rs_i|rn_i|vi|i)\[(\d+)\]$')
scope=re.compile(r'^(?:u_gunit\.|u_bk_sel\.|u_seqhost\.u_seqhost\.|u_eng\.u_e\.|u_s_[346][NS]\.)')
groups=defaultdict(dict)
for name,desc in object_items(root/'bind_sinks.json'):
    if not scope.match(name):continue
    m=pin.fullmatch(name)
    if not m:continue
    groups[(m[1],m[2])][int(m[3])]=desc
rows=[]
for (unit,port),bits in sorted(groups.items()):
    if set(bits)!=set(range(276)):continue
    row={'target':unit+'.'+port,'bits':276,'status':'BLOCKED'}
    drivers=set();ages=set();bad=[];variants=set()
    for bit,desc in sorted(bits.items()):
        if not isinstance(desc,list) or len(desc)!=4 or desc[0]!='pin':
            bad.append({'bit':bit,'description':desc});continue
        m=re.fullmatch(r'(.+)\.(\w+)\[(\d+)\]',desc[1])
        if not m or int(m[3])!=bit or type(desc[2]) is not int or desc[2]<0:
            bad.append({'bit':bit,'description':desc});continue
        drivers.add(m[1]+'.'+m[2]);ages.add(desc[2]);variants.add(bool(desc[3]))
    row.update(drivers=sorted(drivers),age_edges=sorted(ages),source_is_glue=sorted(variants))
    if not bad and len(drivers)==1 and len(ages)==1:
        row['status']='PASS_EXACT_RAW_BOUND_WORD'
        row['source']=next(iter(drivers));row['age_edges']=next(iter(ages))
    else:row['bad_bits']=bad[:8]
    rows.append(row)
meta={'schema':'opentallas.s81.middle_v_raw_routes.v1',
      'scope':'Current event2 evbind2 clean bind-stage V words; full verification pending separately',
      'source_asbuilt_sha256':digest(root/'asbuilt.json'),
      'bound_top_sha256':digest(root/'rtl/s81_bound_top.sv'),
      'bind_sinks_sha256':digest(root/'bind_sinks.json'),
      'routes':rows,'internal_body_cycles_included':False,
      'buffer_aliases_inferred':False,'physical_START_qualified':False,'full_token':False}
(out/'routes.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({'rows':len(rows),'pass':sum(r['status']=='PASS_EXACT_RAW_BOUND_WORD' for r in rows),
                  'blocked':sum(r['status']=='BLOCKED' for r in rows)}))
for row in rows:print(json.dumps(row))
