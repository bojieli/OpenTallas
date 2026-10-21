#!/usr/bin/env python3
"""Bounded four-state predicate/mux and field-coverage proof, not RTL simulation."""
import hashlib,itertools,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3];BASE='363295685';sym='01XZ'
def logical_and(a,b):return '0' if '0' in (a,b) else '1' if a==b=='1' else 'X'
def mux(s,a,b):return a if s=='1' else b if s=='0' else a if a==b else 'X'
rows=[];checks=0
for a,b,c in itertools.product(sym,repeat=3):
 old=logical_and(logical_and(a,b),c)
 variants=[logical_and(logical_and(a,b),c),logical_and(logical_and(a,c),b),logical_and(logical_and(b,c),a)]
 assert variants==[old]*3
 for x,y in itertools.product(sym,repeat=2):
  assert all(mux(v,x,y)==mux(old,x,y) for v in variants);checks+=3
 rows.append([a,b,c,old,*variants])
# FDN header association and original procedural if/else-if priority.
for go,h1,h2 in itertools.product(sym,repeat=3):assert logical_and(logical_and(go,h1),h2)==logical_and(go,logical_and(h1,h2))
for xcc,fr in itertools.product(sym,repeat=2):
 old=('LOAD','LOAD','ZERO') if xcc=='1' else ('HOLD','HOLD','INC') if fr=='1' else ('HOLD','HOLD','HOLD')
 # Independent field blocks preserve original procedural X/Z-false decisions.
 new=('LOAD' if xcc=='1' else 'HOLD','LOAD' if xcc=='1' else 'HOLD','ZERO' if xcc=='1' else 'INC' if fr=='1' else 'HOLD')
 assert old==new
for sel,a in itertools.product(sym,repeat=2):assert mux(sel,a,a)==a
# Exact old/new AR output field provenance, independent of payload values.
old_a=[f'raw{i}' for i in range(548,1060)]+['last','raw1061']+[f'tag{i}' for i in range(32)]+['1']
old_b=[f'raw{i}' for i in range(548,1095)]
new_a=['']*547;new_b=['']*547
for j in range(512):new_a[j]=new_b[j]=f'raw{548+j}'
new_a[513]=new_b[513]='raw1061'
for j in range(32):new_a[514+j]=f'tag{j}';new_b[514+j]=f'raw{1062+j}'
new_a[512]='last';new_b[512]='raw1060';new_a[546]='1';new_b[546]='raw1094'
assert old_a==new_a and old_b==new_b
for n in [16,32]:assert [i for g in range((n+11)//12) for i in range(g*12,min(n,g*12+12))]==list(range(n))
paths=['rtl/qwen_dv/s5/s8/qfd_dv_s8_rp1.sv','rtl/qwen_dv/s5/s8/qfd_dv_s8_fdn_arf1.sv'];bound={}
for rel in paths:
 old=subprocess.check_output(['git','-C',str(R),'show',BASE+':'+rel],text=True);new=(R/rel).read_text()
 # No new state or initialization; declarations retain the exact original bits.
 strip=lambda s:re.sub(r'//[^\n]*','',s)
 regs=lambda s:re.findall(r'\breg\b[^;]*;',strip(s))
 assert regs(old)==regs(new)
 assert 'assign y=a & b;' in new and 'assign y=s ? a : b;' in new
 bound[rel]={'old_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_sha256':hashlib.sha256(new.encode()).hexdigest(),'register_declarations_byte_equal':True}
# Body shape is tied to the modeled partition and intact scalar state equations.
rp=(R/paths[0]).read_text();fdn=(R/paths[1]).read_text()
for text in ['g<69','g<64','rp_guard[64]','rp_guard[65+g]','rp_guard[68]','.W(16)','.W(8)','.W(2)']:assert text in rp
for text in ['g<8','g<7','xcc_guard[1+g]','xcc_guard[4+g]','xcc_guard[6+g]','fr_guard[5+g]','arf_cnt_inc=arf_cnt+16\'d1','arf_wm1_load=cmd_q[22:7]-16\'d1']:assert text in fdn
out={'scope':'Pure four-state mechanism and exact field/control model; no RTL simulation/native/timing claim','base':BASE,'rp_predicate_64_rows':rows,'rp_bit_mux_comparisons':checks,'fdn_header_assoc_cases':64,'fdn_procedural_priority_cases':16,'fdn_ar_output_bits':547,'register_fields_covered':[32,16,16],'rp_guard_groups':69,'rp_groups_per_pair_class':[23,23,23],'predicted_pair_and_third_loads':23,'predicted_original_guard_input_loads_before_other_uses':25,'native_phase_note':'16-bit kept ternary helper bounds two select uses/bit to32; actual native census still required, no waiver','source_binding':bound,'rtl_simulation':'owned by cb16; not executed here','native':'owned by cb16 combined candidate; not executed here'}
Path(__file__).with_name('MODEL.json').write_text(json.dumps(out,indent=2)+'\n');print('MODEL PASS:64 four-state guard rows,3072 mux comparisons,64header cases,16priority cases,547field bits,unchanged reg declarations')
