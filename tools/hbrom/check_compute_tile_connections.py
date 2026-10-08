#!/usr/bin/env python3
"""Check thin physical wrapper connections against the independently driven bench.

This is source-level port/parameter equivalence at ENABLE=1, STALL=0 and
cancel=0, not a replacement for the connected arithmetic or timing gates.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def balanced(s,start):
    depth=0
    for pos in range(start,len(s)):
        if s[pos]=='(':depth+=1
        elif s[pos]==')':
            depth-=1
            if depth==0:return s[start+1:pos],pos+1
    raise ValueError('Unbalanced source')

def bindings(s):
    result={}; pos=0
    while True:
        m=re.search(r'\.(\w+)\s*\(',s[pos:])
        if not m:break
        a=pos+m.end()-1; value,pos=balanced(s,a)
        if m[1] in result:raise ValueError('Duplicate port '+m[1])
        result[m[1]]=re.sub(r'\s+','',value)
    return result

def instance(s,module,name):
    for m in re.finditer(r'\b'+module+r'\s*#\s*\(',s):
        parameters,end=balanced(s,m.end()-1)
        n=re.match(r'\s*(\w+)\s*\(',s[end:])
        if n and n[1]==name:
            ports,_=balanced(s,end+n.end()-1)
            return bindings(parameters),bindings(ports)
    raise ValueError('Missing instance '+name)

def run():
    paths=['rtl/hbrom/ot_hbrom_compute_tile.sv','tests/rtl/hbrom_compute_tb.sv']
    wrapper,bench=[(ROOT/p).read_text() for p in paths]
    checks=[]
    for module,wi,bi in [('ot_hbm_accel_sm_v','sm','dut'),('ot_hbrom_rom_feed','feed','feed')]:
        wp,wc=instance(wrapper,module,wi);bp,bc=instance(bench,module,bi)
        replacements={'RMAX':'4096','PAIR_COUNT':'128','PAIRS':'128','FEED_PROTECT':'1'}
        normalize=lambda v:replacements.get(v,v)
        wp={k:normalize(v) for k,v in wp.items()};bp={k:normalize(v) for k,v in bp.items()}
        if wp!=bp:raise ValueError((module,'parameters',wp,bp))
        # Benchmark throttle acts only on request valid/ready and is disabled
        # for this equivalence condition. Cancellation is disabled there.
        wc={k:({'sm_fault':'fault','cancel':"1'b0"}.get(v,v)) for k,v in wc.items()}
        bc={k:({'feed_req_ready':'req_ready','req_v&&!throttle':'req_v'}.get(v,v)) for k,v in bc.items()}
        if wc!=bc:raise ValueError((module,'ports',wc,bc))
        checks.append(dict(module=module,parameters=wp,ports=wc,all_ports_equal=True))
    for expression in ['.clk(clk)', '.ce_in(rom_ce[m])']:
        if expression not in wrapper or expression not in bench:raise ValueError(expression)
    # Algebraically identical constant-width packed port slices.
    compact=lambda s:re.sub(r'\s+','',s)
    if '.addr_in(rom_addr[12*m+:12])' not in compact(wrapper):raise ValueError('wrapper ROM address')
    if '.addr_in(rom_addr[m*12+:12])' not in compact(bench):raise ValueError('bench ROM address')
    if '.rd_out(rom_q[274*m+:274])' not in compact(wrapper):raise ValueError('wrapper ROM return')
    if 'assign#(ROM_SS_CQ_NS)rom_q[m*274+:274]=macro_q;' not in compact(bench):raise ValueError('bench ROM timing connection')
    return dict(status='PASS_STATIC_PORT_PARAMETER_EQUIVALENCE',conditions=['wrapper ENABLE=1 PAIRS=128 FEED_PROTECT=1','bench STALL=0','wrapper cancel=0','corresponding ROM macro returns identical personalized payloads; timing qualified separately'],checks=checks,ROM_count=256,ROM_index='8*bankgroup+2*stream+parity',limitations=['No connected arithmetic pass is asserted by this source check','Wrapper blackboxes carry real timing in physical flow; benchmark uses explicit SS delay','Configuration validity and activation publication remain caller obligations'],source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths+[str(Path(__file__).relative_to(ROOT))]})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=run();a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
