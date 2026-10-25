import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]); cases=json.load(open(p/'master_id_binding_cases.json'));stub=[];seen=set();tb=['module tb;integer cyc,checks=0;']
for i,c in enumerate(cases):
 top=c['top']
 if top not in seen:
  seen.add(top);decl=[];body=[]
  for name,(d,w) in c['top_ports'].items():
   decl.append(f'{d} wire [{w-1}:0] {name}')
   if d=='output':
    h=hashlib.sha256(name.encode()).hexdigest();value=int((h*((w+255)//256)),16)&((1<<w)-1)
    body.append(f"assign {name}={w}'h{value:x};")
  stub.append('module '+top+'('+','.join(decl)+');\n'+'\n'.join(body)+'\nendmodule')
 con=[];clause=[];drive=[]
 for j,(b,(d,w)) in enumerate(sorted(c['old_buses'].items())):
  sig=f'b_{i}_{j}';tb.append(f"{'reg' if d=='input' else 'wire'} [{w-1}:0] {sig};");con.append(f'.{b}({sig})')
  if d=='input':
   for k in range((w+31)//32):
    width=min(32,w-32*k);drive.append(f'{sig}[{32*k}+:{width}]=$random;')
  canonical=c['port_map'][b]
  clause.append(f'if({sig} !== d{i}.u_shared.u_core.{canonical})$fatal(1,"binding mismatch {i}.{b}");checks=checks+1;')
 tb.append(c['adapter']+f' d{i}('+','.join(con)+');')
 clause.append(f"if(d{i}.u_shared.u_core.{c['id_port']} !== {c['id_width']}'d{c['id_value']})$fatal(1,\"replica ID mismatch {i}\");checks=checks+1;")
 for b,value in c['inherited_ties'].items():clause.append(f"if(d{i}.u_shared.u_core.{b} !== {c['top_ports'][b][1]}'d{value})$fatal(1,\"terminal specialization mismatch\");checks=checks+1;")
 c['drive']=drive;c['check']=clause
tb.append('initial begin for(cyc=0;cyc<64;cyc=cyc+1)begin')
for c in cases:tb.extend(c['drive'])
tb.append('#1;')
for c in cases:tb.extend(c['check'])
tb.append('end $display("MASTER_ID_BINDING_PASS replicas=48 checks=%0d",checks);$finish;end endmodule')
(p/'binding_stubs.sv').write_text('\n'.join(stub)+'\n')
(p/'binding_tb.sv').write_text('\n'.join(tb)+'\n')
s=(p/'master_id_parent_adapters.sv').read_text();a=cases[0];old=f".{a['id_port']}({a['id_width']}'d{a['id_value']})";new=f".{a['id_port']}({a['id_width']}'d{a['id_value']^1})";assert old in s
(p/'master_id_parent_adapters_mutant.sv').write_text(s.replace(old,new,1))
