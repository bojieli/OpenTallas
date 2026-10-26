#!/usr/bin/env python3
"""Split actual mapped noFP1 LSL fault cones at exclusive FF-Q nodes, preserving all existing state/edges."""
import argparse,collections,copy,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('json',type=pathlib.Path);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--functions',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
j=json.loads(a.json.read_text());m=j['modules']['ot_qwen_tile_lsl'];cells=m['cells'];drivers={};users=collections.defaultdict(set)
for n,c in cells.items():
 for pn,d in c['port_directions'].items():
  for b in c['connections'][pn]:
   if d=='output':
    assert b not in drivers,(b,n,drivers.get(b));drivers[b]=(n,c,pn)
   elif d=='input':users[b].add(n)
raw=set();cone=set();visited=set();inputs={b for p in m['ports'].values()if p['direction']=='input'for b in p['bits']}
def visit(b):
 if b in visited:return
 visited.add(b);assert isinstance(b,int)and b not in inputs,('notFF-only',b)
 n,c,pn=drivers[b]
 if c['type'].startswith('DFF'):raw.add(b);return
 assert c['type'] in j['modules'],('unknowncell',c['type']);cone.add(n)
 for pp,d in c['port_directions'].items():
  if d=='input':
   for bb in c['connections'][pp]:visit(bb)
faultbits=m['ports']['lfault']['bits']+m['ports']['tfault']['bits']
for b in faultbits:visit(b)
assert not (raw & set(m['ports']['t_out']['bits'])),'rawflag aliases dataoutput'
shared={b:sorted(users[b]-cone)for b in raw if users[b]-cone}
assert not shared,('COPY_REQUIRED actualsharedQmustnotbeexported',shared)
for n in cone:
 for pn,d in cells[n]['port_directions'].items():
  if d=='output':
   for b in cells[n]['connections'][pn]:assert not(users[b]-cone),('coneusedinternally',n,b,users[b]-cone)
raw=sorted(raw);leaf=copy.deepcopy(m);leaf['attributes'].pop('top',None)
leaf['ports']={n:p for n,p in leaf['ports'].items()if n not in ('lfault','tfault')};leaf['ports']['fault_q']={'direction':'output','bits':raw}
leaf['cells']={n:c for n,c in leaf['cells'].items()if n not in cone};leaf['netnames']['fault_q']={'hide_name':0,'bits':raw,'attributes':{}}
for n in ('lfault','tfault'):leaf['netnames'].pop(n,None)
wrapper={'attributes':{'top':'00000000000000000000000000000001'},'ports':copy.deepcopy(m['ports']),'cells':{n:copy.deepcopy(cells[n])for n in cone},'netnames':{}}
for n,pn in wrapper['ports'].items():wrapper['netnames'][n]={'hide_name':0,'bits':pn['bits'],'attributes':{}}
wrapper['netnames']['fault_q']={'hide_name':0,'bits':raw,'attributes':{}}
wrapper['cells']['u_native_rawleaf']={'hide_name':0,'type':'ot_qwen_tile_lsl_rawfault_m3','parameters':{},'attributes':{'keep_hierarchy':'00000000000000000000000000000001'},'port_directions':{n:p['direction']for n,p in leaf['ports'].items()},'connections':{n:p['bits']for n,p in leaf['ports'].items()}}
# Mechanical whole-graph identity: every original state cell and every data cell is untouched; the same25gates move only.
recombined=dict(leaf['cells']);recombined.update({n:c for n,c in wrapper['cells'].items()if n!='u_native_rawleaf'})
assert recombined==cells
ff_before={n:c for n,c in cells.items()if c['type'].startswith('DFF')};ff_after={n:c for n,c in leaf['cells'].items()if c['type'].startswith('DFF')};assert ff_before==ff_after
j['modules'].pop('ot_qwen_tile_lsl');j['modules']['ot_qwen_tile_lsl_rawfault_m3']=leaf;j['modules']['ot_qwen_tile_lsl']=wrapper
(a.out/'partition.json').write_text(json.dumps(j)+'\n')
funcs=json.loads(a.functions.read_text());models=[]
for typ in sorted({cells[n]['type']for n in cone}):
 ports=j['modules'][typ]['ports'];ins=[n for n,p in ports.items()if p['direction']=='input'];outs=[n for n,p in ports.items()if p['direction']=='output'];assert len(outs)==1
 fn=funcs[typ]['function'].replace('!','~').replace('*','&').replace('+','|')
 models.append('module '+typ+'('+','.join(ins+outs)+'); input '+','.join(ins)+'; output '+outs[0]+'; assign '+outs[0]+' = '+fn+'; endmodule')
