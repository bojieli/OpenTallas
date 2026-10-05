#!/usr/bin/env python3
"""Actual parameter-source Engram product producer/handoff; no oracle injection."""
import argparse,hashlib,json,struct,subprocess
from pathlib import Path
import hdc_isa_v41 as I
ROOT=Path(__file__).resolve().parents[1]
SOURCE_PIN='b0cfaee4c9b4ab64606fc33d0d246e2ed685f559'
SOURCE_PATH='results/quality/w16_engram_home_service_demand_20261001/demand.json'
PROGRAM_PIN='4080bb5fd'
PROGRAM_PATH='results/rtl/w17_connected_token_preparation_20261001/full40_crom_bound_templates_v2.json'
REVISION='dba1be0a40aa45a94ad051997016db3960a90277'
ELEMENTS=20480

def sha(raw):return hashlib.sha256(raw).hexdigest()
def object_json(pin,path):
 raw=subprocess.check_output(['git','show',pin+':'+path],cwd=ROOT)
 return json.loads(raw),{'commit':pin,'path':path,'sha256':sha(raw)}

def mul_bf16_bits(q,k):
 """Integer binary32 RNE of exact BF16 operands; gradual underflow, +0 zero."""
 if not 0<=q<65536 or not 0<=k<65536:raise ValueError('BF16 bit extent')
 def decode(x):
  exp=(x>>7)&255;frac=x&127
  if exp==255:raise ValueError('nonfinite parameter input')
  return (frac,-133) if exp==0 else (128+frac,exp-134)
 qm,qe=decode(q);km,ke=decode(k);m=qm*km;e=qe+ke
 if not m:return 0
 sign=((q^k)&32768)<<16;power=m.bit_length()-1+e
 if power>127:return sign|0x7f800000
 if power>=-126:return sign|((power+127)<<23)|((m<<(24-m.bit_length()))&0x7fffff)
 shift=e+149
 if shift>=0:frac=m<<shift
 else:
  n=-shift;frac=m>>n;remainder=m&((1<<n)-1);half=1<<(n-1)
  if remainder>half or (remainder==half and frac&1):frac+=1
 return sign|frac if frac else 0

def verify_pair(binding,layer,qraw,kraw):
 if binding is None:raise ValueError(f'L{layer} actual q/k source pair unbound')
 if binding.get('layer')!=layer or binding.get('checkpoint_revision')!=REVISION:
  raise ValueError('source layer/revision mismatch; no L14 substitution')
 for family,raw in [('q_weight',qraw),('k_weight',kraw)]:
  source=binding['inputs'][family]
  if source['tensor']!=f'layers.{layer}.engram.{family}' or source['dtype']!='BF16' or source['shape']!=[4,5120]:
   raise ValueError('source parameter identity/shape/dtype')
  authority,ref=object_json(source['source_manifest_commit'],source['source_manifest_path'])
  entry=authority.get('files',{}).get('w.engram.'+family,{})
  if ref['sha256']!=source['source_manifest_sha256'] or authority.get('layer')!=layer or authority.get('checkpoint',{}).get('revision')!=REVISION:
   raise ValueError('immutable source manifest layer/SHA')
  if entry.get('tensor')!=source['tensor'] or entry.get('format')!='BF16' or entry.get('shape')!=[4,10240] or entry.get('sha256')!=source['sha256']:
   raise ValueError('immutable source parameter binding')
  if len(raw)!=40960 or sha(raw)!=source['sha256']:raise ValueError('source parameter SHA/extent')
 return True

def produce(binding,layer,qraw,kraw):
 verify_pair(binding,layer,qraw,kraw)
 q=struct.unpack('<20480H',qraw);k=struct.unpack('<20480H',kraw)
 bits=[mul_bf16_bits(a,b) for a,b in zip(q,k)]
 if any((v>>23)&255==255 for v in bits):raise ValueError('nonfinite product; producer fault, not published')
 product=struct.pack('<20480I',*bits)
 crom=b''.join(struct.pack('<II',v,0) for v in bits)
 return product,crom

def retained_source_binding(layer):
 demand,ref=object_json(SOURCE_PIN,SOURCE_PATH);sources=demand['generated_constants']['retained_sources']
 if layer!=14:return None
 inputs={}
 for family in ('q_weight','k_weight'):
  full=f'layers.{layer}.engram.{family}';s=sources[full]
  inputs[family]={'tensor':full,'dtype':'BF16','shape':[4,5120],'sha256':s['sha256'],
   'path':s['path'],'source_manifest_commit':s['existing_manifest_commit'],'source_manifest_path':s['existing_manifest_path'],
   'source_manifest_sha256':s['existing_manifest_sha256']}
 return {'layer':layer,'checkpoint_revision':REVISION,'inputs':inputs,'source_authority':ref}

