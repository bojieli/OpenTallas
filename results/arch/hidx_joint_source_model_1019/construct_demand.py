import json,gzip,hashlib,collections,math,resource,bisect
from pathlib import Path
P=Path('input');O=Path('construction_demand');O.mkdir(exist_ok=True)
def load(f):return json.load(gzip.open(P/f,'rt')) if f.endswith('.gz') else json.load(open(P/f))
trees=json.load(gzip.open('out_demand/native_RMST_tree_ledger.json.gz','rt'));site=json.load(gzip.open('out_demand/site_plan.json.gz','rt'));pg=load('pg_ledger.json');reserve=load('clock_reserve.json')
assert len(site)==11145 and len(trees)==11449
reserved={tuple(z) for a in reserve['reserved_H_rays'].values() for z in a};HS={};HO={};VO={(l,x):[] for l in ['M3','M5'] for x in pg['summary'][l+':via_landing:all']['clear_track_nm']}
for region in ['south','band','north']:
 HS[region]=[(l,y) for l in ['M4','M2'] for y in pg['summary'][l+':via_landing:'+region]['clear_track_nm'] if (l,y) not in reserved]
 for z in HS[region]:HO[z]=[]
def collision(a,b,own,net):return any(n!=net and a<=d+100 and b>=c-100 for c,d,n in own)
records=[]
for i,t in enumerate(trees):
 pts=[[round(a*1000),round(b*1000)] for a,b in t['access_points_um']]
 spanx=max(z[0] for z in pts)-min(z[0] for z in pts);spany=max(z[1] for z in pts)-min(z[1] for z in pts)
 boundary=any(not(2160<=x<=138240 and 56160<=y<=84240) for x,y in pts)
 local=not boundary and t['max_tree_root_path_um']<=3.0 and spany<=1080
 records.append({'net_index':i,'driver':t['driver'],'points_nm':pts,'local':local,'span_x_nm':spanx,'span_y_nm':spany,'native_max_cap_fF':t['native_max_cap_fF'],'original_corner_cap':t['corner_cap']})
