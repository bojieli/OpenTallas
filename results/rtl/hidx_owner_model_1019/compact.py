#!/usr/bin/env python3
"""Compact complete inventory without duplicating every transparent alias."""
import collections,gzip,hashlib,json,pathlib,sys
r=pathlib.Path(sys.argv[1]);o=r/'owner_model'
sys.path.insert(0,str(r))
from dft.liberty import _parse_groups,_read_text,_strip_heavy
lib=[b for k,a,b in _parse_groups(_strip_heavy(_read_text(r/'census/SEQ.lib')))['groups'] if k=='library'][0]
ff={}
for k,a,b in lib['groups']:
    if k!='cell':continue
    cp=[bb['attrs']['capacitance'] for kk,aa,bb in b['groups'] if kk=='pin' and bb['attrs'].get('clock')=='true']
    if cp:ff[a[0]]=(float(b['attrs']['area']),sum(map(float,cp)))
counts=collections.Counter();rows=0
with gzip.open(o/'all_owner_sink_records.jsonl.gz','rt') as h,gzip.open(o/'owner_index.jsonl.gz','wt') as w:
    for line in h:
        x=json.loads(line); rows+=1
        if x['role']=='ff': counts[x['native_master']]+=1
        for p,bs in x['native_inputs'].items():
            x['native_inputs'][p]=[b['net'] for b in bs]
        x['names']=[n for n in x['names'] if not any(t in n for t in ('.tree.','.drive.','.tdrive.','.hdrive.','.bit_copy.','.enable_drive.','.group_drive.'))]
        x['endpoint_list']='all_owner_sink_records.jsonl.gz at same driver; complete native pins retained remotely'
        del x['endpoints']
        w.write(json.dumps(x,separators=(',',':'))+'\n')
meta={'rows':rows,'clock_unit':'fF','area_unit':'um2',
      'ff_masters':{k:{'count':v,'area':ff[k][0],'clock_cap':ff[k][1]} for k,v in counts.items()},
      'ff_area':sum(ff[k][0]*v for k,v in counts.items()),
      'ff_clock_cap':sum(ff[k][1]*v for k,v in counts.items()),
      'seq_library_sha256':hashlib.sha256((r/'census/SEQ.lib').read_bytes()).hexdigest(),
      'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in o.glob('*.gz')}}
(o/'artifact_manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta,indent=2))
