"""Same-ABI explicit face source candidate for current native RING. No zero-shift claim."""
from pathlib import Path
import re,json
P=Path(__file__).resolve().parent
text=(P/'native_cut.sv').read_text();head=text[:text.index(');')];ports=[]
for direction,span,name in re.findall(r'\b(input|output)\s+wire\s*(\[[^]]+\])?\s*(\w+)\s*,?',head):
 w=1
 if span:
  a,b=map(int,re.findall(r'\d+',span));w=abs(a-b)+1
 ports.append((direction,span or '',name,w))
assert len(ports)==45,len(ports)
passports={'clk','rst_n','strap_qid'}
metadata={'ports':[{'direction':d,'range':s,'name':n,'width':w,'latency_cycles':0 if n in passports else 1} for d,s,n,w in ports],'extra_edges_per_feedforward_traversal':2,'scope':'same-ABI source candidate with explicit physical outer FFs; requires actual caller/calendar bridge before adoption','passthrough':sorted(passports)}
lines=['`default_nettype none','module current_native_ring_face (']
lines += [f' {d} wire {s} {n}'+(',' if i<len(ports)-1 else '')for i,(d,s,n,w)in enumerate(ports)];lines+=[');']
connections=[]
for direction,span,name,w in ports:
 if name in passports:connections.append(f'.{name}({name})');continue
 if direction=='input':
  lines += [f' reg {span} src_face_{name};',f' always @(posedge clk) src_face_{name} <= {name};'];connections.append(f'.{name}(src_face_{name})')
 else:
  lines += [f' wire {span} src_body_{name};',f' reg {span} src_face_{name};',f' always @(posedge clk) src_face_{name} <= src_body_{name};',f' assign {name}=src_face_{name};'];connections.append(f'.{name}(src_body_{name})')
lines += ['native_ot_hfd_coll_q2_hard_v8g__ring_ag native_body ('+',\n'.join(connections)+');','endmodule','`default_nettype wire']
candidate='\n'.join(lines)+'\n';(P/'current_native_ring_face.sv').write_text(candidate)
assert ' assign u_ring_fault=src_face_u_ring_fault;'in candidate
(P/'current_native_ring_face_mutant.sv').write_text(candidate.replace(' assign u_ring_fault=src_face_u_ring_fault;',' assign u_ring_fault=src_face_u_ring_fault ^ 1\'b1;'))
(P/'source_candidate.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('PORTS',len(ports),'INPUT_FACE_BITS',sum(w for d,s,n,w in ports if d=='input'and n not in passports),'OUTPUT_FACE_BITS',sum(w for d,s,n,w in ports if d=='output'))
