#!/usr/bin/env python3
"""Export every real endpoint boundary FF after the strict guard passes.
Logical banks are <=32 pin bits; physical faces/sites remain plan-owned.
"""
import argparse,collections,gzip,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import face_guard as G

def build(netlist,top):
    text=Path(netlist).read_text();guard=G.guard(text,top)
    if guard['verdict']!='PASS':raise ValueError('strict face guard did not PASS')
    mods=G.parse(text);T=mods[top];F=G.Flat(mods,top);drv=collections.defaultdict(list);loads=collections.defaultdict(list)
    for ci,(typ,path,pins) in enumerate(F.cells):
        for pin,(direction,nets) in pins.items():
            for n in nets:(drv if direction=='out' else loads)[F.find(n)].append((ci,pin))
    rows=[]
    for port in T.ports:
        if re.match(G.SKIP_RE,port):continue
        direction=T.dirs[port]
        for bit in G._bits_of(T,port):
            cur=F.find(bit);chain=[]
            for _ in range(G.MAX_CHAIN+1):
                ci,pin=(loads if direction=='input' else drv)[cur][0];typ,path,pins=F.cells[ci]
                if G.is_ff(typ):break
                assert G.is_buf(typ)
                nd='out' if direction=='input' else 'in'
                nxt=[n for d,ns in pins.values() if d==nd for n in ns];assert len(nxt)==1
                chain.append(path);cur=F.find(nxt[0])
            else:raise ValueError('missing boundary FF')
            idx=int(re.search(r'\[(\d+)\]$',bit).group(1)) if '[' in bit else 0
            rows.append(dict(port_bit=bit,bus=port,direction=direction,register=path,master=typ,register_pin=pin,buffer_chain=chain,logical_bank=port+'.'+str(idx//32),physical_face='PLAN_REQUIRED'))
    assert len(rows)==guard['checked']==guard['ok']
    assert len({x['register'] for x in rows})==len(rows)
    return dict(schema='opentallas.hbm.endpoint_real_pin_registers.v1',top=top,status='MAPPED_GUARD_PASS_NOT_PLACEMENT',checked=len(rows),logical_bank_max_bits=32,pins=rows)

def main():
    a=argparse.ArgumentParser();a.add_argument('netlist');a.add_argument('--top',required=True);a.add_argument('--out',type=Path,required=True);x=a.parse_args();m=build(x.netlist,x.top)
    x.out.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(x.out,'wt') as f:json.dump(m,f,separators=(',',':'))
    print('ENDPOINT_PIN_MAP PASS',x.top,'bits',m['checked'],'banks',len({r['logical_bank'] for r in m['pins']}))
if __name__=='__main__':main()
