#!/usr/bin/env python3
"""Replace only four proven 0/1-address calendar FIFO masters; preserve every other byte."""
import argparse,hashlib,json,re
from pathlib import Path
OLD='ot_sram_1r1w_64x512_m1_r2c2';NEW='ot_qc_cal_fifo2_512'
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);ap.add_argument('--receipt',required=True);a=ap.parse_args()
source=Path(a.source).read_text();expected={r'\u_gi.u_cal.g_fifo['+str(k)+'].u_fifo'for k in range(4)};rows=[];edits=[]
def zero(expr):
 parts=re.findall(r"1'b[01]",expr)
 return bool(parts)and all(v=="1'b0"for v in parts)and re.sub(r"1'b[01]|[{},\s]",'',expr)==''
def addr2(expr):return bool(re.fullmatch(r"\{(?:1'b0,){5}[A-Za-z_][A-Za-z0-9_]*\}",expr))
for m in re.finditer(OLD+r'\s+(\\\S+)\s*\((.*?)\);',source,re.S):
 name=m[1]
 if name not in expected:continue
 ports=dict(re.findall(r'\.(\w+)\((.*?)\)(?=,|\s*$)',m[2]))
 if set(ports)!={'clk','r_ce_in','r_addr_in','rd_out','w_ce_in','w_addr_in','wd_in','w_mask_in','rr_en','rr_addr','cr_en','cr_sel'}:raise SystemExit('Unexpected port ABI '+name)
 if not all(addr2(ports[k])for k in('r_addr_in','w_addr_in')):raise SystemExit('Address not literally five zero bits plus one bit: '+name)
 if not all(zero(ports[k])for k in('rr_en','rr_addr','cr_en','cr_sel')):raise SystemExit('Repair port not literal-zero: '+name)
 rows.append({'inst':name,'read_address':ports['r_addr_in'],'write_address':ports['w_addr_in'],'repair_literal_zero':True,'old_master':OLD,'new_master':NEW})
 edits.append((m.start(),m.start()+len(OLD)))
if {r['inst']for r in rows}!=expected or len(rows)!=4:raise SystemExit('Must find exactly the four declared FIFO instances')
out=source
for lo,hi in reversed(edits):out=out[:lo]+NEW+out[hi:]
# Restore only the selected master tokens to prove every port/other memory/source byte is unchanged.
restored=out
for m in reversed(list(re.finditer(NEW+r'(?=\s+\\u_gi\.u_cal\.g_fifo\[[0-3]\]\.u_fifo\s)',out))):restored=restored[:m.start()]+OLD+restored[m.end():]
if restored!=source:raise SystemExit('Unexpected change outside the four master tokens')
path=Path(a.out)
if path.exists():raise SystemExit('Refusing existing output '+str(path))
path.parent.mkdir(parents=True,exist_ok=True);path.write_text(out)
receipt={'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'out_sha256':hashlib.sha256(out.encode()).hexdigest(),'changed_master_tokens':4,'other_bytes_identical':True,'added_cycles':0,'qualified_contract':'addresses0/1, repair ports0, no OT_MEM_FAULTS','instances':rows}
Path(a.receipt).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
