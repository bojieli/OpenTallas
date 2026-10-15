#!/usr/bin/env python3
import json
from pathlib import Path
for T in (128,640):
 keys={(h*8+(r//8)%8,r//64,r%8) for h in range(16) for r in range(T)}
 assert len(keys)==16*T
 for row in range(0,T,4):
  assert len({h*8+(row//8)%8 for h in range(16)})==16
result=dict(schema='opentallas.hbm_attn.P_four_fields_model.v1',qualification=False,
 baseline_P128_unchanged=True,fields=4,macros_per_field=128,total_macros=512,
 macro='ot_sram_1r1w_32x128_m1',macro_increment=384,
 macro_increment_area_um2=384*51.408*20.790,macro_total_area_um2=512*51.408*20.790,
 bank='head*8+(row//8)%8',address='epoch*16+row//64',lane='row%8',
 source='ONE actual8x257 nativeRG3 response/FP32gridfault/FILL8 pipeline',
 capture='ONEconverted1024bword +head/burst/epoch broadcasttofourfieldstores',
 outputs='Fourlocal1024b Pwords, each4rows×16heads BF16; unnormalizedexp',
 VM_read_edges=dict(T128=32,T640=160),epochs=2,
 clock=dict(global_pipeline='request/FILL/tags/present/fault',field_ports=4,
  per_field_macro_clock_pins=128,per_field_read_selector_FF=6,
  nominal_field_clock_endpoints=134,synchronous_samephase=True,physical_qualified=False),
 data_volume_T640=dict(nativeFP32_read_bytes=40960,converted_BF16_bytes_per_copy=20480,
  converted_write_bytes_fourcopies=81920),
 audit='FullH16T128/640 bank/address/lane bijection and16distinctbank reads perfield/edge',
 remaining=['Actualhost/currentbank/realprogramme allfourfieldoutput proof+mutants',
 'Mappedglobal/field FF/clock/mux/fanout/area census',
 'Actualfield pins/stations/FILL_LAT/compiler physicalcalendar',
 'SharedHG1 arithmetic localPports and fullnative immutableprice'])
Path('results/arch/hbm_attention_static_1015/P_four_fields_model.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS P4 bank/address model H16 T128/640; same32/160VMrequests,384extraactualmacros')
