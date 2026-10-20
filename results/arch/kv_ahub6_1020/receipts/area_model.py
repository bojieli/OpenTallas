import sys,json,gzip,re,hashlib
from pathlib import Path
sys.path.insert(0,'/work')
import native_census as N
import textbook_lint as T
libs=Path('/work/actual_liberties.txt').read_text().splitlines();areas={}
for path in libs:
 p=Path(path);raw=p.read_bytes();text=(gzip.decompress(raw) if p.suffix=='.gz' else raw).decode()
 text=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
 for typ,_,body in N.groups(text):
  if typ=='library':
   for kind,name,cell in N.groups(body):
    if kind=='cell':
     am=re.search(r'\barea\s*:\s*([-+0-9.eE]+)',cell)
     area=am.group(1) if am else None
     if area is not None:areas[name]=float(re.match(r"[-+0-9.eE]+",area).group())
roles,_=N.liberty_roles(libs)
p=next(Path('/work/results/asap7').glob('*/base/1_2_yosys.v'))
g,_=T.flatten(T.parse_verilog(p.read_text()),'qkd_ahub_static_dw_g6_lp')
rec=json.loads(Path('/work/record.json').read_text());pfx={}
for r,data in rec['regions'].items():
 for n in data['children']:pfx[n]=r
 pfx['u_lpr_'+r]=r
for l in rec['landings']:
 pfx[f"u_lpl_{l['name']}_w"]=l['src_region'];pfx[f"u_lpl_{l['name']}_r"]=l['dst_region']
for n in ('u_io','u_core','u_recip'):pfx['u_lprc_'+n]='c'
for i in range(4):pfx['u_lprc_u_zh'+str(i)]='z'+str(i)
out={r:dict(cells=0,flops=0,area_um2=0) for r in list(rec['regions'])+['unnamed']};missing=set();tot=0
for master,name,pins in g.cells:
 r=next((r for n,r in pfx.items() if name.startswith(n) and name[len(n):len(n)+1] in ('.','/','[')),'unnamed')
 if master in ('ot_nhb_zh','ot_qkh_recip_leaf'):continue
 if master not in areas:missing.add(master);continue
 d=out[r];d['cells']+=1;d['flops']+=int(roles[master]['sequential']);d['area_um2']+=areas[master];tot+=areas[master]
for d in out.values():d['area_um2']=round(d['area_um2'],3)
assert not missing, 'unpriced actual masters: '+str(sorted(missing))
result=dict(netlist_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),std_area_um2=round(tot,3),regions=out,missing_masters=sorted(missing),scope='Mapped std cells only, before CTS/repair; unnamed logic not assigned region. Full stage fence fill required.')
Path('/work/area_model.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result,indent=1))
