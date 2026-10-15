#!/usr/bin/env python3
"""Pre-RTL exact packed136 static gather and real SRAM row-cache budget."""
from fractions import Fraction
import hashlib,json
from pathlib import Path

def model():
 # Reuse the historical assembler's exact 5-sector gather, four 64-bit shifts,
 # and 4/4/4/5 consumed-sector advance, without its handshake state machine.
 source='rtl/gpu/ot_gpu_payload_assemble.sv'
 for phase in range(4):
  window=bytes((i*17+phase)&255 for i in range(160))
  got=(int.from_bytes(window,'little')>>(phase*64))&((1<<1088)-1)
  assert got.to_bytes(136,'little')==window[phase*8:phase*8+136]
 return dict(schema='opentallas.hbm-svc-sm-packed136.v1',default_PACKED136=0,
  reused_bitpacking_source=source,reused_bitpacking_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
  handshake_state_reused=False,record_bytes=136,weight_bytes=128,scale_bytes=8,
  packet_layout='{valid,tag10,scale64,weights1024}',sectors_per_four_rows=17,
  fixed_sector_count_per_five_edges=[4,4,4,4,1],fixed_row_capture_offsets=[3,4,5,6],
  steady_stream_cycles_per_row=1.25,immutable_price_cycles_per_row=1.374315789,
  component_cadence_fits_immutable_price=Fraction(5,4)<=Fraction('1.374315789'),
  sector_window_entries=16,sector_window_data_FF=4096,sector_window_valid_FF=16,
  row_cache_macros=5,macro='ot_sram_1r1w_128x256_m1_r2c2',
  cache_banks=2,rows_per_bank=64,cache_tag_FF=1280,cache_valid_FF=128,
  cache_macro_area_um2=5*3893.853,SRAM_read_rows_per_cycle=1,
  final_padding='whole packed block only, up to128-byte HBM line; never160-byte per-record padding',
  block_sector_counts={str(n):((n*136+127)//128)*4 for n in [1,2,3,4,16,64]},
  actual_XOR_four_PC_source_bound=False,checkpoint_image_bound=False,
  full_native_SM83_programme_bound=False,compiler_calendar_bound=False,
  physical_qualified=False,adopted=False,
  faults='missing/extra fixed sector or row, stale epoch, bad index, duplicate, owned bank, incomplete read')
if __name__=='__main__':print(json.dumps(model(),indent=2))
