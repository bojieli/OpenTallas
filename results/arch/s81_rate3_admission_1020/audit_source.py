"""Immutable 012a3a074 row ownership/allocation audit. Never a full-stage PASS."""
import collections,hashlib,json,math,os,subprocess,sys,traceback
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
import xs_place as X
import xs_bf as B
import xs_topo as T
import lower_xs as L
import dv_layer_compile as C
DR='/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref';FX=Path('/srv/opentallas-scratch/claude/s81-calpipe/fixtures')
die=C.Die(C.die_tree(None,DR))
if len(sys.argv)>1 and sys.argv[1]=='--defaultcompile':
 out=dict(frame='u_f_0R00',op='ffn.shared_gu',scope='default exact-input compile A/B')
 try:
  rec,field=X.compile_frame(die,out['frame'],str(FX/'L0'),[out['op']],only=set())
  out.update(success=True,nphases=rec['nphases'])
 except Exception as e:
  traceback.print_exc();out.update(success=False,type=type(e).__name__,error=str(e))
 print('DEFAULT_COMPILE',json.dumps(out),flush=True);sys.exit(0)
O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=False)
import v41_rom_ksplit_bankmap as S
sl={L.slice_index(die,s):s for s in die.slices()};all_results={};alloc=[]
for layer in ['L0','L2','L14','L20']:
 fx=X.Fix(FX/layer);ops=X.XS_OPS[layer];r=[]
 for op in ops+X.BF_OPS[layer]:
  groups=B.bf_groups(fx,op) if op in B.BF_OPS else X.op_groups(fx,op)
  for gi,g in enumerate(groups):
   owners={};byframe=[]
   for sid in range(16):
    frames=die.frames_of(sl[sid]);assert len(g['groups'][sid])==len(frames)
    for fi,fr in enumerate(frames):
     for row in g['groups'][sid][fi]:owners.setdefault(row,[]).append(fr)
     byframe.append(dict(sid=sid,frame=fr,rows=len(g['groups'][sid][fi])))
   expected=set(range(len(g['rows'])));missing=sorted(expected-set(owners));extra=sorted(set(owners)-expected);dup={k:v for k,v in owners.items() if len(v)!=1}
   row=dict(op=op,mat=g['mat'],expected=len(expected),missing=missing,extra=extra,duplicate=dup,
    coverage_PASS=not(missing or extra or dup),rows_per_slice=[sum(len(z) for z in group) for group in g['groups']],
    rows_per_frame_histogram=dict(collections.Counter(x['rows'] for x in byframe)),
    ownership_sha256=hashlib.sha256(json.dumps(owners,sort_keys=True).encode()).hexdigest())
   if op not in B.BF_OPS:
    f=X.fmt_of(fx,g['mat']);K=fx.w(g['mat']).shape[1]*(2 if f=='fp4' else 1);nseg,_=X.nseg_for(f,K,X.NPAIRS);Rph=2*(X.NPAIRS//nseg)
    nch=math.ceil(max(x['rows'] for x in byframe)/Rph);chunks=[]
    for sid in range(16):
     for fi,fr in enumerate(die.frames_of(sl[sid])):
      original=g['groups'][sid][fi];parts=[T.chunk(g,original,ch,Rph) for ch in range(nch)]
      assert sum(parts,[])==original
      chunks.append(dict(frame=fr,rows=[len(z) for z in parts]))
    row.update(phases=nch,rows_per_phase_histogram=dict(collections.Counter(n for x in chunks for n in x['rows'])),empty_FP_chunks=sum(n==0 for x in chunks for n in x['rows']))
    if layer=='L0' and op in ['ffn.experts_gu','ffn.down']:
     pairwords=[len(S.segment_order(f,a,b)) for a,b in S.segments(K,nseg)]
     # Production compile_frame gives every phase floor(12/nseg)*nseg slots unless compact flag; with chunks of3/4 rows
     # ceil(rows/2)==2 so compact flag saves no slots either. This is actual source allocation policy, not raw bytes.
     for x in chunks:
      slots=[min((12//nseg)*nseg,math.ceil(n/2)*nseg) if os.environ.get('OT_XS_COMPACT_TAILS')=='1' and n else (12//nseg)*nseg for n in x['rows']]
      alloc.append(dict(frame=x['frame'],mat=g['mat'],op=op,fmt=f,K=K,chunk_rows=x['rows'],chunk_slots=slots,
       address_increments=sum((n//nseg)*sum(pairwords) for n in slots),paired_segment_words=pairwords))
   r.append(row)
 all_results[layer]=r
# Phase0 uses a separate untouched placement path.
ap=[];seen=[]
for sid in range(16):
 _,p=L.placement(die,sl[sid]);rows=[v for x in p for v in x['rows']];seen+=rows
 if len(rows)!=L.ROWS_PER_SLICE:ap.append(dict(sid=sid,slice=sl[sid],frames=len(p),placed=rows,expected=list(range(28*sid,28*(sid+1)))))
missing_ap=sorted(set(range(28*16))-set(seen))
# One expert's exact address totals are shape-invariant across all15,360 immutable identities; all six fixture experts
# are checked separately. Separate shared FP8 down from routed FP4; no model payload rebuild.
byframe={}
for a in alloc:
 if a['fmt']!='fp4':continue
 d=byframe.setdefault(a['frame'],dict(gu=[],down=[]))
 d['gu' if a['op']=='ffn.experts_gu' else 'down'].append(a['address_increments'])
for fr,d in byframe.items():
 assert len(d['gu'])==len(d['down'])==6 and len(set(d['gu']))==len(set(d['down']))==1
 d.update(per_expert_addresses=d['gu'][0]+d['down'][0],q_pairs=12,mean_pair_per_expert=(d['gu'][0]+d['down'][0])/12,
  max_experts_necessary_bound_before_dense=(12*8192)//(d['gu'][0]+d['down'][0]))
bound=min(d['max_experts_necessary_bound_before_dense'] for d in byframe.values())
result=dict(scope='IMMUTABLE_SOURCE_ROW_COVERAGE_AND_ALLOCATION_ONLY',source='012a3a074',full_stage_qualified=False,
 env={k:os.environ.get(k) for k in ['OT_XS_QPAIRS','OT_XS_GU_MERGE','OT_XS_TOPO','OT_XS_PROP','OT_XS_COMPACT_TAILS']},
 topology=T.describe(),frame_masters=dict(collections.Counter(die.inst[fr]['master'] for sid in sl for fr in die.frames_of(sl[sid]))),
 post_phase0_groups=all_results,phase0=dict(missing_rank_rows=missing_ap,affected=ap,coverage_PASS=not missing_ap),
 actual_source_policy_per_expert=byframe,source_policy_max_experts_per_stage_before_dense=bound,
 source_policy_minimum_stages_before_dense=math.ceil(15360/bound),
 note='Earlier>=118stage necessary bound required fixed80down rows/slice; PROP changes down ownership so that old bound is historical, not transferred. New bound derives current padded slot policy.',
 admission_gaps=['selected stage/expert map','dense weights and per-pair allocation/cfg limits','a_proj missing rows','production rank-tag emission','GU and PROP CAP cfg_d/lifetime','native producer-to-consumer stage evidence','F8 SVC MU occupancy','changed consumer/gather ownership transport and source ages'])
(O/'source_audit.json').write_text(json.dumps(result,indent=1)+'\n');(O/'allocation_rows.json').write_text(json.dumps(alloc,indent=1)+'\n')
inputs={}
for mod in list(sys.modules.values()):
 p=getattr(mod,'__file__',None)
 if p and str(p).startswith(str(R)) and str(p).endswith('.py'):inputs[str(Path(p).relative_to(R))]=hashlib.sha256(Path(p).read_bytes()).hexdigest()
(O/'imported_sources.json').write_text(json.dumps(inputs,indent=1)+'\n')
print('SOURCE_AUDIT',json.dumps(dict(source=result['source'],post_phase0_groups_PASS=all(g['coverage_PASS'] for rows in all_results.values() for g in rows),phase0_missing=missing_ap,max_experts=bound,min_stages=result['source_policy_minimum_stages_before_dense'],allocation_histogram=dict(collections.Counter(d['per_expert_addresses'] for d in byframe.values())))),flush=True)
