import importlib.util,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('shared',ROOT/'tools/dsrom_shared_native_vm_model.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
def test_cold_model_exact():
 assert M.model()==json.loads((ROOT/'results/uarch/dsrom_shared_native_vm_20261003/model.json').read_text())
def test_full_single_provider_no_phantom_ports():
 m=M.model();assert m['native']['replicas']==1 and m['native']['macros']==256 and m['native']['bytes']==2**21
 assert m['native']['MACs_per_cycle']==0
 assert m['native']['read_peak_bytes_per_cycle']==256
 assert len(m['read_endpoints'])==5 and len(m['write_endpoints'])==3
 assert not m['admission']['protected_parent'] and not m['admission']['physical']
def test_actual_maximum_conflict_calendar_and_wait():
 m=M.model();c=m['calendar']
 assert c['write_batches_max']==128 and c['write_edges_bound_without_external_stall']==770
 assert [r['service_edges_bound_without_external_stall'] for r in m['read_endpoints']]==[16,10,10,34,58]
 assert 'unspecified consumer never assigned finite' in c['queue_bound_condition']
 assert 'D4 is not4transaction credits' in m['related_parent']['II']
def test_actual_owner_safe_hook_not_archive():
 r=M.model()['current_runtime'];assert r['source_count']==125
 assert r['parameters']==dict(WINDOW_REFILL_CREDITS=8,WINDOW_REFILL_OWNER_SAFE=1)
 assert all('inputs/' not in p for p in r['source_sha256'])
 assert not r['whole_parent_swapped'] and not r['standalone_WINDOW_rerun']
 for p,h in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
 for node in ('core','field','collective','WINDOW'):assert r['observer_hierarchy'][node].startswith('dut.')
def test_raw_defaultoff_and_exact_row_receipt():
 p=(ROOT/'rtl/model_ready_ds_shared_native_20261003/ot_ds_native_vm_related_parent.sv').read_text()
 assert 'parameter integer ENABLE=0' in p
 assert 'accepted_row_mask<=row_en' in p and 'row_visible_mask=w_visible[1] ? accepted_row_mask' in p
 assert 'provider_debt|{w_pending,reqp}' in p
 assert '.allcopies_fenced(1\'b0)' in p
 assert 'q_v[0]=qraw_0&&reply_retire_ready_0' in p
 assert 'w_visible=was_write_pending&~w_pending&~wquar' in p
def test_actual_sram_mask_not_address_truncation_admission():
 p=(ROOT/'rtl/model_ready_ds_shared_native_20261003/ot_ds_native_write_formats.sv').read_text()
 assert 'me[2112+p*30+15+:15]' in p
 assert 'bad[0]=1' in p and 'me[2048+p*16+l]' in p
 assert 'row[7936+:128]' in p
 assert 'r_addr[240+15+:15]' in (ROOT/'rtl/model_ready_ds_shared_native_20261003/ot_ds_native_vm_related_parent.sv').read_text()
def test_retained_registered_transpose_hold_no_capture_edge():
 p=(ROOT/'rtl/model_ready_ds_shared_native_20261003/ot_chip_v41x_coll_transpose_related_vm.sv').read_text()
 assert 'parameter integer ELASTIC_PIPE = 0' in p
 assert 'pipe_can_load = !pipe_v || out_ready' in p
 assert p.count('ELASTIC_PIPE == 0 || pipe_can_load')==4
 assert 'pipe_last && (ELASTIC_PIPE == 0 || out_ready)' in p
