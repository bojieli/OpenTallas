#!/usr/bin/env python3
"""Read-only source-pinned 109-bus model; never writes a compiler table."""
import collections, hashlib, json, pathlib, re, sys
W=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(W/'tools'))
import die_port_bind as P
S=W/'results/arch/qw_source_age_1019'; O=pathlib.Path(__file__).resolve().parent
read=lambda f:json.loads((S/f).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S/'die.v')=='7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7'
ex=read('repaired_export.json'); old=read('compute_compiled.json');diffs=read('reexport_vs_historical_compiled_FAIL.json')['age_diffs']
assert len(diffs)==109 and ex['digest']==old['digest']
buses={b['id']:b for b in ex['buses']};nets,_,_,insts=P.parse_die(S/'die.v'); inst={n:(m,c)for m,n,pr,c in insts if m!='__assign__'}
rev={}; aliases={}
for m,n,pr,c in insts:
 if m=='__assign__':
  a=re.match(r'assign\s+(.+?)\s*=\s*(.+)$',n,re.S)
  if a:
   lb=P.expr_bits(a[1],nets);rb=P.expr_bits(a[2],nets)
   if lb and rb and len(lb)==len(rb):aliases.update(zip(lb,rb))
 elif m.startswith(('qfd_rly','qfd_land','qkd_rly','qkd_land')) and 'a'in c and 'b'in c:
  a=P.expr_bits(c['a'],nets);b=P.expr_bits(c['b'],nets)
  assert a and b and len(a)==len(b)
  for bi,ai in zip(b,a):
   assert bi not in rev;rev[bi]=(n,ai)
lanes={r['landing']:r for r in read('fwd_lanes.json')['lanes'] if r.get('E') is not None}
sources=read('source_paths.json');snapshots={k:v for k,v in sources.items()}
for v in snapshots.values(): assert sha(S/'source'/v['snapshot'])==v['sha256']
def roots(name):
 m,c=inst[name];return {k:v for k,v in c.items() if k in ('ck','clk')}
def own(name):return next(iter(roots(name).values()),None)
def trace(bit,starts):
 chain=[];seen=set()
 while bit not in starts:
  assert bit not in seen,('loop',bit);seen.add(bit)
  if bit in aliases:bit=aliases[bit];continue
  assert bit in rev,('unresolved',bit)
  n,bit=rev[bit];chain.append(n)
 return tuple(reversed(chain))
module_sources={}
for entry in snapshots.values():
 text=(S/'source'/entry['snapshot']).read_text()
 for mod in P.parse_modules(text,entry['snapshot']):
  module_sources.setdefault(mod.name,[]).append((entry,mod,text))
def evidence(master,port):
 choices=module_sources.get(master,[])
 if not choices:return dict(status='SOURCE_MODULE_MISSING',publication_edge=None)
 entry,mod,text=choices[-1]
 hits=[]
 for no,line in enumerate(text.splitlines(),1):
  if re.search(r'\b'+re.escape(port)+r'\b',line) and not line.lstrip().startswith('//'):
   hits.append(dict(line=no,text=line.strip()))
 edge=None;status='OUTPUT_CONE_UNRESOLVED'
 if re.search(r'\b'+re.escape(port)+r'(?:\[[^\]]+\])?\s*<=',mod.body):
  # Direct output NBA and only one functional clock in this module.
  clocks=set(re.findall(r'posedge\s+(\w+)',mod.body))
  if clocks=={'ck'}:edge='posedge ck (output nonblocking assignment)';status='DIRECT_ROOT_REGISTER'
 if master=='qfd_d2d_static' and re.search(r'assign\s+'+port+r'\s*=\s*PR\s*\?\s*q_'+port,mod.body):
  assert re.search(r'parameter integer PR\s*=\s*1',text)
  assert 'PR' not in read('die.v.params.json')['masters'][master]
  edge='posedge ck (PR=1 output q_'+port+')';status='PR_OUTPUT_REGISTER'
 if master=='qfd_dv_slice2_w':
  core={'ag_wo':'ag_dn_o','ss_wo':'st','dd_wo':'ch_dn_o','ccv_wo':'cc_o','ccm_wo':'cc_o','ccw_wo':'cc_o','cct_wo':'cc_o','ard_wo':'ch_dn_o','arl_wo':'ch_dn_o','arm_wo':'ch_dn_o','art_wo':'ch_dn_o','arv_wo':'ch_dn_o'}
  if port in core:
   ct=(S/'source/050_qfd_dv_slice2.sv').read_text();q=core[port]
   assert re.search(r'\b'+q+r'\s*<=',ct)
   edge='posedge ck (face alias of u_core.'+q+' register)';status='WRAPPED_ROOT_REGISTER'
 if master=='qfd_embedding_word_provider' and port=='embed_scale_q':
  edge='posedge ck (store.embed_scale_q register)';status='CHILD_ROOT_REGISTER'
 if master=='qfd_embedding_word_provider' and port=='embed_code_q':status='CHILD_SRAM_OUTPUT_NATIVE_READ_ARC_UNPROVEN'
 if master=='qfd_sigbump':status='EXTERNAL_STRAP_PUBLICATION_UNKNOWN'
 return dict(snapshot=entry['snapshot'],sha256=entry['sha256'],port_lines=hits,publication_edge=edge,status=status)
