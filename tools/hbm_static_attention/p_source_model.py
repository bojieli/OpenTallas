"""Source-exact candidate P gather model; no behavioral payload memory implied."""
import json
from pathlib import Path
# FP32 input is head-major[h][T], native BF16-grid contract rejects low16!=0.
# Each VM burst writes eight128-bit words of eight upper16values/head.
# A datapath word is four rows×16heads: one bank read/head, with four
# consecutive values always within an eight-value physical word.
for T in (128,640):
 for r in range(0,T,4):
  assert r%8 in (0,4)
  assert len({h*8+(r//8)%8 for h in range(16)})==16
  for h in range(16):
   bank=h*8+(r//8)%8;addr=r//64
   assert bank<128 and addr<16 and r%8+4<=8
model=dict(schema='opentallas.hbm_attn.p_source_model.v1',qualification=False,
 canonical_source='ot_hgi_att_unit head-major FP32 P[h][T], descriptor headstride preserved, low16nonzero faults',
 native_VM=dict(quadrant='NE',RG=3,bank_payload_bits=256,banks=8,registered_response_edges=6,consumer_capture_edges=7,request_register_edges=1),
 source_reads_per_record={'128':32,'640':160},source_bytes_per_record={'128':8192,'640':40960},
 datapath=dict(H=16,TD=32,PWORDS=2,values_per_word=64,word_bits=1024,rows_per_word=4,layout='p_w[(rowwithin4*16+head)*16+:16]'),
 actual_memory=dict(master='ot_sram_1r1w_32x128_m1',count=128,depth=32,epochs=2,capacity_bytes=65536,area_um2=128*51.408*20.790),
 write=dict(banks_per_edge=8,bank='head*8+VMbank',address='epoch*16+burst',payload='8FP32upper16values per128-bit SRAMword'),
 read=dict(banks_per_edge=16,bank='head*8+(row//8)%8',address='epoch*16+row//64',select='row%8 is0or4; fourBF16values perhead',latency_edges=1),
 native_outer_instruction_candidate=dict(opcode=4,P_fetch_bit=28,burst_high_bit=29,existing_query_fields_unchanged=True,maximum_burst=9,programme_cold_config_words=339,maximum_Pprefetch_launch_words=170,total_cold_words=509),
 port_audit='All32/160Pwordreadphases use16distinctbanks; no bankreadconflict, fourrows nevercross8valueword',
 remaining=['Actual mappedSRAM RTL+realVM source/fullshape/mutants','Target49 literalP-fetch decode/absoluteprogramme','ActualP softmax producer joins including BF16-grid and NaN/Inf fault propagation','Measured2epochoverlap and immutablethroughput','Physicalmacro/clock/cut/route/systemgeometry'])
p=Path('results/arch/hbm_attention_static_1015/p_source_model.json');p.write_text(json.dumps(model,indent=2)+'\n')
print('PASS Psource port model fullH16 T128/640; actualRTL nativeprogramme unqualified')