# Longest intervals first; separate actual local same-neighborhood edges from exterior.
order=sorted(records,key=lambda r:(r['local'],-r['span_x_nm'],-len(r['points_nm']),r['net_index']))
fail=[];counts=collections.Counter();geometry=[]
for r in order:
 n=r['net_index'];pts=r['points_nm'];a=min(x for x,y in pts);b=max(x for x,y in pts)
 regions=['band','south','north'] # shortest actual complete contacts, not compulsory exterior detours
 # Actual source/sink vertical length determines belt choice. LayerM4 is preferred
 # at equal region cost, M2 supplies overflow; no changing actual endpoints.
 candidates=[]
 for reg in regions:
  for lay,y in HS[reg]:
   candidates.append((sum(abs(v-y) for u,v in pts),0 if lay=='M4' else 1,lay,y,reg))
 candidates.sort()
 chosen=None
 for cost,lp,lay,y,reg in candidates:
  if not collision(a-48,b+48,HO[lay,y],n):chosen=(lay,y,reg);break
 if chosen is None:
  fail.append({'net_index':n,'reason':'H_INTERVAL_UNASSIGNED','local':r['local'],'x_interval_nm':[a,b],'contacts':len(pts)});counts['H_fail']+=1;continue
 lay,hy,reg=chosen;HO[lay,hy].append((a-48,b+48,n));counts['H_'+lay+'_'+reg]+=1
 leads=[];netfail=False
 for pi,(px,py) in enumerate(pts):
  yl,yh=sorted([py,hy]);vc=None
  for vl,vx in sorted(VO,key=lambda z:(abs(z[1]-px),z[0]!='M3')):
   if not collision(yl-48,yh+48,VO[vl,vx],n):vc=(vl,vx);break
  if vc is None:
   fail.append({'net_index':n,'point_index':pi,'reason':'M3_VERTICAL_INTERVAL_UNASSIGNED','y_interval_nm':[yl,yh],'contact_nm':[px,py],'H_trunk':[lay,hy,a,b]});counts['V_contact_fail']+=1;netfail=True;continue
  vl,vx=vc;VO[vc].append((yl-48,yh+48,n));vc=vx;boundary_M4=px<2160 or px>138240;boundary_M5=not boundary_M4 and (py<2160 or py>138240);stack=['VIA34'] if boundary_M4 else ['VIA45','VIA34'] if boundary_M5 else ['VIA12','VIA23'];leads.append({'point_index':pi,'native_contact_nm':[px,py],'M3_x_nm':vc,'vertical_layer':vl,'vertical_nm':[yl,yh],'M2_local_jog_nm':abs(px-vc),'H_via':'VIA34' if lay=='M4' else 'VIA23','base_contact_stack':stack,'base_vias':abs((4 if boundary_M4 else 5 if boundary_M5 else 1)-int(vl[1]))+abs(int(vl[1])-int(lay[1])),'exact_source_stack':['VIA'+str(k)+str(k+1) for k in range(min(4 if boundary_M4 else 5 if boundary_M5 else 1,int(vl[1])),max(4 if boundary_M4 else 5 if boundary_M5 else 1,int(vl[1])))],'exact_trunk_stack':['VIA'+str(k)+str(k+1) for k in range(min(int(vl[1]),int(lay[1])),max(int(vl[1]),int(lay[1])))],'contact_jog_layer':'M4' if boundary_M4 or boundary_M5 else 'M2'})
 if netfail:counts['V_net_fail']+=1
 # Actual horizontal span must include assigned Vcolumns: extension may conflict!
 if leads:
  aa=min([a]+[z['M3_x_nm'] for z in leads]);bb=max([b]+[z['M3_x_nm'] for z in leads])
  if collision(aa-48,bb+48,HO[lay,hy],n):
   fail.append({'net_index':n,'reason':'H_EXTENSION_COLLIDES_AFTER_M3_OWNERSHIP','original_interval_nm':[a,b],'extended_interval_nm':[aa,bb],'H_trunk':[lay,hy]});counts['H_extension_fail']+=1;netfail=True
  HO[lay,hy][-1]=(aa-48,bb+48,n)
 else:aa,bb=a,b
 vert=sum(z['vertical_nm'][1]-z['vertical_nm'][0] for z in leads)/1000
 jog=sum(z['M2_local_jog_nm'] for z in leads)/1000;hl=(bb-aa)/1000
 jogcap=sum(z['M2_local_jog_nm']/1000*(.178475 if z['contact_jog_layer']=='M4' else .174942) for z in leads)
 cwire=sum((z['vertical_nm'][1]-z['vertical_nm'][0])/1000*(.155554 if z['vertical_layer']=='M3' else .164264) for z in leads)+jogcap+hl*(.178475 if lay=='M4' else .174942)
 caps={co:{'native_plus_external_fF':v['native_plus_external_fF'],'assigned_wire_fF':cwire,'total_excluding_unknown_via_fringe_fF':v['native_plus_external_fF']+cwire,'native_max_fF':r['native_max_cap_fF'].get(co),'assigned_contact_complete':not netfail} for co,v in r['original_corner_cap'].items()}
 for co,c in caps.items():
  if c['native_max_fF'] is not None and c['total_excluding_unknown_via_fringe_fF']>c['native_max_fF']:counts['cap_violation_'+co]+=1
 geometry.append({'net_index':n,'driver':r['driver'],'local':r['local'],'H_layer':lay,'H_y_nm':hy,'H_x_nm':[aa,bb],'region':reg,'leads':leads,'native_contacts':len(pts),'assigned_contacts':len(leads),'base_via_count':sum(z['base_vias'] for z in leads),'length_um':{'H':hl,'M3':vert,'local_M2_jog':jog},'corner_cap':caps,'construction_conflict':netfail})
counts['nets_total']=len(records);counts['H_assigned']=len(geometry);counts['contacts_total']=sum(len(r['points_nm']) for r in records);counts['contacts_assigned']=sum(len(r['leads']) for r in geometry);counts['short_local_nets']=sum(r['local'] for r in records)
out={'status':'FAIL' if fail else 'GEOMETRIC_ASSIGNMENT_ONLY_OPEN_ACCESS_DRC','counts':dict(counts),'failures':fail,'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.iterdir()},'clock_reserved_rays':len(reserved),'source_cells':len(site),'maxrss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'open':['M1pin-nativelegalviaaccess','localM2jogownership','viaCut-stagger-and-signal-crossing-DRC','boundary-layertermination','actualPGconnectivity','clocknetwork-phases-STA','sourceDcalc-and-viafringingcap','sourceDensityReview','M5-extra-via-local-M4-jog-ownership','all-new-native-via-fringing-cap','native-waveform-setup-hold-upstream-clock-root-budget']}
json.dump(out,open(O/'verdict.json','w'),indent=2)
with gzip.open(O/'per_net_geometry.json.gz','wt') as f:json.dump(geometry,f)
print(json.dumps({'status':out['status'],'counts':out['counts'],'maxrss_kb':out['maxrss_kb'],'first_failures':fail[:5]},indent=2))
