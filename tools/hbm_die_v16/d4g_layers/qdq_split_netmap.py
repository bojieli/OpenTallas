#!/usr/bin/env python3
"""Elaborate the existing QDQ r3 soft composition for actual die leaf placement.

Run on the fleet. This is source generation, not a closure or equivalence campaign.
Native children stay blackboxes; only wires and the two real parent glue gates flatten.
"""
import argparse, hashlib, json, re, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
D = 'rtl/hbm_accel/generic/qw/'
SD = D + 'static/'
TOP = 'ot_hgi_qdq_host_split_r3'
SOFT = {TOP: SD+'ot_hgi_qdq_host_split_r3.sv',
        'ot_hgi_qdq_static_transport_split_r4': SD+'ot_hgi_qdq_transport_r4.sv',
        'ot_hgi_qdq_quant_bank_pair_r2': SD+'ot_hgi_qdq_host_split_r2.sv'}
LEAF = {
 'ot_hgi_qdq_nw_program_leaf': (SD+'ot_hgi_qdq_nw_program_leaf.sv','hgi_qdq_program_nw48_r1'),
 'ot_hgi_qdq_transport_ctl_r4': (SD+'ot_hgi_qdq_transport_r4.sv','hgi_qdq_tsplit_ctl_r4s'),
 'ot_hgi_qdq_transport_rslice': (SD+'ot_hgi_qdq_transport_split.sv','hgi_qdq_tsplit_rslice_r2'),
 'ot_hgi_qdq_transport_wslice': (SD+'ot_hgi_qdq_transport_split.sv','hgi_qdq_tsplit_wslice'),
 'ot_hgi_qdq_lg_port_group_r2': (SD+'ot_hgi_qdq_transport_r2.sv','hgi_qdq_lg_r2'),
 'ot_hgi_qw_dec': (D+'ot_hgi_qw_dec.sv',None)}
GLUE = 'rtl/hbm_accel/die_glue/hbfd_qdq_split_glue.sv'

def module(src, name):
    text=(ROOT/src).read_text()
    match=re.search(r'\bmodule\s+'+re.escape(name)+r'\b.*?\bendmodule',text,re.S)
    if not match: raise ValueError((name,src))
    return match.group(0)

def integer(value):
    return int(value,2) if isinstance(value,str) and set(value)<={'0','1'} else value

def build(out, rl, wc, xr):
    if rl+4+2*xr>126 or wc+2+xr>63: raise ValueError('ctl_r4 range exceeded')
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); lib=td/'leaf.v'; soft=td/'soft.v'; result=td/'net.json'
        headers=[]
        for master,(src,_) in LEAF.items():
            body=module(src,master)
            # Preserve the actual parameter and ANSI-port declarations, discard leaf implementation.
            end=body.index(');')+2
            headers.append('(* blackbox *) '+body[:end]+'\nendmodule\n')
        lib.write_text('\n'.join(headers))
        soft.write_text('\n'.join(module(src,m) for m,src in SOFT.items()))
        cmd=f'read_verilog -sv -lib {lib}; read_verilog -sv {soft}; chparam -set RL {rl} -set WC {wc} -set XR {xr} -set XR_SIM 0 {TOP}; hierarchy -top {TOP}; proc; flatten; opt_clean -purge; write_json {result}'
        subprocess.run(['yosys','-Q','-T','-p',cmd],check=True)
        data=json.loads(result.read_text())
    m=next(v for v in data['modules'].values() if integer(v.get('attributes',{}).get('top','0'))==1); input_bits={}
    for p,x in m['ports'].items():
        if x['direction']=='input':
            for b,bit in enumerate(x['bits']): input_bits.setdefault(bit,(p,b))
    def token(bit):
        if bit in ('0','1'): return ['C',int(bit)]
        if bit in ('x','z'): raise ValueError('undriven source composition bit')
        if bit in input_bits: return ['P',*input_bits[bit]]
        return ['N',bit]
    children={}; glue_n=0
    for cn,c in m['cells'].items():
        cm=c['type']; params={k:integer(v) for k,v in c.get('parameters',{}).items()}
        if cm not in LEAF and cm in data['modules']:
            mod=data['modules'][cm]
            cm=mod.get('attributes',{}).get('hdlname',cm).split()[-1]
            params={k:integer(v) for k,v in mod.get('parameter_default_values',{}).items()}
        if cm in LEAF:
            src,kit=LEAF[cm]
            view=f'physical/ref_tile/{kit}/views/{cm}' if kit else 'physical/hgi_quant_wide_views/2b1df5142_dec_s260/ot_hgi_qw_dec'
        elif cm in ('$or','$logic_and'):
            if any(len(bits)!=1 for bits in c['connections'].values()): raise ValueError('unexpected wide glue')
            cm={'$or':'hbfd_qdq_split_or','$logic_and':'hbfd_qdq_split_and'}[cm]
            src=GLUE; view=None; params={}; glue_n+=1
        else: raise ValueError(f'unexpected non-native child {cn}: {cm}')
        name=cm if src==GLUE else re.sub(r'[^a-zA-Z0-9_]','_',cn.lstrip('\\'))
        if name in children: raise ValueError('colliding child name '+name)
        children[name]=dict(master=cm,source=src,params=params,physical_view=view,
            rtl_path=cn,ports={p:dict(direction=c['port_directions'][p],bits=[token(b) for b in bits]) for p,bits in c['connections'].items()})
    drivers={}
    for name,c in children.items():
        for p,x in c['ports'].items():
            if x['direction']=='output':
                for b,t in enumerate(x['bits']):
                    if t[0]=='N':
                        if t[1] in drivers: raise ValueError('multiple drivers')
                        drivers[t[1]]=[name,p,b]
    sources=sorted(set(SOFT.values())|{v[0] for v in LEAF.values()}|{GLUE})
    record=dict(schema='opentallas.hbm.qdq-split-netmap.v1',top=TOP,
        params=dict(RL=rl,WC=wc,XR=xr,XR_SIM=0),children=children,
        outputs={p:[token(b) for b in x['bits']] for p,x in m['ports'].items() if x['direction']=='output'},
        net_drivers={str(k):v for k,v in drivers.items()},
        sources={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},
        timing=dict(rq=3+xr,wq=9+3*xr,beat_done=9+3*xr,record_done=9+3*xr),
        physical_children=sum(bool(c['physical_view']) for c in children.values()),glue_cells=glue_n)
    Path(out).write_text(json.dumps(record,separators=(',',':'))+'\n')
    print(json.dumps(dict(physical_children=record['physical_children'],glue_cells=glue_n,children=list(children))))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('out');ap.add_argument('--rl',type=int,required=True);ap.add_argument('--wc',type=int,default=4);ap.add_argument('--xr',type=int,required=True)
    a=ap.parse_args();build(a.out,a.rl,a.wc,a.xr)
