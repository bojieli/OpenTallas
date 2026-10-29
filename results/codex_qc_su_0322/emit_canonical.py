"""Opt-in candidate: two exact native SU wiring masters; no leaf logic/parameter changes."""
import json,pathlib,re
import canonical_graph as C
D=pathlib.Path(__file__).resolve().parent;O=D/'canonical';O.mkdir(exist_ok=True)
def atom(x):
 n,b=x
 if n=='CONST':return f"1'b{b}"
 if n=='CLK':return 'clk'
 if n=='RST':return 'rst_n'
 return f"{dict(I='c_i',O='c_o').get(n,n)}[{b}]"
def vector(v):return atom(v[0]) if len(v)==1 else '{'+', '.join(atom(q) for q in reversed(v))+'}'
records=[]
for h,masters in C.census()['groups'].items():
 z=C.canonical(masters[0]);name='qfd_qc_su_native_l0' if z['outputs']==302 else 'qfd_qc_su_native_lx'
 nets={}
 for c in z['cells']:
  for v in c['ports'].values():
   for n,b in v:
    if n not in ['I','O','CLK','RST','CONST']:nets[n]=max(nets.get(n,0),b)
 lines=['// Candidate exact native SU wiring: unchanged child modules/parameters/registers; zero added cycles.','`default_nettype none',f'module {name}(input wire clk, input wire rst_n, input wire [{z["inputs"]-1}:0] c_i, output wire [{z["outputs"]-1}:0] c_o);']
 lines += [f'  wire [{b}:0] {n};' for n,b in sorted(nets.items())]
 for c in z['cells']:
  lines.append('    '+c['module']+(' '+c['params'] if c['params'] else '')+' u_u_'+c['role']+'0 (')
  lines.append(',\n'.join('        .'+p+'('+vector(v)+')' for p,v in sorted(c['ports'].items())))
  lines.append('    );')
 lines+=['endmodule','`default_nettype wire',''];(O/(name+'.sv')).write_text('\n'.join(lines))
 records.append(dict(module=name,inputs=z['inputs'],outputs=z['outputs'],graph_sha256=h,actual_native_masters=masters,unchanged_leaf_params={c['role']:c['params'] for c in z['cells']},added_cycles=0))
(O/'mapping.json').write_text(json.dumps(dict(status='CANDIDATE ONLY; boundary miter/current profile and physical gates required',canonical_masters=records),indent=1)+'\n');print(json.dumps(records,indent=1))
