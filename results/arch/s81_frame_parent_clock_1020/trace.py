import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools'))
import die_port_bind as D
B=Path(__file__).parent;v=B.parent/'s81_mu7_slot_model_1020/inputs/mu6_die.v';nets,tin,tout,insts=D.parse_die(v,'dv_die')
byname={n:(m,p,c) for m,n,p,c in insts};edges={};sinks={}
for m,n,p,c in insts:
 for port,expr in c.items():
  bits=D.expr_bits(expr,nets)
  if bits is None:continue
  for i,bit in enumerate(reversed(bits)):
   sinks.setdefault(bit,[]).append(dict(instance=n,master=m,port=port,bit=i))
  if port in ['ck_o','Y','GCLK','ck_xc','ck_line','ck_v','ck_rt','xok']:
   for i,bit in enumerate(reversed(bits)):edges.setdefault(bit,[]).append((n,m,port,i))
def label(b):return b[0]+('['+str(b[1])+']' if nets.get(b[0],(1,0))[0]>1 else '')
def walk(bit):
 path=[];seen=set()
 while bit[0] not in tin:
  if bit in seen or len(edges.get(bit,[]))!=1:return dict(path=path,error='nonunique_or_absent_clock_source',net=label(bit),drivers=edges.get(bit,[]))
  seen.add(bit);n,m,p,i=edges[bit][0];node=dict(net=label(bit),instance=n,master=m,output_port=p,bit=i);path.append(node);c=byname[n][2]
  if p=='ck_o':inputport='ck';node['RTL_expected_sense']='negative_unate' if m.startswith('dsfd_dvrlyh_') else 'positive_unate'
  elif p=='Y':inputport='A';node['RTL_expected_sense']='positive_unate' if m.startswith('BUF') else 'UNKNOWN'
  elif p=='GCLK':
   inputport='CLK';node['RTL_expected_sense']='gated_positive_unate_needs_native_enablecheck';node['gate_controls']={k:v for k,v in c.items() if k not in ['CLK','GCLK']}
  elif p=='xok':
   inputport='xk';node['RTL_expected_sense']='positive_unate_from_source_u_xo_nonhalf_relay_NOT_NATIVEQUALIFIED'
  elif p.startswith('ck_'):
   inputport='clk' if 'clk' in c else None;node['RTL_expected_sense']='slice_native_forwarding_provenance_OWED'
  else:return dict(path=path,error='unresolved_source_contract')
  if inputport is None:return dict(path=path,error='unknown_clock_input')
  q=D.expr_bits(c[inputport],nets)
  if inputport=='xk':
   bit=list(reversed(q))[i]
  elif len(q)==1:bit=q[0]
  else:return dict(path=path,error='nonscalar_clock_root')
 return dict(path=path,root=label(bit),root_period_ps=900 if bit[0]=='ck_hbm' else 833.333)
rows=[]
for m,n,p,c in insts:
 if not n.startswith('u_f_') or 'xk' not in c:continue
 bits=D.expr_bits(c['xk'],nets);rows.append(dict(instance=n,master=m,connected_ports=sorted(c),xk=[dict(bit=i,net=label(b),upstream=walk(b)) for i,b in enumerate(reversed(bits))],xok_connected='xok' in c,xok_consumers='NONE: port absent from current bound instance' if 'xok' not in c else [[u for u in sinks.get(b,[]) if not(u['instance']==n and u['port']=='xok')] for b in reversed(D.expr_bits(c['xok'],nets))]))
out=dict(source='1b7b9d5d772008559e1b2467bc12de0fc067e2bd',parent_bind_die_sha256=hashlib.sha256(v.read_bytes()).hexdigest(),scope='terminal strict-bound current mu6 connectivity; RF2 source/view NOT adopted. RTL expected senses are not native qualification.',frames=rows)
(B/'parent_clock_map.json').write_text(json.dumps(out,indent=2));print('FRAMES',len(rows),'XK',sum(len(r['xk']) for r in rows),'XOK_CONNECTED',sum(r['xok_connected'] for r in rows));print(json.dumps(rows[0],indent=2)[:3200])
