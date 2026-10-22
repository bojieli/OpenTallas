from pathlib import Path
import json,re,hashlib,collections
import textbook_lint as T
raw=Path('original.v').read_bytes();assert hashlib.sha256(raw).hexdigest()=='5cefd6970b66c353c978540880889c918d95de523261c865ff251db7b74872a0'
g,top=T.flatten(T.parse_verilog(raw.decode()),None);A=T.build(g,None);clk,_=T.clock_nets(g,A);order=T.topo(g,A,clk);q={};lev={};pred={};scale=T.THRESHOLDS['depth_scale']
for c,kind in enumerate(A['kind']):
 if kind in ['ff','macro']:
  for n in T._out_nets(g,A,c):q[n]=(0.0,g.cells[c][1]);lev[n]=0
for c in order:
 if A['kind'][c] not in ['comb','buf']:continue
 ins=[n for n in T._in_nets(g,A,c,False)if n in q]
 if not ins:continue
 best=max(ins,key=lambda n:q[n][0]);depth,start=q[best];weight=T.cell_w(g.cells[c][0]);levels=max(lev[n]for n in ins)+(A['kind'][c]!='buf')
 for n in T._out_nets(g,A,c):q[n]=(depth+weight,start);lev[n]=levels;pred[n]=(best,c)
alias=collections.defaultdict(list)
for name,n in g.net_id.items():alias[g.find(n)].append(name)
def trace(n):
 out=[];seen=set()
 while n in pred:
  assert n not in seen;seen.add(n);up,c=pred[n];out.append(dict(instance=g.cells[c][1],master=g.cells[c][0],weight_ps=T.cell_w(g.cells[c][0])*scale));n=up
 return list(reversed(out))
ends=[];stages={};outputs=[]
for c,kind in enumerate(A['kind']):
 if kind not in ['ff','macro','icg']:continue
 outputs_of_cell=[a for n in T._out_nets(g,A,c)for a in alias[n]]
 tags=sorted(set(a.split('[')[0]for a in outputs_of_cell if a.startswith('sp_')))
 for pn,bs in g.cells[c][2].items():
  if A['pin_dir'][c].get(pn)!='in' or pn in T.SEQ_CLK_PINS:continue
  for n in bs:
   if n not in q:continue
   row=dict(estimate_ps=round(q[n][0]*scale,1),levels=lev[n],start=q[n][1],endpoint=g.cells[c][1]+'/'+pn,source_aliases=outputs_of_cell[:12],cone=trace(n))
   ends.append(row)
   for tag in tags:
    if tag not in stages or row['estimate_ps']>stages[tag]['estimate_ps']:stages[tag]=row
for name,(d,n)in g.ports.items():
 if d=='output' and name.startswith('w_addr[')and n in q:outputs.append(dict(estimate_ps=round(q[n][0]*scale,1),levels=lev[n],endpoint=name,start=q[n][1],cone=trace(n)))
ends.sort(key=lambda r:r['estimate_ps'],reverse=True);outputs.sort(key=lambda r:r['estimate_ps'],reverse=True)
r=dict(scope='unchanged textbook scalar mapped-cell estimate; no physical wire/load/slew or STA claim',mapped_sha256=hashlib.sha256(raw).hexdigest(),parser_sha256=hashlib.sha256(Path('textbook_lint.py').read_bytes()).hexdigest(),cells=len(g.cells),flops=A['kind'].count('ff'),macros=A['kind'].count('macro'),reg_to_reg_top=ends[:8],stages=stages,address_outputs=outputs)
Path('profile.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(worst=ends[0],stage_ps={k:v['estimate_ps']for k,v in stages.items()},address=outputs[0])))
