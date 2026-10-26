#!/usr/bin/env python3
"""Explicit gate LUT for the immutable SFU exp coefficient case, zero cycles.

A packed literal select is combinational logic, so Yosys proc_rom does not
invent a 256x61 memory requiring an unrelated SRAM macro. Simulation keeps
exact original case/X semantics; the synthesis branch is exhaustively checked
on all256 binary indices before adoption. Original source files stay untouched.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def rewrite(text, function='ln2_nk'):
    pattern=r'    function automatic \[63:0\] '+re.escape(function)+r'\(input \[7:0\] (\w+)\);\n(.*?)    endfunction'
    matches=list(re.finditer(pattern,text,re.S))
    if len(matches)!=1:raise ValueError('expected one exact64-bit/8-bit coefficient function')
    m=matches[0];arg=m[1];body=m[2]
    clean=re.sub(r'//[^\n]*','',body)
    row=re.compile(r"8'd(\d+)\s*:\s*"+re.escape(function)+r"\s*=\s*\{32'h([0-9a-fA-F]{8}),\s*32'h([0-9a-fA-F]{8})\};")
    values=[0]*256;seen=set()
    for n,hi,lo in row.findall(clean):
        n=int(n)
        if n in seen or not 0<=n<256:raise ValueError('duplicate/out-of-range coefficient row')
        seen.add(n);values[n]=(int(hi,16)<<32)|int(lo,16)
    rest=row.sub('',clean)
    rest=re.sub(r'case\s*\('+re.escape(arg)+r'\)|endcase|default:\s*'+re.escape(function)+r"\s*=\s*64'd0\s*;",'',rest)
    if rest.strip() or len(seen)!=254:raise ValueError('coefficient function is not the exact254-row/default0 contract')
    packed=''.join(f'{x:016x}' for x in reversed(values))
    new=(f'    function automatic [63:0] {function}(input [7:0] {arg});\n'
         '`ifdef SYNTHESIS\n'
         f"        localparam [16383:0] CASE_GATE_TABLE = 16384'h{packed};\n"
         f'        {function} = CASE_GATE_TABLE[64*{arg} +: 64];\n'
         '`else\n'+body+'`endif\n    endfunction')
    result=text[:m.start()]+new+text[m.end():]
    return result,dict(function=function,binary_indices=256,explicit_rows=254,default_zero_rows=sorted(set(range(256))-seen),
                       table_sha256=hashlib.sha256(b''.join(x.to_bytes(8,'little') for x in values)).hexdigest(),added_cycles=0,
                       source_sha256=hashlib.sha256(text.encode()).hexdigest(),result_sha256=hashlib.sha256(result.encode()).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--function',default='ln2_nk');a=p.parse_args()
    out,rec=rewrite(a.source.read_text(),a.function);a.out.write_text(out);a.out.with_suffix('.lut.json').write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps(rec))


if __name__=='__main__':main()
