"""Guarded N-only NB sidecar translation. Usage: IN OUT M_PLAN N_PLAN. Refuses stale sidecar coordinates."""
import json,sys,hashlib
from pathlib import Path
src,out,mp,np=map(Path,sys.argv[1:5]);assert src.resolve()!=out.resolve()
d=json.loads(src.read_bytes());m=json.load(open(mp));n=json.load(open(np));tn='cbn_q00__cldbcda913'
assert hashlib.sha256(mp.read_bytes()).hexdigest()=='beaa07b778ce233b9608c48ee0c843c59e03a1490ae57a0e917e4091d27702ad'
assert hashlib.sha256(np.read_bytes()).hexdigest()=='d99a1840f308911fc1f90e64f540b99693d2a4ae715c91c67914ff0aea33b72e'
a=m['partition_types'][tn]['clock']['landing_contract'];b=n['partition_types'][tn]['clock']['landing_contract'];r=d['collector']['types'][tn]
def source(row):return next(s for s in row if s['name']=='nb_i00')
triples=[(r['bands']['nb_i00'],a['bands']['nb_i00'],b['bands']['nb_i00']),(source(r['local_sources'])['band'],source(a['collector_local_sources'])['band'],source(b['collector_local_sources'])['band'])]
for side,old,new in triples:
 assert side['instance']==old['instance']==new['instance']=='u_cland_nb_i00'
 assert side['rect_um']==old['rect_um'], 'Refuse stale M sidecar band; regenerate or reconcile source bands before N'
 for key in ('rect_um','max_pin_to_band_hop_um'):side[key]=new[key]
out.write_text(json.dumps(d,indent=1)+'\n')
print(json.dumps(dict(input=str(src),input_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),output=str(out),output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),changed_fields='Two NB rect x0/x2 pairs and two derived maximum-hop metadata values',preserved='Source xy/node/tap, native tree, cycle/count values, all other types')))
