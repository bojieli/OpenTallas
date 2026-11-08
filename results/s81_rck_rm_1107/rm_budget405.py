import csv,re,json
from pathlib import Path
P=Path('/tmp/codex-rck-redesign-1107');r=list(csv.DictReader(open(P/'cts_cells.tsv'),delimiter='\t'))
def bits(tok):
 d={}
 for x in r:
  if tok in x['name'] and x['master'].startswith('DFF'):
   n=re.search(r'\[(\d+)\]',x['name'][x['name'].index(tok)+len(tok):]);
   if n:d[int(n[1])]=(float(x['x']),float(x['y']))
 return {k:v for k,v in d.items() if k<512}
s=bits('u_face_q_d.q');t=bits('u_bout_coll_o0/q');assert len(s)==len(t)==512,(len(s),len(t))
out=[]
for b in range(512):
 sl=b//8;c=(1837+18*(sl%8),107+18*(sl//8));a=s[b];z=t[b]
 # ±5um any-site slice corner margin, then split into equal registered legs.
 di=abs(c[0]-a[0])+abs(c[1]-a[1])+18
 do=abs(c[0]-z[0])+abs(c[1]-z[1])+18
 out.append({'bit':b,'actual_face_q_d':a,'slice_center':c,'actual_bout':z,'input_max_each_of2':di/2,'output_max_each_of3':do/3})
res={'core_um':[1828,98,1972,242],'slice_um':[18,18],'per_slice_bits':8,'source':'actual u_dec.u_face_q_d.q[bit], NOT intrinsic u_out.q_d','dest':'actual u_bout_coll_o0/q[bit]','anysite_margin_L1_um':18,'input_max_registered_hop':max(x['input_max_each_of2']for x in out),'output_max_registered_hop':max(x['output_max_each_of3']for x in out),'input_fail_bits':sum(x['input_max_each_of2']>405for x in out),'output_fail_bits':sum(x['output_max_each_of3']>405for x in out),'note':'planning only, straight-line L1 sites. Equal subdivisions need coherent placement/clock constraint and noobstruction. Exact cell-area/PG/routing/control budgets remainHOLD. No placedimage/kit.','bits':out}
(P/'rm_405_perbit_budget.json').write_text(json.dumps(res,indent=2)+'\n');print({k:v for k,v in res.items()if k!='bits'})
