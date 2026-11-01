import json,gzip,re,collections,pathlib,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=pathlib.Path('/srv/opentallas-scratch/claude/wt/codex-qc-tload-protocol-1131/results/qc_stm_geometry_1131');o=b/'overlay';q=json.load(gzip.open(b/'private_proposal_v2.json.gz'));g=json.load(gzip.open(b/'native_graph_r5.json.gz'));t=json.load(open(o/'type_overlay.json'));old=json.load(open(o/'density_failure_census.json'));bands=q['landing_bands_entire_cell_bbox_um'];rom={n:k.rsplit('.',1)[-1] for k,v in g['ROM_first_capture_cells'].items() for n in v};pub=json.load(gzip.open(o/'native_export_launch_manifest.json.gz'));pubnames={r['last_native_launch_FF'] for x in pub['exports'] if x['data_port']=='b_tw_data_ctl_o' for r in x['bits']};rows=collections.defaultdict(list);windows={};reasons={}
for n in g['local_clock_cells']:
 key=None;box=None;why=''
 if n in pubnames:key='N_publication';box=q['N_publication_box'];why='actual per-bit exported publication last-launch manifest'
 elif n in rom:key='ROM_first_capture_'+rom[n];box=q['ROM_capture_boxes'][rom[n]];why='actual registered ROM support first-capture manifest'
 elif re.match(r'u_bound\.u_core\.tw_(data|addr|kind|we)(?:\[|\$)',n):key='core_publication_relay';box=q['core_publication_relay_box'];why='actual source named existing core tw_* register bank (1051)'
 else:
  for bus,r in bands.items():
   if n.startswith('u_bound.u_cland_'+bus+'.') or n.startswith('u_bound.u_bin_'+bus+'.') or re.match(r'u_bound\.u_pd\d+_'+re.escape(bus)+r'_\d+\.',n):key='landing_'+bus;box=r;why='actual native input-ring/post-ring/boundary bus role with same declared band';break
 if key is None:
  if '.u_stream.' in n:key='UNRESOLVED_stream_'+re.sub(r'\[\d+\]','[*]',n.split('u_stream.',1)[1].split('$_')[0]);why='actual stream bank/consumer graph known; prior proposal only point anchor, no declared whole-cell bank window'
  elif '.u_ft_' in n:key='UNRESOLVED_FT_'+n.split('.')[1];why='exact FT stage/coordinate known; no declared finite whole-bank target window'
  elif '.u_tload.' in n:key='UNRESOLVED_tload_control';why='not in actual ROM first-capture manifest; cannot assume a ROM data-capture window'
  elif n.startswith(('u_bound.u_bin_','u_bound.u_bout_')):key='UNRESOLVED_boundary_'+n.split('.')[1];why='native bus role known; no whole-cell capture/publication window declared for this bus'
  else:key='UNRESOLVED_control_reset_'+n.split('.')[1];why='actual existing reset/start/collector vertex known; source planned point is not declared whole-cell window'
 rows[key].append(n);reasons[key]=why
 if box is not None:windows[key]=box
assert sum(map(len,rows.values()))==52609;assert len({n for v in rows.values() for n in v})==52609
homes=[(z['name'],z['xy']) for z in t['clock']['taps']];tab=[]
def mindist(p,r):return max(r[0]-p[0],0,p[0]-r[2])+max(r[1]-p[1],0,p[1]-r[3])
def maxdist(p,r):return max(abs(p[0]-x)+abs(p[1]-y) for x in (r[0],r[2]) for y in (r[1],r[3]))
for key,ns in sorted(rows.items()):
 r=windows.get(key);tab.append({'group':key,'native_FF_count':len(ns),'native_named_FFs':ns,'existing_whole_cell_window_um':r,'role_evidence':reasons[key],'potential_endpoint_homes_radius200':([n for n,p in homes if mindist(p,r)<=200] if r else[]),'entire_window_endpoint_homes_radius200':([n for n,p in homes if maxdist(p,r)<=200] if r else[]),'minimum_1200_capacity_groups':math.ceil(len(ns)/1200),'status':'semantic window resolved; estimated geometry ONLY' if r else'UNRESOLVED finite window'})
known=sum(len(rows[k]) for k in windows);summary={'native_total':52609,'exact_no_duplicate':True,'resolved_FFs':known,'unresolved_FFs':52609-known,'resolved_windows':len(windows),'unresolved_groups':len(rows)-len(windows),'existing_clock_endpoints':76,'unchanged_endpoint_homes':True,'no_new_standard_GEN_report':True,'full_coverage':'UNPROVEN: finite whole-cell windows absent for unresolved native groups. Point anchors cannot support a physical density qualification.','remaining_plan_problem':{'empty_targets':old['empty'],'overload_targets':old['overloaded'],'radius_excess':old['overradius']},'no_clock_identity_credit':True}
with gzip.open(o/'semantic_window_membership.json.gz','wt') as f:json.dump({'summary':summary,'groups':tab},f,indent=1)
(o/'semantic_window_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with open(o/'semantic_window_table.tsv','w') as f:
 f.write('group\tnative_FFs\twindow_status\tpotential_homes\tentire_window_homes\tcapacity_groups\trole_evidence\n')
 for x in tab:f.write('\t'.join(map(str,[x['group'],x['native_FF_count'],x['status'],len(x['potential_endpoint_homes_radius200']),len(x['entire_window_endpoint_homes_radius200']),x['minimum_1200_capacity_groups'],x['role_evidence']]))+'\n')
fig,axs=plt.subplots(1,2,figsize=(13,12));bad=set(old['empty'])|set(old['overloaded'])
for a in axs:
 a.add_patch(Rectangle((0,0),311.04,613.44,fill=False));a.set(xlim=(-8,319),ylim=(-8,622),aspect='equal',xlabel='um',ylabel='um')
 for h in t['hard_cores']:
  x,y=h['origin_um'];a.add_patch(Rectangle((x,y),121.848,62.952,fc='#ddd',ec='black'))
 for n,p in homes:a.plot(*p,'rx' if n in bad else'b.',ms=4);a.text(p[0]+1,p[1]+1,n.replace('clk','t'),fontsize=5)
for x in old['rows']:
 if x['port'] in bad:axs[0].text(x['x']+1,x['y']-4,str(int(x['estimated_load'])),fontsize=5,color='red')
for name,r in windows.items():
 a=axs[1];a.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc='green',alpha=.12,ec='green'));a.text((r[0]+r[2])/2,(r[1]+r[3])/2,name.replace('landing_',''),fontsize=5,ha='center')
axs[0].set_title('Existing target homes: 12 empty / 4 overload\nLatest failed ESTIMATED density; no CAD')
axs[1].set_title(f'Semantic finite windows: {known:,} resolved FFs\n{52609-known:,} unresolved: explicit planning problem')
fig.suptitle('PRIVATE STM semantic-window proposal — no endpoint/source/count changes\nGreen = existing whole-cell windows; red targets require planning, not a waiver',fontsize=11);fig.tight_layout(rect=(0,0,1,.94));fig.savefig(o/'semantic_window_problem.png',dpi=145);print(json.dumps(summary))
