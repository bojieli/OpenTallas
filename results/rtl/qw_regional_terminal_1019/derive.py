"""Bounded postprocessing of preserved existing results, no simulator or source changes."""
import collections,csv,gzip,hashlib,json,pathlib
P=pathlib.Path(__file__).resolve().parent
def read(p):
 q=P/'raw'/p
 return json.loads(gzip.decompress(q.with_suffix(q.suffix+'.gz').read_bytes()) if not q.exists() else q.read_bytes())
rows=[]; summary={}
for mode in ['rA','rB']:
 x=read(f'd/{mode}/die_clock_check.json');m=read(f'd/{mode}/tt/manifest.json');v=read(f'd/{mode}/regional_verdict.json');targets=read('d/targets.json');bad={w[0] for w in v['intra']['worst']}
 for r in sorted(bad):
  ts=[t for t in x['tiles'] if t['region']==r]; ps=[p for p in x['pairs'] if p.get('region_a')==r and p.get('region_b')==r];w=max(ps,key=lambda p:p.get('flop_skew_ps',0));c=x['neighbour_check']['classes']['intra:'+r]
  rows.append(dict(mode=mode,region=r,pairs=c['pairs'],over=c['over'],tt_pair_max=c['tt_ps']['max'],ff_pair_max=c['ff_ps']['max'],tt_full_entry_spread=x['regions'][r]['flop_arrival_ps']['spread'],entries=len(ts),masters=json.dumps(dict(collections.Counter(t['master'] for t in ts)),sort_keys=True),assumed_entries=sum(t['master'] in targets['assumed'] for t in ts),xmin=min(t['x'] for t in ts),xmax=max(t['x'] for t in ts),ymin=min(t['y'] for t in ts),ymax=max(t['y'] for t in ts),local_root=json.dumps(m['local_root_xy'][m['trees'][r]['root']]),worst_tt_pair=json.dumps(w,sort_keys=True)))
 summary[mode]=dict(verdict=v,clock_cells=x['counts']['clock_cells'],topology_branch_load_max=max(collections.Counter(m['parent'].values()).values()),assumed_sink_entries=sum(t['master'] in targets['assumed'] for t in m['sinks'].values()),measured_sink_entries=sum(t['master'] not in targets['assumed'] for t in m['sinks'].values()),failed_master_groups=dict(collections.Counter('includes_CB16' if any(t['master']=='qfd_c_b16_dv' for t in x['tiles'] if t['region']==r) else 'reset_only' if all(t['master'].startswith('qfd_rst_rep') for t in x['tiles'] if t['region']==r) else 'other' for r in bad)))
with (P/'failed_regions.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(P/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print({k:{q:v[q] for q in ['clock_cells','topology_branch_load_max','assumed_sink_entries','measured_sink_entries','failed_master_groups']} for k,v in summary.items()})
