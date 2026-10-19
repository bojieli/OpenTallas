"""Bounded deterministic MODEL over 331 pinned reset interfaces; no synthesis."""
import collections,gzip,json,math,pathlib,csv,hashlib,os
P=pathlib.Path(__file__).resolve().parent
LAND_FF=3 # exact qfd_rst_rep: one input FF and two registered output FFs
OLD=pathlib.Path(os.environ.get('QW_PRIOR_EVIDENCE',str(P.parent/'qw_regional_terminal_1019'/'raw'/'d')))
def old(s):return json.loads(gzip.decompress((OLD/s).read_bytes()))
def read(s):
 p=P/s
 return json.loads(p.read_bytes() if p.exists() else gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes()))
M=old('rA/tt/manifest.json.gz');L=read('native_leaf.json');N=read('parent_native.json');S=read('selected.json')
def native_path(leaf,net):
 nets={q['name']:q for q in leaf['signal_nets']}; result=[];seen=set()
 while net not in seen:
  seen.add(net);n=nets[net];result.append(dict(net=net,ports=n['ports']))
  if n['ports']:return result
  drivers=[q for q in n['pins'] if q['io']=='OUTPUT']
  assert len(drivers)==1,(net,drivers)
  d=drivers[0];result.append(d)
  if not d['master'].startswith(('BUF','INV')):return result
  inputs=[(k,q) for k,v in nets.items() for q in v['pins'] if q['inst']==d['inst'] and q['io']=='INPUT']
  assert len(inputs)==1,(d,inputs)
  net=inputs[0][0]
 raise ValueError('cycle')
def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def transform(v,xy):
 assert v['orientation']=='R0',v['orientation']
 return [v['transform_offset'][k]/v['units']+xy[k] for k in range(2)]
def trace_parent(pin):
 a=[pin];seen={pin}
 while a[-1] in M['parent']:
  p=M['parent'][a[-1]];assert p not in seen;seen.add(p);a.append(p)
 return a
cells={x[0]:dict(master=x[1],xy=x[2:]) for x in M['cells']}
entries={};regions=collections.defaultdict(list)
for pin,s in sorted(S.items()):
 inst=pin.rsplit('/',1)[0];v=N['instances'][inst];leaf=L[v['master']]
 captures=[]
 for c in leaf['capture_cells']:
  pins={q['pin']:dict(q,absolute_xy=transform(v,q['xy'])) for q in c['pins']}
  captures.append(dict(instance=c['name'],master=c['master'],pins=pins,native_clock_path=native_path(leaf,pins['CLK']['net']),native_data_path=native_path(leaf,pins['D']['net'])))
 entry=dict(pin=pin,inst=inst,region=s['tree'],native_master=v['master'],xy=[s['x'],s['y']],capture_ff=len(captures),captures=captures,old_clock_path=trace_parent(pin),old_source_root=M['trees'][s['tree']]['root'],old_clock_path_cells={k:cells[k] for k in trace_parent(pin) if k in cells})
 entries[inst]=entry;regions[s['tree']].append(inst)
def feasible(group):
 pts=[entries[n]['xy'] for n in group]+[c['pins']['CLK']['absolute_xy'] for n in group for c in entries[n]['captures']]
 return sum(entries[n]['capture_ff'] for n in group)<=32 and max(dist(a,b) for a in pts for b in pts)<=320
groups=[];assign={}
for r,names in sorted(regions.items()):
 # Exact input/capture coordinates, stable lexicographic order, no centroid.
 pending=sorted(names,key=lambda n:(entries[n]['xy'][1],entries[n]['xy'][0],n))
 while pending:
  group=[pending.pop(0)]
  for n in pending[:]:
   if feasible(group+[n]):group.append(n);pending.remove(n)
  ident=r+'_p'+str(sum(g['old_region']==r for g in groups))
  pts=[c['pins']['CLK']['absolute_xy'] for n in group for c in entries[n]['captures']]
  anchor=min(group,key=lambda n:(max(dist(entries[n]['xy'],q) for q in pts),n))
  root=entries[anchor]['xy'];g=dict(id=ident,old_region=r,source_root=M['trees'][r]['root'],members=group,capture_ff=sum(entries[n]['capture_ff'] for n in group),entry_pins=len(group),root_reference_pin=entries[anchor]['pin'],root_reference_xy=root,max_root_capture_l1_um=max(dist(root,q) for q in pts),capture_diameter_l1_um=max(dist(a,b) for a in pts for b in pts),root_legal_pg_site=None,native_phase=None)
  groups.append(g)
  for n in group:assign[n]=ident
