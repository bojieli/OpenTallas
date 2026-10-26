#!/usr/bin/env python3
"""W0 physical repairs guided by actual CTS timing and viewed pin-cell bands."""
import json,pathlib,sys,subprocess
from build_a2f_parent_kits import sites
import die_port_bind as D
R=pathlib.Path(__file__).resolve().parents[2]
assert json.load(open('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock'))['owner']=='codex'
for key in sys.argv[1:] or ['header','payload']:
 s=json.load(open(R/f'tools/ref_tile/specs_s81vm_a2f_parent_0310/{key}.json'))
 rev='r3' if key=='header' else 'r2';s['name']=s['top']+'_native_0310_'+rev
 if key=='header':
  s['outline']['h']=32.4
  why='r1 tall empty86.4um CTS R296.7/spread81.5 TT-26.9; r2height21.6 CTS R240.4/spread51.4 TT+47.7 but N/S pin-cell depths8.57+10.17um exceed17.3umcore. Height32.4um leaves9.3um between pin-cell bands; width216um/RTL/staticedges unchanged.'
 else:
  s['outline']['h']=75.6
  s['pins']={'N':['i_data','ck','o_epoch'],'S':['o_data'],'W':['i_mask','o_mask','rst_n']}
  why='r1 CTS optimizer shows o_mask <- i_mask W-to-E1166.4um unregistered wire failing about820ps. Coface input/output masks on W (sameedge one register); move clock to N-centre to halve worst clock distance, epoch at N-centre. Height75.6um accommodates425W-facepins. Data still N/S, rootcount/RTL/staticcalendar unchanged.'
 s['structural_change']=why;s['slot_change_request']['why']=why+' Exact parent pin rebind required.'
 m=next(x for x in D.parse_modules((R/s['sources'][0]).read_text(),s['sources'][0]) if x.name==s['top']);e=m.env({});ww={n:m.width(n,e) for n in m.ports}
 w,h=s['outline']['w'],s['outline']['h'];pins=[];t=[]
 for f,names in s['pins'].items():
  b=[(n,i) for n in names for i in range(ww[n])];
  if key=='payload' and f=='W':b=[(n,i) for i in range(212) for n in ['i_mask','o_mask']]+[('rst_n',0)]
  layer='M5' if f in 'NS' else'M4';ss=sites(w if f in'NS'else h,layer)
  central=[x for x in b if x[0] in ('ck','o_epoch')];b=[x for x in b if x[0] not in ('ck','o_epoch')];b[len(b)//2:len(b)//2]=central
  assert len(b)<=len(ss),(key,f,len(b),len(ss))
  for j,(n,i) in enumerate(b):
   q=ss[int((j+.5)*len(ss)/len(b))];x,y=(q,h if f=='N'else 0) if f in'NS'else(w if f=='E'else 0,q)
   p=n if ww[n]==1 else f'{n}[{i}]';sz='.024 .192' if layer=='M5'else'.192 .024'
   pins.append(dict(port=p,face=f,layer=layer,x_um=x,y_um=y));t.append(f'place_pin -pin_name {{{p}}} -layer {layer} -location {{{x} {y}}} -pin_size {{{sz}}} -force_to_die_boundary')
 assert len(pins)==sum(ww.values())
 d=R/f'physical/s81_vm_a2f_parent_0310/{key}_{rev}';d.mkdir(exist_ok=True)
 pp=d/(s['top']+'.tcl');pp.write_text('\n'.join(t)+'\n');old=s['io_tcl'];s['io_tcl']=str(pp.relative_to(R))
 (d/(s['top']+'.pins.json')).write_text(json.dumps(dict(master=s['top'],outline_um=[w,h],pins=pins),indent=1)+'\n')
 s['job']['extra_paths']=[s['io_tcl'] if p==old else p for p in s['job']['extra_paths']];s['job']['tag']='repack'+rev[1:]
 p=R/f'tools/ref_tile/specs_s81vm_a2f_parent_0310/{key}_{rev}.json';p.write_text(json.dumps(s,indent=1)+'\n')
 subprocess.run(['python3','tools/ref_tile/ref_tile.py','gen',str(p)],cwd=R,check=True)
