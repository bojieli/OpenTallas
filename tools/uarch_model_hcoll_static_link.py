#!/usr/bin/env python3
"""Pre-build analytic model for HBM545 static native SRAM/CRC link wrapper."""
import json

def model():
    return {
      'status':'UNQUALIFIED_ANALYTIC_ONLY',
      'source_revision':'4c66b6a95',
      'payload_bits':545,'frame_bits':596,'crc_bits':32,
      'frame_identity':'epoch8 + monotonically consumed slot6; max64 frames per epoch',
      'native_store':{'macros':4,'macro_shape':[64,512], 'physical_storage_bits':131072,
                      'usable_payload_bits':64*545,'logical_slots':64},
      'clock_roots':5,
      'pins':{'input_bits':1180,'output_bits':1155,'total':2335},
      'replay_leaf_declared_flops_each':2+3*6+3*137,
      'control_flop_estimate_upper_bound':2500,
      'wrapper_control_flops_upper_bound':33,
      'largest_clock_root_estimated_sinks':2533,
      'mux_logic':'four137-bit write-age bypass muxes; CRC32 masked parity XORs',
      'crc_parallel_xor_gate_upper_bound':2*32*(545+19-1),
      'bandwidth':{'max_frames_per_cycle':1,'payload_bits_per_cycle':545,
                   'wire_bits_per_cycle':596,'epoch_max_frames':64},
      'latency_edges':{'slot_read_to_registered_tx':3,'pin_rx_to_checked_payload':1},
      'area_estimate':'4*native64x512_macro_area + flop/mux/CRC cell area; no library calibrated numbers',
      'unverified':['mapped area','assigned die slot','physical bandwidth/PHY','clock phases',
                    'die timing','drain/restart calendar','exceptional retry implementation'],
    }
if __name__=='__main__': print(json.dumps(model(),indent=2,sort_keys=True))
