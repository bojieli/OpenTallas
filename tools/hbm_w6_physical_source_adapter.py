#!/usr/bin/env python3
"""Literal package inlining for legacy SV frontends; unchanged function bodies.

Emits the one frozen candidate, not a synthesized replacement or arithmetic
oracle. Original package/module/test sources remain byte-identical. The exact
original611-assertion bench must pass this representation before mapping.
"""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def prepare(out):
    pkg=ROOT/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'
    rtl=ROOT/'rtl/gpu/w6/ot_gpu_rf_visibility_fence_w6.sv'
    p=pkg.read_text();r=rtl.read_text()
    start='package ot_gpu_w6_secded_pkg;';end='endpackage';imp='  import ot_gpu_w6_secded_pkg::*;'
    if p.count(start)!=1 or p.count(end)!=1 or r.count(imp)!=1:raise ValueError('exact literal package boundary')
    body=p.split(start)[1].split(end)[0]
    if len(re.findall('function automatic',body))!=3:raise ValueError('all3 source functions preserved')
    flat=r.replace(imp,body)
    if flat.replace(body,imp)!=r:raise ValueError('lossless literal inlining')
    ports=[];head=r[r.index(')(\n')+3:r.index('\n);')];direction=None;width=1
    for t in head.replace('\n',' ').split(','):
        t=t.strip();m=re.fullmatch(r'(input|output)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)',t)
        if m:direction=m[1];width=int(m[2])+1 if m[2] else 1;name=m[3]
        elif re.fullmatch(r'\w+',t):name=t
        else:raise ValueError('exact port syntax')
        ports.append((name,direction,width))
    top='// Full32 physical sizing top; original W6 default remains off.\nmodule ot_gpu_w6_full32_context #(parameter bit ENABLE=0)(\n'
    top+=',\n'.join('  '+d+' wire '+('' if n in ('clk','por_n','rst_n') else '['+str(32*w-1)+':0] ')+n for n,d,w in ports)+'\n);\n'
    top+='  genvar sm; generate for(sm=0;sm<32;sm=sm+1) begin:g_SM\n'
    top+='    ot_gpu_rf_visibility_fence_w6 #(.ENABLE(ENABLE)) u_W6(\n'
    top+=',\n'.join('      .'+n+'('+n+('' if n in ('clk','por_n','rst_n') else '[sm*'+str(w)+'+:'+str(w)+']')+')' for n,d,w in ports)+'\n    );\n  end endgenerate\nendmodule\n'
    out.mkdir(parents=True,exist_ok=False)
    (out/'w6_literal_inline.sv').write_text(flat);(out/'w6_full32_context.sv').write_text(top)
    h=lambda b:hashlib.sha256(b).hexdigest()
    receipt=dict(schema='W6_LITERAL_FRONTEND_ADAPTER_V1',original_package_sha256=h(pkg.read_bytes()),original_module_sha256=h(rtl.read_bytes()),
                 unchanged_function_body_sha256=h(body.encode()),literal_inline_sha256=h(flat.encode()),full32_top_sha256=h(top.encode()),
                 source_default_ENABLE=0,physical_requested_ENABLE=1,replicas=32,
                 original_source_modified=False,numerical_or_hardware_qualified=False)
    (out/'source_representation.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.out)
