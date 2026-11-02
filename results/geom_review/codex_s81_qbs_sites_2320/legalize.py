import sys,json,copy,pathlib,tkinter,collections,re,importlib.util
P=pathlib.Path('/home/ubuntu/coord/tmp/codex-qbs-sites-2320');sys.path.insert(0,str(P/'tooltree/tools/die_plan'))
import core_infra as CI,core_infra_plan as CP,die_clock_128 as D,core_sink_census as C
s=importlib.util.spec_from_file_location('G','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
T=tkinter.Tcl();src=pathlib.Path('/srv/opentallas-scratch/claude/codex-s81-qbs-centre-2255');names=['BUFx2_ASAP7_75t_R','BUFx16f_ASAP7_75t_R','BUFx12_ASAP7_75t_R','BUFx24_ASAP7_75t_R'];libs={c:D.lib_cells(c,src/'libexport',names=names) for c in ['TT','FF']};summary={}
for mod in ['dsfd_node_LLfu','dsfd_node_LLfd','dsfd_node_NNfu']:
 out=P/mod;r=[list(T.splitlist(l)) for l in (out/'sites.tsv').read_text().splitlines()];u=int(next(x[1] for x in r if x[0]=='DBU'));r0=next(x for x in r if x[0]=='ROW0');sw=float(r0[4]);sh=float(r0[6]);I=lambda x:int(round(float(x)*u));tech={'dbu':u,'core':list(map(int,next(x[1:] for x in r if x[0]=='CORE_DBU'))),'rows':[],'masters':{},'obstacles':[]}
 for x in r:
  if x[0]=='ROW':a,b=float(x[1]),float(x[2]);tech['rows'].append({'rect':[I(a),I(b),I(a+int(x[4])*sw),I(b+sh)],'site':I(sw),'orient':x[3]})
  if x[0]=='MASTER':tech['masters'][x[1]]=[I(x[2]),I(x[3])]
  if x[0]=='FIXED':tech['obstacles'].append({'name':x[1],'kind':'fixed','rect':[I(z) for z in x[3:7]]})
 pg={ly:sorted({tuple(map(float,x[3:7])) for x in r if x[0] in ['PG','PGVIA'] and x[2]==ly}) for ly in ['M4','M5']};assert all(pg.values())
 sl=json.load(open(src/'tree4_slew0_slices'/f'{mod}.json'));sl['core_tree']['install_stage']='pre_gpl';sl['pushdown']={'islands':[],'repeaters':[]};sl['pg_obstructions_um']={k:[list(z) for z in v] for k,v in pg.items()}
 owned=sl['islands'][0]['rect_um'];blocks=[x for x in r if x[0]=='BLOCKAGE'];skipped=[]
 for x in blocks:
  b=list(map(float,x[2:6]))
  if b==owned:skipped.append({'id':x[1],'rect_um':b,'reason':'exact source-owned centre_clock_entry reservation replaced by preGPL fixed planned cells under existing12.2a1; normalFP source regeneration, NOT reuse'});continue
  tech['obstacles'].append({'name':'blockage:'+x[1],'kind':'blockage','rect':[I(z) for z in b]})
 assert len(skipped)==1
 d=G.Design(out/'geom.tsv');face=set()
 for p in d.pins:
  if G.CLOCK_PIN_RE.search(p['name']) or re.match(r'^rst_n(?:\[0\])?$',p['name']):continue
  nn=d.pin_net.get(p['k'])
  if nn is None:continue
  if p['io']=='OUTPUT':
   seen=set()
   while nn not in seen:
    seen.add(nn);a=d.nets[nn][1]
    if not a or a[0]!='i':break
    k=d.kind(a[1])
    if k=='S':face.add(a[1]);break
    inc=[n for n,c in d.cell_in.get(a[1],[]) if not c]
    if k!='B' or len(inc)!=1:break
    nn=inc[0]
  elif p['io']=='INPUT':
   stack=[nn];seen=set()
   while stack:
    nn=stack.pop()
    if nn in seen:continue
    seen.add(nn)
    for a in d.nets[nn][2]:
     if a[0]!='i' or a[2]:continue
     k=d.kind(a[1])
     if k=='S':face.add(a[1])
     elif k=='B':stack.extend(d.drives.get(a[1],[]))
 for cid in face:
  c=d.cells[cid];tech['obstacles'].append({'name':c[6],'kind':'face','rect':[I(z) for z in c[2:6]]})
 # Conservative full-cell exclusion of ACTUAL PG rectangles; no guessed straps/row bands.
 for ly,rects in pg.items():
  for i,b in enumerate(rects):tech['obstacles'].append({'name':f'actualPG:{ly}:{i}','kind':'pg','rect':[I(z) for z in b]})
 (out/'technology.json').write_text(json.dumps(tech,indent=1));(out/'actual_pg.json').write_text(json.dumps(sl['pg_obstructions_um'],indent=1));(out/'owned_bay_replacement.json').write_text(json.dumps(skipped,indent=2))
 legalized,rep=CP.legalize_slice(sl,tech)
 for n in legalized['core_tree']['nodes']:n['xy_um']=legalized['cell_placements'][n['name']]['centre_um']
 plan=CI.compile_slice(legalized);gate=CI.trunk_pg_clearance(legalized,plan);points={C.tcl_name(C.unescape(c[6])):G.ctr(c) for c in d.cells.values() if c[0]=='S'}
 model=CP.predict_tree(legalized,libs,points,{},wire_r_kohm_um=.178475*.8,wire_c_ff_um=.164264*.9,input_slew_ps=0.)
 (out/'legalized_slice.json').write_text(json.dumps(legalized,indent=1));(out/'legalization.json').write_text(json.dumps(rep,indent=2));(out/'pg_gate.json').write_text(json.dumps(gate,indent=2));(out/'model_slew0.json').write_text(json.dumps(model,indent=1))
 summary[mod]={'rows':len(tech['rows']),'fixed_TAPs':sum(x['kind']=='fixed' for x in tech['obstacles']),'face_flops':len(face),'pg_unique':{k:len(v) for k,v in pg.items()},'owned_bay_replaced':skipped,'legalization':rep,'pg_trunk':gate,'model':{c:{k:v.get(k) for k in ['min_ps','mean_ps','max_ps','window_ps','prediction','out_of_calibration_leaves']} for c,v in model['corners'].items()}}
 print(mod,json.dumps(summary[mod]),flush=True)
(P/'SUMMARY.json').write_text(json.dumps(summary,indent=2))
