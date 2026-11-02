from pathlib import Path
import json,gzip,collections
r=Path('/srv/opentallas-scratch/claude')
a10=json.load(gzip.open(r/'codex-qc-core-nio-a10-sites-1102/A10_READER_SITE_PROPOSAL.json.gz'))
a11=json.load(gzip.open(r/'codex-qc-core-nio-a11-sites-1102/A11_READER_SITE_PROPOSAL.json.gz'))
rt=r/'codex-qc-core-nio-a11-sites-1102'
g=json.load(gzip.open(rt/'source.json.gz')); bo=json.load(gzip.open(rt/'bounds.json.gz'))
co=json.load(gzip.open(rt/'constraints.json.gz')); geo=json.load(open(rt/'geometry.json'))
seed={x['ff'] for x in a10['failed']+a11['failed']};edges=bo['edges'];adj=collections.defaultdict(set)
for a,b in edges: adj[a].add(b);adj[b].add(a)
mov=seed|{v for f in seed for v in adj[f]};sites={x['ff']:x for x in a11['rows']};fixed={};nodes={}
for ff,n in g['ff_nodes'].items():
    w=1.404 if 'DFFASR' in n['type'] else 1.08
    row={'ff':ff,'name':n['name'],'type':n['type'],'width_um':w,'height_um':.27,'clock_net':n['connections']['CLK']}
    if ff in mov:
        row['uv_bounds']=bo['bounds'][ff];row['fixed_endpoint_constraints']=co['FF_macro_constraints'].get(ff,[])
        row['prior_center_um']=sites.get(ff,{}).get('center_um');nodes[ff]=row
    elif ff in sites: row['center_um']=sites[ff]['center_um'];fixed[ff]=row
    else: raise ValueError(('failed_outside_movable',ff))
cut=[e for e in edges if any(f in mov for f in e)]
out=r/'codex-qc-core-nio-joint-source-1102';out.mkdir(exist_ok=True)
packet={'status':'FINITE_NATIVE_SITE_SOURCE_REPAIR_PREP_NOT_PLACEMENT_OR_EQUIVALENCE','geometry':geo,'movable':nodes,'immutable':fixed,'edges':cut,'native_site_um':[.054,.27],'site_center_rule':'X centers aligned0.054; Y centers0.135+row*0.27. Typed FF widths1.08/1.404, not1.728 packing-envelope pitch.','reach_budgets_um':{'FF_center':399,'macro_center_default':402,'type_pin_center':149},'seed_failures':sorted(seed),'unqualified':['same-edge +1 qv copy is model only; no source/nativecount/function credit','48 reset-source FFs/126edges held for ordinary reset rederivation','A11 pairedN/F3S window remap69.12um; LC/CA/provider/clock/boot/view/pinPG/parent ABI held']}
with gzip.open(out/'FINITE_JOINT_PROBLEM.json.gz','wt') as f:json.dump(packet,f,separators=(',',':'))
s={'source':'A11 greedy sites, A10/A11 failure union +onehop DATA neighbors','A10_failed':len(a10['failed']),'A11_failed':len(a11['failed']),'union_seed_count':len(seed),'movable_count':len(nodes),'immutable_count':len(fixed),'typed_incident_edges':len(cut),'native_site_um':[.054,.27],'prior_packing_pitch_um':[1.728,.27],'same_reach_budgets':True,'status':'FINITE_PROBLEM_EXTRACTED_NO_SOLVER_RESULT'}
(out/'SUMMARY.json').write_text(json.dumps(s,indent=2)+'\n');print(s)
