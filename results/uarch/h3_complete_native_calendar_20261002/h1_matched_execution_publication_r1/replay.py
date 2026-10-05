"""Source-matched H1 edge calibration, finite selector and actual PC0 binding."""
import gzip,hashlib,importlib.util,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
spec=importlib.util.spec_from_file_location('h1_calendar_source',ROOT/'tools/h3_complete_native_calendar.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
names=['rtl/gpu/ot_gpu_rf_service.sv','rtl/gpu/ot_gpu_scratch_service.sv','rtl/gpu/ot_gpu_full_sm_service.sv','rtl/test/full_sm_service/tb_full_service_exact.sv','rtl/test/full_sm_service/tb_storage.sv']
sources={n:gzip.decompress((BASE/(Path(n).name+'.gz')).read_bytes()) for n in names}
verdict=json.loads((BASE/'verdict.json').read_bytes());review=json.loads((BASE/'review.json').read_bytes());logs={n:(BASE/n).read_bytes() for n in ['actual_sim.log','storage_sim.log']}
contract=c.h1_calibrated_service_contract(verdict,review,logs,sources)
policy=c.prove_reserved_h1_fair_owner(contract)
projection=json.loads(gzip.decompress((BASE/'PC0_projection.json.gz').read_bytes()));homes={int(k):v for k,v in json.loads(gzip.decompress((BASE/'PC0_home_subset.json.gz').read_bytes())).items()}
calendar=c.compile_reserved_h1_publications(projection,homes,contract)
summary={k:v for k,v in calendar.items() if k not in ['packets','client_inventory','per_SM_reference_edge_upper']}
summary.update(new_policy=dict(physical_fan_in=3,local_waits=policy['local_wait_bounds'],new_software_policy_installed_as_RTL=False),
 measured_H1_SIMD_done_after_accept_edges=contract['SIMD_done_after_accept_edges'],
 baseline_host_write_starvation_with_all_sinks_ready=True,
 C0_outer_version_reverse_contract=None,V1_integer_convert_bit_predicate_executed_hardware_contract=None,
 producer_calibration_scope='actual96 PC0 published RF versions/homes only; source arithmetic not reexecuted',
 numerical_tests_scope='retained actual128 H1 directed FADD/FMUL RNE/sign/subnormal/refusal/mirror tests and exhaustive RF/shared address cases; not DS full-token tests')
outputs={'edge_contract.json':contract,'finite_owner_policy_r3.json':policy,'summary.json':summary,'PC0_local_H1_reference_calendar_r3.json.gz':calendar}
cdc_pins=json.loads((BASE/'CDC_source_pins.json').read_bytes())
cdc=c.h1_clock_crossing_obligations({n:gzip.decompress((BASE/(Path(n).name+'.gz')).read_bytes()) for n in cdc_pins},cdc_pins)
outputs['CDC_obligations.json']=cdc
if '--program-root' in sys.argv:
 program_root=Path(sys.argv[sys.argv.index('--program-root')+1])
 demands=c.inventory_h1_program_demands(
  (program_root/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz').read_bytes(),
  (program_root/'results/uarch/h3_qwen_complete_native_20261002/bounded_r2/Qwen_tiled.json.gz').read_bytes())
 outputs['both_program_demand_inventory.json.gz']=demands
for name,value in outputs.items():
 data=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode() if not name.endswith('.gz') else gzip.compress(json.dumps(value,sort_keys=True,separators=(',',':')).encode(),mtime=0)
 p=BASE/name
 if '--verify' in sys.argv:
  if p.read_bytes()!=data:raise ValueError('actual H1 policy/publication replay changed '+name)
 elif p.exists():
  if p.read_bytes()!=data:raise ValueError('immutable existing evidence differs; successor required')
 else:p.write_bytes(data)
print(json.dumps(dict(status=policy['status'],baseline_host_write_starvation_proved=True,
 source_publications=384,registered_home_clients=calendar['registered_version_home_clients'],
 source_packet_counts=calendar['packet_counts'],H1_SIMD_done_after_accept=12,
 local_port_wait_bounds=policy['local_wait_bounds'],full_production_admitted=False,hardware_qualified=False),sort_keys=True))
