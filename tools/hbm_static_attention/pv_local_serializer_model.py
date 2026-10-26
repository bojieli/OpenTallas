#!/usr/bin/env python3
"""Opt-in D: local PV banks, preserving exact H16/D512 output contract."""
import json
from pathlib import Path

def bank(t,c,g):return (t*16+c)*4+g
seen=set()
for t in range(32):
 for c in range(16):
  for h in range(16):
   key=(bank(t,c,h//4),h%4)
   assert key not in seen;seen.add(key)
assert len(seen)==8192
for c in range(16):
 w={bank(t,c,g) for t in range(32) for g in range(4)}
 assert len(w)==128
 assert all(b//64==t for t in range(32) for b in [bank(t,c,g) for g in range(4)])
for h in range(16):
 for k in range(8):
  selected={bank(4*k+d//16,d%16,h//4) for d in range(64)}
  assert len(selected)==64
# Wrong headgroup selector reads the wrong quartet, though data ports stay legal.
assert bank(0,0,1)!=bank(0,0,0)
result=dict(schema='opentallas.hbm_attn.pv_local_D_model.v1',qualification=False,
 opt_in=True,baseline128_unchanged=True,H=16,D=512,
 bank='(tile*16+c)*4+head//4',address='epoch (0 or1)',lane='head%4',
 physical_memory=dict(macro='ot_sram_1r1w_32x128_m1',banks=2048,banks_per_tile=64,
  allocated_bytes=1048576,useful_bytes_two_epochs=65536,
  area_um2=2048*51.408*20.790,increment_over128_um2=1920*51.408*20.790),
 capture=dict(edges=16,selected_banks_per_edge=128,payload_bits_per_edge=16384,
  local='Each tile receives only its16FP32+16flag payload; writes4macros at selected dimension'),
 drain=dict(edges=128,selected_banks_per_edge=64,VM_bits_per_edge=2048,
  order='head0..15,block0..7;4adjacent tiles perblock',
  local='Each selected tile emits sixteenFP32+flags from its sixteen dimension banks'),
 status=dict(storage_FF=16384,read_pipeline_FF=8192,per_tile_storage_FF=512,
  per_tile_read_FF=256,per_tile_macro_clock_pins=64),
 clocks=dict(explicit_bank_clock_ports=4,global_control_clock_ports=1,
  nominal_tile_sequential_clock_endpoints=836,nominal_bankroot_endpoints=6688,
  contract='All5 clock inputs synchronous and phase matched; actual clock gates/buffers/tree/delay/skew not yet synthesized or qualified'),
 audit=dict(full8192word_bijection=True,all16phases128distinctwrites=True,
  all128drains64distinctreads=True,bankcapture_tile_local=True,
  wrong_headgroup_mapping_detected=True),
 remaining=['Actual macro RTL/fullshape,flags,twoepochs,simultaneousreuse and mutants',
 'Actual WG1/currentbank commit join',
 'Mapped mux/decoder/control/register and fullclock overhead',
 'Actual tile placement/pins/cut/routing and native immutable price'])
Path('results/arch/hbm_attention_static_1015/pv_local_D_model.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS D local PV bank model:8192word bijection,16x128write,128x64read,32local homes; physical overhead open')