allinst=collections.defaultdict(set)
for pin,s in M['sinks'].items():allinst[pin.rsplit('/',1)[0]].add(s['tree'])
# Monotone split fixed point: every newly crossed reset receiver needs the
# separately priced two-stage, THREE-FF native landing. Count clock loads too.
iterations=0
while True:
 iterations+=1;extra=collections.Counter()
 for net,v in N['nets'].items():
  for a in [q for q in v['pins'] if q['io']=='OUTPUT']:
   for b in [q for q in v['pins'] if q['io']=='INPUT']:
    ai,bi=a['inst'],b['inst']
    if ai in entries and bi in entries and entries[ai]['region']==entries[bi]['region'] and assign[ai]!=assign[bi]:extra[bi]+=LAND_FF
 changed=False;nextgroups=[]
 for g in groups:
  if sum(entries[n]['capture_ff']+extra[n] for n in g['members'])<=31:nextgroups.append(g);continue
  changed=True;remaining=list(g['members']);pieces=[]
  while remaining:
   ns=[remaining.pop(0)]
   for n in remaining[:]:
    if sum(entries[k]['capture_ff']+extra[k] for k in ns+[n])<=31:ns.append(n);remaining.remove(n)
   ident=g['id']+'_s'+str(len(pieces));ng=dict(g,id=ident,members=ns);pieces.append(ng)
   for n in ns:assign[n]=ident
  nextgroups.extend(pieces)
 groups=nextgroups
 if not changed:break
 assert iterations<332
for g in groups:
 pts=[c['pins']['CLK']['absolute_xy'] for n in g['members'] for c in entries[n]['captures']]+[q['xy'] for n in g['members'] for q in N['instances'][n]['pins'] if q['pin']=='d' and extra[n]]
 anchor=min(g['members'],key=lambda n:(max(dist(entries[n]['xy'],q) for q in pts),n))
 g.update(capture_ff=sum(entries[n]['capture_ff'] for n in g['members']),conditional_landing_ff=sum(extra[n] for n in g['members']),clock_load_ff=sum(entries[n]['capture_ff']+extra[n] for n in g['members']),entry_pins=len(g['members']),root_reference_pin=entries[anchor]['pin'],root_reference_xy=entries[anchor]['xy'],max_root_capture_l1_um=max(dist(entries[anchor]['xy'],q) for q in pts),capture_diameter_l1_um=max(dist(a,b) for a in pts for b in pts))
 oldroot=M['root_buffer'][g['source_root']];xy=cells[oldroot]['xy'];length=dist(xy,g['root_reference_xy'])
 g.update(existing_source_root_buffer=oldroot,existing_source_buffer_xy=xy,source_to_candidate_l1_floor_um=length,minimum_405_clock_segments=max(1,math.ceil(length/405)),accepted_eight_su_parent_root=None)
edges=[]
for net,n in sorted(N['nets'].items()):
 src=[q for q in n['pins'] if q['io']=='OUTPUT'];dst=[q for q in n['pins'] if q['io']=='INPUT']
 for a in src:
  for b in dst:
   if a['inst']==b['inst']:continue
   ao=sorted(allinst[a['inst']]);bo=sorted(allinst[b['inst']]);an=assign.get(a['inst']);bn=assign.get(b['inst']);sameold=len(ao)==len(bo)==1 and ao==bo
   crossing=bool((an or bn) and ((an and bn and an!=bn) or (not(an and bn))))
   e=dict(net=net,source=a,capture=b,old_source_roots=ao,old_capture_roots=bo,new_source=an,new_capture=bn,new_crossing=crossing,newly_crossed=sameold and crossing,signal_class='reset' if b['pin'] in ['d','rst','rst_i','reset','reset_n','rsi'] or net.startswith('n_rst') else 'unclassified',pin_l1_um=dist(a['xy'],b['xy']),minimum_405_segments=math.ceil(dist(a['xy'],b['xy'])/405),qualified_physical_route=None,native_phase=None,first_use_epoch=None)
   edges.append(e)
new=[e for e in edges if e['newly_crossed']];cross=[e for e in edges if e['new_crossing']]
assert len(edges)==len({(e['net'],e['source']['inst'],e['source']['pin'],e['capture']['inst'],e['capture']['pin']) for e in edges})
for e in new:
 e['conditional_new_receiver_landing']=dict(native_master='qfd_rst_rep',ff=LAND_FF,plain_ff_area_floor_um2=LAND_FF*.2916,native_frame_area_um2=12.96*6.48,extra_receiver_edges=2,old_receiver_latency_edges=10 if entries[e['capture']['inst']]['native_master'].endswith('p8') else 2,new_receiver_latency_edges=12 if entries[e['capture']['inst']]['native_master'].endswith('p8') else 4,async_assert_hardware=None,all_corner_aperture=None,pulse_stretch=None,clock_root=assign[e['capture']['inst']],placement=None)
