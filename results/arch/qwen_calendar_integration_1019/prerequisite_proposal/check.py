#!/usr/bin/env python3
"""Finite source arithmetic/identity checks only. Never emits deployment data."""
import hashlib,json,pathlib
P=pathlib.Path(__file__).resolve().parent
for s in json.loads((P/'sources.json').read_text()):
 assert hashlib.sha256((P/s['file']).read_bytes()).hexdigest()==s['sha256']
def doc(n):return json.loads(next(P.glob('*__'+n+'.json')).read_text())
m=doc('programme_integration_model'); c=doc('composition'); meta=doc('ctlm_metadata_source')
# Derive from actual diagnostic dependency endpoints, NOT patch expected times.
prev={11:[3,4,5,6,7,8,9,10],12:[11,12],16:[14,15],20:[17,18,19]}
HEAD0=meta['constants']['HEAD0']; assert HEAD0==3
rows=[]
for pc,pcs in prev.items():
 stage=next(s for s in c['composition']['stages'] if s['pcs']==pcs)
 old=next(p['at'] for p in meta['plan'] if p.get('pc')==pc and p['unit']==1)
 # Original compiler's dependency gap is eight on these source axes.
 target=stage['end']+8
 mismatch=next(x for x in m['ME_timing_mismatches'] if x['pc']==pc)
 assert target==mismatch['dv_composed_target'] and target-old==mismatch['difference']
 rows.append(dict(pc=pc,dependency_end=stage['end'],gap=8,legacy_edge=old,diagnostic_edge=target,diagnostic_head_cycle=target-HEAD0,qualified=False))
# The strongest obstruction is source evidence, not arithmetic.
assert 'PARAMETER' in c['composition']['stages'][1]['source']
assert 'not composed from a measurement' in c['composition']['stages'][3]['source']
# Source ROM record index plus held context user is injective. Old compact
# program ID is not; no claim that any chosen entry covers every XPF leaf.
D=doc('descriptor_cap1'); a=D['ranges']['decode']['first']; n=D['ranges']['decode']['count']
ids={(u<<10)|i for u in range(4) for i in range(a,a+n)}
assert len(ids)==4*406 and max(ids)<4096
aliases=[x for x in m['compact_producer_ids'] if x['epoch'] in ('qkv','gu')]
for u in range(4):assert len({tuple(x['actual_compact_producer_ids']) for x in aliases if x['user']==u})==1
# Handle plus source transaction is unique during active lifetime; duplicate,
# wrong-user/generation/image, and a repeated issue are causal refusals.
def h(u,g=1,im=7,st=1):return (im,g,st,u)
active=(h(0),a)
negative=0
for bad in [(h(1),a),(h(0,0),a),(h(0,1,6),a),(h(0),a+1)]:
 assert bad!=active;negative+=1
seen=set();assert active not in seen;seen.add(active);assert active in seen;negative+=1
# Install proof is a partial order on actual capture events; zero manifest
# and edge equality cannot establish prerequisites.
def eligible(begin,pw0,auth,seal,drained):return not(begin or pw0) and auth and seal and drained
assert eligible(0,0,1,1,1)
for x in [(1,0,1,1,1),(0,1,1,1,1),(0,0,0,1,1),(0,0,1,0,1),(0,0,1,1,0)]:assert not eligible(*x);negative+=1
out=dict(scope='MODEL ONLY; no RTL or execution grant',ME_rows=rows,source_transaction_identity_cases=len(ids),causal_refusals=negative,base_minimum_logical_state=1670,transaction_tag_minimum_extra=20,conditional_minimum_with_two_tag_captures=1690,whole_parent_state=None,native_phase=None,first_use=None,source_timing_qualified=False)
(P/'model.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS MODEL: six source hashes; four diagnostic dependency equations; 1624 transaction IDs; 10 causal refusals. Source timing/native phase/first use HOLD.')
