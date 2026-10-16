#!/usr/bin/env python3
"""Source-bound scalar-root writer physical-wrapper grant; no active adoption."""
import argparse
import collections
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import hbm_die_views as V


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-ref',required=True)
    ap.add_argument('--source',default='rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_vmwrite_roots_v6_physical.sv')
    ap.add_argument('--request',default='results/rtl/hbm_writer_v6_0324/typed_root_request.json')
    ap.add_argument('--out',default='results/arch/hbm_die_v15/writer_roots_v6_1016')
    a=ap.parse_args();out=ROOT/a.out;out.mkdir(parents=True,exist_ok=True)
    get=lambda ref,p:subprocess.check_output(['git','-C',str(ROOT),'show',f'{ref}:{p}'])
    raw=get(a.source_ref,a.source);request_raw=get(a.source_ref,a.request);request=json.loads(request_raw)
    master=Path(a.source).stem
    with tempfile.NamedTemporaryFile(suffix='.sv') as f:
        f.write(raw);f.flush();ports=V.L.parse_module(f.name,master,dict(MUT=0))['ports']
    template=get('8e0909ea1','physical/hbm_coll_writer_mid_0030/io.tcl').decode()
    records=re.findall(r'ot_assigned_pin_exact\s+\{([^}]+)\}\s+(M\d)\s+([NSEW])\s+([\d.]+)',template)
    width,height=request['outline_um'];target={p['port']:(p['face_requested'],p['approx_center_um']) for p in request['ports']}
    assert len(target)==16 and set(target)<=set(ports)
    data={f:[] for f in 'NSEW'}
    for name,layer,face,pos in records:
        if name=='clk':continue
        if name=='rgx_data[942]':face,pos='W','194.412'
        m=re.fullmatch(r'(rgx_data|kq)\[(\d+)\]',name)
        if m:
            chunk=512 if m[1]=='rgx_data' else 281;index=int(m[2]);name=f'{m[1]}{index//chunk}[{index%chunk}]'
        data[face].append((name,float(pos)))
    def legal(pos,face):
        if face in 'WE':return True
        k=0
        while 2.16+.3+5.4*k-.06<=width:
            lo=2.16+.3+5.4*k-.06
            for a,b in [(lo,lo+.12),(lo+.192,lo+.312)]:
                if pos+.036>a and pos-.036<b:return False
            k+=1
        return True
    clocks={};positions={};face_capacity={}
    for name,(face,want) in target.items():
        length=width if face in 'NS' else height
        avail=[round(.012+k*.048,6) for k in range(math.ceil((4.32-.012)/.048),math.floor((length-4.32-.012)/.048)+1)]
        pos=min((v for v in avail if legal(v,face)),key=lambda v:abs(v-want))
        assert all(f!=face or abs(pos-v)>=.096-1e-8 for f,v in clocks.values())
        clocks[name]=(face,pos);positions[name]=(face,pos)
    for face in 'NSEW':
        items=sorted(data[face],key=lambda x:x[1]);length=width if face in 'NS' else height
        for spacing in [.144,.096]:
            avail=[]
            for k in range(math.ceil((4.32-.012)/.048),math.floor((length-4.32-.012)/.048)+1):
                pos=round(.012+k*.048,6)
                if not legal(pos,face):continue
                if any(f==face and abs(pos-v)<.192-1e-8 for f,v in clocks.values()):continue
                if not avail or pos-avail[-1]>=spacing-1e-8:avail.append(pos)
            if len(avail)>=len(items):break
        assert len(avail)>=len(items),(face,len(items),len(avail))
        picks=[avail[round(i*(len(avail)-1)/(len(items)-1))] for i in range(len(items))] if len(items)>1 else [avail[len(avail)//2]]
        for (name,_),pos in zip(items,picks):positions[name]=(face,pos)
        bits=len(items)+sum(f==face for f,_ in clocks.values())
        face_capacity[face]=dict(bits=bits,length_um=length,utilization=round(bits*.096/length,6))
        assert bits*.096/length<=.60
    expected={n if b==1 else f'{n}[{k}]' for n,(direction,b) in ports.items() for k in range(b)}
    assert set(positions)==expected,(expected-set(positions),set(positions)-expected)
    perbus=collections.defaultdict(list)
    for name,(face,pos) in positions.items():
        m=re.fullmatch(r'(.+)\[(\d+)\]',name);base=m[1] if m else name;bit=int(m[2]) if m else 0
        perbus[base].append((bit,face,pos))
    pins=[]
    for base,items in perbus.items():
        items.sort();faces={v[1] for v in items};assert len(faces)==1,(base,faces)
        face=next(iter(faces));cs=[v[2] for v in items]
        pins.append(dict(name=base if len(items)==1 else f'{base}[{len(items)-1}:0]',face=face,
                         layer='M5' if face in 'NS' else 'M4',bit_centres_um=cs,
                         offset=round(sum(cs)/len(cs),6),span_um=[min(cs)-.048,max(cs)+.048]))
    for face in 'NSEW':
        cs=sorted(pos for f,pos in positions.values() if f==face)
        assert len(cs)==len(set(cs)) and all(b-a>=.096-1e-8 for a,b in zip(cs,cs[1:]))
    entries=[dict(pin=n,face=f,layer='M5' if f in 'NS' else 'M4',offset=pos,
                  clock_reference='actual phi-R per independently measured root required') for n,(f,pos) in clocks.items()]
    grant=dict(schema='opentallas.hier_contract.v1',qualification=False,canonical_die_contract_mutated=False,
               slots=[dict(name='coll_writer_roots_v6_physical_master',cell=master,source=a.source,
                           source_sha256=hashlib.sha256(raw).hexdigest(),source_prerequisite=a.source_ref,
                           kind='tile',outline=dict(w=width,h=height),params=dict(MUT=0),pins=pins,
                           clock_entry=next(x for x in entries if x['pin']=='clk_body'),clock_entries=entries,
                           clock_entry_domains=request['clock_entry_domains'],clock_port='clk_body',physical_view=None,
                           face_capacity=face_capacity,pin_status='SOURCE_BOUND_TYPED_ROOT_PROPOSAL_NO_VIEW',
                           pg_layer='M5',signal_max_layer='M5',layer_cap='M5',strap_layer='M6',
                           instances=[f'coll_{q}_writer0' for q in ['SW','SE','NW','NE']])],
               request_sha256=hashlib.sha256(request_raw).hexdigest(),native_source_proof=request['proof'],
               normal_cycles_added=request['normal_cycles_added'],declared_state_bits_added=request['declared_state_bits_added'],
               open=['physical-flow exact bench/mutant binding','actual ODB assigned-bit/PG readback',
                     'measured per-root insertion/spread and phi-R','TT setup/FF hold/DRC0','current parent/die pin binding'])
    (out/'grant.json').write_text(json.dumps(grant,indent=1)+'\n')
    lines=['# Exact source-bound data/scalar-root assignment; actual ODB readback mandatory.',
           'source /src/physical/common_flow/assigned_pin_exact.tcl']
    for name,(face,pos) in sorted(positions.items()):
        lines.append(f'ot_assigned_pin_exact {{{name}}} {"M5" if face in "NS" else "M4"} {face} {pos:.6f}')
    lines+=['# Consuming native gate must verify exact assigned-pin ODB readback.','']
    (out/'assigned_pins.tcl').write_text('\n'.join(lines))
    print(json.dumps(dict(source_sha256=hashlib.sha256(raw).hexdigest(),ports=len(ports),bits=len(expected),faces=face_capacity)))


if __name__=='__main__':main()
