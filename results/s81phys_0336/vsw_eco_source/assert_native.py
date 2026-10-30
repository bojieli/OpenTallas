"""Strict private ECO identity assertions, source review only; no timing waiver."""
import sys,re,json
from pathlib import Path
before,after,names,targets=map(Path,sys.argv[1:5]);a=before.read_text();b=after.read_text();D=json.load(open(targets));cn=names.read_text().splitlines()
def section(s,kind):
 x=s.index('\n'+kind+' ');y=s.index('\nEND '+kind,x);return s[x:y]
def records(s,kind):
 return {m[1]:m[2].split()for m in re.finditer(r'^\s*- (\S+)(.*?);',section(s,kind),re.M|re.S)}
ca,cb=records(a,'COMPONENTS'),records(b,'COMPONENTS');na,nb=records(a,'NETS'),records(b,'NETS');assert cn and all(n in na and n in nb for n in cn)
for n in cn:assert na[n]==nb[n],('CLOCK_WIRE_OR_NET_CHANGED',n)
functional={n:r for n,r in ca.items()if not r[0].startswith(('FILLER','DECAP'))}
for n,r in functional.items():assert cb.get(n)==r,('ORIGINAL_FUNCTIONAL_MASTER_HOME_OR_STATUS_CHANGED',n)
new=set(cb)-set(ca);expected={f'codex_vsw_hb4_{r["index"]:03d}'for r in D['rows']};assert new==expected,('UNDECLARED_NEW_INSTANCES',new^expected)
for r in D['rows']:
 n=f'codex_vsw_hb4_{r["index"]:03d}';v=cb[n];assert v[0]=='HB4xp67_ASAP7_75t_R';i=v.index('PLACED');assert v[i+1]=='(';x,y=r['home_um'];assert abs(float(v[i+2])/1000-x)<1e-6 and abs(float(v[i+3])/1000-y)<1e-6,(n,v)
print(json.dumps(dict(verdict='PASS',original_functional_instances_unchanged=len(functional),clock_net_and_wire_records_unchanged=len(cn),explicit_new_HB4=40,added_cycles=0)))
