"""Actual-journal directed binding to parent's finite selected-interval compiler."""
import gzip,hashlib,importlib.util,json,sys,sqlite3,zlib,tempfile,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
spec=importlib.util.spec_from_file_location('group_calendar',ROOT/'tools/h3_complete_native_calendar.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
SOURCE=BASE.parent/'group128_execution_join_r1'
control=json.loads(gzip.decompress((BASE/'execution.json.gz').read_bytes()))
inventory=json.loads(gzip.decompress((BASE.parent/'portable_input_closure_r1/r34_portable_r4/source_inventory.json.gz').read_bytes()))
program=dict(templates=inventory['native_templates'],instructions=[dict(pc=r['pc'],rank_bindings=r['actual_rank_template_bindings']) for r in inventory['corrected_PC_bindings']])
parent_source=gzip.decompress((SOURCE/'source_inputs/h4_hbm_selected_intervals.py.gz').read_bytes())
expected=json.loads((SOURCE/'source_pins.json').read_bytes())['tools/h4_hbm_selected_intervals.py']['sha256']
if hashlib.sha256(parent_source).hexdigest()!=expected:raise ValueError('parent finite compiler source pin changed')
ns=dict(__name__='retained_parent_interval_compiler',__file__=str(ROOT/'tools/h4_hbm_selected_intervals.py'))
exec(compile(parent_source,'parent-18f632-finite-intervals','exec'),ns)
selected_raw=(SOURCE/'source_inputs/selected_group_call.json.gz').read_bytes()
selected_pin=json.loads((SOURCE/'source_pins.json').read_bytes())['results/uarch/h4_hbm_selected_intervals_20261002/DS_selected_r1/selected_calls.json.gz']
if hashlib.sha256(selected_raw).hexdigest()!=selected_pin['projection_sha256']:raise ValueError('selected call projection pin changed')
selected=json.loads(gzip.decompress(selected_raw))
row=next(r for r in selected['calls'] if (r['PC'],r['rank'])==(control['PC'],control['rank']))
bounds=dict(backend_bound_edges=1,consumer_bound_edges=1,reverse_bound_edges=1)
with tempfile.TemporaryDirectory() as tmp:
 path=Path(tmp)/'events.sqlite'
 with gzip.open(BASE/'events.sqlite.gz','rb') as source,path.open('wb') as output:shutil.copyfileobj(source,output)
 if hashlib.sha256(path.read_bytes()).hexdigest()!=control['journal_uncompressed_sha256']:raise ValueError('actual provider/shared journal archive changed')
 db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
 def reader(journal,start,end):
  for blob, in db.execute('select value from event where journal=? and seq>=? and seq<? order by seq',(journal,start,end)):
   yield json.loads(zlib.decompress(blob))
 bindings=c.bind_executed_group_shared64(control,program,row,'r34-cost-ledger:PC%d:rank%d'%(control['PC'],control['rank']),bounds,journal_reader=reader)
 db.close()
bindings['origin']='Actual df6/r36 backing reads, global source lease, shared64 movement and real two-mirror publication; seeded directed payloads, not full released-checkpoint token'
bindings['actual_source_receipts']=len(control['actual_source_receipts'])
bindings['actual_mirrored_publication']=control['actual_RF_mirror_journal']
bindings['source_global_view_released']=control['source_global_view_released']
result=ns['compose'](dict(selected,calls=[row]),bindings,require_complete=True)
records={'directed_interval_bindings.json.gz':bindings,'directed_finite_intervals.json.gz':result}
verify='--verify' in sys.argv
for name,data in records.items():
 raw=gzip.compress(json.dumps(data,sort_keys=True,separators=(',',':')).encode(),mtime=0);path=BASE/name
 if verify:
  if path.read_bytes()!=raw:raise ValueError('directed source journal/finite interval replay changed')
 else:
  if path.exists():raise ValueError('fresh record required')
  path.write_bytes(raw)
print('PASS_ACTUAL_JOURNAL_TO_PARENT_FINITE_INTERVAL_ABI')
print(json.dumps(dict(call_id=row['call_id'],commands=len(result['intervals']),finite_model_edge_upper=result['selected_movement_retirement_edge_upper'],SW_ticks_to_edges_converted=False,existing_cost_charges_added=result['existing_RF_I64_RMW_C0_provider_charges_added'],complete_token_latency=result['complete_token_latency'],production_calls_closed=0),sort_keys=True))
