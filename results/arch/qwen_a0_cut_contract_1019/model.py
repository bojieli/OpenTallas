"""Finite exact source cut/ownership/retention model; no EDA or source activation."""
import collections,functools,gzip,hashlib,io,json,pathlib,random,re
P=pathlib.Path(__file__).resolve().parent
B=P.parent/'qwen_a0_compact_engine_1019'
g={'__file__':str(B/'model.py')}
exec((B/'model.py').read_text().split('origins=json.load')[0],g)
cells,drivers,consumers,upstream,downstream,outs,issue,cut,hardrows,old,areas=[g[x] for x in ['cells','drivers','consumers','upstream','downstream','outs','issue','cut','hardrows','old','areas']]
def gz(name,obj):
 with (P/name).open('wb') as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as f:
   f.write(json.dumps(obj,sort_keys=True,separators=(',',':')).encode())
def cellof(e):return e.rsplit('/',1)[0]
def isff(n):return n in cells and cells[n][0].startswith('DFF')
def clk(n):return cells[n][1].get('CLK',cells[n][1].get('clk')) if n in cells else None
# Seed every actual immediate hard-input driver and hard-output receiver by its
# real transformed terminal. This is source ownership, not placed FF locations.
anchors=collections.defaultdict(list)
for h in hardrows:
 if h['type'] not in ('SIGNAL','CLOCK'):continue
 es=h.get('actual_upstream_boundaries',[]) if h['direction']=='INPUT' else downstream(h['net'])
 for e in es:
  n=cellof(e)
  if isff(n):anchors[n].append({'child':h['child'],'pin':h['pin'],'shapes':h['actual_shapes'],'direction':h['direction']})
@functools.lru_cache(None)
def ff_neighbors(n):
 m,p=cells[n]; a=set()
 if 'D' in p:a.update(cellof(e) for e in upstream(p['D']) if isff(cellof(e)))
 for op in outs(m,p):a.update(cellof(e) for e in downstream(p[op]) if isff(cellof(e)))
 return frozenset(a-{n})
@functools.lru_cache(None)
def ownership(n):
 if n in issue:return {'region':'compact_issue','clock':clk(n),'source_hop_to_hard_seed':None,'seed_cells':[],'hard_children':[],'qualified_position':None}
 if n in anchors:dist=0; found={n}
 elif isff(n):
  seen={n};front={n};found=set();dist=0
  while front and not found:
   dist+=1;new=set().union(*(ff_neighbors(x) for x in front))-seen
   found=set(new)&set(anchors);seen.update(new);front=new
 else:dist=None;found=set()
 hs=sorted({a['child'] for x in found for a in anchors[x]})
 candidates=[]
 for x in sorted(found):
  for a in anchors[x]:
   for shape in a['shapes']:
    r=shape['rect_um'];cx=(r[0]+r[2])/2;cy=(r[1]+r[3])/2
    at=[min(1166.4,max(129.6,cx)),min(393.12,max(349.92,cy))]
    distance=max(129.6-r[2],r[0]-1166.4,0)+max(349.92-r[3],r[1]-393.12,0)
    candidates.append((distance,abs(at[0]-583.2)+abs(at[1]-362.88),a['child'],a['pin'],x,at,r))
 chosen=min(candidates) if candidates else None
 return {'region':'existing_regional_IO/'+('+'.join(hs) if hs else 'UNRESOLVED'),'clock':clk(n),'source_hop_to_hard_seed':dist if found else None,'seed_cells':sorted(found),'hard_children':hs,'proposed_existing_IO_band_point_um':chosen[5] if chosen else None,'nearest_actual_terminal':{'child':chosen[2],'pin':chosen[3],'seed_FF':chosen[4],'rect_um':chosen[6],'necessary_pin_to_band_L1_um':chosen[0]} if chosen else None,'qualified_position':None}
