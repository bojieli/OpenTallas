#!/usr/bin/env python3
"""Candidate-only audit of universal-calendar capacity tails (no manifest writes)."""
import argparse,hashlib,json,re
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('contract');ap.add_argument('unresolved');ap.add_argument('output');a=ap.parse_args()
rtl=Path('rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar.sv')
layout={n:(int(lo),int(w)) for n,lo,w in re.findall(r'assign\s+(\w+)=calendar\[(\d+)\+:(\d+)\];',rtl.read_text())}
assert len(layout)==17,layout
c=json.loads(Path(a.contract).read_text());u=json.loads(Path(a.unresolved).read_text())['entries'];proof=[];candidates=[]
for n in sorted(x for x in c['instances'] if x.startswith(('epcal_','vmfc_'))):
 used=set();consumers=set()
 for e in c['edges']:
  s=e['source']
  if s[0]==n and s[1] in layout:
   off,w=layout[s[1]];assert 0<=s[2]<s[3]<=w
   used.update(range(off+s[2],off+s[3]));consumers.add(e['sink'][0])
 width=max(used)+1;assert used==set(range(width)),(n,width,len(used))
 assert width==({'epcal_SW':38}.get(n,19) if n.startswith('epcal_') else 89),(n,width)
 entries=[]
 for v in u:
  if v['instance']==n and v['port'] in layout:
   off,w=layout[v['port']]
   for lo,hi in v['unread_ranges']:assert width<=off+lo<=off+hi<187,(n,v)
   entries.append(dict(instance=n,port=v['port'],unread_ranges=v['unread_ranges'],bit_count=v['bit_count'],reason=f'Universal187 capacity tail above fully connected {width}-bit custom payload; not semantic use of universal port names',allowlist_candidate=True,root_review_required=True))
 assert sum(v['bit_count'] for v in entries)==187-width
 candidates+=entries;proof.append(dict(instance=n,used_payload_range=[0,width-1],unused_capacity_range=[width,186],consumers=sorted(consumers)))
r=dict(schema='opentallas.calendar_tail_review_1019.v1',manifest_adopted=False,bit_count=sum(v['bit_count'] for v in candidates),proof=proof,candidates=candidates,evidence={'universal_slice_map':str(rtl),'source_sha256':hashlib.sha256(rtl.read_bytes()).hexdigest(),'historical_generator':'tools/hbm_die_v15/complete_host_targets_2330.py explicitly keeps high outputs unused; original vmfc W89','current_contract_sha256':hashlib.sha256(Path(a.contract).read_bytes()).hexdigest()},limitation='Intended overprovisioning only: W187 hardware does not reject nonzero custom-unused tail. Compiler tail-zero image evidence not included. calendar_v/done and all actual payload bits excluded. Root review required before adoption.')
assert r['bit_count']==1045,r['bit_count'];Path(a.output).write_text(json.dumps(r,indent=1)+'\n');print('CALENDAR_TAIL_REVIEW_CANDIDATE bits=1045; no manifest adopted')
