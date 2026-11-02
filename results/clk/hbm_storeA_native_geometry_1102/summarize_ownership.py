from pathlib import Path
import json,collections,re,gzip,hashlib,resource
R=Path.cwd();data=json.load(open(R/'macro_ownership.json'));binding=json.load(open(R/'native_macro_binding.json'));byname={x['actual_native_name']:x for x in binding['rows']};out=[];global_read_ff=set();global_read_abi=set()
for q in data:
 row=dict(instance=q['instance'],master=q['master'],planned_xy_um=byname[q['instance']]['planned_xy_um'],planned_orient=byname[q['instance']]['planned_orient'],native_clock=byname[q['instance']]['native_clock'],groups={})
 for group,g in q['pin_groups'].items():
  ends=g['frontier_union'];ff=sorted({e[1]for e in ends if e[0]=='ff'});abi=sorted({e[1]for e in ends if e[0]=='port'});macro=sorted({e[1]for e in ends if e[0]=='macro'})
  row['groups'][group]=dict(direction=g['direction'],signal_bits=g['bit_count'],FF_instances=ff,ABI_ports=abi,other_macros=macro,FF_count=len(ff),ABI_count=len(abi))
  if g['direction']=='OUTPUT':global_read_ff.update(ff);global_read_abi.update(abi)
 out.append(row)
(R/'ownership_summary.json').write_text(json.dumps(dict(status='PASS_LOGICAL_NATIVE_SRAM_FRONTIERS',macros=out,global_read_output_capture_FF_count=len(global_read_ff),global_read_output_capture_FF=sorted(global_read_ff),global_read_output_ABI_count=len(global_read_abi),scope='actual net graph, conservative combinational-cell reach to sequential/macro/ABI boundaries; planned macro positions from exact32name certificate, no placed stdcell coordinates'),indent=2)+'\n')
print('READOUTPUT',len(global_read_ff),'FF',len(global_read_abi),'ABI');print('READOUT_PERBANK',collections.Counter((r['groups']['rd_out']['FF_count'],r['groups']['rd_out']['ABI_count'])for r in out))
del data
abi=json.load(open(R/'output_capture_frontiers.json'));groups={}
for p in abi:
 name=re.sub(r'\[\d+\]$','',p['port']);g=groups.setdefault(name,dict(bits=0,source_FF=set(),direct_input_ports=set(),macros=set(),max_combinational_cells=0));g['bits']+=1;g['max_combinational_cells']=max(g['max_combinational_cells'],p['combinational_cells_visited'])
 for kind,owner,pin in p['frontier']:
  g['source_FF'if kind=='ff'else'direct_input_ports'if kind=='port'else'macros'].add(owner)
for g in groups.values():
 for k in ('source_FF','direct_input_ports','macros'):g[k]=sorted(g[k]);g[k+'_count']=len(g[k])
(R/'output_capture_summary.json').write_text(json.dumps(groups,indent=2)+'\n');del abi
for name in ['macro_ownership.json','output_capture_frontiers.json','graph.tsv']:
 with open(R/name,'rb')as f,gzip.open(R/(name+'.gz'),'wb',compresslevel=5)as o:
  while block:=f.read(1024*1024):o.write(block)
print('SUMMARY_DONE maxrss_kb',resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
