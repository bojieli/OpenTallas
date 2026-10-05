"""Bounded all-290 lowering join to genuine ot_gpu_sm_q on ONE shared edge.

No W4 SIMD aliases, expected payloads, arithmetic or fabricated whole terminal.
The installed sourcebook must bind the actual TC leaf and its consumption tap.
Whole output publication remains all ranges + actual issuer visibility/reverse.
"""
import hashlib,json,argparse
from copy import deepcopy
from pathlib import Path
from tools.gpu_sys import canonical_qwen_service_calendar as C
from tools.gpu_sys import canonical_qwen_matrix_padding as P
from tools.gpu_sys import canonical_qwen_matrix_services as S
FIELDS={'start':('input',1),'op_rows':('input',13),'op_c':('input',16),
 'op_g':('input',8),'op_scale':('input',1),'busy':('output',1),
 'd_valid':('input',1),'d_ready':('output',1),'d_base':('input',32),'d_lines':('input',24),
 'req_v':('output',1),'req_ready':('input',1),'req_addr':('output',32),'req_tag':('output',10),
 'rsp_v':('input',1),'rsp_tag':('input',10),'rsp_data':('input',1024),
 'xw_en':('input',1),'xw_addr':('input',10),'xw_grp':('input',1),'xw_data':('input',2048),
 'sw_en':('input',1),'sw_addr':('input',12),'sw_data':('input',16),
 'rv':('output',1),'rrow':('output',12),'rdata':('output',512),'fault':('output',1),
 'arrive':('output',1),'release_in':('input',1),'released':('output',1),
 'consume_valid':('output',1)}
SOURCE='rtl/gpu/ot_gpu_sm_q.sv'
PARAMS=dict(SUB=4,LS=32,NC=16,IL=8,RMAX=4096,LEV=5,NXM=16,MAX_OUT=512)

def select_engine_sources(installer_root):
 """Emitters consume Boole's actual source selector with baseline selected.

 The lookahead child remains off until its loaded context is qualified. This
 never replaces guarded RF/SIMD or changes arithmetic/memory port contracts.
 """
 from tools.hbm_accel_epilogue_ha8 import select_native_engine
 return select_native_engine(installer_root=installer_root,
                             enable_ha3_clock_lookahead=False)

class TCPins:
 def __init__(self,root,rank,SM,*,enabled=False):
  C.need(enabled,'genuine whole TC join default off')
  C.need(type(rank) is int and rank in (0,1) and type(SM) is int and 0<=SM<32,'actual execution rank/SM')
  contract=root.book.get('matrix_TC_contract',{})
  C.need(contract.get('module')=='ot_gpu_sm_q' and contract.get('parameters')==PARAMS,
         'genuine ot_gpu_sm_q parameters, never W4 SIMD/PC40')
  sha=contract.get('source_sha256')
  C.need(type(sha) is str and len(sha)==64 and root.book.get('source_sha256',{}).get(SOURCE)==sha,
         'genuine TC source identity in installed book')
  C.need(contract.get('consume_tap')=='u_sm.w_valid && u_sm.w_ready','actual accepted bulk-copy line tap')
  for n,(direction,width) in FIELDS.items():
   p=root.book['pins'].get('tc_'+n,{})
   C.need(p.get('direction')==direction and p.get('leaf_bits')==width and p.get('count')==64
          and p.get('bits')==width*64,'actual TC pin direction/width '+n)
  self.root=root;self.index=rank*32+SM
 def get(self,name):
  C.need(name in FIELDS,'source TC field')
  w=FIELDS[name][1];return (self.root.get('tc_'+name)>>(self.index*w))&((1<<w)-1)
 def set(self,name,value):
  C.need(name in FIELDS and FIELDS[name][0]=='input','TC actual input only')
  w=FIELDS[name][1];C.need(type(value) is int and 0<=value<1<<w,'TC source operand width')
  with self.root.lock:
   n='tc_'+name;mask=((1<<w)-1)<<(self.index*w)
   self.root.set(n,(self.root.get(n)&~mask)|(value<<(self.index*w)))
 def tick(self):self.root.tick()

