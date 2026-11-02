import pathlib,json,sys,csv,copy,math
r=pathlib.Path('/srv/opentallas-scratch/claude/codex-s81-qbs-centre-2255');sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-s81-die-2032/tools/die_plan');import core_infra_plan as CP,die_clock_128 as D,core_sink_census as C,core_infra as CI
names=['BUFx2_ASAP7_75t_R','BUFx16f_ASAP7_75t_R','BUFx12_ASAP7_75t_R','BUFx24_ASAP7_75t_R'];libs={c:D.lib_cells(c,r/'libexport',names=names) for c in ['TT','FF']};out={};chosen={};all_sl={}
for s in ['LLfu','LLfd','NNfu']:
 mod='dsfd_node_'+s;k=r/'actual_place'/f'{mod}_c';base=json.load(open(r/'slices'/f'{mod}.json'));sinks,other=C.census((k/f'run/results/asap7/kl_{mod}_c/base/1_synth.v').read_text(),'clk[0]');assert not other
 xy={C.unescape(q['name']):(float(q['x'])+float(q['w'])/2,float(q['y'])+.135) for q in csv.DictReader(open(k/'placed.csv')) if q['kind']=='ff'};assert set(xy)==set(sinks);pts={C.tcl_name(n):p for n,p in xy.items()}
 ns=sorted(sinks,key=lambda n:(xy[n][1],xy[n][0],n));h=len(ns)//2;groups=[]
 for half in [ns[:h],ns[h:]]:
  a=sorted(half,key=lambda n:(xy[n][0],xy[n][1],n));groups.extend([a[:len(a)//2],a[len(a)//2:]])
 variants=[]
 for count in range(21):
  sl=copy.deepcopy(base);nodes=[];parent='port:clk';bay=[20.532,37.692,22.692,40.032]
  # Plan-designed fixed entry trunk, selected from a priori NLDM/geometry only.
  sites=[(x,y) for y in [37.935,38.205,38.475,39.555,39.825] for x in [20.817,21.249,21.681,22.113]]
  for i,(x,y) in enumerate(sites[:count]):
   n=f'qb_entry_{i}';nodes.append({'name':n,'master':'BUFx2_ASAP7_75t_R','xy_um':[x,y],'parent':parent,'island_rect_um':bay});parent=n
  nodes.append({'name':'qb_root','master':'BUFx16f_ASAP7_75t_R','xy_um':[21.612,38.892],'parent':parent,'island_rect_um':bay})
  for ns_,y in [('S',21.6),('N',56.16)]:nodes.append({'name':f'qb_{ns_}','master':'BUFx12_ASAP7_75t_R','xy_um':[21.612,y],'parent':'qb_root'})
  leaves=[]
  for g,name,x,y,par in zip(groups,['SW','SE','NW','NE'],[12.96,30.24,12.96,30.24],[21.6,21.6,56.16,56.16],['S','S','N','N']):
   n='qb_'+name;nodes.append({'name':n,'master':'BUFx12_ASAP7_75t_R','xy_um':[x,y],'parent':'qb_'+par});leaves.append({'node':n,'sinks':[C.tcl_name(z) for z in g],'cts_open':True,'domain_sinks':len(g),'cts_fanout':24,'cts_stages':2})
  sl['core_tree']={'clock_port':'clk','stage_basis':'total','install_stage':'pre_cts','late_dpl_max_um':4.32,'nodes':nodes,'leaves':leaves};CI.compile_slice(sl)
  ans=CP.predict_tree(sl,libs,pts,{},wire_r_kohm_um=.178475*.8,wire_c_ff_um=.164264*.9)
  good=all(v['prediction']=='VALID' for v in ans['corners'].values())
  passed=good and all(abs(ans['corners'][c]['mean_ps']-target)<=20 for c,target in [('TT',250),('FF',202.5)])
  variants.append({'entry_trunk_cells':count,'model_calibration_valid':good,'nominal_target_20ps_pass':passed,'corners':{c:{z:v[z] for z in ['min_ps','mean_ps','max_ps','window_ps','prediction','out_of_calibration_leaves']} for c,v in ans['corners'].items()}})
  if passed and s not in chosen:chosen[s]={'entry_trunk_cells':count,'total_clock_cells':len(nodes),'model':ans};all_sl[s]=sl
 out[s]=variants
(r/'clock4_model_sweep.json').write_text(json.dumps(out,indent=1)+'\n');(r/'clock4_model_chosen.json').write_text(json.dumps(chosen,indent=1)+'\n')
for s,sl in all_sl.items():
 d=r/'tree4_slices'/('dsfd_node_'+s+'.json');d.parent.mkdir(exist_ok=True);d.write_text(json.dumps(sl,indent=1)+'\n')
print(json.dumps({s:{k:v for k,v in q.items() if k!='model'}|{'mean_ps':{c:a['mean_ps'] for c,a in q['model']['corners'].items()}} for s,q in chosen.items()}));print('counts chosen',len(chosen))
