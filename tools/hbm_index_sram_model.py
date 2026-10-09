"""Unified microarchitecture extension: physical banked IKS return storage."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def model():
 from uarch_model import DFF_UM2,hbm_index_service_model
 base=hbm_index_service_model()
 name='ot_sram_1r1w_128x256_m1_r2c2'
 path=ROOT/'physical/asap7_memory_macros'/name/(name+'.json')
 macro=json.loads(path.read_text())
 bits={'checks':64*32*10,'duplicated_valid':32*64*2,'write_metadata':32*(12+1),
 'macro_capture':64*266,'decoded_data':64*256,'read_metadata_pipeline':5*(11+64*12+64),
 'credit_state':8*7*2,'group_state':2*(11+11+1)}
 # Read metadata/capture/decoder registers are explicit RTL, not free SRAM.
 return dict(schema='opentallas.hbm_index_sram_model.v1',status='PREBUILD_NOT_QUALIFIED',
 base_model=base,source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()},
 geometry=dict(PCs=32,banks_per_PC=2,logical_slots_per_bank=32,bank='j[0]',address='j[5:1]',native_macro_words=128,
 unused_native_words_per_macro=96,macros=64,width_um=macro['area']['macro_width_um'],height_um=macro['area']['macro_height_um']),
 compute=dict(MACs_per_cycle=0,input_bytes_per_cycle=1024,output_bytes_per_cycle=1088,read_sectors_per_group=34,
 read_bytes_per_bank_per_cycle=32,write_bytes_per_bank_per_cycle=32,read_write_ports='independent native 1R1W; at most one read and one write per bank'),
 protection=dict(data='K256 R10 SECDED',encoders=32,decoders=64,check_sidecar='32x10 FF each bank; captured synchronously beside macro word',
 valid='duplicate complement scoreboard; compare continuously and fail closed',control='complement duplicate group/counters/credit registers; fail closed',
 uncorrectable='suppress group output, sticky fault; captured sectors may retire but no incorrect bytes escape',check_sidecar_bits=20480),
 area=dict(macros_mm2=64*macro['area']['macro_area_um2']/1e6,sidecar_DFF_mm2=bits['checks']*DFF_UM2/1e6,
 explicit_register_bits=bits,explicit_register_lower_bound_mm2=sum(bits.values())*DFF_UM2/1e6,
 alternative_64x512_macro_mm2=.852,codec_logic_area='synthesis measurement pending; lower bound does not include codec XOR/compare and remap muxes',
 region_utilization=.55,outline_fit='requires HBM wiring owner r25I bank placement; no P&R launched until fit'),
 timing=dict(corners={k:{x:v[x] for x in ['clk_to_q_ps','min_period_ps','setup_ps','hold_ps']} for k,v in macro['timing'].items()},
 streaming_period_ps=833,setup_uncertainty_ps=60,SS_macro_capture_remaining_ps=833-60-macro['timing']['ss']['clk_to_q_ps'],
 read_issue_to_output_cycles=5,stages=['native SRAM synchronous edge','explicit data/check capture','SECDED syndrome','SECDED correction','remap/output'],
 encoder_write_cycles=1,valid_visible='after encoded macro write edge',retirement='after explicit capture, never at issue',
 initiation_interval_cycles=1,credits='reserved for all8lanes at issue; final returned credits retained'),
 boundaries=dict(captured_read_bits_per_cycle=34*266,output_bits_per_cycle=8*1099,reverse_credit_bits=8,
 descriptor_fanout=32,routing_tracks_lower_bound=8*1099+8,channel_capacity='pending r25I floorplan',routing_check='NOT QUALIFIED'),
 latency=dict(added_read_pipeline_cycles=5,added_write_encoder_cycles=1,ideal_fullframe_issue_cycles=171,
 theoretical_fullframe_drain_cycles=176,added_seconds_per_descriptor_at1p2GHz=6/1.2e9,
 token_composition='8 index layers; descriptor delay and sustained bandwidth measured in actual controller bench, no speculative gain'),
 adopted=False,physical_qualified=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
