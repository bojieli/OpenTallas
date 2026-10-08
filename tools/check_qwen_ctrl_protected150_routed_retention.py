import re,json,hashlib,argparse
from pathlib import Path

def audit(path):
 s=Path(path).read_text();errs=[]
 cells=[]
 for m in re.finditer(r'^\s*(DFF\w+)\s+(\\\S+|\S+)\s+\((.*?)\);',s,re.M|re.S):
  ports={k:v.strip() for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',m[3])}
  cells.append(dict(type=m[1],name=m[2].lstrip('\\'),q=ports.get('Q',ports.get('QN')),d=ports.get('D')))
 replicas=[];qsets=[]
 for g in range(2):
  prefix=f'u.g_replica[{g}].u/';ff=[c for c in cells if c['name'].startswith(prefix)]
  if len(ff)!=2355:errs.append(f'replica{g} FFcount {len(ff)} !=2355')
  qs={c['q'] for c in ff};qsets.append(qs)
  if None in qs or len(qs)!=len(ff):errs.append(f'replica{g} duplicate ormissing FF outputs')
  critical=[]
  targets=['head','core.on.write_ready_bank']+[f'core.on.wq_oh[{i}]' for i in range(4)]
  for name in targets:
   bitset=set();selected=[]
   pattern=re.compile(re.escape(prefix+name)+r'\[(\d+)\]\$_DFF')
   for c in ff:
    m=pattern.match(c['name'])
    if m:bitset.add(int(m[1]));selected.append(c)
   if bitset!=set(range(32)):errs.append(f'replica{g} {name} missing/aliased bits {sorted(bitset)}')
   critical.extend(selected)
  replicas.append(dict(root=prefix,ff_cells=len(ff),critical_roots=critical))
 if qsets[0]&qsets[1]:errs.append('cross-replica FF output alias')
 guards=[c for c in cells if c['name'].startswith(('u.trip_seen$','u.permit_state$'))]
 if len(guards)!=2 or len({c['q'] for c in guards})!=2:errs.append('sticky guard roots absent/merged')
 return dict(status='PASS_MAPPED_STATE_RETENTION' if not errs else 'FAIL_MAPPED_STATE_RETENTION',stage='actual routed6_final.v',netlist_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),total_ff=len(cells),replicas=replicas,guard_roots=guards,errors=errs,claim='Actual separately named FF instances and disjoint output nets for both2355-state replicas and2halt rails; all192critical state bits perreplica retain distinct mapped FF roots.',limits=['No analog or common-mode fault coverage','This retention result does not override failing SS/FF or refresh-handoff gates'])
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('netlist');ap.add_argument('--out',required=True);a=ap.parse_args();r=audit(a.netlist);Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k not in ('replicas','guard_roots')});raise SystemExit(bool(r['errors']))
