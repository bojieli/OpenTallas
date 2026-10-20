import json,re,sys,importlib.util,hashlib,collections
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);sp=importlib.util.spec_from_file_location('qfull',root/'tools/qwen_cluster/qc_full_kit.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
spec=json.loads((root/'physical/ref_tile/qfd_c_b16_full/spec.json').read_text());txt=(root/'rtl/physical/qcluster/qfd_c_b16_full.sv').read_text().split('module qfd_c_b16_fullb_fabric')[0]
P={x['inst']:dict(x=x['at'][0],y=x['at'][1],kind=Path(x['view']).name,orient=x.get('orient','R0')) for x in spec['children']}
for mod in ['qfd_c_land_w','qfd_c_land_r1h']:m.LEFS[mod]=(0,0,{})
m.DIR_OUT.add('bank');drv,sinks,resolve,widths=m.netlist(txt)
W=spec['outline']['w'];H=spec['outline']['h'];ranges=spec['pin_ranges'];faces=spec['pins'];env={'W':W,'H':H}
by=collections.defaultdict(list)
for dst,b in sinks:by[resolve(b)[1]].append(dst)
def fixed(ep):
 if ep and ep[0] in P:return m.pin_at(P,*ep)
 return None
def clip(poly,a,b,c):
 ans=[]
 for v,z in zip(poly,poly[1:]+poly[:1]):
  fv=a*v[0]+b*v[1]-c;fz=a*z[0]+b*z[1]-c
  if fv<=1e-7:ans.append(v)
  if (fv<0)!=(fz<0):
   t=fv/(fv-fz);ans.append((v[0]+t*(z[0]-v[0]),v[1]+t*(z[1]-v[1])))
 return ans
port_terms=collections.defaultdict(list)
for port in ranges:
 if port.startswith('bco') or port in ['rs','rs_o']:
  for pb in range(widths.get(port,1)):
   ds,_=resolve((port,pb))
   if ds:port_terms[ds].append(m.port_xy(env,ranges,faces,port,pb,widths[port]))
rows=[]
for inst in re.finditer(r'qfd_c_land_w\s+#\(\.W\((\d+)\).*?\)\s+(u_\w+)_w\s*\(',txt):
 width=int(inst[1]);base='u_fab.'+inst[2];winst=base+'_w';rinst=base+'_r';half=width//2
 inputep={dst[2]:resolve(b) for dst,b in sinks if dst[0]==winst and dst[1]=='i'}
 outputep={k:b for b,d in drv.items() for k in [d[2]] if d[0]==rinst and d[1]=='o'}
 for hi in [0,1]:
  terms=[];unknown=[]
  for k in range(half):
   g=k+hi*half;ds,b=inputep.get(g,(None,None));xy=fixed(ds)
   if xy is None and b and b[0] in ranges:xy=m.port_xy(env,ranges,faces,b[0],b[1],widths[b[0]])
   if xy is None:unknown.append({'role':'input','bit':g,'driver':ds,'net':b})
   else:terms.append(('i',k,xy))
   b=outputep.get(g);found=False
   for dst in by.get(b,[]):
    xy=fixed(dst)
    if xy is not None:terms.append(('o',k,xy));found=True
    elif dst[0]!=winst:unknown.append({'role':'output','bit':g,'sink':dst,'net':b})
   for xy in port_terms[(rinst,'o',g)]:terms.append(('o',k,xy));found=True
   if not found:unknown.append({'role':'output_no_fixed_sink','bit':g,'net':b})
  choices=[]
  for orient in ['R0','MY','MX','R180']:
   ulo,vlo=-1e20,-1e20;uhi,vhi=1e20,1e20
   for role,k,(sx,sy) in terms:
    px=0 if role=='i' else 43.2;py=1+49.84*(k+.5)/half
    if orient in ['MY','R180']:px=43.2-px
    if orient in ['MX','R180']:py=51.84-py
    su=sx+sy-px-py;sv=sx-sy-px+py;ulo=max(ulo,su-405);uhi=min(uhi,su+405);vlo=max(vlo,sv-405);vhi=min(vhi,sv+405)
   poly=[(0,0),(W-43.2,0),(W-43.2,H-51.84),(0,H-51.84)]
   for a,b,c in [(1,1,uhi),(-1,-1,-ulo),(1,-1,vhi),(-1,1,-vlo)]:poly=clip(poly,a,b,c) if poly else[]
   choices.append({'orientation':orient,'necessary_polygon_xy':poly,'fixed_intersection_nonempty':bool(poly),'min_reach_uv_necessary_um':405+max(ulo-uhi,vlo-vhi)/2})
  rows.append({'ring':inst[2],'half':hi,'width':half,'fixed_terms':len(terms),'unknown_endpoint_count':len(unknown),'unknown_examples':unknown[:5],'choices':choices,'status':'UNQUALIFIED_JOINT_ENDPOINTS' if unknown else('FIXED_TERM_PINPLAN_INTERSECTION' if any(x['fixed_intersection_nonempty']for x in choices)else'FIXED_TERM_405_INFEASIBLE')})
result={'scope':'Analytical pin-plan necessary bounds on immutable original diagnosticA0 parent; actual leafpins/PG/placementcollision/roots/newA0 binding NOT qualified. No bank multicycle exception. Unknown endpoint edges are not admitted.','source_sha256':{f:hashlib.sha256((root/f).read_bytes()).hexdigest()for f in ['tools/qwen_cluster/qc_full_kit.py','rtl/physical/qcluster/qfd_c_b16_full.sv','physical/ref_tile/qfd_c_b16_full/spec.json']},'half_macros':len(rows),'status_counts':dict(collections.Counter(x['status']for x in rows)),'rows':rows};out.write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items()if k not in ['rows','source_sha256']})
