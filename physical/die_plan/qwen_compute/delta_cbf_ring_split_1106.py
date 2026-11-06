import sys,json,pathlib,copy,hashlib
R=pathlib.Path(sys.argv[1]);sys.path[:0]=[str(R/'tools/die_plan'),str(R/'physical/die_plan/qwen_compute/cores')]
import schema as S,gen_phys as G,reset_tree as RT,sle_ctl_pins as SP
PTH=R/'physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json';D=json.load(open(PTH));P=S.Plan(D,str(PTH));TN='cbf_q00__cl1b5a6458';T=D['partition_types'][TN];T0=copy.deepcopy(T)
OUT=R/'physical/die_plan/qwen_compute/cbf_ring_split_1106';OUT.mkdir(exist_ok=True)
places={'na_i00':('sle_cland_w515_n',[17.28,2466.72],[88.56,51.84],'N',90.19,72.02),'nb_i00':('sle_cland_w515_n_301',[1129.68,2466.72],[88.56,51.84],'N',89.96,71.58),'bc_i00':('sle_cland_w517_s_300',[17.28,17.28],[89.184,51.84],'S',89.85,71.62),'bc_i10':('sle_cland_w517_s_300',[626.4,17.28],[89.184,51.84],'S',89.85,71.62)}
rows=[]
for bus,(m,org,wh,face,tt,ff) in places.items():
 pp=[(b,x,y) for n,b,l,x,y,f in G.type_pins(P,TN) if n==bus];pp.sort(key=lambda q:(q[1],q[0]));W=len(pp);order=[q[0] for q in pp];table=SP.ring_pins(m,W,face,wh,order)
 pf=R/'physical/die_plan/qwen_compute/plan_of_record/cores/cbn_ring'/f'{m}_pins.json';original=json.load(open(pf));assert table==original,(bus,m,'signed pin-table mismatch')
 b=T['clock']['landing_contract']['bands'][bus];assert b['instance']=='u_cland_'+bus and b['ring_place']=='ff';inst='cl_'+bus;ck=next(x for x in table['pins'] if x['name']=='clk')
 T['hard_cores'].append(dict(inst=inst,module=m,origin_um=org,outline_um=wh,orient='R0',track_offset_um=[.012,.012],pins_file='cores/cbn_ring/'+pf.name,physical_inst='u_bound.u_cland_'+bus,physical_master=m,param_wrap=dict(base='ot_dp_clk_landing_cas',params=dict(W=W,DEPTH=4,WFALL=1,WREG=1,DSREP=1)),reset_net='cland_start',cells=11606 if W==515 else 11652,note='CBF registered input ring reuse; exact signed pin table, zero added data cycles; private candidate, collector event pending'))
 T['clock']['taps'].append(dict(name=inst+'.clk',kind='core',xy=[round(org[0]+ck['x']+.012,3),round(org[1]+ck['y']+.012,3)],insertion_ps=tt,insertion_ff_ps=ff,budget_owner='Measured qualified child local read clock; no parent timing credit'))
 b['hard_core']=inst;b['rect_um']=[*org,round(org[0]+wh[0],3),round(org[1]+wh[1],3)]
 rows.append(dict(bus=bus,master=m,W=W,face=face,origin=org,outline=wh,pins_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(),tt_mean=tt,ff_mean=ff))
for i,h in enumerate(T['hard_cores']):
 x,y=h['origin_um'];w,ht=h['outline_um'];assert x>=4.32 and y>=4.32 and x+w<=T['outline_um'][0]-4.32 and y+ht<=T['outline_um'][1]-4.32
 for k in T['hard_cores'][i+1:]:
  a,b=k['origin_um'];c,d=k['outline_um'];assert min(x+w,a+c)<=max(x,a) or min(y+ht,b+d)<=max(y,b),(h['inst'],k['inst'])
for k,b in T['clock']['landing_contract']['bands'].items():
 if b.get('hard_core'):continue
 if 'rect_um' not in b:continue
 a,b0,c,d=b['rect_um']
 for h in T['hard_cores'][4:]:
  x,y=h['origin_um'];w,ht=h['outline_um'];assert min(c,x+w)<=max(a,x) or min(d,y+ht)<=max(b0,y),(k,h['inst'])
Q=copy.deepcopy(D);Q['partition_types'][TN]=T0;assert Q==json.load(open(PTH))
EV=R.parent/'ev';EV.mkdir(exist_ok=True);candidate=EV/'plan_cbf_candidate.json';candidate.write_text(json.dumps(D,separators=(',',':'))+'\n')
report=dict(event='QC-CBF-RF1',type=TN,source_plan_sha256=hashlib.sha256(PTH.read_bytes()).hexdigest(),rows=rows,added_data_cycles=0,landing_children_qualified=True,native_compute_children_qualified=False,parent_signed=False,reset_collector='NOT REATTACHED/NOT PROVED/NOT NATIVE BOUND',remaining='Output bc_o01 congestion and FF tap affinity remain independent; no timing closure claim',hard_cores=T['hard_cores'],outline=T['outline_um'])
(OUT/'geometry_report.json').write_text(json.dumps(report,indent=1)+'\n');print(candidate);print(json.dumps(rows))