def runtime_product_tag(binding,rank,epoch,program_sha,product_sha):
 if binding is None:raise ValueError('actual source pair required before runtime tag')
 if type(rank) is not int or rank not in range(4) or type(epoch) is not int or not 0<=epoch<2**32:
  raise ValueError('runtime identity')
 audit,_=object_json(PROGRAM_PIN,PROGRAM_PATH)
 if program_sha!=audit['ranks'][rank]['encoded_template_sha256']:raise ValueError('runtime actual program/rank binding')
 return {'rank':rank,'layer':binding['layer'],'epoch':epoch,'program_sha256':program_sha,
  'CROM_image_sha256':audit['ranks'][rank]['CROM_image_sha256'],
  'q_sha256':binding['inputs']['q_weight']['sha256'],'k_sha256':binding['inputs']['k_weight']['sha256'],
  'product_sha256':product_sha,'operation':'FP32_RNE_MUL_CANONICAL_ZERO','elements':ELEMENTS,
  'layout':'head-major j*5120+i; lane=i%1024,slot=i//1024; 4heads x5slots/lane'}

def accept_runtime_product(binding,layer,qraw,kraw,result,tag,expected_tag,*,producer_done,output_quiet,consumer_drain):
 """Source-bound bit gate, then explicit publish/lifetime fence; no source invention."""
 expected,_=produce(binding,layer,qraw,kraw)
 authority_tag=runtime_product_tag(binding,tag.get('rank'),tag.get('epoch'),tag.get('program_sha256'),sha(expected))
 if tag!=authority_tag:raise ValueError('runtime source/operation/program identity')
 if tag!=expected_tag or tag.get('layer')!=layer or tag.get('q_sha256')!=sha(qraw) or tag.get('k_sha256')!=sha(kraw):
  raise ValueError('runtime source/tag/epoch mismatch')
 if tag.get('elements')!=ELEMENTS or tag.get('operation')!='FP32_RNE_MUL_CANONICAL_ZERO':raise ValueError('runtime operation/extent')
 if len(result)!=81920 or result!=expected or tag.get('product_sha256')!=sha(result):raise ValueError('runtime product bits/rounding/order')
 if producer_done is not True or output_quiet is not True:raise ValueError('product not yet visible; producer/outputs not drained')
 if type(consumer_drain) is not bool:raise ValueError('consumer drain unknown/nonboolean')
 return {'product_visible':True,'consumer_read_allowed':True,'credit_release_allowed':bool(consumer_drain),
  'physical_CROM_base':None,'physical_VM_base':None,'runtime_transport_qualified':False}

def lower_vm_product(qbase,kbase,outbase,*,opt_in=False):
 """Existing SU operation only; caller must supply reserved published VM sources."""
 if not opt_in:raise ValueError('opt_in required; no live overlay')
 spans=[(b,b+ELEMENTS) for b in (qbase,kbase,outbase)]
 if any(not isinstance(b,int) or b<0 or e>2**19 for b,e in spans):raise ValueError('VM address extent')
 if any(max(a,c)<min(b,d) for i,(a,b) in enumerate(spans) for c,d in spans[i+1:]):raise ValueError('VM source/output overlap')
 op={'unit':I.UNIT_SU,'pred':0,'su_nout':4,'su_nin':5120,
  'a_src':I.SRC_VM,'a_base':qbase,'a_so':5120,'a_si':1,'b_src':I.SRC_VM,'b_base':kbase,'b_so':5120,'b_si':1,
  'm1':I.M1_AB,'m2':I.M2_BYP,'ad':I.AD_BYP,'e1':I.E1_BYP,'e2':I.E2_BYP,'rnd':0,
  'dst':I.DST_VM,'o_base':outbase,'o_so':5120,'o_si':1}
 word=I.encode(full_shape=True,**op);decoded=I.decode(word,full_shape=True)
 if any(decoded[k]!=v for k,v in op.items()):raise AssertionError('producer command codec')
 return op

def require_full40_source_pairs(source_contract):
 for layer in (1,14):
  if source_contract['inputs'].get(f'L{layer}') is None:
   raise ValueError(f'full40 execution blocked: L{layer} actual parameter-source pair absent')
  binding=source_contract['inputs'][f'L{layer}']
  if binding.get('layer')!=layer:raise ValueError('full40 layer-specific source binding')
  for family in ('q_weight','k_weight'):
   s=binding['inputs'][family];authority,ref=object_json(s['source_manifest_commit'],s['source_manifest_path'])
   entry=authority.get('files',{}).get('w.engram.'+family,{})
   if authority.get('layer')!=layer or ref['sha256']!=s['source_manifest_sha256'] or entry.get('tensor')!=f'layers.{layer}.engram.{family}' or entry.get('sha256')!=s['sha256']:
    raise ValueError('full40 immutable parameter-source binding')
 return True

