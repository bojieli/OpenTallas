import csv,json,re,hashlib,functools,gzip
from collections import defaultdict,Counter
from pathlib import Path
import argparse
p=argparse.ArgumentParser(description='Build literal source-pinned parent connectivity bindings from the read-only ODB pin extraction.')
p.add_argument('extraction_directory',type=Path)
b=p.parse_args().extraction_directory
rows=list(csv.DictReader((b/'cell_pins.tsv').open(),delimiter='\t'))
cells=defaultdict(dict); drivers=defaultdict(list); master={}
for r in rows:
 n=r['instance'];cells[n][r['pin']]=r;master[n]=r['master']
 if r['io']=='OUTPUT':drivers[r['net']].append((n,r['pin']))
ports={r['net']:r['port'] for r in csv.DictReader((b/'ports.tsv').open(),delimiter='\t') if r['io']=='INPUT'}
def family(n):
 s=n.replace('\\','')
 if s.startswith('u_sp.g_bst.u_bst.g_line.line['):
  return 'broadcast_D3_final' if int(re.search(r'line\[(\d+)\]',s)[1])>=3260 else None
 if s.startswith('u_ld.'):return 'loader'
 if s.startswith('g_qx.g_qb.g_bx.'):return 'XS_gated_capture'
 if s.startswith('g_qx.g_qb.'):return 'config_go_free_capture'
 if s.startswith('g_qx.g_ir.'):return 'go_free_capture'
 if s.startswith('g_qx.g_qz_cg.'):return 'gate_enable_free'
 if '.g_mz.' in s:return 'reset_free_launch'
 if re.match(r'g_qx.g_mac\[\d+\]\.o_',s):return 'result_gated_launch'
 if '.bkf_r' in s or s.startswith('g_qx.g_qo.') or s.startswith(('sticky_fault','fault$_')):return 'busy_fault_free_capture'
 if s.startswith('u_return.u_n.'):return 'return64_free_capture'
 if s.startswith(('u_prv.','u_prd.','q0_')):return 'root_free_capture'
 return None
@functools.lru_cache(None)
def roots(net):
 out=set()
 if net in ports:out.add('PORT/'+ports[net])
 for n,p in drivers[net]:
  if master[n].startswith(('DFF','TIE','ICG')):out.add(n+'/'+p)
  else:
   for pin,r in cells[n].items():
    if r['io']=='INPUT' and pin not in ('VDD','VSS'):out.update(roots(r['net']))
 return frozenset(out)
def direct_chain(net):
 path=[]
 while len(drivers[net])==1:
  n,p=drivers[net][0]
  path.append({'pin':n+'/'+p,'net':net,'master':master[n]})
  if not master[n].startswith(('INV','BUF')):break
  ins=[r for r in cells[n].values() if r['io']=='INPUT' and r['pin'] not in ('VDD','VSS')]
  if len(ins)!=1:break
  net=ins[0]['net']
 return path
out=[]; counts=Counter();edgecounts=Counter()
for n in sorted(cells):
 f=family(n)
 if not f or not master[n].startswith('DFF'):continue
 counts[f]+=1
 item={'family':f,'instance':n,'master':master[n],'pins':{p:r['net'] for p,r in cells[n].items()}}
 # Full final D3 exporters are retained, with QN/inverter net connectivity.
 for p in ('D','RESETN','SETN'):
  if p not in cells[n]:continue
  net=cells[n][p]['net'];src=sorted(roots(net))
  if f=='return64_free_capture':src=[s for s in src if family(s.rsplit('/',1)[0])=='result_gated_launch' or p!='D']
  if f=='broadcast_D3_final' and p=='D':continue
  item.setdefault('bindings',{})[p]={'capture_pin':n+'/'+p,'startpoints':src,'direct_driver_chain':direct_chain(net)}
  edgecounts[f+':'+p]+=len(src)
 out.append(item)
icg=cells['g_qx.g_cg.u_cg.u_icg']
gate={'instance':'g_qx.g_cg.u_cg.u_icg','master':master['g_qx.g_cg.u_cg.u_icg'],'pins':{p:r['net'] for p,r in icg.items()},'ENA_startpoints':sorted(roots(icg['ENA']['net'])),'ENA_driver_chain':direct_chain(icg['ENA']['net'])}
# Source-qualified clock relation only; source ODB has no propagated CTS/SPEF.
for item in out:
 item['clock_relation']='q_gated' if item['pins'].get('CLK')==icg['GCLK']['net'] else 'core_clk' if item['pins'].get('CLK')==icg['CLK']['net'] else 'UNRESOLVED'
