"""Exact ordinary-VM I operands for actual retained native indexed LOADs."""
import collections,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/hbm_next'))
from isa_loader import load_isa
IR,IC=load_isa()
root=Path(__file__).parents[1];packet=json.loads((root/'canonical_resident_cached/stream.json').read_text());raw=(root/'canonical_resident_cached/stream.hgi1r').read_bytes();source=IC.decode_all(Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r').read_bytes());depth={};stack=[]
for i,(_,r,x,_)in enumerate(source):
 depth[i]=tuple(stack)
 if(r.unit,r.op)==('CTL','LOOP'):stack.append(i)
 elif(r.unit,r.op)==('CTL','ENDLOOP'):stack.pop()
assert not stack
out=[]
for pos,m in enumerate(packet['records']):
 if m['kind']!='body':continue
 r,x,_=IR.decode_one(raw,m['offset'])
 if r.unit!='DMA'or r.op!='LOAD'or not r.desc['A'].indexed:continue
 orig=source[m['source_record']][1];idesc=r.desc['I'];a=r.desc['A'];assert not depth[m['source_record']], 'indexed LOAD inside loop needs actual L bound'
 assert idesc.space=='VM'and idesc.fmt=='U32'and idesc.n==idesc.m==1 and not any(getattr(idesc,k)for k in('lstride','l1stride','dyn_sel','dyn_mul','indexed','n_sel'))
 # L=0 outside loops; row slots are separate DYN selectors, not L.
 rows=IR.expand(r,x);indices=[q.desc['I'].base for slot,q in rows];assert all(0<=v<262144 for v in indices)
 w=idesc.base;out.append(dict(stream_record=pos,source_record=m['source_record'],source_original_Iword=orig.desc['I'].base,lowered_Iword=w,I_effective_plus_L=indices,L=0,source_slots=m.get('source_slots'),source_format=a.fmt,source_n=a.n,source_dyn_mul=a.dyn_mul,source_encoded_HBMbase=a.base,source_code=a.base>>37,ordinary_VM=dict(quad=w>>16,bank=(w>>3)&7,sector=w>>3,wordlane=w&7),I_raw_MDesc_hex=f'{IR.HGI.mdesc(idesc):064x}'if hasattr(IR.HGI,'mdesc')else None))
result=dict(status='ACTUAL_RETAINED_INDEXED_OPERAND_ADDRESSES_NO_STATIC_RESOLVER_ADOPTION',source_records=len({r['source_record']for r in out}),emitted_records=len(out),expanded_scalar_row_index_reads=sum(len(r['I_effective_plus_L'])for r in out),min_Iword=min(r['lowered_Iword']for r in out),max_Iword=max(r['lowered_Iword']for r in out),format_counts=dict(collections.Counter(r['source_format']for r in out)),source_code_counts=dict(collections.Counter(r['source_code']for r in out)),all_ordinary_VM=True,all_L0_outside_loops=True,aperture_or_mirror_used=False,records=out,holds=['runtime U32 Iword values remain actual VMread data; no ROM IDs or assumed cache','identical address can represent different value epochs; compiler anchors/writes must invalidate any index reuse','sharing existing STATIC BACK read client requires explicit fixed-date mux/ownership and pipeline return identity','source original I506112 is symbolic source namespace, lowered actual I addresses are ordinary18bitwords'])
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='records'}))
