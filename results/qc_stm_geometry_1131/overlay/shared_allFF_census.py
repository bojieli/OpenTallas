import json,gzip,collections,math,pathlib
B=pathlib.Path(__file__).resolve().parent.parent;O=B/'overlay';P=json.load(gzip.open(O/'finite_window_shared.json.gz'));S=json.load(gzip.open(O/'semantic_window_membership.json.gz'));F=json.load(gzip.open(O/'forwarded_FF_window_membership.json.gz'));M=json.load(gzip.open(O/'native_all_FF_masters.json.gz'));G=json.load(gzip.open(B/'native_graph_r5.json.gz'));T=json.load(open(O/'type_overlay.json'));Q=json.load(gzip.open(B/'private_proposal_v2.json.gz'))
def area(r):return max(0,r[2]-r[0])*max(0,r[3]-r[1])
def inter(a,b):return [max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
def bound(a,b):return max(abs(x-u)+abs(y-v) for x in (a[0],a[2]) for y in (a[1],a[3]) for u in (b[0],b[2]) for v in (b[1],b[3]))
def cellarea(ns):return sum(math.prod(G['native_DFF_bboxes_um'][M[n]['master']]) for n in ns)
regions=[]
for x in S['groups']:
 if not x['existing_whole_cell_window_um']:continue
 ns=x['native_named_FFs'][:]
 if x['group'].startswith('landing_'):
  bus=x['group'][8:];ns += next(z['exact_named_FFs'] for z in F['records'] if z['bus']==bus)
 regions.append(dict(name=x['group'],kind='existing_semantic_intent',window_um=x['existing_whole_cell_window_um'],native_named_FFs=ns))
for x in P['new_private_regions']:regions.append(dict(name=x['group']+':'+str(x['tile']),kind=x['kind'],window_um=x['window_um'],native_named_FFs=x['native_named_FFs'],connectivity=x['actual_connectivity']))
allnames=[n for z in regions for n in z['native_named_FFs']];assert len(allnames)==68857 and len(set(allnames))==68857 and set(allnames)==set(M)
for z in regions:
 ns=z['native_named_FFs'];z['actual_FF_count']=len(ns);z['actual_master_counts']=dict(collections.Counter(M[n]['master'] for n in ns));z['actual_clock_root_counts']=dict(collections.Counter(','.join(M[n]['clock_roots']) for n in ns));z['actual_FF_area_um2']=cellarea(ns);r=z['window_um'];z['FF_area_fraction_in_own_window']=z['actual_FF_area_um2']/area(r);mw=max(G['native_DFF_bboxes_um'][M[n]['master']][0] for n in ns);z['conservative_row_capacity']=math.floor((r[2]-r[0]+1e-8)/mw)*math.floor((r[3]-r[1]+1e-8)/.27);z['row_fit']=z['conservative_row_capacity']>=len(ns)
 z['whole_window_radius200_homes']=[h['name'] for h in T['clock']['taps'] if max(abs(h['xy'][0]-x)+abs(h['xy'][1]-y) for x in (r[0],r[2]) for y in (r[1],r[3]))<=200]
 z['clock_home_status']='GEOMETRIC candidates ONLY; actual nearest load and source identity UNQUALIFIED. Forwarded-root cells stay on exact fclk_in_*.'
# Each unique FF is priced once in ONE intent region; overlaps combine densities, not duplicated memberships.
ov=[]
for i,a in enumerate(regions):
 for b in regions[i+1:]:
  r=inter(a['window_um'],b['window_um'])
  if area(r)>1e-8:ov.append(dict(a=a['name'],b=b['name'],intersection_um=r,overlap_area_um2=area(r),projected_uniform_FF_area_fraction_sum=a['FF_area_fraction_in_own_window']+b['FF_area_fraction_in_own_window']))
# Conservative rectangular bounds on actual bank/stage graph, not new cycle/timing proof.
def union(rr):return [min(x[0] for x in rr),min(x[1] for x in rr),max(x[2] for x in rr),max(x[3] for x in rr)]
ft=collections.defaultdict(lambda:collections.defaultdict(list));stream=collections.defaultdict(list)
for x in P['new_private_regions']:
 ev=x['actual_connectivity']
 if x['kind']=='FT':ft[ev['slot']][ev['stage']].append(x['window_um'])
 if x['kind']=='stream':stream[ev['bank']].append(x['window_um'])
edges=[]
for bank,st in ft.items():
 for k in sorted(st):
  if k+1 in st:edges.append(dict(kind='actual_adjacent_FT_stages',source=bank+':'+str(k),target=bank+':'+str(k+1),conservative_window_bound_um=bound(union(st[k]),union(st[k+1]))))
for a,ss in G['stream_native_bank_dependencies'].items():
 for b,n in ss.items():
  if a in stream and b in stream:edges.append(dict(kind='actual_native_stream_bank_dependency',source=a,target=b,actual_dependency_count=n,conservative_window_bound_um=bound(union(stream[a]),union(stream[b]))))
summary={'scope':'NEW private shared-soft-row planning proposal; NO GEN/CAD, no qualified clock assignment','native_FF_total':68857,'unique_named_FF_total':len(set(allnames)),'local_clk_FFs':52609,'forwarded_root_FFs':16248,'local_clk_FF_area_um2':cellarea([n for n in M if M[n]['clock_roots']==['clk']]),'forwarded_FF_area_um2':F['area_um2'],'all_FF_area_um2':sum(z['actual_FF_area_um2'] for z in regions),'actual_nonFF_standard_cell_area_um2':10691.5869,'nonFF_regional_allocation':'UNRESERVED requirement; FF-only row occupancy DOES NOT establish whole-logic regional capacity','regions':len(regions),'unallocated_native_FFs':0,'failed_conservative_row_fits':sum(not z['row_fit'] for z in regions),'overlap_pairs':len(ov),'max_projected_pair_uniform_FF_fraction':max((z['projected_uniform_FF_area_fraction_sum'] for z in ov),default=0),'density_caveat':'Uniform area projection over soft windows, NOT actual cell placement; pair sum assumes no concealed shared FF identity. Exact named membership attached, everyFFpricedonce. NonFF/clocktree placement remains unpriced regionally.','unchanged_clock_endpoints':76,'native_clock_sources_connections_unchanged':True,'max_conservative_FT_window_bound_um':max((x['conservative_window_bound_um'] for x in edges if x['kind']=='actual_adjacent_FT_stages'),default=0),'max_conservative_stream_window_bound_um':max((x['conservative_window_bound_um'] for x in edges if x['kind']=='actual_native_stream_bank_dependency'),default=0),'over405_conservative_window_edges':sum(x['conservative_window_bound_um']>405 for x in edges),'reach_status':'Conservative region-cartesian bound only; sparse native bit-level paths and actual placed first-capture/r2r remain unmeasured. No automatic extra cycles or source fixes.'}
(O/'shared_allFF_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(O/'shared_allFF_membership.json.gz','wt') as f:json.dump(dict(summary=summary,regions=regions,overlap_occupancy=ov,actual_native_graph_window_bounds=edges),f,indent=1)
with open(O/'shared_allFF_regions.tsv','w') as f:
 f.write('region\tFFs\tactual_FF_area_um2\twindow_area_um2\tprojected_FF_fraction\trow_fit\tclock_roots\n')
 for z in regions:f.write('\t'.join(map(str,[z['name'],z['actual_FF_count'],z['actual_FF_area_um2'],area(z['window_um']),z['FF_area_fraction_in_own_window'],z['row_fit'],z['actual_clock_root_counts']]))+'\n')
print(json.dumps(summary))
