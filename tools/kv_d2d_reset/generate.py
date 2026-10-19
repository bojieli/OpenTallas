#!/usr/bin/env python3
"""Frozen NTX3/PR1/.16 mapped-source reset partition; no clock/data edge changes."""
import argparse,copy,hashlib,json,re
from pathlib import Path
SUPPORTED_SHA={'qkd_d2d_static': '16d87dc783f74351fc1f7770ea667a6b6d51f170e8efb0645d826837e17f7571', 'qkd_d2d_static_ovl': '35956044d90fe26c3508e48d1112d7caec146a3fd8a8104867b42a800ced804c'}
CELL=re.compile(r'^  (\w+) (\\[^\s]+|\w+)\s*\(\n(.*?)^  \);',re.M|re.S)
PIN=re.compile(r'\.(\w+)\((.*?)\)',re.S)
def cells(t):
 out=[]
 for m in CELL.finditer(t):
  out.append(dict(master=m[1],name=m[2],pins={p:n.strip() for p,n in PIN.findall(m[3])},start=m.start(),end=m.end()))
 return out
def render(c):
 return '  '+c['master']+' '+c['name']+' (\n'+',\n'.join('    .'+p+'('+n+' )' for p,n in c['pins'].items())+'\n  );'
def generate(source,top,limit=24):
 t=Path(source).read_text(); assert hashlib.sha256(t.encode()).hexdigest()==SUPPORTED_SHA[top], 'unsupported source/profile'; cs=cells(t); byout={}; loads={}
 for c in cs:
  for p,n in c['pins'].items():
   if p in ('Y','QN','Q','RDATA'): byout[n]=c
   elif p not in ('VDD','VSS'): loads.setdefault(n,[]).append((c,p))
 roots=sorted(n for n in loads if 'u_reset_regions.g_p[1].q[' in n and len(loads[n])>limit)
 replacements={}; remove=set(); added=[]; proof=[]
 for ix,n in enumerate(roots):
  inv=byout[n]; assert inv['master']=='INVx1_ASAP7_75t_R'
  ff=byout[inv['pins']['A']]; assert ff['master']=='DFFHQNx1_ASAP7_75t_R'
  assert len(loads[inv['pins']['A']])==1
  sinks=loads[n]; groups=[sinks[k:k+limit] for k in range(0,len(sinks),limit)]
  d=ff['pins']['D']; clk=ff['pins']['CLK']; remove.update((inv['start'],ff['start']))
  for k,g in enumerate(groups):
   q=f'kv_reset_copy_{ix}_{k}'
   added.append(f'  (* keep = "true", dont_touch = "true" *) reg {q};\n  (* keep = "true", dont_touch = "true" *) always @(posedge {clk}) {q} <= {d} ;')
   for c,p in g:
    replacements.setdefault(c['start'],copy.deepcopy(c))['pins'][p]=q
  proof.append(dict(state_relation='old QN = ~copy; original INV.Y = copy',initial_state='uninitialized; first common clock samples identical D; existing clocked cold-reset contract required',root=n,old_ff=ff['name'],old_inv=inv['name'],D=d,CLK=clk,old_loads=len(sinks),copies=len(groups),max_load=max(map(len,groups)),groups=[[[c['name'],p] for c,p in g] for g in groups]))
 chunks=[]; last=0
 for c in cs:
  chunks.append(t[last:c['start']]); chunks.append('' if c['start'] in remove else '  (* keep = 1 *)\n'+render(replacements[c['start']]) if c['start'] in replacements else '  (* keep = 1 *)\n'+t[c['start']:c['end']]); last=c['end']
 chunks.append(t[last:]); out=''.join(chunks)
 out=out.replace('module '+top+'(', 'module '+top+'_reset24 #(parameter integer NTX=3, PR=1, SAFE_RC=1, parameter [31:0] TXDP=32\'h03030416) (',1)
 out=out.replace('endmodule', "generate if (NTX!=3 || PR!=1 || SAFE_RC!=1 || TXDP!=32'h03030416) begin : g_bad_profile\n invalid_kv_d2d_reset24_profile use_supported_frozen_profile();\n end endgenerate\nendmodule",1)
 out=out.replace('endmodule','\n'.join(added)+'\nendmodule',1)
 # All clone inputs are also priced; exact original load counts include reset and ordinary data.
 extra={}
 for p in proof: extra[p['D']]=extra.get(p['D'],0)+p['copies']-1
 dloads={n:len(loads[n])+v for n,v in extra.items()}
 assert max(dloads.values(),default=0)<=32,dloads
 return out,dict(profile=dict(NTX=3,PR=1,SAFE_RC=1,TXDP='0x03030416'),source_sha256=hashlib.sha256(t.encode()).hexdigest(),top=top,limit=limit,roots=proof,shared_D_actual_loads=dloads,added_flops=sum(p['copies']-1 for p in proof),unchanged_other_cells=len(cs)-2*len(proof),clock_edges_added=0,reset_edges_added=0)
def main():
 a=argparse.ArgumentParser();a.add_argument('source');a.add_argument('top',choices=['qkd_d2d_static','qkd_d2d_static_ovl']);a.add_argument('output');x=a.parse_args();out,p=generate(x.source,x.top);Path(x.output).write_text(out);Path(x.output+'.json').write_text(json.dumps(p,indent=2)+'\n')
if __name__=='__main__':main()