class ConsumptionAuthority:
 """Observe a real TC line acceptance at the shared edge, retain full origin.

 All ownership/ports delegate to the existing physical provider. This wrapper
 supplies only the exact accepted-line witness; busy/timers never consume it.
 Install around that provider BEFORE constructing finite MATRIX services.
 """
 def __init__(self,provider,TC):
  C.need(isinstance(TC,TCPins),'genuine source-bound TC pins')
  self.provider=provider;self.TC=TC;self.services=None;self.offer=None;self.accepted=None
 def __getattr__(self,n):return getattr(self.provider,n)
 def attach(self,services):
  C.need(self.services is None and services.a is self,'same actual provider and services')
  self.services=services
 def before_edge(self):
  self.offer=None
  if self.TC.get('consume_valid'):
   line=self.services.line
   C.need(line is not None and line.get('phase')=='consume',
          'real TC line consumed only after actual source gather delivered')
   C.need(self.accepted is None,'one retained TC consumption witness')
   self.offer=(line['tag'],line['plan']['line_address'],
               self.services.origin['GO_tuple239'],deepcopy(line['reservation']))
 def after_edge(self):
  if self.offer is not None:self.accepted=self.offer;self.offer=None
 def matrix_weight_consumed(self,tag,line_address,reservation):
  if self.accepted is None:return False
  C.need(self.accepted==(tag,line_address,self.services.origin['GO_tuple239'],reservation),
         'actual consumed TC line full saved GO/source reservation')
  self.accepted=None;return True


def bind_operator(root,authority,services,native,source_PC,rank,SM,*,enabled=False):
 """Return runnable original all-290 controller with real operand pins.

 Caller supplies source-selected full operator services and Nash's whole-range
 authority. Binding does not tick, start a job or synthesize lease/ready events.
 """
 C.need(isinstance(services,S.MatrixPhysicalServices) and services.a is authority,
        'actual same hardware authority for finite input/output services')
 p=TCPins(root,rank,SM,enabled=enabled)
 C.need(services.scratch.p.root is root and services.scratch.p.index==p.index,
        'TC and scratch client same captured execution location and clock')
 return P.MatrixOperatorController(p,services,native,source_PC,enabled=enabled)

def compose(root):
 root=Path(root);path=root/'results/uarch/qwen_matrix_loop_source_20261003/split64_services/model_ready.json'
 predecessor=json.loads(path.read_text())
 return dict(schema='qwen.matrix-TC-source-join-r1',fields=FIELDS,parameters=PARAMS,
  source_pins={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in
   [SOURCE,'tools/gpu_sys/canonical_qwen_matrix_tc_pins.py',str(path.relative_to(root))]},
  lowering_MATRIX_PCs=290,split64_PCs=72,source_primitive_calls=192147228,
  MAC_per_cycle_per_engine=2048,source_unique_MAC_per_cycle=128,
  replicas=64,replica_accounting='existing full SM slot reservation once; guarded W4 has no TC',
  xstore_macros_per_engine=16,weight_ring_macros_per_engine=4,row_scale_macros_per_engine=1,
  xstore_write_bytes_per_edge=256,weight_capture_bytes_per_edge=128,result_bytes_per_valid=64,
  payload_register_addition_bits=0,additional_clock_or_control_FF=0,
  port_boundary_bits_per_engine=sum(w for d,w in FIELDS.values()),
  physical_capacity_tracks=None,engine_reserved_area_um2=None,
  latency_composition='reuse each exact source operation floor below; actual finite gather/ACK/lease costs mandatory',
  operation_floors=[dict(source_PC=o['source_PC'],tile_count=o['tile_count'],model=o['model']) for o in predecessor['operations']],
  source_all290_floor_SHA=hashlib.sha256(path.read_bytes()).hexdigest(),
  whole_completion='full frozen range set, every page ACK owner55 plus engine visibility and captured GO239 terminal/reverse',
  actual_installed_engine=False,physical_admission=False,actual_token_latency_ps=None,
  mutable_storage_protection_qualified=False,
  remaining=['Euclid genuine TC top/book install and shared consume tap',
   'source/protection/SSFF of actual TC memories and loaded boundary',
   'Nash complete input census/multioutput grouping/typed-zero output',
   'actual provider gathering, whole visibility and saved GO239 completion'])

def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args()
 args.out.write_text(json.dumps(compose(Path(__file__).resolve().parents[2]),indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
