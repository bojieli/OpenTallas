#!/usr/bin/env python3
"""Zero-cycle private output FF for scalar OR/reduction cones of same-reset FFs.
The retained state and its internal consumers are untouched. New Q is f(Qold),
new D is f(Dold), and new asynchronous reset is f(old reset constants).
Only plain $adff sources and OR/boolean reductions are accepted, fail closed.
"""
import argparse,copy,json,re
from pathlib import Path
ONE=format(1,'032b')

def retime(j,top,names,mutant=False):
 j=copy.deepcopy(j);m=j['modules'][top];cells=m['cells'];ports=m['ports'];nets=m['netnames'];nid=max(b for c in cells.values() for bs in c['connections'].values() for b in bs if isinstance(b,int));report=[]
 def new():
  nonlocal nid
  nid+=1;return nid
 for ordinal,pn in enumerate(names):
  port=ports[pn]
  if port['direction']!='output' or len(port['bits'])!=1:raise ValueError('only scalar outputs')
  drv={b:(cn,c,p,k) for cn,c in cells.items() for p,bs in c['connections'].items() if c['port_directions'][p]=='output' for k,b in enumerate(bs)};root=port['bits'][0];memo={};ctrl=None;src=[];clone=[]
  def lift(b):
   nonlocal ctrl
   if isinstance(b,str):
    if b not in ('0','1'):raise ValueError('undef constant in cone')
    return b,int(b)
   if b in memo:return memo[b]
   if b not in drv:raise ValueError('combinational cone reaches input or undriven bit')
   cn,c,op,idx=drv[b];t=c['type']
   if t=='$adff' and op=='Q':
    key=(tuple(c['connections']['CLK']),tuple(c['connections']['ARST']),c['parameters']['CLK_POLARITY'],c['parameters']['ARST_POLARITY'])
    if ctrl is None:ctrl=key
    if key!=ctrl:raise ValueError('mixed clock/reset control')
    width=len(c['connections']['Q']);rv=str(c['parameters']['ARST_VALUE']).rjust(width,'0')[-width:][::-1][idx]
    if rv not in '01':raise ValueError('undef reset value')
    src.append((cn,idx));memo[b]=(c['connections']['D'][idx],int(rv));return memo[b]
   if t not in ('$or','$logic_or','$reduce_or','$reduce_bool') or op!='Y' or len(c['connections']['Y'])!=1:raise ValueError('unsupported cone cell '+t)
   if t=='$or' and (len(c['connections']['A'])!=1 or len(c['connections']['B'])!=1):raise ValueError('bitwise OR must be scalar')
   nc=copy.deepcopy(c);vals={}
   for ip,bs in c['connections'].items():
    if c['port_directions'][ip]!='input':continue
    z=[lift(x) for x in bs];nc['connections'][ip]=[x[0] for x in z];vals[ip]=[x[1] for x in z]
   rv=int(any(vals['A']) or any(vals.get('B',[])))
   q=new();nc['connections']['Y']=[q];nc['attributes']={'src':'retime_status scalar OR cone'};name=f'hrstatus_{pn}_cone_{len(clone)}';cells[name]=nc;clone.append(name);memo[b]=(q,rv);return memo[b]
  d,rv=lift(root)
  if ctrl is None:raise ValueError('output has no registered source')
  if mutant and ordinal==0:
   z=new();cells[f'hrstatus_{pn}_mut']={'hide_name':0,'type':'$not','parameters':{'A_SIGNED':ONE[:-1]+'0','A_WIDTH':ONE,'Y_WIDTH':ONE},'attributes':{},'port_directions':{'A':'input','Y':'output'},'connections':{'A':[d],'Y':[z]}};d=z
  q=new();clk,arst,cp,ap=ctrl
  cells[f'hrstatus_{pn}']={'hide_name':0,'type':'$adff','parameters':{'WIDTH':ONE,'CLK_POLARITY':cp,'ARST_POLARITY':ap,'ARST_VALUE':str(rv)},'attributes':{'keep':ONE,'src':'retime_status zero-cycle private status flop'},'port_directions':{'CLK':'input','ARST':'input','D':'input','Q':'output'},'connections':{'CLK':list(clk),'ARST':list(arst),'D':[d],'Q':[q]}}
  port['bits']=[q];nets[pn]['bits']=[q];nets[pn].setdefault('attributes',{})['keep']=ONE
  report.append({'port':pn,'old_bit':root,'new_bit':q,'source_flops':src,'cloned_cells':clone,'reset_value':rv,'added_ff':1,'added_cycles':0})
 return j,{'top':top,'outputs':report,'added_ff':len(report),'added_cycles':0,'mutant':mutant}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('pre');p.add_argument('post');p.add_argument('report');p.add_argument('--top',required=True);p.add_argument('--outputs',nargs='+',required=True);p.add_argument('--mutant',action='store_true');a=p.parse_args();j,r=retime(json.load(open(a.pre)),a.top,a.outputs,a.mutant);Path(a.post).write_text(json.dumps(j));Path(a.report).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r))
