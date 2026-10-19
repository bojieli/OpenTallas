#!/usr/bin/env python3
"""Finite source/artifact integrity only; does not elaborate or map RTL."""
import hashlib,json,pathlib,re
p=pathlib.Path(__file__).resolve().parent
m=json.loads((p/'model.json').read_text()); rows=json.loads((p/'endpoints.json').read_text())
expected={'ot_sram_oldread_wreg.sv':'67df3246d6cb5648945ca87ef2fd2f46f6e631df622bc19f39432286f97a46f0','ot_s81sl_slice_lep.sv':'84dbae565e70f150e17e0f1e81e7975be68f2074ecf5057b9f5a367a5fe2813f'}
for f,h in expected.items(): assert hashlib.sha256((p/'input'/f).read_bytes()).hexdigest()==h
assert len(rows)==2195 and len({(r['bank'],r['terminal']) for r in rows})==2195
assert sum(r['use'] not in ('POWER','GROUND') for r in rows)==2185
assert sum(r['logical_endpoint'] in ("1'b0","1'b1") for r in rows)==887
assert sum(r['terminal'].startswith('rd_out') and r['logical_endpoint'] is None for r in rows)==87
assert all(r['native_master'] is None and r['placement'] is None and not r['selected_new_master'] for r in rows)
assert all(r['group']==4*r['bank'] for r in rows)
assert m['state']['total_declared_soft_FF']==553+18*10+70*11+553==2056
assert m['caller_group_state']['total_FF']==18*(9+9+10+4+1)==594
assert m['state']['macro_data_bits']==5*512*128
assert m['state']['useful_bits']==553*512
assert m['declared_port_bits']==1+70+1+162+553+1+162+553+18+18
old=(p/'input/original_lep_512x128.lef').read_bytes()
assert hashlib.sha256(old).hexdigest()==m['conditional_geometry']['old_master_authority']['sha256']
size=re.search(rb'SIZE\s+(\S+)\s+BY\s+(\S+)\s*;',old)
assert list(map(float,size.groups()))==[174.120,29.736]
assert abs(m['conditional_geometry']['old_macro_area_um2']-5*174.120*29.736)<1e-8
g=json.loads((p/'input/spread192_upper_pg.json').read_text())['families']['sc2']
assert g['outline_unchanged_nm']==[216840,43800]
assert m['conditional_geometry']['outline_um']==[216.840,43.800]
assert abs(m['conditional_geometry']['macro_area_um2']-5*216.840*43.800)<1e-8
print('PASS finite source hashes,2195 unique terminal roles,887 constants,87 unused outputs,complete state/port arithmetic; native/placement/SC2 adoption remain NULL')
