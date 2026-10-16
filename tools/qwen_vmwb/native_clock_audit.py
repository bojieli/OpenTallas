#!/usr/bin/env python3
"""Audit actual elaborated cell connections, independently of declared clock count."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('netlist',type=Path);p.add_argument('--expect',choices=['pass','fail'],default='pass');p.add_argument('--out',type=Path);a=p.parse_args()
x=json.loads(a.netlist.read_text());m=x['modules']['ot_qfd_vm_region_nx'];pins=['ck_ctrl','ck_in_lo','ck_in_hi','ck_mem_lo','ck_mem_hi','ck_cap_lo','ck_cap_hi','ck_out_lo','ck_out_hi'];bus=m['ports']['native_ck']['bits'];rows=[];fail=[]
for n,c in m['cells'].items():
 if c['type'] not in ['qvm_bank_banked_native','qvm_su_bank_native']:continue
 if c['type']=='qvm_bank_banked_native':i=int(re.search(r'g_b\[(\d+)\]',n)[1])
 else:
  cp=int(re.search(r'g_c\[(\d+)\]',n)[1]);j=int(re.search(r'g_j\[(\d+)\]',n)[1]);i=8+cp*2+j
 for k,pin in enumerate(pins):
  got=c['connections'][pin];want=[bus[9*i+k]];row={'cell':n,'pin':pin,'bit':got,'expected_bit':want};rows.append(row)
  if got!=want:fail.append(row)
actual=len(set(str(r['bit']) for r in rows));passed=len(rows)==126 and len(fail)==0 and actual==126
out={'passed':passed,'physical_clock_pins':len(rows),'unique_clock_connections':actual,'mismatches':fail,'connections':rows,'scope':'Actual elaborated region bank clock ports only; no phase/delay/CTS qualification'}
if a.out:a.out.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['connections','mismatches']},indent=2));assert passed==(a.expect=='pass')