rows=[]
for d in diffs:
 b=buses[d['bus']];si,sp=b['src']['inst'],b['src']['port'];di,dp=b['dst']['inst'],b['dst']['port'];dp=dp.split('__')[0]
 start=set(P.expr_bits(inst[si][1][sp],nets));end=P.expr_bits(inst[di][1][dp],nets)
 paths=set()
 for bit in end:
  try:paths.add(trace(bit,start))
  except AssertionError:
   # Concatenated input: retain only this source's exact bit subset.
   if '__' not in b['dst']['port']:raise
 assert len(paths)==1,(b['id'],paths)
 chain=list(paths.pop());assert len(chain)==b['stages']
 landrows=[lanes[n] for n in chain if n in lanes];plain=[n for n in chain if n not in lanes and not inst[n][0].startswith(('qfd_rlyh','qkd_rlyh'))]
 assert sum(r['E']+1 for r in landrows)+len(plain)==b['age_edges']
 clock_checks=[]
 for lr in landrows:
  seq=list(lr['stations'])+[lr['landing']];fc=inst[seq[0]][1];lc=inst[seq[-1]][1]
  clock_checks.append(dict(bid=lr['bid'],n=lr['n'],E=lr['E'],E_sta=lr.get('E_sta'),D=read('fwd_lanes.json')['D'],declared_window_ok=(lr.get('E_sta') is not None and lr['E_sta']<=read('fwd_lanes.json')['D']-1),K=lr['K'],G=lr['G_reset_tree'],R0=lr['R0_reset_tree'],calendar=lr['cal'],source_gate_clock=fc.get('ck_s',fc.get('ck')),landing_read_clock=lc['ck'],landing_output_register=True,source_metadata_clock=lr['src_ck'],destination_metadata_clock=lr['dst_ck'],reset_root=lr.get('reset_calendar_root'),chain=seq))
 first=clock_checks[0] if clock_checks else None;last=clock_checks[-1] if clock_checks else None
 source_root=own(si);dest_root=own(di)
 sm=b['src']['master']
 publication='external strap; no clocked source publication proven' if sm=='qfd_sigbump' else 'declared root identified; exact functional output cone/publication edge requires family proof'
 src_ev=evidence(b['src']['master'],sp);dst_ev=evidence(b['dst']['master'],dp)
 rows.append(dict(source_evidence=src_ev,destination_evidence=dst_ev,bus=b['id'],family=si+' -> '+di,width=b['width'],source=b['src'],destination=b['dst'],source_declared_clock=source_root,destination_declared_clock=dest_root,source_publication_edge=src_ev['publication_edge'],source_publication_status=src_ev['status'],raw_relay_frames=b['stages'],historical_compiled_age=d['schedule'],current_export_ideal_pin_age=b['age_edges'],difference=b['age_edges']-d['schedule'],actual_ordered_instances=chain,plain_relay_instances=plain,landings=clock_checks,source_gate_matches_declared_root=(first['source_gate_clock']==source_root) if first and source_root else None,landing_matches_destination_root=(last['landing_read_clock']==dest_root) if last and dest_root else None,hard_source_output_cycles_in_relay_age=0,hard_destination_input_cycles_in_relay_age=0,hard_boundary_origin_proof=None,native_source_capture_phase_ps=None,production_consumer_first_use_edge=None,adoptable_effective_age=None))
assert len(rows)==109
summary=[]
for fam in sorted({r['family']for r in rows}):
 rs=[r for r in rows if r['family']==fam];summary.append(dict(family=fam,buses=len(rs),age_changes=dict(collections.Counter(str(r['historical_compiled_age'])+' -> '+str(r['current_export_ideal_pin_age'])for r in rs)),source_gate_root_mismatches=[r['bus'] for r in rs if r['source_gate_matches_declared_root'] is False],destination_root_mismatches=[r['bus']for r in rs if r['landing_matches_destination_root'] is False]))
result=dict(schema='opentallas.qwen.109_source_age_model.v1',verdict='MODEL_ONLY_HOLD',source_commit='7cda48173',bus_count=109,family_count=len(summary),raw_digest=ex['digest'],source_hashes={f:sha(S/f)for f in ['die.v','repaired_export.json','compute_compiled.json','fwd_lanes.json','source_paths.json','reexport_vs_historical_compiled_FAIL.json']},unchanged_source_snapshots=snapshots,families=summary,buses=rows,hardware_change=None,area_delta_um2=0,token_delta=None,recompile_authorized=False,limits=['Export ideal ages are not functional publication or measured phase qualification.','Landing o is included once; hard-child pin FFs are excluded.','G and R0 are declared GEN epochs, not physical clock measurement.','Historical compiled schedule remains FAIL; no annotation or payload masking.'])
(O/'ledger.json').write_text(json.dumps(result,indent=1)+'\n')
print('MODEL_ONLY_HOLD buses=109 families='+str(len(summary)))
print('delta_counts',dict(collections.Counter(r['difference']for r in rows)))
print('source_clock_mismatch',sum(r['source_gate_matches_declared_root'] is False for r in rows),'destination_clock_mismatch',sum(r['landing_matches_destination_root'] is False for r in rows))
