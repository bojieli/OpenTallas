import json, glob, sys, datetime
B='/home/ubuntu/claude-takeover-20261007/budget-audit-1010/'
frags=[json.load(open(B+f+'.json')) for f in ('hbm_compute','hbm_datactl','qwen_rom','ds_rom') if __import__('os').path.exists(B+f+'.json')]
rows=[]
for f in frags:
    for r in f['rows']: r.setdefault('fragment',f['fragment']); rows.append(r)
order={'INFEASIBLE':0,'GAP':1,'THIN':2,'UNKNOWN':3,'OK':4}
rows.sort(key=lambda r:(order.get(r.get('flag'),5), r.get('tok_s_impact') if isinstance(r.get('tok_s_impact'),(int,float)) else 0))
out=dict(schema='opentallas.budget_audit.v1',generated_utc=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
  method='top-down: required = minimum sustained throughput a unit/interface/port needs on the token critical path (with the overlap the compiled program allows) at the designed tok/s; designed from RTL/spec; measured from RTL benches where present; margin = (measured or designed) / required; flag margin < 1.1 (THIN = 1.0-1.1, GAP < 1.0, INFEASIBLE = structurally cannot reach). No fixed % of HBM peak (owner rule 2026-10-10 06:58).',
  targets={f['fragment']:f.get('target_rates') for f in frags},rows=rows,notes={f['fragment']:f.get('notes',[]) for f in frags})
json.dump(out,open(sys.argv[1],'w'),indent=1)
for r in rows:
    if r['flag']!='OK': print(r['flag'],r['id'],r.get('margin'),r.get('tok_s_impact'),'NEW' if r.get('new_gap') else 'known',r.get('owner_stream'))
