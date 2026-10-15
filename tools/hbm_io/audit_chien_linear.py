#!/usr/bin/env python3
"""Independently audit emitted XOR equations as exact GF(2) linear forms.

This complements actual SV simulation; it deliberately supports only the emitted
assign syntax, rejecting unknown expressions rather than pretending to be an HDL
parser. Reference multiplication uses carryless polynomial product/reduction,
not the generator's iterative GF multiplication.
"""
import argparse,json,pathlib,re

def polynomial_mul(a,b):
 p=0
 for i in range(10):
  if b>>i&1:p^=a<<i
 for i in range(18,9,-1):
  if p>>i&1:p^=0x409<<(i-10)
 return p

def power(k):
 result=1;a=2;k%=1023
 while k:
  if k&1:result=polynomial_mul(result,a)
  a=polynomial_mul(a,a);k>>=1
 return result

def product(offset,c):
 return [sum(1<<(offset+b) for b in range(10) if polynomial_mul(1<<b,c)>>j&1) for j in range(10)]

def audit(path):
 wires={'x':[1<<b for b in range(470)],'y':[None]*2200,'step':[None]*470}
 count=0
 for line in path.read_text().splitlines():
  if line.startswith('wire [9:0] '):wires[line[11:-1]]=[None]*10
  if not line.startswith('assign '):continue
  m=re.fullmatch(r"assign (\w+)\[(\d+)(\+:10)?\] = (.*);",line)
  if not m:raise ValueError('unsupported assign '+line)
  name,offset,width,expr=m.groups();offset=int(offset);value=[0]*(10 if width else 1)
  for term in expr.split(' ^ '):
   if term=="1'b0":continue
   n=re.fullmatch(r'(\w+)(?:\[(\d+)\])?',term)
   if not n:raise ValueError('unsupported term '+term)
   v=wires[n[1]] if n[2] is None else [wires[n[1]][int(n[2])]]
   assert len(value)==len(v) and all(x is not None for x in v)
   value=[a^b for a,b in zip(value,v)]
  wires[name][offset:offset+len(value)]=value;count+=1
 expected=[]
 for k in range(55):
  for group in range(4):
   val=[0]*10
   coeffs=range(16) if group==0 else range(30) if group==1 else range(1,16,2) if group==2 else [0]
   for i in coeffs:
    off=(i*10 if group in (0,2) else 160+i*10 if group==1 else 460)
    p=product(off,power(-i*k if group!=3 else k));val=[a^b for a,b in zip(val,p)]
   expected+=val
 assert wires['y']==expected,'evaluation linear form mismatch'
 expected=[]
 for i in range(47):expected+=product(i*10,power(-(i if i<16 else i-16)*55 if i<46 else 55))
 assert wires['step']==expected,'next-slice linear form mismatch'
 return {'status':'PASS','parsed_assignments':count,'exact_output_linear_forms':2670,'input_basis_bits':470,'implied_basis_output_checks':2670*470}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=pathlib.Path);args=p.parse_args();print(json.dumps(audit(args.source),indent=2))
