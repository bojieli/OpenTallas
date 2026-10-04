import json,re,hashlib,threading
from pathlib import Path
import pytest
from tools.gpu_sys.canonical_qwen_native_aperture_cluster import ports
from tools.gpu_sys.canonical_qwen_native_aperture_ports import NativeAperturePorts,NativeInitialPorts
from tools.gpu_sys.canonical_qwen_transport import TransportError
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'rtl/model/qwen_hbm_native_aperture_factory_20261003_r6_bound_final'
def book():return json.loads((OUT/'ports.json').read_text())
def test_actual_header_book_and_real_leaf_cluster_connections():
 b=book();s=(OUT/(b['top']+'.sv')).read_text();spec=ports(OUT/(b['top']+'.sv'))
 for n,p in b['pins'].items():assert (spec[n]['direction'],spec[n]['bits'])==(p['direction'],p['bits']),n
 assert 'ot_gpu_qwen_native_aperture_range_owner #' in s
 assert 'original_banked_owner' in s and 'ot_gpu_qwen_banked_manifest_range_owner #' in s
 assert 'ot_gpu_qwen_native_aperture_cluster #' in s
 assert 'ot_gpu_qwen_initial_completion #' in s
 assert 'assign local_shared_router_drained=kv_shared_drained && (&scratch_drained);' in s
 assert '|| (|scratch_fault)' in s
 assert 'source_owner_native_rf_workspace_free[i]=!tc_busy[i]' in s
 assert 'rfdrain_w6_local_RF_empty[i] || private_held' in s
 assert 'source_owner_query_result_workspace[i]' in s
 assert 'native_initial_busy && issuer_rf_range_ack_valid' in s
 assert 'native_bank_query_empty[32]' in s
 assert 'all_clean && !g_source_owner[i].enabled_native_bank.u_source_owner.q[0]' in s
 assert 'localparam integer Q_LIVE=0;' in (ROOT/'rtl/experimental/canonical_qwen_native_apertures_20261003/ot_gpu_qwen_native_aperture_range_owner.sv').read_text()
 assert b['full_build_ready'] is False and b['native_aperture_contract']['physical_profile_and_controller_installed'] is False

def test_immutable_old_leaf_branch_and_unforgeable_observation_setters():
 b=book();s=(OUT/(b['top']+'.sv')).read_text();old=(ROOT/'rtl/model/qwen_hbm_banked_atomic_factory_20261003_r5'/(b['top']+'.sv')).read_text()
 a=old.index(' ot_gpu_qwen_banked_manifest_range_owner #');z=old.index('\n );',a)+len('\n );');assert old[a:z] in s
 cpp=(OUT/'pin_driver.cpp').read_text()
 for n,p in b['pins'].items():
  if n.startswith(('native_aperture_','native_initial_')) and p.get('direction')=='input' and not p.get('host_writable'):
   assert f'if(name=="{n}"){{auto v=' not in cpp,n
 for n in ['authority_valid','authority_shape_sha','source_owner_held','result_owner_held','output_visible','issuer_held_tuple']:
  p=b['pins']['native_aperture_'+n];assert p['direction']=='output' and p['count']==64 and p['block']=='native_aperture'

class Root:
 def __init__(self):self.book=book();self.lock=threading.RLock();self.v={'native_apertures_enabled':1};self.calls=[]
 def get(self,n):return self.v.get(n,0)
 def set(self,n,v):self.calls.append((n,v));self.v[n]=v
 def tick(self):self.calls.append('EDGE')
 def settle(self):self.calls.append('EVAL')
def test_component_constructors_no_ticks_and_no_host_authority_writes():
 root=Root();p=NativeAperturePorts(root,63);i=NativeInitialPorts(root);assert root.calls==[]
 p.set('cursor_load_sequence',123);assert root.v['native_aperture_cursor_load_sequence']==123<<(63*64)
 for n in ['authority_valid','issuer_held_tuple','profile_valid','read_operand']:
  with pytest.raises(TransportError):p.set(n,1)
 for n in ['busy','visible_valid','terminal_valid','reverse_valid']:
  with pytest.raises(TransportError):i.set(n,1)
 i.set('go_input_bits',17);assert root.v['native_initial_go_input_bits']==17
 assert 'EDGE' not in root.calls
 root.v['native_apertures_enabled']=0
 with pytest.raises(TransportError):NativeAperturePorts(root,0)

def test_retained_route_raw_terminal_pins():
 d=ROOT/'rtl/model/qwen_native_rf_route_20261003/directed_r1';t=json.loads((d/'terminal.json').read_text());assert t['verdict']=='PASS_NATIVE_RF_ROUTE_FIXTURE'
 assert t['source_sha256']==t['post_sha256']
 for p,h in t['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
 assert 'cycles=13' in (d/'runtime.log').read_text()


def test_saved_metadata_views_preserve_passed_router_handshake_body():
 old=(ROOT/'rtl/model/qwen_native_rf_route_20261003/ot_gpu_qwen_native_rf_route.sv').read_text()
 new=(ROOT/'rtl/model/qwen_native_rf_route_20261003/ot_gpu_qwen_native_rf_route_r2.sv').read_text()
 new=new.replace('module ot_gpu_qwen_native_rf_route_r2 ', 'module ot_gpu_qwen_native_rf_route ')
 new=new.replace(' output wire [63:0] bank_pending_read,bank_pending_write,\n','')
 new=new.replace(' output wire [575:0] bank_saved_read_slot,output wire [2943:0] bank_saved_read_owner,\n','')
 for line in new.splitlines(keepends=True):
  if line.startswith(('  assign bank_pending_', '  assign bank_saved_read_')):new=new.replace(line,'')
 assert new==old

def test_initial_write_admission_and_pending_identity_are_physical():
 b=book();s=(OUT/(b['top']+'.sv')).read_text()
 assert 'assign native_external_write_admit[i]=initial_offer_admit &&' in s
 assert 'native_initial_initial_write_admit[(i==32)?1:0] && initial_Q' in s
 assert 'source_owner_query_result_write[i]' in s
 assert 'source_owner_query_result_tuple[i*239+:239]==native_initial_event_tuple' in s
 assert 'native_aperture_rfroute_bank_pending_write[i] ? native_aperture_rfroute_bank_saved_read_owner[i*46+:46]' in s
 assert b['manifest_contract']['ABI_sha256']==hashlib.sha256((ROOT/'results/uarch/canonical_qwen_native_apertures_20261003/pins.json').read_bytes()).hexdigest()
 assert b['native_aperture_contract']['route_module']=='ot_gpu_qwen_native_rf_route_r2'