def contract():
 audit,auditref=object_json(PROGRAM_PIN,PROGRAM_PATH);demand,ref=object_json(SOURCE_PIN,SOURCE_PATH)
 roles=[]
 for rank in audit['ranks']:
  offset=0
  for stage in rank['stages']:
   for missing in stage['unbound']:
    if stage['layer'] in (1,14):roles.append({'rank':rank['rank'],'layer':stage['layer'],'pc':offset+missing['instruction'],
      'operand':missing['operand'],'elements':missing['elements'],'actual_base':None,
      'encoded_program_sha256':rank['encoded_template_sha256'],'CROM_image_sha256':rank['CROM_image_sha256']})
   offset+=stage['instruction_count']
 if len(roles)!=8:raise ValueError('all4rank generated operand inventory')
 pins={}
 for path in ['tools/hdc_golden.py','tools/hdc_golden_v41.py','tools/hdc_program_v41.py','tools/hdc_replay_v41.py',
              'rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv','rtl/hdc/v41x/ot_hdc_v41x_vec.sv',
              'rtl/hdc/ot_hdc_fastfp_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv']:
  raw=subprocess.check_output(['git','show','d2c28c279:'+path],cwd=ROOT);pins[path]={'commit':'d2c28c279','sha256':sha(raw)}
 return {'schema':'opentallas.w11.generated-Engram-source-runtime-contract.v1','program_source':auditref,'source_inventory':ref,
  'producer_consumer_source_pins':pins,'inputs':{'L1':None,'L14':retained_source_binding(14)},'actual_operand_bindings':roles,
  'producer':{'operation':'BF16 bits <<16 -> exact FP32 RNE multiply -> canonical+0; no BF16 product round',
   'golden_order':'p=FP32(q*k); M1=FP32(h*p); M2=FP32(M1*key); original tree reduction; no algebraic reorder',
   'origin':'hdc_program_v41.Layout host-generated parameter product; current4778 ISA reads precomputed CROM b operand, has no q*k producer',
   'existing_SU_lowering':'optional separate initialization descriptor M1_AB over published q/k VM operands; not inserted or run',
   'input_raw_BF16_bytes_per_layer':81920,'widened_FP32_input_bytes_per_layer':163840,'product_FP32_bytes_per_layer':81920,
   'CROM64_logical_slice_bytes_per_layer':163840,'SU1024_ideal_emit_vectors':20,'requested_input_useful_bits_per_serial_emit':65536,
   'requested_output_useful_bits_per_serial_emit':32768,'actual_q_port':None,'actual_k_port':None,'actual_product_write_port':None,
   'VM_note':'vec_lane rd_re activates4streams/live lane even when C/D bypassed; actual VM/port costs mustprice unused reads too',
   'VM_scratch_reservation':None,'model_composed_init_latency':None},
  'per_lane_layout':{'logical_index':'j*5120+i','j_heads':4,'i_elements_per_head':5120,'SU_lanes':1024,
   'lane':'i%1024','slot_per_head':'i//1024','products_per_lane':20,'source_qk_same_index':True},
  'dependencies':['immutable exact-layer q/k parameter authority and sourceSHA, never activation/oracle fixture',
   'q/k published source ports + scratch reservation and input drain','product operator completes, all20vectors visible and output quiet',
   'matching source/program/rank/layer/epoch/productSHA and exact20480extent accepted','separate actual CROM/VM home and producer-consumer binding proof',
   'coefficient consumer dependency published only after all products visible; original h*p thenkey order',
   'attention descriptor DRAIN->IDLE plusengineidle/outputquiet before finalcredit release'],
  'current_live_vehicle':{'source_pin':'4e38326d6f361bc85e660f48c59c355e2bb95274','scope':'Godel L0only; no L1 q/k DUTprovider available',
   'source':'owner handoff; no process/source mutations','overlay':False,'restart':False},
  'status':'BLOCKED_L1_ACTUAL_SOURCE_PAIR_AND_CURRENT_DUT_PROVIDER_ABSENT',
  'L14_retained_product_reference':demand['generated_constants']['L14_oracle'],
  'symbolic_CROM_append_is_physical_image':False,'full40_execution_bound':False,'checkpoint_reads':0,'RTL_runs':0,'hardware_admission':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--prove-retained-l14',action='store_true');a=p.parse_args()
 if a.out.exists():raise ValueError('preserve immutable outputs')
 c=contract();artifacts={}
 if a.prove_retained_l14:
  b=c['inputs']['L14'];raw=[]
  for family in ('q_weight','k_weight'):
   path=Path(b['inputs'][family]['path']);resolved=path.resolve()
   if '.cache' in resolved.parts or 'safetensors' in resolved.name:raise ValueError('checkpoint reads prohibited')
   raw.append(path.read_bytes())
  product,crom=produce(b,14,*raw)
  old=c['L14_retained_product_reference']
  if sha(product)!=old['FP32_product_bits_sha256'] or sha(crom)!=old['CROM64bit_product_slice_sha256']:
   raise ValueError('retained source product exactness failed')
  artifacts={'L14.product.fp32.bin':product,'L14.product.crom64-logical-slice.bin':crom}
  c['L14_actual_software_product']={'status':'PASS_ACTUAL_RETAINED_PARAMETER_BITS','FP32_sha256':sha(product),'CROM64_slice_sha256':sha(crom),
    'elements':ELEMENTS,'retained_parameter_bytes_read':81920,'physical_base':None,'physical_image':False}
 a.out.mkdir(parents=True)
 for name,raw in artifacts.items():(a.out/name).write_bytes(raw)
 (a.out/'contract.json').write_text(json.dumps(c,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':c['status'],'L14_product':c.get('L14_actual_software_product'),'L1_source':None}))
