#!/usr/bin/env python3
"""Emit default-off parallel-prefix integer adders in the shipped flat hash.

Only the two combinational functions change under OT_S81ENG_HASH_PREFIX_ADD.
The default carry-select bodies, tables, registers, clocks and cycle count stay
identical. Regenerate the existing layer halves from that one flat source.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFINE = 'OT_S81ENG_HASH_PREFIX_ADD'
FUNCTIONS = (('add64cs',64),('csa28',28))


def prefix(name,width,mutant=False):
    levels=(width-1).bit_length()
    text=f'''    function automatic [{width-1}:0] {name}(input [{width-1}:0] a, input [{width-1}:0] b);
        reg [{width-1}:0] p [0:{levels}];
        reg [{width-1}:0] g [0:{levels}];
        integer k;
        begin
            p[0] = a ^ b;
            g[0] = a & b;
            for (k = 0; k < {levels}; k = k + 1) begin
                g[k+1] = g[k] | (p[k] & (g[k] << (32'd1 << k)));
                p[k+1] = p[k] & (p[k] << (32'd1 << k));
            end
            {name} = p[0] ^ {{g[{levels}][{width-2}:0], 1'b0}};
'''
    if mutant:
        text+=f'            {name}[17] = p[0][17] ^ g[{levels}][15]; // wrong carry bit control\n'
    return text+'        end\n    endfunction'


def bodies(text):
    out={}
    for name,width in FUNCTIONS:
        pat=rf'    function automatic \[{width-1}:0\] {name}\(.*?    endfunction'
        found=re.findall(pat,text,re.S)
        if len(found)==2 and '`ifdef '+DEFINE in text:
            assert found[0]==prefix(name,width),name
            out[name]=found[1]
        else:
            assert len(found)==1,(name,len(found))
            out[name]=found[0]
    return out


def vehicle(text):
    original=bodies(text)
    out=['module hash_add_miter(input wire [63:0] a64,b64, input wire [27:0] a28,b28,',
         ' output wire equal64,equal28,mut_equal64,mut_equal28);']
    for name,width in FUNCTIONS:
        out.append(original[name].replace(name,'gold'+str(width)))
        out.append(prefix('fast'+str(width),width))
        out.append(prefix('mut'+str(width),width,True))
        out.append(f'    assign equal{width} = gold{width}(a{width},b{width}) == fast{width}(a{width},b{width});')
        out.append(f'    assign mut_equal{width} = gold{width}(a{width},b{width}) == mut{width}(a{width},b{width});')
    return '\n'.join(out+['endmodule',''])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path)
    ap.add_argument('--vehicle',type=Path);a=ap.parse_args()
    flat=a.root/'rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_n32.sv'
    text=flat.read_text();old=bodies(text)
    if '`ifdef '+DEFINE not in text:
        for name,width in FUNCTIONS:
            text=text.replace(old[name],f'`ifdef {DEFINE}\n'+prefix(name,width)+'\n`else\n'+old[name]+'\n`endif',1)
        flat.write_text(text)
    subprocess.run([sys.executable,str(a.root/'tools/s81_dv/eng_rr/gen_hash_n32_layer.py')],cwd=a.root,check=True)
    if a.vehicle:a.vehicle.write_text(vehicle(text))


if __name__=='__main__':main()
