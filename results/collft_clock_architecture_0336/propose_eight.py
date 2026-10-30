import json,sys,collections,statistics
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import schema as S,gen_phys as G
B=Path(__file__).parent;allrows=json.loads((B/'clock_sinks.json').read_text());rows=[a for a in allrows if a['root']=='clk'];groups=collections.defaultdict(list)
for a in rows:groups[a['name'].split('/')[0]].append(a)
# Eight actual external clock BTerms, two per populated station band. No buffer is reclassified as a root.
coords=[(365,17.28),(120,17.28),(120,331.2),(365,331.2),(120,662.4),(365,662.4),(120,976.32),(365,976.32)]
raw=dict(schema='opentallas.die_plan.v1',die=dict(name='qwen_compute',outline_um=[17000,17000],reach_um=405),partition_types={'collft':dict(module='collft',outline_um=[786.24,993.6],clock={})},partitions=[],ports=[],lanes=[])
P=S.Plan(raw);ts=[dict(name='clk'if i==0 else f'clk_t{i}',xy=list(G._snap_tap(P,x,y)))for i,(x,y)in enumerate(coords)]
assignment={};load=collections.Counter();cohorts=[]
for name,rr in sorted(groups.items(),key=lambda p:(-len(p[1]),p[0])):
 x=statistics.median(a['xy'][0]for a in rr);y=statistics.median(a['xy'][1]for a in rr)
 choices=sorted(range(8),key=lambda i:(abs(x-ts[i]['xy'][0])+abs(y-ts[i]['xy'][1]),i))
 j=next((j for j in choices if load[j]+len(rr)<=1500),None)
 assert j is not None,(name,len(rr),load)
 load[j]+=len(rr)
 cohorts.append(dict(name=name,sinks=len(rr),tap=ts[j]['name'],centroid_um=[x,y]))
 for a in rr:assignment[a['name']]=ts[j]['name']
for i,t in enumerate(ts):
 rr=[a for a in rows if assignment[a['name']]==t['name']];t.update(sinks=len(rr),max_direct_L1_um=max(abs(a['xy'][0]-t['xy'][0])+abs(a['xy'][1]-t['xy'][1])for a in rr),actual_clock_body_reserved=False,electrically_qualified=False)
exports={'fclk_out_crec_rx_s1_o':'clk_t6','fclk_out_crec_rx_s2_o':'clk_t6','fclk_out_crec_tx_s1_o':'clk','fclk_out_crec_tx_s2_o':'clk','fclk_out_fltk_o':'clk_t7','fclk_out_fltv_o':'clk_t7'}
report=dict(scope='UNADOPTED SOURCE/MODEL PROPOSAL, NOT BUILD-QUALIFIED',clock_domain='RCLK only',total_sinks=len(rows),max_sinks=max(load.values()),tap_limit=1500,root_count=8,taps=ts,cohorts=cohorts,assignments=assignment,forwarded_domains=collections.Counter(a['root']for a in allrows if a['root']!='clk'),proposed_export_taps=exports,monitor_export='UNRESOLVED actual cland_up source/FSTART/ready co-location required',per_corner_electrical_status={'TT':'NOT RUN; actual pin/C/driver/wire model required','FF':'NOT RUN; actual pin/C/driver/wire model required'},functional_scope='Every actual RCLK sink retained once; every FCLK sink owner unchanged; no state/data/reset cycle change. New per-entry phase and actual-source export relation need qualification.',required_config={'clock.tap_mode':'explicit','clock.tap_max_sinks':1500,'clock.tap_radius_um':200,'OT_TAP_MAX_SINKS':1500},required_physical='Reserve real M7/M6->cell access and all-body-legal clock roots/repeaters; actual remote branches remain >200um before buffering',die_bindings=[dict(part=n,origin_um=o,taps=[dict(port=t['name'],die_xy_um=[t['xy'][0]+o[0],t['xy'][1]+o[1]])for t in ts])for n,o in [('coll_f1',[777.6,6445.44]),('coll_f2',[777.6,7439.04])]])
(B/'eight_entry_proposal.json').write_text(json.dumps(report,indent=1))
print(json.dumps({k:report[k]for k in ('total_sinks','max_sinks','root_count','taps')},indent=1))
