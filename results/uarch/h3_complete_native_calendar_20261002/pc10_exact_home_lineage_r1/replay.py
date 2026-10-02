"""Exact committed native -> R41 provider -> retained PC10 adapter, no execution."""
from pathlib import Path
import gzip,hashlib,importlib.util,json,sys
from types import SimpleNamespace
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
MAIN=Path(sys.argv[sys.argv.index('--source-root')+1]) if '--source-root' in sys.argv else (ROOT if (ROOT/'tools/h4_hbm_w19_pc10_endpoints.py').is_file() else Path('/home/ubuntu/OpenTallas'));sys.path.insert(0,str(MAIN/'tools'));sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('lineage_calendar',ROOT/'tools/h3_complete_native_calendar.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
import h4_hbm_w19_pc10_endpoints as endpoint
from ds_hbm_storage_home_binding_r41 import bind_storage
native_path=MAIN/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
manifest_path=MAIN/'results/uarch/ds_hbm_connected_source_r37_20261002/inputs/prefix_input_manifest.json.gz'
raw=native_path.read_bytes();native=json.loads(gzip.decompress(raw));manifest=json.loads(gzip.decompress(manifest_path.read_bytes()))
homes=endpoint.decoded(endpoint.inputs(),'homes.json.gz')['homes']
state=gzip.decompress((BASE/'ds_hbm_finite_state_homes_r30.py.gz').read_bytes());binding=gzip.decompress((BASE/'ds_hbm_storage_home_binding_r41.py.gz').read_bytes())
if hashlib.sha256(Path(bind_storage.__code__.co_filename).read_bytes()).hexdigest()!=hashlib.sha256(binding).hexdigest():raise ValueError('actual source binder pin')
bound,bound_homes,directory,report=bind_storage(native,homes,manifest)
provider=SimpleNamespace(native=bound,homes=bound_homes,generation=1,locations={})
try:endpoint.ProductionPC10(provider)
except ValueError as exc:historical_refusal=str(exc)
else:raise ValueError('original extended-directory refusal must remain')
adapter=c.production_pc10_with_home_lineage(endpoint,provider,native,manifest,native_source=raw,state_source=state,binding_source=binding)
try:adapter.ready(0)
except ValueError as exc:actual_PC9_gate=str(exc)
else:raise ValueError('absent actual PC9 bytes must refuse')
proof=adapter.home_lineage
if (proof['original_homes'],proof['bound_homes'],proof['appended_state_homes'])!=(286114,290730,4616):raise ValueError('complete actual home lineage')
proof.update(original_constructor_refusal_preserved=historical_refusal,missing_actual_PC9_refusal=actual_PC9_gate,
    actual_provider_not_constructed=True,production_native_calls_executed=0,
    source_inputs={str(p.relative_to(MAIN)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [native_path,manifest_path,Path(endpoint.__file__)]},
    pinned_generic_calendar_executor_guard_unchanged=True,
    later_generic_calendar_file_pin_join_pending=True)
path=BASE/'lineage_proof.json';data=(json.dumps(proof,sort_keys=True,indent=2)+'\n').encode()
if '--verify' in sys.argv:
 if path.read_bytes()!=data:raise ValueError('exact lineage replay changed')
elif path.exists():raise ValueError('fresh lineage evidence required')
else:path.write_bytes(data)
print(json.dumps(dict(status=proof['status'],original_homes=proof['original_homes'],bound_homes=proof['bound_homes'],added=proof['appended_state_homes'],PC9_gate=actual_PC9_gate,production_calls=0,hardware_qualified=False),sort_keys=True))
