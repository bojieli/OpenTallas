#!/usr/bin/env python3
"""Independent exact integer oracle for the all-one KV, fixedT32 programme.

E2M1 code2 times E4M3 scale0x38 is exactly1. Every selected BF16 Q/P value
is a positive dyadic integer times2^-10. Their sums fit24 significand bits,
so every exact FP32 sum is independent of DUT reduction-tree order.
"""
import json,re,sys
from pathlib import Path

def bf16_units(bits):
    assert bits>>15==0
    exp=(bits>>7)&255
    assert 124<=exp<128
    return (128+(bits&127)) << (exp-124)

def units_to_fp32(n):
    assert 0<n<1<<24
    msb=n.bit_length()-1
    return ((msb+117)<<23)|((n-(1<<msb))<<(23-msb))

log=Path(sys.argv[1]);text=log.read_text();checks=0;errors=[];counts={f'{k}{p}':0 for k in ('SCORE','PV_RAW') for p in (0,1)}
score=[units_to_fp32(sum(bf16_units(0x3e80+32*h+d) for d in range(32))) for h in range(8)]
pv=[units_to_fp32(sum(bf16_units(0x3e00+8*r+h) for r in range(32))) for h in range(8)]
for line in text.splitlines():
    m=re.fullmatch(r'(SCORE|PV_RAW) case([01]) relative(\d+) (?:row|c)(\d+) payload([0-9a-f]+) flags([0-9a-f]+)',line)
    if not m:continue
    kind,case,date,tag,payload,flags=m.groups();key=kind+case;seq=counts[key];counts[key]+=1
    expected=score if kind=='SCORE' else pv
    if int(tag)!=(4*seq if kind=='SCORE' else seq):errors.append(f'{key} tag{tag} sequence{seq}')
    if int(flags,16):errors.append(f'{key} tag{tag} flags{flags}')
    raw=int(payload,16)
    for lane in range(32):
        got=(raw>>(32*lane))&0xffffffff;want=expected[lane%8];checks+=1
        if got!=want:errors.append(f'{key} tag{tag} lane{lane} got{got:08x} expected{want:08x}')
if any(n!=8 for n in counts.values()):errors.append(f'output counts {counts}')
if not re.search(r'^NATIVE_PROGRAMME PASS',text,re.M):errors.append('programme did not PASS')
result={'status':'PASS' if not errors else 'FAIL','scope':'independent exact fixedT32 all-one KV arithmetic oracle; no global PIO/PVO calibration', 'integer_unit':'2^-10','checked_fp32_fields':checks,'counts':counts,'expected_score_by_head':[f'{x:08x}' for x in score],'expected_pv_by_head':[f'{x:08x}' for x in pv],'errors':errors[:40],'error_count':len(errors)}
log.with_name('oracle.json').write_text(json.dumps(result,indent=2)+'\n')
print(f"NATIVE_EXACT_ORACLE {result['status']} fields{checks} errors{len(errors)}")
for err in errors[:8]:print(err)
sys.exit(bool(errors))
