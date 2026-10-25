#!/usr/bin/env python3
"""Extract the eight changed reset/control flops from the exact flat-root view.
The cut is only a local control equivalence gate, not full-root/signoff LEC.
"""
import argparse,re
from pathlib import Path
from overlay_root_delivered_reset import overlay

def extract(src):
    changed=overlay(src)
    blocks=re.findall(r"  always @\(posedge buffer_clk\)\n    if \(!\\u\.u_buffer\.u_rr\.relay_q\[0\]\[0\] \)[^\n]+\n    else [^\n]+",changed)
    if len(blocks)!=5:raise ValueError('expected five exact flat buffer control blocks')
    start=changed.index('  // Timed delivered-reset pipeline,')
    end=changed.index('  assign _67103_',start)
    pipeline=changed[start:end]
    names=['rd_v','wp','rp','r_delay','r_publish']
    decl='\n'.join('reg \\u.u_buffer.'+n+' ;' for n in names)
    text=r'''
`timescale 1ns/1ps
module tkm_flat_buffer_reset_cut(input buffer_clk,rst_n,w_v,r_v,
output wire[4:0]state,output wire local_reset_n);
wire \u.buf_wv ;assign \u.buf_wv =w_v;
wire \u.read_v ;assign \u.read_v =r_v;
reg \u.u_buffer.u_rr.relay_q[0][0] ;
wire \u.u_buffer.u_rr.sync_q[0] ;
wire \u.u_buffer.u_rr.sync_q[1] ;
'''+decl+'\n'+'\n'.join(blocks)+'\n'+pipeline
    text+='assign state={'+','.join('\\u.u_buffer.'+n+' ' for n in names)+'};\n'
    text+='assign local_reset_n=\\u.u_buffer.u_rr.relay_q[0][0] ;\nendmodule\n'
    return text

def main():
    a=argparse.ArgumentParser();a.add_argument('source',type=Path);a.add_argument('out',type=Path);x=a.parse_args()
    x.out.write_text(extract(x.source.read_text()))
if __name__=='__main__':main()
