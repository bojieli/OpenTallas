#!/usr/bin/env python3
"""Extract real adapted frame connections and compare with the plan, emit OUT.sv.

Usage: frame_forward_miter.py TOP.v PLAN.json INSTANCE_MAP.json OUT.sv
MUT1 miswires the first destination to the next frame. Existing frame core RTL
is unchanged; this vehicle checks the new logical connections at every bit.
"""
from pathlib import Path
import json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'physical/die_plan/s81/bind'))
import asbparse as A
_,top,pf,mf,out=sys.argv
_,inst=A.parse(top);plan=json.loads(Path(pf).read_text());im=json.loads(Path(mf).read_text())['frames']
def frame(p):return 'u_'+im[p[:-3]]
def conn(n,p):return next((e for q,e in inst[n]['conns'] if q==p),None)
sources=sorted(n for n in inst if (conn(n,'xo') or '').startswith('pf_xo_'))
ix={n:i for i,n in enumerate(sources)};bywire={conn(n,'xo'):n for n in sources}
assert len(bywire)==len(sources)==24
actual=[];expected=[]
for e in plan['ports']:
 if e['src']['bus']!='xo_o0' or e['dst']['bus']!='xo_i0':continue
 s,d=frame(e['src']['part']),frame(e['dst']['part'])
 if s not in ix:continue
 wire=conn(d,'x');assert wire in bywire,(d,wire)
 actual.append(ix[bywire[wire]]);expected.append(ix[s])
assert len(actual)==24
sv='''`timescale 1ns/1ps
module tb #(parameter MUT=0);
reg clk=0; always #1 clk=~clk;
reg [1103:0] payload[24];
wire [1103:0] actual[24];
integer i,j,k,errors=0;
'''
for i,a in enumerate(actual):sv+=f'assign actual[{i}]=payload[(MUT && {i}==0) ? {(a+1)%24} : {a}];\n'
sv+='initial begin\nfor(i=0;i<128;i=i+1)begin\n@(negedge clk);\nfor(j=0;j<24;j=j+1)begin\n'
for b in range(0,1104,32):sv+=f'payload[j][{min(1103,b+31)}:{b}]=$urandom;\n'
sv+='end\n@(posedge clk);#0.01;\n'
for i,e in enumerate(expected):sv+=f'if(actual[{i}]!==payload[{e}])errors=errors+1;\n'
sv+='''end
$display("FRAME_FORWARD_MITER MUT=%0d edges=%0d bits_per_edge=26496 errors=%0d",MUT,i,errors);
if((MUT==0 && errors!=0)||(MUT!=0 && errors==0))$fatal(1,"mapping miter/negative-control failed");
$finish;end
endmodule
'''
Path(out).write_text(sv)
print('mapped24 actual frame connections against independent plan endpoints')