# Shared combinational cells are assigned ONCE from their actual first storage
# boundaries. Multiple regions remain a joint routing obligation, not clones.
@functools.lru_cache(None)
def endpoint_owner(e):
 n=cellof(e)
 if n not in cells:return {'region':'port','clock':None,'hard_children':[]}
 if n in issue or isff(n):return ownership(n)
 m,p=cells[n]
 ss=set()
 for pin,net in p.items():
  ss.update(cellof(x) for x in (downstream(net) if pin in outs(m,p) else upstream(net)) if isff(cellof(x)))
 refs=[ownership(x) for x in sorted(ss)]
 hs=sorted({h for r in refs for h in r['hard_children']})
 points=sorted(r['proposed_existing_IO_band_point_um'] for r in refs if r.get('proposed_existing_IO_band_point_um'))
 point=[sorted(p[0] for p in points)[len(points)//2],sorted(p[1] for p in points)[len(points)//2]] if points else [583.2,362.88]
 return {'proposed_shared_cone_band_point_um':point,'assignment_rule':'one joint median point of actual existing IO source/consumer anchors; unqualified site and route','region':'shared_existing_cone/'+('+'.join(hs) if hs else 'compact_or_unresolved'),'clock':None,'hard_children':hs,'storage_boundary_cells':sorted(ss),'qualified_position':None,'cloned':False}
rootnets={cells[cellof(r['driver'])][1][r['driver'].rsplit('/',1)[1]] for r in old['roots'] if not r['master'].startswith('TIE')}
ledger=[]; external=set(); pairs=set(); pairclasses=collections.defaultdict(set); roles=collections.Counter()
for r in cut:
 eps=r['inside_drivers']+r['inside_consumers']+r['outside_drivers']+r['outside_consumers']
 pins=[e.rsplit('/',1)[-1] for e in eps if not e.startswith('PORT/')]
 ups=r['actual_upstream_storage_or_port'];dns=r['actual_downstream_first_storage']
 if 'CLK' in pins or 'clk' in pins or r['net']=='ck':kind='clock'
 elif ups and all(cellof(e) in cells and cells[cellof(e)][0].startswith('TIE') for e in ups):kind='tie'
 elif any(x in pins for x in ['RESETN','SETN']) or r['net'].startswith('a0_reset'):kind='reset_or_async_control'
 elif r['net'] in rootnets:kind='unsafe_control_root'
 else:kind='data_or_decoded_control'
 roles[kind]+=1
 ext=r['outside_drivers']+r['outside_consumers'];external.update(ext)
 upff=[e for e in ups if isff(cellof(e))];dnff=[e for e in dns if isff(cellof(e))]
 for a in upff:
  for b in dnff:
   pairs.add((a,b));pairclasses[(a,b)].add(kind)
 ledger.append({**r,'cut_class':kind,'outside_endpoint_assignment':{e:endpoint_owner(e) for e in ext},'existing_boundary_pair_product':{'producer_endpoints':upff,'consumer_endpoints':dnff,'pair_count':len(upff)*len(dnff)},'retention_contract':{'actual_clock_pairs':sorted({str(clk(cellof(a)))+' -> '+str(clk(cellof(b))) for a in upff for b in dnff})},'selected_new_landing':False,'landing_selection_status':'UNRESOLVED_actual_endpoint_sites_clock_phase_epoch_required','added_state_bits':None,'added_edges':None})
gz('cut_contracts.json.gz',ledger)
gz('outside_endpoint_assignment.json.gz',{e:endpoint_owner(e) for e in sorted(external)})
gz('cross_clock_data_ports.json.gz',[{'producer':a,'consumer':b,'producer_clock':clk(cellof(a)),'consumer_clock':clk(cellof(b)),'cut_nets':[r['net'] for r in ledger if a in r['actual_upstream_storage_or_port'] and b in r['actual_downstream_first_storage']],'producer_assignment':ownership(cellof(a)),'consumer_assignment':ownership(cellof(b)),'qualified_phase_and_reset_epoch':None} for a,b in sorted(pairs) if 'data_or_decoded_control' in pairclasses[(a,b)] and clk(cellof(a))!=clk(cellof(b))])
gz('existing_registered_pairs.json.gz',[{'producer':a,'consumer':b,'producer_clock':clk(cellof(a)),'consumer_clock':clk(cellof(b)),'cut_roles':sorted(pairclasses[(a,b)]),'data_launch_capture_qualified':False} for a,b in sorted(pairs)])
# Native combinational evaluator. Pin groups A1/A2/B etc retain actual names.
def logic(master,v):
 k=master.split('x')[0]
 if k=='INV':return 1-v['A']
 if k=='BUF':return v['A']
 if k.startswith('TIE'):return int('HI' in k)
 if k.startswith(('XOR','XNOR')):
  x=sum(v.values())%2;return 1-x if k.startswith('XNOR') else x
 if k=='MAJ':return int(sum(v.values())>=2)
 if k.startswith(('AND','NAND','OR','NOR')):
  x=int(all(v.values())) if k.startswith(('AND','NAND')) else int(any(v.values()))
  return 1-x if k.startswith(('NAND','NOR')) else x
 if k.startswith(('AO','OA')):
  groups=collections.defaultdict(list)
  for p,x in v.items():groups[p[0]].append(x)
  ao=k.startswith('AO');parts=[all(xs) if ao else any(xs) for xs in groups.values()]
  x=int(any(parts) if ao else all(parts));return 1-x if 'I' in k else x
 raise ValueError((master,v))
# A witness is a two-state, pre-edge retention counterexample, NOT proof it is
# reset-reachable under a presently missing production boot contract.
roots=[];rng=random.Random(20261019)
source_traces=json.load(gzip.open(P.parent/'qwen_a0_topology_firstuse_1019/source_boundaries.json.gz'))['roots']
traces={r['driver']:r for r in source_traces}
for r in old['roots']:
 if r['master'].startswith('TIE'):continue
 n,op=r['driver'].rsplit('/',1);m,p=cells[n];net=p[op]
 tr=traces[r['driver']]
 terminals=[x['native_terminal'] for x in tr['terminals'] if not x['native_terminal'].startswith('PORT/')]
 protected=set(tr['original_canonical_D_cone_terminals_keep_original_root'])
 base={'driver':r['driver'],'master':m,'canonical_input_source_boundaries':{ip:sorted(upstream(x['net'])) for ip,x in r['canonical_native_inputs'].items() if ip!='CLK'},'canonical_inputs':{ip:{'net':nn,'actual_immediate_drivers':[cn+'/'+cp for cn,cp in drivers.get(nn,[])],'actual_upstream_storage_or_port':sorted(upstream(nn))} for ip,nn in p.items() if ip not in outs(m,p)},'first_storage':sorted(downstream(net)),'protected_original_terminals':sorted(protected),'qualified_boot_first_use':None,'actual_clock':'ck','production_first_use_status':'HOLD_real_reset_epoch_recovery_and_accepted_go_contract'}
 parities={}
 def walk(nn,parity):
  for cn,ip in consumers.get(nn,[]):
   cm,pp=cells[cn]
   if cm.startswith(('BUF','INV')):
    for oo in outs(cm,pp):walk(pp[oo],parity ^ int(cm.startswith('INV')))
   else:parities[cn+'/'+ip]=parity
 walk(net,0)
 if not m.startswith('DFF'):
  moved=[e for e in terminals if e not in protected]
  groups=[{'INV_parity':parity,'native_terminals':mm[i:i+32]} for parity in (0,1) for mm in [[e for e in moved if parities[e]==parity]] for i in range(0,len(mm),32)]
  invs=sum(x['INV_parity'] for x in groups)
  base.update({'mechanism':'same_combinational_master_same_actual_input_nets','logical_equivalence':'combinational identity for every input valuation; no new state or cycle','canonical_original_retained':True,'clone_partitions':groups,'selected_extra_logic_cells':len(groups),'selected_extra_logic_area_um2':len(groups)*areas[m],'extra_polarity_INVx1':invs,'extra_polarity_INV_area_um2':invs*areas['INVx1_ASAP7_75t_R'],'input_load_increment':{ip:len(groups) for ip in p if ip not in outs(m,p)},'new_state_bits':0,'new_logical_edges':0,'native_recount_reset_tie_input_fanout_phase':'HOLD','transparent_polarity_rewire':'each negative group gets one counted native INVx1; original protected transparent paths retained; no deletion credit'})
 else:
  candidates=[]
  for tt in tr['terminals']:
   terminal=tt['native_terminal']
   if terminal in protected or terminal.startswith('PORT/'):continue
   for target in tt['first_storage_or_macro_boundaries']:
    if target.endswith('/D'):candidates.append((terminal,target))
  assert candidates
  witness=None
  for trial in range(200):
   boundary_values={};cache={}
   def ev(nn,override):
    if nn==net:return 0
    key=(nn,override)
    if key in cache:return cache[key]
    ds=drivers.get(nn,[])
    if nn.startswith('CONST/'):v=int(nn[-1])
    elif not ds:v=boundary_values.setdefault('PORT/'+nn,rng.getrandbits(1))
    else:
     assert len(ds)==1,nn
     cn,cp=ds[0];cm,pp=cells[cn]
     if cm.startswith('DFF') or cm in g['abstracts']:v=boundary_values.setdefault(cn+'/'+cp,rng.getrandbits(1))
     else:v=logic(cm,{ip:(override ^ parities[terminal] if cn+'/'+ip==terminal else ev(nv,override)) for ip,nv in pp.items() if ip not in outs(cm,pp)})
    cache[key]=v;return v
   for terminal,target in candidates:
    cache.clear()
    tn=cellof(target);dnet=cells[tn][1]['D']
    try:
     if terminal==target:a=parities[terminal];b=1 ^ parities[terminal]
     else:a=ev(dnet,0);b=ev(dnet,1)
    except (ValueError,AssertionError):continue
    if a!=b:
     async_values={ip:ev(nn,0) for ip,nn in p.items() if ip in ('RESETN','SETN')}
     if any(x!=1 for x in async_values.values()):continue
     witness={'kind':'arbitrary_pre_edge_clone_retention','trial':trial,'rewired_native_terminal':terminal,'transparent_INV_parity':parities[terminal],'target':target,'target_clock':clk(tn),'canonical_root_output':0,'arbitrary_clone_output':1,'consumer_D_with_canonical':a,'consumer_D_with_clone':b,'root_async_controls_current_values':async_values,'other_boundary_outputs':dict(sorted(boundary_values.items())),'both_next_root_values':'same original canonical D on this edge','reset_reachable':None,'proof_scope':'disproves arbitrary-start same-edge consumer equivalence; does not disprove a future actual reset/valid-overwrite contract'};break
   if witness:break
  assert witness,r['driver']
  base.update({'mechanism':'shared_canonical_D_sequential_clone_NOT_ADOPTED','specific_counterexample':witness,'selected_extra_state_bits':None,'selected_partition':None,'async_reset_inputs':{k:v for k,v in p.items() if k in ('RESETN','SETN')}})
 if 'split_r' in n:
  contract={'source_lines':[489,493,506,552,600,691,705,706,707],'accepted_configuration':'!pend && !active && go captures i_split','first_structural_capture':'every clk edge in unreset pr_a/kpad/shifted terms/klim/tag registers, including before GO','first_meaningful_use':'after accepted GO, old active=0 suppresses x_re and e_v on E0; direct issue/tag uses new split from E1; retained derived terms/limits must keep original multi-edge pipeline and KV_PREP/IL conditions','not_proved':'all reset epochs and earliest accepted GO; all retained destination validity until overwritten'}
 elif 'wsrc_r' in n:
  contract={'source_lines':[506,507,549,564,690],'accepted_configuration':'!pend && !active && go captures i_wsrc','first_structural_capture':'tstep_r and e_wsrc can capture every edge while configuration is arbitrary','first_meaningful_use':'first active edge after accepted GO for read-enable/tag; KV-derived tstep still requires its original term/sum/result stages','not_proved':'actual boot/GO epoch, native capture phase and complete invalid-state flush'}
 elif 'k_last' in n:
  contract={'source_lines':[556,571,572,576,689,694],'accepted_configuration':'GO captures kc_is_1; actual canonical feedback changes on j_last boundaries','first_structural_capture':'unreset e_last/e_opend tag capture every edge; loop k may consume when active && j_last','first_meaningful_use':'first active issue after accepted GO for e_last; original IL-spaced j_last for loop transition','not_proved':'first accepted GO and all tag-valid/overwrite epochs; clones may not replace canonical feedback'}
 elif 'active_o' in n:
  contract={'source_lines':[535,538,540,545,596,597,679,680],'accepted_configuration':'asynchronous rst_n clears active; GO sets active or pend, pending delay later sets active','first_structural_capture':'e_v and x_re/loop state sample active at each edge','first_meaningful_use':'actual reset assertion establishes canonical/clone equality only if both receive the same real reset; no unqualified arbitrary-start equality','not_proved':'physical reset distribution/recovery, first meaningful launch after actual boot and regional phases'}
 else:
  contract={'source_lines':[],'accepted_configuration':'no extra state; replicas use every same original input net','first_structural_capture':'original first-storage terminal set retained exactly','first_meaningful_use':'unchanged by logical combinational replication','not_proved':'new upstream reset/control loads, actual propagation and native max fanout fixed point'}
 base['semantic_first_use_contract']=contract
 base['first_storage_actual_controls']={e:{'clock':clk(cellof(e)),'async_controls':{ip:nn for ip,nn in cells[cellof(e)][1].items() if ip in ('RESETN','SETN')}} for e in base['first_storage'] if isff(cellof(e))}
 roots.append(base)
checks=[]
for rr in roots:
 if not rr['master'].startswith('DFF'):
  nn=cellof(rr['driver']);mm,pp=cells[nn];ips=sorted(ip for ip in pp if ip not in outs(mm,pp))
  table=[]
  for mask in range(1<<len(ips)):
   vv={ip:(mask>>i)&1 for i,ip in enumerate(ips)};value=logic(mm,vv)
   table.append({'inputs':vv,'original':value,'every_same_master_replica':value,'wrong_output_polarity_mutant':1-value})
  moved=[e for part in rr['clone_partitions'] for e in part['native_terminals']]
  assert len(moved)==len(set(moved))
  assert not set(moved)&set(rr['protected_original_terminals'])
  assert all(0<len(part['native_terminals'])<=32 for part in rr['clone_partitions'])
  checks.append({'driver':rr['driver'],'exact_truth_table':table,'partition_disjoint_complete_except_protected':len(moved)+len(rr['protected_original_terminals'])==len(traces[rr['driver']]['terminals'])})
 else:
  w=rr['specific_counterexample'];assert w['consumer_D_with_canonical']!=w['consumer_D_with_clone']
  assert w['rewired_native_terminal'] not in rr['protected_original_terminals']
assert all(c['partition_disjoint_complete_except_protected'] for c in checks)
gz('root_contracts.json.gz',roots)
(P/'finite_checks.json').write_text(json.dumps({'logic_identity_tables':checks,'seven_distinct_retention_witnesses':7,'scope':'finite source/model checks, not RTL simulation or native physical qualification'},indent=2)+'\n')
# Every source pair retains identity. A ring cost is recorded as a formula;
# selecting edges before actual placements/phases/epochs would invent hardware.
ffpair={cellof(a) for a,b in pairs}|{cellof(b) for a,b in pairs}
selected_input_loads=collections.Counter()
for rr in roots:
 if 'selected_extra_logic_cells' in rr:
  nn=cellof(rr['driver']);mm,pp=cells[nn]
  for ip,nv in pp.items():
   if ip not in outs(mm,pp):selected_input_loads[nv]+=rr['selected_extra_logic_cells']
summary={'selected_logic_input_load_increment_by_actual_net':dict(selected_input_loads),'selected_logic_extra_storage_bits':0,'selected_logic_added_edges':0,'selected_logic_new_clock_pins':0,'selected_logic_input_pins':sum(selected_input_loads.values()),'selected_logic_access_RC_energy':None,'compact_plus_logic_area_um2':482.90418+sum(r.get('selected_extra_logic_area_um2',0)+r.get('extra_polarity_INV_area_um2',0) for r in roots),'status':'MODEL_SOURCE_CONTRACT_PARTIAL_NO_ACTIVATION','source_sha256':g['hashlib'].sha256(g['source'].encode()).hexdigest(),'source_cells':len(cells),'expanded_bus_connections':65,'expanded_bus_bits':11480,'non_PG_hard_pins':11567,'cut_nets':len(cut),'cut_classes':dict(roles),'outside_immediate_endpoints':len(external),'distinct_existing_registered_pairs':len(pairs),'distinct_pair_FF':len(ffpair),'existing_FF_are_not_new_landing_bits':True,'pair_role_counts':dict(collections.Counter(k for v in pairclasses.values() for k in v)),'native_clock_pair_counts':dict(collections.Counter(str(clk(cellof(a)))+' -> '+str(clk(cellof(b))) for a,b in pairs)),'data_pair_clock_counts':dict(collections.Counter(str(clk(cellof(a)))+' -> '+str(clk(cellof(b))) for a,b in pairs if 'data_or_decoded_control' in pairclasses[(a,b)])),'hard_pin_seed_FF':len(anchors),'combinational_partition_models':sum(not r['master'].startswith('DFF') for r in roots),'sequential_retention_counterexamples':sum(r['master'].startswith('DFF') for r in roots),'selected_logic_clone_cells':sum(r.get('selected_extra_logic_cells',0) for r in roots),'selected_logic_clone_area_um2':sum(r.get('selected_extra_logic_area_um2',0) for r in roots),'selected_polarity_INV':sum(r.get('extra_polarity_INVx1',0) for r in roots),'selected_logic_plus_polarity_area_um2':sum(r.get('selected_extra_logic_area_um2',0)+r.get('extra_polarity_INV_area_um2',0) for r in roots),'new_sequential_landing_bits':None,'new_sequential_edges':None,'complete_selected_landing_cost':None,'landing_cost_rule':'W payload+all identity/valid/epoch bits; four slots cost 4*W storage plus actual metadata/control, reset2 and native clock pins; coherent >2048 bits must use SRAM; width cannot be split to evade rule','all_121_CB16_endpoints':'HOLD','PG_contact_native_phase_first_use':'HOLD','same_phase_clock_assumption':False,'RTL_EDA_jobs':0}
(P/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
manifest={str(p.relative_to(P.parent.parent.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [B/'model.py',B/'crossing_ledger.json.gz',B/'hard_pin_ownership.json.gz',P.parent/'qwen_a0_reset_1019/r3/candidate.v.gz',P/'semantic_source.sv',P.parent/'qwen_a0_ownership_1019/ownership.json',P.parent/'qwen_a0_ownership_1019/native_abstracts.json.gz',P.parent/'qwen_a0_ownership_1019/native_area.json',P.parent/'qwen_a0_topology_firstuse_1019/transformed_pins.json.gz',P.parent/'qwen_a0_topology_firstuse_1019/source_boundaries.json.gz']}
(P/'input_hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(summary,indent=2,sort_keys=True))
