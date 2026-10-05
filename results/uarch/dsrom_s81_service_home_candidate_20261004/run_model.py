import gzip,json,hashlib
from pathlib import Path
from dsrom_s81_service_home_candidate import candidate
p=Path(__file__).resolve().parent
r=p/'inputs'
def load(n):return json.loads((r/n).read_text())
demand=json.load(gzip.open(r/'demand-r5.json.gz','rt'))
bindings=[json.loads(line) for line in gzip.open(r/'node_bindings.jsonl.gz','rt')]
model=candidate(demand,bindings,load('stage_map.json'),load('providers.json'),
                json.loads((p/'field_fragments.json').read_text()),load('link.json'),load('component.json'),
                protected_group=load('protected.json'),die_screen=load('die_screen.json'),
                template={'su_mm2':12.80594,'att_mm2':45.86549,'idx_mm2':7.52245,
                          'vm_mm2':0.89234,'hc_mm2':18.31349,'collective_mm2':1.38967,
                          'gather_mm2':1.38823,'capture_mm2':0.10868,'scope':'representative scan template, not all324 installed replicas'},
                enable=True)
model['input_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in r.iterdir() if f.is_file()}
model['tool_sha256']={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['dsrom_s81_service_home_candidate.py','dsrom_s81_unified_components.py','run_model.py']}
(p/'candidate.json').write_text(json.dumps(model,indent=2)+'\n')
print('candidate nonfield_nodes',len(model['assignments']),'runs',len(model['ordered_nonfield_runs']),'field_ops',len(model['field_movements']))
print('transport_only_analytical_us',model['analytical_packet_transfer_ns']/1000,'raw_bytes_rank_L20',model['bytes_per_rank_by_layer'][20])
print('L20_nonfield_stage',model['homes'][20],'field_stages',sorted({s for m in model['field_movements'] if m['node'].startswith('L20.') for s in m['field_stages']}))
print('area', {k:v for k,v in model['physical_service_union'].items() if k in ['protected_VM_outline_mm2','die_lower_bound_mm2','over_reticle_at_least_mm2','over_2pct_margin_at_least_mm2','fits_reticle']})
print('verdict INFEASIBLE_PROTECTED_SERVICE_SLOT parent_dispatch_ready=False; all existing jobs untouched')
