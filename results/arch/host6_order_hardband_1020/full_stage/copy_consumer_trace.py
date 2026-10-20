from pathlib import Path
import json,gzip,collections,hashlib
p=Path('/srv/opentallas-scratch/claude/codex-order-final0720/out');source=p/'source_liberty_graph_identity.json.gz';d=json.load(gzip.open(source,'rt'));terms=d['terminal_index'];copied={'u78242_c0/u_cell','u78242_c1/u_cell','u78243_c0/u_cell','u78243_c1/u_cell'}
roots={i for i,t in enumerate(terms) if t.get('instance') in copied and t['pin']=='QN'};assert len(roots)==4,(len(roots),copied)
rows=[];counts=collections.Counter()
for line in gzip.open(p/'all_nonclock_stage_edges.tsv.gz','rt'):
 if line.startswith('root_id'):continue
 a,b,scope,dist=line.rstrip().split('\t')
 if int(a) not in roots:continue
 root,end=terms[int(a)],terms[int(b)];rows.append(dict(root=root,endpoint=end,scope=scope,L1_um=float(dist)));counts[(root['instance'],end['kind'],end.get('master','PORT'),end['pin'])]+=1
seq={r['instance']:r for r in d['sequential_instances']};mem=[]
for s in seq.values():
 if s['kind']=='synchronous_sram':mem.append(s)
out=p.parent/'copy_trace';out.mkdir(exist_ok=True)
summary=dict(source_identity_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),odb_sha256=d['odb_sha256'],copied_four_physical_cells=sorted(copied),stage_edges=len(rows),macro_stage_edges=[r for r in rows if r['endpoint']['kind']=='memory_data_control'],consumer_counts=[dict(root=k[0],endpoint_kind=k[1],endpoint_master=k[2],endpoint_pin=k[3],count=v) for k,v in counts.items()],macro_pin_inventory=mem,scope='Actual final5_1GRT complete combinational-cone consumers of the four physical HQN copies. Within-pair one-edge convergence theorem is separate. This structural trace does not prove no pre-first-edge macro corruption or reset-valid masking; those remain temporal obligations.')
(out/'summary.json').write_text(json.dumps(summary,indent=2))
with gzip.open(out/'all_consumers.json.gz','wt') as f:json.dump(rows,f,separators=(',',':'))
print('COPY_TRACE',len(rows),'macro_edges',len(summary['macro_stage_edges']))
