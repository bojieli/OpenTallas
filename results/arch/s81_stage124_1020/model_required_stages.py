"""Bounded actual slot model for116-frame idx3; no full exact campaign."""
exec(open(__file__.replace('model_required_stages.py','probe_inventory_slots.py')).read().split('res={}')[0])
import xs_stage_map as SM
model=json.loads((D/'inventory_slot_model.json').read_text())['116']
die=XC._die('/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref')
die.plan['blocks']=[b for b in die.plan['blocks'] if b['name'] not in removed];TP.set_from_die(die)
frames=['u_f_3L02','u_f_3R03','u_f_0L00','u_f_0L10']
dense={};raw=[]
for cls,L in [('L0',0),('L1',1),('L2',2),('L14',14),('L20',20),('L24',24)]:
 fix=XC.layer_ops(L)[2]; rows=[]
 for frame in frames:
  r=XC.frame_alloc(die,frame,str(Path('/srv/opentallas-scratch/claude/s81-calpipe/fixtures')/fix),{'id':f'L{L}_n0','dense_layer':L,'experts':0})
  rows.append(r);raw.append({'class':cls,'frame':frame,'q':r['q_fill_ub'],'bf':r['bf_fill'],'phases':r['nphases']})
 dense[cls]={'q':max(max(r['q_fill_ub']) for r in rows),'bf':max(max(r['bf_fill'] or [0]) for r in rows),'phases':max(r['nphases'] for r in rows)}
 print('DENSE_MODEL',cls,json.dumps(dense[cls]),flush=True)
slope=model['worst_expert_words_per_pair_representatives']
# Take the largest small-N per-expert phase charge, including the fixed phase.
ph=max(r['phases']/r['n'] for r in model['exact_small_rows'])
c={'slope':slope,'phases_per_expert':ph,'dense':dense,'source':'actual116inventory four representative frames N1/N2/N3 and denseN0; all-frame exact qualification owed'}
for n in range(124,400):
 m=SM.build(n,c,'116-frame idx3, pinned pair policy; bounded allocator model')
 if m['stages_count']<=n and all(s['model_load']<8192 and s['n_experts']<=SM.nmax(c,SM.cls_of(s['dense_layer']) if s['dense_layer'] is not None else None) for s in m['stages']): break
else: raise RuntimeError('no feasible bounded model')
copy=sum(len(s['dies']) for s in m['stages'] if s['copy_b'])
out={'scope':'bounded actual-slot model, NOT full exact capacity or MU calendar qualification','inventory_sha256':model['inventory_sha256'],'costs':c,'dense_raw':raw,'required_stage_count_model':n,'layer_dies':4*n,'copy_B_dies_map_policy':copy,'fixed_other_dies_model':52,'total_dies_model':4*n+copy+52,'added_hops_over97':n-97,'added_token_latency_us_model':round((n-97)*.3776,4),'logic_area_mm2_model':round((4*n+copy+52)*799.21,2),'AR_MTP':'unqualified until new physical-stage occupancy calendar; old46/10 not inherited'}
(D/'required_stage_model.json').write_text(json.dumps(out,indent=2)+'\n')
(D/'stage_map_required_MODELONLY.json').write_text(json.dumps(m,indent=2)+'\n')
print('REQUIRED_STAGE_MODEL',json.dumps({k:v for k,v in out.items() if k!='dense_raw'}),flush=True)
