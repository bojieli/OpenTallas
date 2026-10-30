import json,re,bisect
from pathlib import Path
P=Path(__file__).parent
L=P.parent/'hb_model'
def table(text,kind):
 b=re.search(kind+r'\s*\([^)]*\)\s*\{(.*?)\n\s*\}',text,re.S)[1]
 ax=[[float(x) for x in re.search(r'index_'+str(i)+r'\s*\("([^"]+)"',b)[1].split(',')] for i in [1,2]]
 vs=[[float(x) for x in r.split(',')] for r in re.findall(r'"([^"\n]+)"',b[b.index('values'):])]
 return ax,vs
def interp(tab,s,c):
 (x,y),v=tab;i=max(0,min(len(x)-2,bisect.bisect_right(x,s)-1));j=max(0,min(len(y)-2,bisect.bisect_right(y,c)-1));a=(s-x[i])/(x[i+1]-x[i]);b=(c-y[j])/(y[j+1]-y[j]);return (1-a)*(1-b)*v[i][j]+(1-a)*b*v[i][j+1]+a*(1-b)*v[i+1][j]+a*b*v[i+1][j+1]
reports={}
for corner in ['TT','FF']:
 tabs={n:{k:table((L/f'{n}_{corner}.txt').read_text(),k) for k in ['cell_rise','cell_fall']} for n in ['BUFx2_ASAP7_75t_R','HB4xp67_ASAP7_75t_R']}
 rows=[r.split('\t') for r in (P/f'chain_{corner}.tsv').read_text().splitlines()[1:]];groups={}
 for r in rows:groups.setdefault(int(r[0]),{})[int(r[1])]=[r[2]]+list(map(float,r[3:]))
 vals=[]
 for i,g in sorted(groups.items()):
  out={'chain':i,'first':g[0][0],'old_cells':[]}
  for trans,skind in [('rise',0),('fall',1)]:
   if corner=='TT':capidx,slewi=2,5+skind
   else:capidx,slewi=1,7+skind
   old=sum(interp(tabs['BUFx2_ASAP7_75t_R']['cell_'+trans],g[j][slewi],g[j][capidx]) for j in [0,1,2])
   # Baseline qualification uses actual first-input slew and existing last-output load; post-edit wires remain unmeasured.
   new=interp(tabs['HB4xp67_ASAP7_75t_R']['cell_'+trans],g[0][slewi],g[2][capidx])
   out[trans]={'old_cell_sum_ps':round(old,5),'new_cell_ps':round(new,5),'cell_delta_ps':round(new-old,5),'first_input_slew_ps':g[0][slewi],'old_last_output_cap_ff':g[2][capidx]}
  vals.append(out)
 reports[corner]={'chains':vals,'min_cell_delta_ps':min(x[t]['cell_delta_ps'] for x in vals for t in ['rise','fall']),'max_cell_delta_ps':max(x[t]['cell_delta_ps'] for x in vals for t in ['rise','fall'])}
result={'schema':'opentallas.kv.hold_collapse_nldm_certificate.v1','status':'CELL_ONLY_ESTIMATE_WIRES_NOT_QUALIFIED','basis':'Actual routedB50 TT/FF input slews and output net total min/max capacitance from OpenSTA; actual RVT Liberty bilinear tables (extrapolation at edge as usual). Each original BUF gets its own actual slew/load. New HB4 uses original first-input slew and final-output load.','scope':'This is not timing closure: new input/output wire geometry, source-drive load change, old interior wire delay and new output slew/capture setup still need prototype.','corners':reports}
(P/'nldm_certificate.json').write_text(json.dumps(result,indent=1)+'\n')
print({k:{q:v[q] for q in ['min_cell_delta_ps','max_cell_delta_ps']} for k,v in reports.items()})