(a.out/'cone_models.v').write_text('\n'.join(models)+'\n')
cone_bits=sorted({b for n in cone for bs in cells[n]['connections'].values()for b in bs});raw_index={b:i for i,b in enumerate(raw)}
def emit(name,mutant=False):
 lines=[f'module {name}(input [{len(raw)-1}:0] q, output [8:0] fault);']
 lines+=['wire '+','.join('n'+str(b)for b in cone_bits)+';']
 for b,i in raw_index.items():lines.append(f'assign n{b}=q[{i}];')
 for i,n in enumerate(sorted(cone)):
  c=cells[n];args=[]
  for pn,bs in c['connections'].items():
   assert len(bs)==1;args.append('.'+pn+'(n'+str(bs[0])+')')
  lines.append(c['type']+' c'+str(i)+'('+','.join(args)+');')
 for i,b in enumerate(faultbits):lines.append(f'assign fault[{i}]=n{b}'+(" ^ 1'b1"if mutant and i==8 else'')+';')
 lines.append('endmodule');return'\n'.join(lines)+'\n'
(a.out/'reference_cone.v').write_text(emit('reference_cone'));(a.out/'reconstructed_cone.v').write_text(emit('reconstructed_cone'));(a.out/'mutant_cone.v').write_text(emit('mutant_cone',True))
(a.out/'miter.v').write_text(f'module miter(input [{len(raw)-1}:0] q,output ok);wire[8:0]a,b;reference_cone r(q,a);reconstructed_cone g(q,b);assign ok=a==b;endmodule\nmodule mutant_miter(input [{len(raw)-1}:0]q,output ok);wire[8:0]a,b;reference_cone r(q,a);mutant_cone g(q,b);assign ok=a==b;endmodule\n')
area=sum(float(j['modules'][c['type']]['attributes'].get('area',0))for c in leaf['cells'].values()if c['type']in j['modules']);physical=sum(c['type']in j['modules']for c in leaf['cells'].values())
receipt={'status':'STRUCTURAL_PARTITION_PASS, faultconeSATpending, no physical view','source_json_sha256':hashlib.sha256(a.json.read_bytes()).hexdigest(),'raw_flag_bits':len(raw),'raw_flags':raw,'moved_comb_cells':len(cone),'moved_cell_types':dict(collections.Counter(cells[n]['type']for n in cone)),'original_physical_cells':sum(c['type']in j['modules']for c in cells.values()),'leaf_physical_cells':physical,'leaf_area_um2':area,'leaf_FF':len(ff_after),'whole_graph_recombined_identical':True,'all_state_cells_identical':True,'raw_Q_internal_consumers_after_cut':0,'new_FF':0,'extra_flag_pins_per_LSL':len(raw)-9,'extra_flag_pins_per_A0':8*(len(raw)-9),'cycles_added':{'data':0,'fault':0,'boot':0},'planned_new_leaf_um':[115.2,140.4],'planned_util':area/(115.2*140.4),'actual_output_launch_cells':[{'bit':i,'original_cell':drivers[b][0],'cell_type':drivers[b][1]['type'],'pin':drivers[b][2]}for i,b in enumerate(raw)]}
(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:receipt[k]for k in ['raw_flag_bits','moved_comb_cells','leaf_physical_cells','leaf_FF','new_FF','planned_util']}))