def delta(n,stack=()):
 assert n not in stack
 es=[e for e in edges if e['capture']['inst']==n and e['source']['inst'] in entries]
 return max([delta(e['source']['inst'],stack+(n,))+(2 if e['newly_crossed'] else 0) for e in es] or [0])
local_extra_max=max(delta(n) for n in entries)
def longest(n):
 es=[e for e in edges if e['capture']['inst']==n and e['source']['inst'] in entries]
 if not es:return []
 e=max(es,key=lambda e:delta(e['source']['inst'])+(2 if e['newly_crossed'] else 0))
 return longest(e['source']['inst'])+[e]
end=max(entries,key=delta);path=longest(end)
(P/'longest_conditional_release_path.json').write_text(json.dumps(dict(start=path[0]['source'] if path else None,end=end,additional_edges=local_extra_max,reset_owners=[dict(instance=n,region=entries[n]['region'],new_group=assign[n],old_source_root=entries[n]['old_source_root'],old_repeat_latency=10 if entries[n]['native_master'].endswith('p8') else 2) for n in ([path[0]['source']['inst']]+[e['capture']['inst'] for e in path] if path else [end])],connections=path,source_absolute_epoch=None,capture_absolute_epoch=None,producer_pulse19_20_same_domain_proof=None),indent=1)+'\n')
assert all(feasible(g['members']) for g in groups)
summary=dict(model='candidate physical partition; native phase/PG/epochs HOLD',old_regions=len(regions),entries=len(entries),capture_ff=sum(v['capture_ff'] for v in entries.values()),masters=dict(collections.Counter(v['native_master'] for v in entries.values())),proposed_groups=len(groups),additional_groups=len(groups)-len(regions),group_capture_ff_max=max(g['capture_ff'] for g in groups),root_capture_l1_max_um=max(g['max_root_capture_l1_um'] for g in groups),existing_incident_directed_bits=len(edges),all_incident_crossings=len(cross),newly_crossed_directed_bits=len(new),new_crossed_nets=len({e['net'] for e in new}),new_crossed_classes=dict(collections.Counter(e['signal_class'] for e in new)),new_crossed_pin_l1_max_um=max(e['pin_l1_um'] for e in new),crossing_nets_2ff_floor=2*len({e['net'] for e in new}),new_destinations_2ff_conservative=2*len(new),storage_four_slot_ff_if_misapplied=4*len(new),new_routed_wire_um=None,new_clock_buffers=None,new_pg_connections=None,absolute_reset_epoch=None,su_added_edges=None,mu_added_edges=None,total_area_um2=None)
summary.update(distinct_net_destination_groups=len({(e['net'],e['new_capture']) for e in new}),conditional_plain_ff_landing_area_floor_um2=round(2*len(new)*0.2916,8),conditional_new_reset_release_max_selected_subgraph_edges=local_extra_max,groups_per_old_root_max=max(collections.Counter(g['old_region'] for g in groups).values()),new_crossed_existing_pin_l1_sum_um=sum(e['pin_l1_um'] for e in new),old_selected_ff_area_um2=round(sum(v['capture_ff'] for v in entries.values())*.2916,8))
summary.update(partition_fixedpoint_iterations=iterations,group_capture_plus_landing_ff_max=max(g['clock_load_ff'] for g in groups))
summary.update(source_to_subroot_l1_sum_floor_um=sum(g['source_to_candidate_l1_floor_um'] for g in groups),source_to_subroot_l1_max_floor_um=max(g['source_to_candidate_l1_floor_um'] for g in groups),source_to_subroot_min405_segments=sum(g['minimum_405_clock_segments'] for g in groups))
summary.update(conditional_exact_native_landing_ff=LAND_FF*len(new),conditional_native_ff_area_floor_um2=round(LAND_FF*len(new)*.2916,8),conditional_native_frame_area_um2=round(len(new)*12.96*6.48,8),conditional_new_landing_clock_ports=len(new),conditional_new_landing_unbound_pg_iterms_if_original_reused=6*len(new))
for k in ['crossing_nets_2ff_floor','new_destinations_2ff_conservative','storage_four_slot_ff_if_misapplied','conditional_plain_ff_landing_area_floor_um2']:
 summary.pop(k)
for name,x in [('entries',entries),('groups',groups),('edges',edges),('summary',summary)]: (P/(name+'.json')).write_text(json.dumps(x,indent=1)+'\n')
with (P/'groups.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['id','old_region','source_root','entry_pins','capture_ff','root_reference_pin','root_reference_xy','max_root_capture_l1_um','capture_diameter_l1_um','members'],extrasaction='ignore');w.writeheader();w.writerows(groups)
print(json.dumps(summary,indent=1))
