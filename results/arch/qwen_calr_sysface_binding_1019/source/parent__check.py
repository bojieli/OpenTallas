#!/usr/bin/env python3
"""Read-only checks of pinned source and arithmetic; no RTL simulation claim."""
from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent
for r in json.loads((p/'sources.json').read_text()):
 assert hashlib.sha256((p/r['artifact']).read_bytes()).hexdigest()==r['sha256'],r
cal=(p/'source/qfd_dv_cmd_cal_mu.sv').read_text()
assert 'CALENDAR_ROM' not in cal and "32'h43414c44" in cal
assert "11'd976" in cal and 'nent, 1\'b0' in cal
assert 'qfd_dv_typed_witness_control' not in (p/'die_connections.txt').read_text()
assert 13*134==1742<2048
# Conditional CALD allocation conflict, NOT a CALR ROM allocation assertion.
for base in range(0,976-2*406+1):
 assert base<=400 and base+2*406-1>=438
m={'scope':'PROPOSED ABI logical floor; not measured, SAFE, or instantiated',
 'identity_bits_per_context':18+18+59+2,'identity_contexts':4,
 'input_capture_bits':{'PW_two_valid_copies_common_address_data':74+2,
 'programme_auth_and_begin':1+1+64+16+1,
 'start_with_identity':1+2+6+16+97,
 'retire_with_identity_and_two_real_final_flags':1+2+6+16+97+2},
 'retirement_seen_flags':8,'internal_c992_extra_ff':7,
 'extra_combinational_internal_c992':135,'tie_sources_minimum':29,
 'physical_input_capture_cost':None,'landings':None,'native_phase':None,
 'reset_epoch':None,'first_use':None,'token_latency':None,
 'production_template_word_allocation':None,'production_instance_count':0}
m['proposed_input_capture_ff_floor']=sum(m['input_capture_bits'].values())
m['proposed_additional_ff_floor_excluding_c992']=4*97+8+m['proposed_input_capture_ff_floor']
(p/'model.json').write_text(json.dumps(m,indent=2)+'\n')
print('PASS: 9 pinned source hashes, frozen CALD classification, template sizing, conditional CALD conflict arithmetic. PROPOSAL only: extra capture/identity FF floor',m['proposed_additional_ff_floor_excluding_c992'])
