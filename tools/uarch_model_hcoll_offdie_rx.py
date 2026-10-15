"""0az off-die elastic block admission before fixed on-die slots."""
def model(block_words=64, ports=3):
 if not 1 <= block_words <= 64: raise ValueError('block_words must be 1..64')
 return dict(schema='hcoll.offdie_rx.v1', block_words=block_words, ports=ports,
   payload_bits=612, ingress_bits_per_cycle_per_port=612,
   output_bits_per_cycle_per_port=612, memory_bytes_per_cycle_per_port=76.5,
   sram_macros_per_port=2, sram_shape='native 64x512; each stores 306 used columns',
   capacity_frames_per_port=64, release_slot_to_pin_edges=3, native_RX_sample_edge=4, native_RX_publish_edge=6,
   last_accept_to_block_ready_edges=2, release_throughput_frames_per_cycle=1,
   block_latency_edges=block_words+2+1+3,
   boundary_tracks_per_port=1224, replica_count=ports,
   mux_cost='two native SRAM registered read ports; no 64-way data flop mux',
   area_slot_fit='UNQUALIFIED: needs actual die boundary slot and native clock/pin gate',
   token_latency='elastic fill variable; admit complete block before native HOST launch; fixed release adds 3 edges',
   status='source candidate only; no board/FEC/multi-die/physical qualification')
if __name__=='__main__':
 import json
 print(json.dumps(model(),indent=2))
