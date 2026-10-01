"""Ordinary GPU index-format capacity screening; never physical admission."""
import hashlib,json,struct,subprocess
from pathlib import Path


def bits_roundtrip(words):
    # Transport existing producer output bits, never reconstruct from quant codes.
    return list(struct.unpack('<'+str(len(words))+'I',struct.pack('<'+str(len(words))+'I',*words)))


def budget(fallback_rows=64):
    if not 0<=fallback_rows<=64: raise ValueError('finite tile')
    # Fixed 512-byte slots: deterministic owner/address mapping for either format.
    regions=[('query_f32',0,16384),('key_f32_term_major',16384,49152),
             ('metadata',49152,51200),('transpose_32x33',51200,55424),
             ('return_slots_16x32',55424,55936)]
    payload=fallback_rows*512+(64-fallback_rows)*68
    sectors=fallback_rows*16+(64-fallback_rows)*3 # independently aligned key records
    metadata_sectors=64 # one 32B descriptor/key, explicit service
    return {'fallback_rows':fallback_rows,'packed_rows':64-fallback_rows,
      'payload_valid_bytes':payload,'read_port_bytes':32*(sectors+metadata_sectors),
      'write_port_bytes':32*(sectors+metadata_sectors),'mixed_commands':2*(sectors+metadata_sectors),
      'shared_750B_fast_cycle_port_floor':(64*(sectors+metadata_sectors)+749)//750,
      'single_stack_command_floor':2*(sectors+metadata_sectors),
      'balanced_four_stack_command_floor':(2*(sectors+metadata_sectors)+3)//4,
      'command_distribution_actual':None,'shared_regions':regions,'shared_peak_bytes':55936,
      'shared_capacity_bytes':65536,'double_buffer_fits':False,
      'key_address_formula':'base512_aligned + local_row*512; descriptor separate base32_aligned + local_row*32',
      'descriptor_fields_bits':{'format':8,'valid_length':16,'owner_rank':8,'address':64,'source_epoch':64,'source_hash_ref':64,'reserved':32},
      'format_codes':{'decoded_producer_f32_le128':0,'packed68_finite_exact_gate_required':1},
      'decoded_shared_word':'4096+term*64+tile_row; adjacent-row warp unique32 banks',
      'transpose_scratch_word':'12800+row*33+col; rows/cols both32 unique banks',
      'transport_rule':'F32 fallback copies actual post-producer IEEE bits including NaN payload/Inf/negative zero; no inverse quantization',
      'producer_write_and_reader_read_both_charged':True,'packed_final_sector_policy':'candidate writes all 96B including explicitly initialized 28B padding; no masked-write service assumed; exact producer padding/ownership gate pending',
      'RF_contract':{'read_ports':2,'write_ports':1,'regs_per_thread':32,'resident_warps_per_SM':32,'streaming_f32_words_per_lane':1,'complete_score_liveness':None},
      'source_to_f32_transpose_shared_bytes':65536 if fallback_rows==64 else None,
      'minimum_f32_transpose_warp_issues':512 if fallback_rows==64 else None,
      'serial_clock_GHz':0.9,'fabric_clock_GHz':1.2,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,
      'contextual_SS_FF':None,'whole_program_cycles':None,'rate_credit':0,'physical_admission':'FAIL_CLOSED'}


def receipt():
    pins={}
    for path in ['tools/hdc_golden_v41.py','tools/w19_hbm_tp96_isa.py','tools/deepseek_hbm_complete_executor.py']:
        blob=subprocess.check_output(['git','show','bb38a691e:'+path]);pins[path]={'source_git':'bb38a691e','sha256':hashlib.sha256(blob).hexdigest()}
    return {'schema':'w13.index-format-screen.v1','source_pins':pins,'baseline_066_preserved':True,
      'all_f32':budget(64),'tagged_mixed_endpoints':[budget(0),budget(64)],
      'domain_rejection':'Inf source scale255 / NaN scale256 cannot imply byte-scale packed admission; no clamp/escape/unreachable assumption',
      'selection':'none: allF32 capacity candidate; tagged packed requires actual exact producer/consumer and both format calendars',
      'open_gates':['source-produced F32 callback bytes and exact consumer instruction binding','packed finite exact gate incl scale253 overflow','descriptor publication/writevisible ACK and reverseCDC','actual per-stack mixed read/write commands/row turnaround','RF score liveness and full arithmetic op calendar','shared return scatter/mux routes and bank service','32SM placement/owner routing and contextual SSFF'],
      'hardware_launch':False}

if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(receipt(),indent=2)+'\n')
