from pathlib import Path
import json,re,hashlib,importlib.util,sys,collections
root=Path('/srv/opentallas-scratch/claude/codex-hroot-address-1021');sp=importlib.util.spec_from_file_location('T',root/'source/textbook_lint.py');T=importlib.util.module_from_spec(sp);sys.modules['T']=T;sp.loader.exec_module(T)
p=root/'hroot-address-map-r2-1021/original.v';raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='4c4b1fa2eca4e65190a0203eea33fb2ff871928c9b5e26cbbef3e4952694fbb6';g,top=T.flatten(T.parse_verilog(raw.decode()),None);A=T.build(g,None);aliases=collections.defaultdict(list)
for name,n in g.net_id.items():
 if re.match(r'(st_d|st_row|s_ring|s_local|s_rbase|s_pitch|s_raddr|s_stk|s_gs|k_sb|k_q|k_blk|k_code|k_scal|st_sec|st_ph|st_wa|u_raddr|u_kcode|u_kscal|w_addr|af_)($|\[|\$)',name):aliases[g.find(n)].append(name)
r=json.load(open(root/'address_cone_estimate.json'));trace=r['successor_selected_wrapper']['worst_address_traces'][0];records=[]
for node in [dict(instance=trace['start'])]+trace['cone']:
 m=re.search(r'u_eng\.u(\d+)_c\d+\.u_cell',node['instance']);assert m,node;ci=int(m[1]);typ,name,pins=g.cells[ci]
 rec=dict(native=node['instance'],cell=ci,original=name,master=typ,pins={pn:[dict(net=g.net_name[n],aliases=aliases[n]) for n in ns] for pn,ns in pins.items()});records.append(rec)
# Start Q inverse-buffer aliases; pin exact expression provenance without assuming FF-state equality.
ci=records[0]['cell'];leaves=[]
for n in T._out_nets(g,A,ci):
 for c,pn,b in A['loads'].get(n,[]):
  if A['kind'][c]=='buf':
   leaves.append(dict(master=g.cells[c][0],instance=g.cells[c][1],outputs=[dict(net=g.net_name[x],aliases=aliases[x]) for x in T._out_nets(g,A,c)]))
out=dict(mapped_sha256=hashlib.sha256(raw).hexdigest(),parser_sha256=hashlib.sha256((root/'source/textbook_lint.py').read_bytes()).hexdigest(),path_from_completed_estimate=trace,start_inverse_buffer_aliases=leaves,path_cells=records,scope='read-only exact existing mapped primitive path-to-source alias trace; structural sensitization and STA closure not asserted');Path('address_equation_trace.json').write_text(json.dumps(out,indent=2)+'\n')
for q in records:
 outaliases=[v['aliases'] for pn,vals in q['pins'].items() if A['pin_dir'][q['cell']][pn]=='out' for v in vals];print(q['cell'],q['master'],outaliases)
print('ROOT_INVERSE_ALIASES',leaves)
