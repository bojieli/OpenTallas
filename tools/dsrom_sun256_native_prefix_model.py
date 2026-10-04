#!/usr/bin/env python3
"""Native SU leaf/staging metadata only; never FP arithmetic or checkpoint payload."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import hdc_isa_v41 as I
E=ROOT/'results/uarch/dsrom_sun256_native_prefix_20261004'
RTL=[f'rtl/hdc/v41x/{n}.sv' for n in ('ot_hdc_v41x_su_adapt','ot_hdc_v41x_sfu','ot_hdc_v41x_vec_lane','ot_hdc_v41x_vec_side','ot_hdc_v41x_vec_red','ot_hdc_v41x_vec')]+['rtl/hdc/'+n+'.sv' for n in ('ot_hdc_delay','ot_hdc_fpu','ot_hdc_fp32_mul_pipe','ot_hdc_sfu','ot_hdc_fastfp','ot_hdc_fastfp_lat','ot_hdc_fp32_mul_lat','ot_hdc_fp32_add_lat','ot_hdc_prefix')]+['rtl/proto/ot_fp32_add_rne_pipe.sv']+['rtl/hdc/v41/'+n+'.sv' for n in ('ot_hdc_fsqrt','ot_hdc_fdiv','ot_hdc_softplus')]

def generate():
 s=subprocess.check_output(['git','show','8460dca67:tools/runtime/dsrom/s81_minimum_prefix.cpp'],cwd=ROOT,text=True)
 rows=[]
 for idx,unit,sha,x in re.findall(r'DsromS81PrefixOperation\{(\d+), (\d+), "([0-9a-f]+)", \{([^}]*)\}',s):
  words=[int(v,16) for v in re.findall(r'0x([0-9a-f]+)u',x)];assert len(words)==64
  d=I.decode(sum(w<<(32*j) for j,w in enumerate(words)),full_shape=True)
  if int(unit)!=2:continue
  if any(d.get(k,0) for k in ('a_ind','b_half','c_pair','mx_d_m','su_d_nout','su_d_nin')):raise ValueError('prefix requires additional source address/dynamic qualification')
  vm=set();external=set()
  for o in range(d['su_nout']):
   for i in range(d['su_nin']):
    for operand in 'abcd':
     a=d[operand+'_base']+o*d[operand+'_so']+i*d[operand+'_si'];src=d[operand+'_src']
     if not 0<=a<1<<19:raise ValueError('VM/source extent19 alias')
     if src==0:vm.add(a)
     else:external.add((src,a))
  groups=sorted({a&~63 for a in vm})
  rows.append(dict(pc=int(idx),literal_sha256=sha,decoded=d,vm_group_bases=groups,
                   vm_unique_scalar_addresses=len(vm),prefetch_groups=len(groups),
                   staged_words=len(groups)*64,external_source_addresses=[list(x) for x in sorted(external)],
                   raw_only_prefetch_elapsed_edges_no_stall=6*len(groups),
                   scope='extra prefetch then native fixed R+2; protected read/grant/consumer waits additive, not raw universalbound'))
 return dict(scope='selected SUN256 native leaf + bounded simulation operand staging; not whole core or architecture adoption',
  source_base='b55aceb096cd2d42307631feda0f51db5f17e324',
  prefix_source='8460dca67:tools/runtime/dsrom/s81_minimum_prefix.cpp',prefix_source_sha256=hashlib.sha256(s.encode()).hexdigest(),
  rtl_closure=RTL,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in RTL+['tools/uarch_model.py','tools/dsrom_shared_native_vm_model.py','tools/hdc_isa_v41.py']},
  parameters=dict(N=256,M=64,LV=7,AW=30,NW=16,KVT_SH=9,MLAT=3,ALAT=3,BCAST_STAGES=0,RET_STAGES=0,CLS_DRAIN=0),
  selected_size_scope='SUN256/SUM64 retained fullshape source; historical uarch_model defaults16/8 NOTselected substitute',
  capacity_check=dict(whole_RMS_elements=5120,selected_vectors=20,LV7_vectors=128,rejected_N16_vectors=320),
  extra_staging=dict(maximum_words=20480,payload_bits=20480*32,address_valid_metadata_floor_bits=20480*20,
                     max_actual_prefix_staged_words=max(r['staged_words'] for r in rows),
                     response_cookie_bits=227,responses_inflight=1,output_collect_words=5376,output_collect_data_address_bits=5376*62,descriptor_hold_bits=2048,
                     model_charge='positive additional read/staging + held publication costs; host simulation adapter NOT new unqualified physicalSRAM/FFcredit'),
  ports=dict(native_operand_elements_per_edge=1024,native_operand_bits=32768,
             native_VM_write_lanes=256,native_reducer_write_lanes=32,
             VM_bank4_read_bytes_per_accepted_request=256,native_raw_read_latency=4,
             native_fixed_operand_sampling='requestR, data atR+2; staged actual replies only'),
  adapter_calendar=dict(prefetch_before_GO=True,prefix_serializes_leaf_ownership=True,
                        launch_requires_all_staged_replies_and_held_input_version=True,
                        result_retirement_requires_actual_matching_VM_visibility=True,
                        variable_VM_stalls='wait indefinitely while retaining owned request; NO fixedlatency fake response',
                        native_arithmetic_only=True,host_FP_compute=False),
  prefix_operations=rows,
  build=dict(scope='SU leaf only; no corearray/HE/provider',source_files=len(RTL),
             admission_peak_GiB=32,estimate_basis='sourcefull256lanes plus64SFU; priorfullSUN256wholecore54.2GBfront; SU-only conservative32GiBadmission nothardcap; replacewithactualpeak',
             workers=16,hard_time_memory_AS_file_limits=False,actual_archive=None),
  missing_costs=dict(checked_read_extra_edges=None,VMpublication_stall=None,source_version_lease_hardware_area=None,physical_adapter_fit=False),
  hardware_or_rate_admission=False)
if __name__=='__main__':
 E.mkdir(parents=True,exist_ok=True)
 (E/'model.json').write_text(json.dumps(generate(),indent=2,sort_keys=True)+'\n')
