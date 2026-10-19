import json, hashlib, subprocess
from pathlib import Path
base=Path('/home/ubuntu/artifacts/kv-d2d-sideband-model-1019')
src=(base/'census.py').read_text().split('    rows=[]')[0]+'    return locals()\n'
ns={};exec(src,ns);a=ns['census'](base/'input/current_sfo_mapped.v.gz')
cells,drivers=a['cells'],a['drivers']
def walk(net,depth=0):
 d=drivers.get(net)
 if not d:return dict(net=net,kind='undriven')
 n,t,pn,j=d
 if n=='PORT':return dict(net=net,port=t)
 t,p=cells[n];r=dict(net=net,cell=n,master=t,pins=p)
 if depth<12:
  ins={k:vs for k,vs in p.items() if k not in ['QN','Q','Y','Z','H','L','CLK','SETN']}
  r['ancestors']={k:[walk(x,depth+1) for x in vs] for k,vs in ins.items()}
 return r
names=['\\u_ot_pr_core.u_core.u_reset_regions.g_fam.fam_all[17]','\\u_ot_pr_core.u_core.u_reset_regions.g_fam.fam_all[23]','\\u_ot_pr_core.u_core.u_reset_regions.g_fam.fam_all[83]','\\u_ot_pr_core.u_core.u_reset_regions.g_fam.fam_all[7]','\\u_ot_pr_core.u_core.u_reset_regions.g_fam.fam_all[8]','\\u_ot_pr_core.u_core.u_reset_regions.g_fam.fam_all[9]']
j=dict(status='SOURCE_ANCESTRY_ONLY',source_sha256=hashlib.sha256(a['s'].encode()).hexdigest(),ancestry=[walk(x) for x in names])
Path(__file__).with_name('reset_ancestry.json').write_text(json.dumps(j,indent=2)+'\n')
