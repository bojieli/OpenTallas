#!/usr/bin/env python3
"""Opt-in exact single-cone successor of pr32. Run model_balanced27.py first.
Usage: emit_balanced27.py <pr32.v> <model.json> <output.v> [MUT]
MUT1 replaces only the final AND by OR for a causal pure-cone negative.
"""
import hashlib,json,re,sys
src=open(sys.argv[1]).read();model=json.load(open(sys.argv[2]));out=sys.argv[3]
mut=int(sys.argv[4]) if len(sys.argv)>4 else 0
assert hashlib.sha256(src.encode()).hexdigest()==model['source_sha256']=='8b4bec803a414206357c445865111f94292af06282dfc60e539223a0375530fb'
cre=re.compile(r'^\s*(?:\(\*[^*]*\*\)\s*)?(\w+)\s+(c\w+)\s*\((.*)\);\s*$',re.M)
remove=set(model['removed_cells'])
def keep(match):return '' if match.group(2) in remove else match.group(0)
dst=cre.sub(keep,src)
new=[];wires=[]
for i,node in enumerate(model['nodes']):
 master=node['master']
 if mut and i==len(model['nodes'])-1:master='OR2x2_ASAP7_75t_R'
 pins={chr(ord('A')+i):net for i,net in enumerate(node['inputs'])};pins['Y']=node['output']
 new.append('  (* keep = 1 *) '+master+' '+node['name']+' ('+', '.join('.'+k+'('+v+')' for k,v in pins.items())+');')
 if node['output']!=model['root']:wires.append(node['output'])
dst=dst.replace('module qkd_kvs_attn_safe_pr32 ', 'module qkd_kvs_attn_safe_pr32b27 ',1)
dst=dst.replace('endmodule','\n'+'\n'.join('  wire '+n+';' for n in wires)+'\n'+'\n'.join(new)+'\nendmodule')
dst='// Opt-in pure NOR27 balanced landed-QN AND tree; emit_balanced27.py MUT '+str(mut)+'\n'+dst
open(out,'w').write(dst)
print('ATTN_BALANCED27_EMIT',hashlib.sha256(dst.encode()).hexdigest(),'MUT',mut,'added_serial_edges',model['serial_edge_delta'])