assert counts['XS_gated_capture']==549,counts
assert counts['result_gated_launch']==126,counts
assert counts['broadcast_D3_final']==1630,counts
assert counts['return64_free_capture']>=8320,counts
assert all(i['clock_relation']!='UNRESOLVED' for i in out)
go=[]
for i in out:
 if 'b_go$_' in i['instance']:
  src=i['bindings']['D']['startpoints'];go=src
  assert any(family(s.rsplit('/',1)[0])=='broadcast_D3_final' for s in src),src
  assert any(s.startswith('u_ld.act') for s in src),src
assert go,'missing both-source go capture'
rec={'schema':'opentallas.dsrom_v9.parent.literal_mapped_pin_bindings.v1','projection_source':'a2beef00ca0319615b8c6020e2f82dd9e3a4d8db','engine_reference':'0032b735573af2d24416eee1cf5911c0ac99ff5d','scope':'Minimum source-faithful parent register projection; arithmetic/four real macros excluded. Full D64 return queues retained. Structural connectivity is not timing sensitization or a full-engine clock qualification.','database_stage':'1_synth.odb','qualified_CTS':False,'qualified_SPEF':False,'qualified_SSFF':False,'missing_input_clocks':True,'uncertainty_ps':{'SS_setup':60,'FF_hold':25},'period_ps':833.333333333,'raw_source_sha256':(b/'source.sha256').read_text(),'raw_connectivity_sha256':hashlib.sha256((b/'cell_pins.tsv').read_bytes()).hexdigest(),'family_counts':dict(counts),'structural_startpoint_counts':dict(edgecounts),'go_launch_startpoints':go,'gate':gate,'unresolved_fault_binding':{'canonicalized_PQ0_loader_fault':"connect fault 1'x",'canonicalized_source':'map_r2/work/orfs/results/asap7/opentallas_ot_v41_v9_parent_clock_context_asap7/base/1_1_yosys_canonicalize.rtlil:24535','mapped_fault_D':'fault$_DFF_PN0_/D','mapped_fault_D_driver':'_103413_/H TIEHIx1_ASAP7_75t_R','absent_source_register_families':['g_qx.g_qo.ff_d','g_qx.g_qo.ffq','g_qx.g_qo.fq','g_qx.g_mac[*].bkf_r'],'qualification':'NO fault timing coverage; source PQ0 reset-only fault collapsed to X at Slang canonicalization. No current-route mutation or full-engine claim.'},'registers':out}
with gzip.open(b/'literal_pin_bindings.json.gz','wt') as f:json.dump(rec,f,separators=(',',':'))
(b/'summary.json').write_text(json.dumps({k:v for k,v in rec.items() if k!='registers'},indent=2)+'\n')
# Literal named-pin collection usable against this same source netlist, not guessed regexp aliases.
with (b/'literal_boundary_pins.tcl').open('w') as f:
 f.write('# Source-pinned mapped parent projection only; no delay, waiver, or full-engine timing assertion.\n# Database/source hashes and literal connectivity: literal_pin_bindings.json.gz / summary.json.\nset v9_parent_literal_pins [dict create]\n')
 for fam in counts:
  f.write('dict set v9_parent_literal_pins '+fam+' {\n')
  for i in out:
   if i['family']!=fam:continue
   for p in ('D','CLK','QN','Q','RESETN','SETN'):
    if p in i['pins']:f.write(' {'+i['instance']+'/'+p+'}\n')
  f.write('}\n')
 f.write('dict set v9_parent_literal_pins gate_clock {\n')
 for p in ('CLK','GCLK','ENA'):f.write(' {g_qx.g_cg.u_cg.u_icg/'+p+'}\n')
 f.write('}\n')
 f.write('foreach family [dict keys $v9_parent_literal_pins] {\n foreach name [dict get $v9_parent_literal_pins $family] {\n  if {[llength [get_pins -quiet $name]] != 1} {error "literal parent pin missing: $name"}\n }\n}\n')
print(json.dumps({'family_counts':dict(counts),'edge_counts':dict(edgecounts),'go':go,'gate':gate},indent=2))
