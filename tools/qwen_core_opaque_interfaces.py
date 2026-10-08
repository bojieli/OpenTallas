#!/usr/bin/env python3
"""Specialize opaque module headers before erasing their implementation.

The header is copied verbatim from the RTL used by the existing prep. A private
process prevents Yosys auto-blackboxing an empty module. Hierarchy resolves all
parameters first; blackbox then removes the placeholder before any simulation,
mapping, or route. No functional output is tied or forced by this operation.
"""
import hashlib,json,re
from pathlib import Path

def rewrite(prep):
    prep=Path(prep);lines=prep.read_text().splitlines()
    names=[x.split()[1] for x in lines if x.startswith('blackbox ')]
    sources=[Path(x.split()[-1]) for x in lines if x.startswith('read_verilog ')]
    headers=[];pins={}
    for name in names:
        found=[]
        for src in sources:
            txt=src.read_text();m=re.search(r'(?m)^module\s+'+re.escape(name)+r'\s*[#(]',txt)
            if m:
                end=txt.index(');',m.start())+2
                found.append((src,txt[m.start():end]))
        if len(found)!=1:raise ValueError(f'{name}: expected one source header, found {len(found)}')
        src,hdr=found[0];pins[name]=dict(source=str(src),sha256=hashlib.sha256(src.read_bytes()).hexdigest(),header_sha256=hashlib.sha256(hdr.encode()).hexdigest())
        headers.append(hdr+'\n reg __opaque_shape_only; always @* __opaque_shape_only=1\'b0;\nendmodule\n')
    stub=prep.parent/'opaque_headers.sv';stub.write_text('\n'.join(headers));out=[];inserted=False
    for x in lines:
        if x.startswith('blackbox '):
            if not inserted:out.append('read_verilog -sv -overwrite '+str(stub));inserted=True
            continue
        out.append(x)
        if x.startswith('hierarchy '):
            out += ['proc','write_json '+str(prep.parent/'specialized_before_blackbox.json')]
            out += ['blackbox '+n+' $paramod*'+n+'*' for n in names]
    prep.write_text('\n'.join(out)+'\n')
    (prep.parent/'opaque_header_pins.json').write_text(json.dumps(pins,indent=2)+'\n')

def validate(path):
    design=json.loads(Path(path).read_text());top=design['modules']['ot_qwen_rom_core'];rows=[]
    for name,cell in top['cells'].items():
        typ=cell['type'];mod=design['modules'].get(typ)
        if mod is None or '__opaque_shape_only' not in mod['netnames']:continue
        declared=mod['ports'];observed=cell['connections']
        if set(declared)!=set(observed):raise ValueError((name,'port set mismatch'))
        for p,decl in declared.items():
            if len(decl['bits'])!=len(observed[p]):raise ValueError((name,p,'port width mismatch'))
        rows.append(dict(instance=name,module=typ,parameters=mod.get('parameter_default_values'),ports={p:dict(direction=d['direction'],bits=len(d['bits'])) for p,d in declared.items()}))
    if not any(x['instance']=='u_me' for x in rows):raise ValueError('ME opaque instance missing')
    su=next(x for x in rows if x['instance']=='g_vsu.u_su');me=next(x for x in rows if x['instance']=='u_me')
    assert su['ports']['kv_we']['bits']==len(top['ports']['kv_we']['bits'])
    assert me['ports']['am_idx']['bits']==len(top['ports']['token']['bits'])
    return dict(status='pass',scope='all opaque instance ports compared with specialized RTL module declarations',instances=rows)

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('prep',type=Path);a.add_argument('--validate',action='store_true');args=a.parse_args()
    if args.validate: print(json.dumps(validate(args.prep),indent=2))
    else:rewrite(args.prep)
