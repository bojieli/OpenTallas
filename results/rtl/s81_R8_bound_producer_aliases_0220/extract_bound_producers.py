from pathlib import Path
import json,re,hashlib
r=Path('/srv/opentallas-scratch2/claude/die-s81-47/bind_ev2/out');bus=json.loads((r/'bus_groups.json').read_text());top=(r/'rtl/s81_bound_top.sv').read_text();topcells={i:dict(type=t,parameter_text=params or '')for t,params,i in re.findall(r'^    (\w+)(?:\s+#\(([^\n]*)\))?\s+(\w+)\s*\(',top,re.M)};types={i:v['type']for i,v in topcells.items()}
rows=[]
for g in bus['landing']:
 if g['aligned_landed']or not g['sink'].startswith('u_f_'):continue
 origs=sorted({m['source']for m in g['members']});assert len(origs)==1;orig=origs[0];typ=types[g['src_part']];p=r/'rtl'/f'{typ}.sv';s=p.read_text();wires=re.findall(r'^    wire \[1103:0\] (\w+);',s,re.M);local_orig=orig.split('.',1)[1]if orig.startswith('u_f_')else orig;normalized='w_'+local_orig.replace('.','_').replace('$','');suffix='_'+orig.split('.')[-2].replace('$','')+'_Y';candidates=[w for w in wires if w==normalized];assert len(candidates)==1,(g['src_part'],typ,orig,candidates);wire=candidates[0]
 m=re.search(r'^    assign '+re.escape(wire)+r' = (.*);$',s,re.M);expr=m[1]if m else None;atoms=None
 if expr and expr.startswith('{')and expr.endswith('}'):
  atoms=[]
  for token in reversed(expr[1:-1].split(',')):
   token=token.strip();b=re.fullmatch(r'(\w+)\[(\d+)(?::(\d+))?\]',token)
   if b:
    name,hi,lo=b.groups();hi=int(hi);lo=int(lo)if lo is not None else hi;atoms.extend((name,i)for i in range(lo,hi+1))
   else:atoms=None;break
 literal=bool(atoms and len(atoms)==1104 and atoms[1]==atoms[567])
 cells=[]
 for cm in re.finditer(r'^    (\w+)(?:\s+#\(([^\n]*)\))?\s+(\w+)\s*\(\s*\n(.*?)^    \);',s,re.M|re.S):
  cells.append(dict(type=cm[1],params=cm[2],name=cm[3],ports=dict(re.findall(r'\.(\w+)\(([^\n]*)\)(?:,|$)',cm[4],re.M))))
 for cm in re.finditer(r'^    (ot_dp_st) #\(([^\n]*)\) (\w+) \(([^;\n]*)\);',s,re.M):
  cells.append(dict(type=cm[1],params=cm[2],name=cm[3],ports=dict(re.findall(r'\.(\w+)\(([^()]*)\)',cm[4]))))
 exports=[dict(instance=c['name'],type=c['type'],parameters=c['params'],ports=c['ports'])for c in cells if c['type']=='ot_dp_st'and c['ports'].get('d')in [wire,wire+'[1103:0]']and re.fullmatch(r'x_o\d+(?:\[1103:0\])?',c['ports'].get('q',''))]
 if literal:assert exports,(typ,wire,'literal alias not connected to source export')
 def segment(token,bit):
  token=token.strip();m=re.fullmatch(r'(\w+)(?:\[(\d+)(?::(\d+))?\])?',token)
  if not m:return None
  name,hi,lo=m.groups()
  if hi is None:return name,bit
  return name,(int(lo)if lo is not None else int(hi))+bit
 def trace(atom):
  steps=[];name,bit=atom
  for depth in range(12):
   found=[]
   for c in cells:
    port='o'if (c['type'].startswith('dsfd_rly_')or c['type']=='ot_s81_rly')else('q'if c['type']=='ot_dp_st'else None)
    if port and port in c['ports']:
     out=segment(c['ports'][port],0)
     if out and out[0]==name:found.append((c,port,out[1]))
   if len(found)!=1:break
   c,port,lo=found[0];incoming=c['ports']['i'if port=='o'else'd'];nextatom=segment(incoming,bit-lo)
   steps.append(dict(instance=c['name'],type=c['type'],parameters=c['params'],clock=c['ports'].get('ck',c['ports'].get('clk')),reset=c['ports'].get('rs',c['ports'].get('rst_n')),enable=c['ports'].get('ea'),input=incoming,output=c['ports'][port]))
   if nextatom is None:break
   name,bit=nextatom
  return dict(steps=steps,endpoint=[name,bit],endpoint_is_primary_port=bool(re.search(r'^    input .*\b'+re.escape(name)+r'\b',s,re.M)),literal_equality_not_inferred_from_matching_registers=True)
 traces={str(b):trace(atoms[b])for b in [1,567]}if atoms and not literal else None
 source_cells=[]
 if not expr:
  for cm in re.finditer(r'^    (\w+)(?:\s+#\(([^\n]*)\))?\s+(\w+)\s*\(\s*\n(.*?)^    \);',s,re.M|re.S):
   body=cm[4]
   if re.search(r'\.(?:Y|q|o)\('+re.escape(wire)+r'(?:\[1103:0\])?\)',body):source_cells.append(dict(type=cm[1],params=cm[2],name=cm[3],ports=body.strip()))
 rows.append(dict(sink=g['sink'],sink_part=g['sink_part'],source_part=g['src_part'],original_source=orig,actual_source_type=typ,actual_top_parameter_bindings=topcells[g['src_part']]['parameter_text'],actual_source_file=str(p),actual_source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),typed_source_wire=wire,exact_original_name_match=(wire==normalized),typed_representative_name_used=(wire!=normalized),source_expression=expr,source_export_faces=exports,source_cell_drivers=source_cells,nonliteral_valid_paths=traces,decoded_packet_width=len(atoms)if atoms else None,bit1_origin=atoms[1]if atoms else None,bit567_origin=atoms[567]if atoms else None,literal_duplicate_valid_proven=literal,physical_clock_reset_sampling_qualified=False,native_measured=(g['sink']=='u_f_0L01.u_r0.$3')))
classes={}
for row in rows:
 key=(row['actual_source_type'],row['source_expression']);classes.setdefault(str(key),[]).append(row['source_part'])
grouped={}
for row in rows:
 key=(row['actual_source_type'],row['actual_top_parameter_bindings']);g=grouped.setdefault(key,dict(module=key[0],parameter_text=key[1],source_parts=[],sink_groups=[]));g['source_parts']=sorted(set(g['source_parts']+[row['source_part']]));g['sink_groups'].append(row['sink'])
report=dict(producer_classes=list(grouped.values()),status='CURRENT_BOUND_PRODUCER_SOURCE_ALIAS_JOIN_NO_PHYSICAL_ADOPTION',actual_bound_top_sha256=hashlib.sha256(top.encode()).hexdigest(),groups=len(rows),literal_duplicates=sum(v['literal_duplicate_valid_proven']for v in rows),remaining_nonliteral=sum(not v['literal_duplicate_valid_proven']for v in rows),actual_source_types=len({v['actual_source_type']for v in rows}),actual_source_module_parameter_classes=len({(v['actual_source_type'],v['actual_top_parameter_bindings'])for v in rows}),rows=rows,source_native_measurements=1,physical_corrections_C=None,R8_qualified=False,provider_or_cohort_flags_changed=False)
print(json.dumps(report,indent=2))
