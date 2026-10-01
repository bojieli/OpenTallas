"""Compose source-bound codec and score regions without double counting."""
import hashlib,json,subprocess
from pathlib import Path
CP='results/rtl/deepseek_hbm_complete_20261001/index-full-codec-phase-r2.json'
SP='results/physical_abi3/asap7/gpu/w13_index_f32_consumer_ports_20261001/crossphase_r1.json'

def pinned(rev,path):
 b=subprocess.check_output(['git','show',rev+':'+path]);return json.loads(b),{'git':rev,'path':path,'sha256':hashlib.sha256(b).hexdigest()}

def build():
 c,cp=pinned('e5d9ad00a',CP);s,sp=pinned('1ef7fc73e',SP)
 regions=c['shared_regions'];raw=regions['raw_packed'];transpose=regions['transpose_scratch_pitch33'];assert raw[1]==transpose[0]
 start=raw[0];end=start+8192;assert end<=transpose[1]
 copies=[]
 for b in range(4):
  for warp in range(64):
   copies.append({'id':f'copy{b}:{warp}','ops':['LOAD32','STORE32'],
     'source_word_base':start//4+warp*32,'destination_word_base':4096+b*2048+warp*32,'lanes':32,
     'dependencies':[f'score{b}:all64outputstoresvisible',f'score{b}:allkeyinputconsumersdone'],
     'RF_ports':'one32bitread/one32bitwrite per lane;writeboth physical copies',
     'bank_words':'base+lane;32unique banks','launch_tick':None,'RF_ready_tick':None,'store_visible_tick':None})
 phases={'codec':regions,'score':{k:v for k,v in regions.items() if k not in ['raw_packed','transpose_scratch_pitch33']}}
 phases['score']['block_score_scratch']=[start,end]
 return {'schema':'w13.index-joint-lifetime.v1','pins':[cp,sp],'original_records_preserved':True,
  'simultaneous_regions_by_phase':phases,'joint_allocation_end_bytes':63488,'capacity_bytes':65536,
  'unused_reused_span_bytes':transpose[1]-end,'extra_vs_allF32_61440':{'joint_buffer_extra':4*544-16*32,'unused_span':384,'sum':2048},
  'scratch_reuse_admission':{'requires':['all raw17word decoder LOAD consumers done','all pitch33 transpose/packer LOAD consumers done','decoded key/query/scales STORE visible','no old raw lease or return allowed to write scratch','fourpublicationbuffers preserve descriptors/generation leases'],'actual_physical_callback_ticks':None,'admitted':False},
  'resident_warp_plan':{'warps_per_SM':32,'lanes_per_warp':32,'SIMT_lanes':128,'block_score_warps':64,'waves_minimum':2,'wave_completion_tick':None,'other_program_warp_reservations':None},
  'ordinary_copy_events':copies,'shared_copy_extra_read_write_bytes':65536,'shared_copy_extra_warp_issues':512,
  'source_codec_demand':c['full_tile_shared_demand'],'source_query_codec_demand':c['query32_codec_demand'],
  'source_score_classification_demand':c['score_operand_exception_classification'],
  'finite_common_port':{'banks':32,'bytes_per_word':4,'bank_ports':'1R1W conditional on same-address order','serial_shared_capacity_bytes_per_cycle':128,'RF':'2R1W logical32bit withtwo physicalreadcopies','combined_quad_service_bytes_per_fast_cycle':750,'actual_instruction_branch_calendar':None,'actual_score_RF_residency_calendar':None,'actual_stack_PC_selector':None,'physical_ACK_CDC_drain':None,'unknown_opcode_latency':None},
  'arithmetic_alternatives':c['FP64_alternative_cost_obligations'],
  'no_hidden_provider':'software handler completion/lease is not physical source ACK or ordinary arithmetic completion',
  'tag16_reuse_gate':'common36client allocator requires sourceACK/capture+CDC/drainedepoch protocol; no seventh-token clip or unilateral wrap',
  'clock_GHz':{'serial':0.9,'fabric':1.2},'SS_FF_qualified':False,'baseline_066_preserved':True,
  'physical_admission':'FAIL_CLOSED','rate_credit':0,'hardware_launch':False}

if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(build(),indent=2)+'\n')
