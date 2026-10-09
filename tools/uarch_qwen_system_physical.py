#!/usr/bin/env python3
"""Full-shape Q1/Q2 sizing before route; physical results never imply numerical adoption."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def model():
    rom=json.loads((ROOT/'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.json').read_text())
    return {'schema':'opentallas.qwen_system_physical_model.v1','model':'Qwen3-8B ROM TP4',
      'crom':{'macs_per_cycle':0,'compute_intensity':0,'replicas_per_die':1,'macros':48,
       'macro':'ot_rom_4096x266_m8','macro_bits':48*4096*266,'useful_data_bits':48*4096*256,
       'memory_ports':{'wide_read_bytes_cycle':16*32,'narrow_read_bytes_cycle':8*32,'peak_useful_output_bytes_cycle':512},
       'boundaries_bits_cycle':{'input':64+64*24+6,'output':4096+3},
       'communication_intensity':'one read response per active lane per cycle; no MACs',
       'replication_cost':{'priority_muxes_4to1x13':16,'priority_muxes_8to1x13':8,'depth_selects_2to1x64':64,'capture_flops':48*256,'stage_fanout':64},
       'outline_um':[777.6,1000],'grid':[4,12],'macro_pitch_um':[190,80],
       'macro_area_um2':48*rom['area']['macro_area_um2'],'slot_area_um2':777600,
       'remaining_area_um2':777600-48*rom['area']['macro_area_um2'],
       'standard_cell_utilization_target':0.55,'capture_pin_corridor_um':190-rom['area']['macro_width_um'],
       'tracks':{'abutted_top_bits':64+1536+4096,'layers':['M4','M6'],'bits_um_per_layer':(64+1536+4096)/(777.6*2),'pitch_um_assumed':0.064,'capacity_tracks':int(777.6/0.064)*2},
       'macro_clk_q_ps':{c:rom['timing'][c]['clk_to_q_ps'] for c in ['ss','tt','ff']},
       'latency':{'pin_edges':5,'su_CRX':4,'su_ML':7,'added_cycles_token':0,'condition':'SU abutted, no relay; no rate credit until physical boundary qualification'},
       'capture_contract':'single-cycle; all 12288 captures at sole macro output pin, no multicycle exception',
       'physical_gate':'TC setup and FF hold actual routed; SS sensitivity, DRC0; preserve 60ps/25ps uncertainty'},
      'sysctl':{'macs_per_cycle':0,'replicas_per_die':1,'prompt_tokens':8192,'token_bits':18,'payload_bits':147456,
       'memory_bytes_cycle':{'read':2.25,'write':2.25},'outline_um':[500,300],'slot_area_um2':150000,
       'latency':{'stage_switch_edges':3,'stage_switch_added_cycles_token':74,'argmax_to_next_edges':'19 + 2*(CTRL_oneway_edges-1)'},
       'prompt_sram':{'macro':'ot_sram_1r1w_1024x256_m2_r2c2','count':1,'tokens_per_row':8,'slot_bits':32,'ecc_bits_token':6,'protected_bits_token':24,'used_bits_row':192,'capacity_tokens':8192,'macro_area_um2':12314.20968,'read_latency_edges':1,'write_mask_bits':256,'replication_cost':'8 static slot write decoders; 8:1 read24 mux; shortened SECDED24 decode; sticky UE fault','read_memory_bytes_cycle':32,'write_memory_bytes_cycle':32,'mutable_protection':'SECDED24 on18btoken; doubles fail closed; no ROM ECC'},'state':'default-off SRAM candidate; physical and exact gates pending'}}
if __name__=='__main__': print(json.dumps(model(),indent=2))
