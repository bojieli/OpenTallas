"""Finish the existing native-table model: upstream cap feedback and full clock.
No coordinate change, native engine, or added electrical assumption.
"""
import json,pathlib,gzip
P=pathlib.Path(__file__).parent
scope={'__file__':str(P/'path_budget.py'),'__name__':'native_budget_reuse'}
exec((P/'path_budget.py').read_text().split('by_source=')[0],scope)
stage=scope['stage'];native=scope['native'];plan=scope['plan']
up=json.load(open(P/'upstream_fixedpoint.json'));j=json.load(open(P/'model.json'));out=[]
for row in up:
 d=row['driver'];corners={}
 for c in ('TT','FF'):
  v=row['corner'][c];corners[c]=stage(c,d['cell'],d['pin'],v['new_all_sink_pin_cap_plus_nominal_wire_fF'])
 out.append(dict(upstream_net=row['upstream_net'],driver=d,exact_stronger_inputs=row['replaced_inv_inputs'],native_stage_bounds=corners,incoming_slew_and_output_wire='Actual unqualified; full native input domain bound only'))
clock=[];cc=j['fresh_clock']['clock_leaf_models']
for row in cc:
 root=row['driver'];bycorner={}
 for c in ('TT','FF'):
  load=row['total_model_fF'][c];bycorner[c]=stage(c,root,'Y',[load,load])
 clock.append(dict(driver=root,sinks=row['sinks'],nominal_pin_plus_RMST_wire_load_fF=row['total_model_fF'],native_stage_bounds=bycorner))
summary=dict(schema='int8.source_owned.upstream_clock_native.v1',upstream_owners=len(out),upstream_native_refused=sum(v['status'].startswith('REFUSE') for r in out for v in r['native_stage_bounds'].values()),full_clock_output_trees=len(clock),clock_native_refused=sum(v['status'].startswith('REFUSE') for r in clock for v in r['native_stage_bounds'].values()),clock_RMST_um=sum(r['RMST_um'] for r in cc),clock_RMST_nominal_wire_fF=sum(r['nominal_clock_wire_fF'] for r in cc),phase_and_actual_RC_qualification=False,PG_and_joint_cut_qualification=False,actual_upstream_fixedpoint=False)
(P/'upstream_clock_native_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(P/'upstream_clock_native.json.gz','wt') as f:json.dump(dict(upstream=out,clock=clock),f)
print(json.dumps(summary,indent=2))
