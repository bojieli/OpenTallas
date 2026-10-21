import json,re,hashlib
from pathlib import Path
Dpath=Path('/home/ubuntu/scratch/tok-func2-hbm/conn_idx/contract_func.json');D=json.loads(Dpath.read_text());A=D['instances'];B=json.loads(Path('/home/ubuntu/scratch/tok-func2-hbm/conn_idx/bundle/slice/boundary.json').read_text());existing=set();edges=D['edges']
pads={n for n,v in A.items() if v['master']=='hbfd_pad'}
# For pad membership, find real endpoints through i/o, not clocks/reset/strap.
def ends(n,seen=None):
 seen=set(seen or ());
 if n in seen:return set()
 seen.add(n);z=set()
 for e in edges:
  s,t=e.get('source',[]),e.get('sink',[])
  if not s or not t:continue
  other=None
  if t[0]==n and t[1]=='i':other=s[0]
  elif s[0]==n and s[1]=='o':other=t[0]
  if other is not None:
   z |= ends(other,seen) if other in pads else {other}
 return z
for kind,producer_qs in [('topk3',('SW','SE','NW')),('coll4',('SW','SE','NW','NE'))]:
 core={'hb_ckgen','su_prog','col_su','col_idx','hb_idx__ctl'}
 for q in ['SW','SE','NW','NE']:
  core|={p+q for p in ['hcollgi_','hcollgl_','hcollrs_','hcollks_','hcollb_','hb_coll_','hb_vms_','calendar_','hleaf_']}
  core|={f'vmb_{q}{b}' for b in range(8)}
 for q in producer_qs:
  core|={f'pgp_{q}',f'sucore_{q}',f'subr_{q}',f'stl_{q}'}|{f'su_{q}{j}' for j in range(4)}
 assert not core-A.keys(),core-A.keys()
 chosen=existing|core
 addedpads={p for p in pads if (z:=ends(p)) and z <= chosen and len(z)>1}
 selected=chosen|addedpads
 additive=sorted(selected-existing)
 # All boundary edges are explicit; this is a core data-path cut, not proof that
 # inactive unrelated SFU/SM/DMA/IDX/HC interfaces have been programmed/covered.
 inputs=[]
 for e in edges:
  s,t=e.get('source',[]),e.get('sink',[])
  if s and t and t[0] in selected and s[0] not in selected:
   if t[0] in core or t[0] in addedpads:inputs.append(dict(name=e['name'],source=s,sink=t,bits=e.get('bits')))
 out=dict(schema='opentallas.gq_wave_source_cut_plan.v1',kind=kind,contract_sha256=hashlib.sha256(Dpath.read_bytes()).hexdigest(),existing_count=len(existing),core_seeds=sorted(core),additive_instances=additive,additive_regex='^(?:'+'|'.join(re.escape(x) for x in additive)+')$',added_count=len(additive),selected_count=len(selected),producer_quarters=list(producer_qs),transport_quarters=['SW','SE','NW','NE'],quiet_source_quarters=['NE'] if kind=='topk3' else [],boundary_inputs_to_core=inputs,status='SOURCE_PLAN_NO_BUILD_NO_FULL_CHAIN_QUALIFIER',obligations=['No core_VM/SU/GQ/ring read/write expected outputs may enter as boundary replay','Unused SFU/HC/DMA/SM/cx auxiliary inputs remain explicit boundary assumptions and quiet ifunarmed','All GQ and ringB faults must be checked or actualhost_status included; no landfault-onlyaggregate','Actual producerprogramme+placement+finiteSU->COLL epochs commonowner, no boundaryfixture substitution'])
 Path('/home/ubuntu/scratch/codex-hbm-gq-wave-1403/'+kind+'.minimum.cut.json').write_text(json.dumps(out,indent=1)+'\n')
 print(kind,'additive',len(additive),'selected',len(selected),'core_boundary_edges',len(inputs))
