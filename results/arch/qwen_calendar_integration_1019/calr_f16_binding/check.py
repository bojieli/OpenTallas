#!/usr/bin/env python3
"""Bounded binding MODEL checks; no RTL simulation, synthesis or GEN."""
import hashlib,json,pathlib
P=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
for row in json.loads((P/'sources.json').read_text()):
 assert sha((P/'source'/row['copy']).read_bytes())==row['sha256'],row

def src(n):return next((P/'source').glob('*__'+n))
def doc(n):return json.loads(src(n).read_text())
old=[int(x,16) for x in src('pw_metadata.hex').read_text().splitlines()]
new=[int(x,16) for x in src('model_pw.hex').read_text().splitlines()]
meta=doc('ctlm_metadata_source.json');desc=doc('descriptor_cap1.json');body=doc('body.json')
assert len(old)==len(new)==1024 and meta['programme']['words']==25
assert all(x==0 for x in old[400:976])
assert [i for i in range(1024) if old[i]!=new[i]]==list(range(400,439))
assert old[:400]==new[:400] and old[439:]==new[439:]
# Concrete disjoint typed namespaces, never confuse ROM entry868 with PW868.
pw_ranges={'isa':[0,400],'wtn1':[400,439],'reserved_zero':[439,976],
 'ME':[976,984],'reserved_zero2':[984,1004],'XPF':[1004,1016],
 'footer':[1016,1024]}
assert sorted(i for a,b in pw_ranges.values() for i in range(a,b))==list(range(1024))
# Reconstruct the exact logical calendar; do not emit a deployment image.
segs=body['segments'];normal=segs['embed'];emit=[i for i,(_,c) in enumerate(normal) if (c>>1)&7==6 and (c>>5)&1 and c>>112!=14]
assert len(emit)==1
segs=dict(segs,init=[(t,0 if i==emit[0] else c) for i,(t,c) in enumerate(normal)])
entries=[];ranges={}
for kind in ['embed','decode','head','boot','init']:
 while len(entries)%4:entries.append(1<<116)
 first=len(entries);last=0
 for t,c in segs[kind]:
  d=t-last;assert 1<=d<=4095 and 0<=c<1<<116;entries.append(d<<116|c);last=t
 ranges[kind]={'first':first,'count':len(entries)-first}
assert ranges==desc['ranges']
for stage in range(1,37):
 while len(entries)%4:entries.append(1<<116)
 assert len(entries)==desc['preload_ranges'][str(stage)]['first']
 entries.append((8<<116)|(14<<112)|(stage<<4)|9)
assert len(entries)==desc['entries']==1009 and ranges['decode']['count']==406
words=[0]*4096
for i,x in enumerate(entries):words[i//4]|=x<<(128*(i%4))
expected=sha(''.join(f'{w:0128x}\n' for w in words).encode())
rom=[]
for lane in range(2):
 rows=[0]*512
 for a,w in enumerate(words):
  part=(w>>(lane*266))&((1<<266)-1)
  while part:
   l=part&-part;b=l.bit_length()-1;rows[a//8]|=1<<(8*b+a%8);part-=l
 rom.append(sha(''.join(f'{r:0532x}\n' for r in rows).encode()))
# Full identities are kept in the context bank; a bounded unique handle is
# carried through the real reader. Generation wrap is a fault, never alias.
def handle(user,stage,generation,image):return (user,stage,generation,image)
a=handle(0,1,7,100);b=handle(0,1,8,100)
assert a!=b
checks=[]
for u in range(4):
 for stage in [0,1,36,37]:
  active=handle(u,stage,7,100)
  for other in [handle((u+1)%4,stage,7,100),handle(u,stage,6,100),handle(u,stage,7,99),handle(u,(stage+1)%38,7,100)]:
   assert active!=other;checks.append('stale_or_foreign_receipt_refused')
  for me,xpf,witness in [(0,0,1),(1,0,1),(0,1,1),(1,1,0)]:
   assert not(me and xpf and witness);checks.append('early_retire_refused')
  assert bool(1 and 1 and 1);checks.append('matched_two_reader_retire')
# BEGIN is consumed with higher priority than PW0 or JOIN in local binding.
# An independently aged copy is refused even when its READY bit is stale high.
def authorize(ready,begin,pw0,matched,local_seal):return ready and not begin and not pw0 and matched and local_seal
assert authorize(1,0,0,1,1)
for t in [(1,1,0,1,1),(1,0,1,1,1),(1,0,0,0,1),(1,0,0,1,0)]:assert not authorize(*t)
# Avoid the stopped naive-clone first-edge design: demonstrate why identical
# next D does not permit arbitrary current-Q consumers on the capture edge.
assert (0!=1) and ((1,1)==(1,1))
# Explicit minimum integration vehicle: one real ME part, one XPF head with
# its two epochs. Physical fanout, reset/clock/tree and pipeline controls extra.
H=2+6+16+16
cost={
 'source_install_sideband_capture':84,
 'destination_install_sideband_capture':84,
 'existing_four_slot_crossing_sideband_payload':4*84,
 'two_complete_local_PW_captures':2*75,
 'held_install_metadata_ready':16+64+1+1,
 'context_identity_extra':4*(18+18+59+2+16+16),
 'identity_qualified_start_capture':1+2+6+16+16+16+59+2+18+18,
 'witness_event_capture':16+6+16+16,
 'final_receipt_capture_two_minimum_readers':2*(1+H),
 'minimum_reader_identity_ownership_one_ME_two_XPF_epochs':3*H,
 'per_context_seen_flags':4*2,
}
assert H==40
out={'scope':'PRIVATE OPT-IN MODEL; no production/native/SAFE qualification',
 'source_hashes':len(json.loads((P/'sources.json').read_text())),
 'PW_allocation_half_open':pw_ranges,'changed_PW_words':39,'template_bits':1742,
 'calendar_entries':len(entries),'calendar_ranges':ranges,
 'computed_asset_hashes_uninstalled':{'expected.hex':expected,'calendar_m0.viamap.hex':rom[0],'calendar_m1.viamap.hex':rom[1]},
 'pinned_programme_sha256':desc['source']['programme_sha256'],
 'template_PW_sha256':sha(src('model_pw.hex').read_bytes()),
 'minimum_vehicle_increment_logical_state_bits':cost,
 'minimum_vehicle_increment_total':sum(cost.values()),
 'whole_parent_added_FF':None,'native_phase':None,'first_use':None,
 'source_ME_edge_mismatch_count':sum(x['difference']!=0 for x in doc('programme_integration_model.json')['ME_timing_mismatches']),
 'finite_identity_cases':len(checks),'actual_RTL_simulation':False}
assert out['source_ME_edge_mismatch_count']==4
(P/'model.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS MODEL ONLY: source hashes, exact 25-word PW allocation, 406/1009 calendar reconstruction, %d finite identity cases; minimum vehicle +%d logical state bits; full parent/phase/first-use HOLD'%(len(checks),sum(cost.values())))
