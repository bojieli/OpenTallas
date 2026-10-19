"""Explicit read-only successor policy for endpoint/geometry-free implicit nets."""
def validate_empty_implicit_pg(row):
 assert (row['name'],row['role']) in [('one_','POWER'),('zero_','GROUND')], 'EMPTY_PG_NAME_ROLE_REFUSED'
 for field in ['iterms','bterms','swires','signal_wire_shapes','vias','contacts','native_pin_cap_fF','external_cap_fF']:
  assert row[field]==0, 'NONEMPTY_IMPLICIT_PG_REFUSED '+field
 assert row['signal_wire'] is None, 'NONEMPTY_IMPLICIT_PG_REFUSED signal_wire'
 return True

if __name__=='__main__':
 import json,copy
 from pathlib import Path
 rows=json.loads(Path('/work/output/empty_implicit_pg_nets.json').read_text());results=[]
 for row in rows:
  assert validate_empty_implicit_pg(row)
  for field in ['iterms','bterms','swires','signal_wire_shapes','vias','contacts','native_pin_cap_fF','external_cap_fF','signal_wire','role']:
   bad=copy.deepcopy(row);bad[field]='SIGNAL' if field=='role' else ('present' if field=='signal_wire' else 1)
   try:validate_empty_implicit_pg(bad)
   except AssertionError as exc:results.append({'name':row['name'],'mutant':field,'verdict':'CAUSAL_REFUSAL','reason':str(exc)})
   else:raise AssertionError('EMPTY_PG_MUTANT_SURVIVED '+field)
 Path('/work/output/empty_pg_policy_causal.json').write_text(json.dumps(dict(actual_empty_rows_PASS=len(rows),causal_refusals=results),indent=2)+'\n')
 print('EMPTY_PG_ACTUAL_PASS',len(rows),'CAUSAL_REFUSALS',len(results))
