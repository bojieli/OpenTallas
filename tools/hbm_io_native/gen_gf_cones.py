#!/usr/bin/env python3
"""Exact GF(1024) linear maps for legacy52symbol encode /55symbol syndrome slices."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/s81_link'))
from rs544 import G,gmul,gpow,EXP
OUT=ROOT/'rtl/hbm_accel/io_native_20261014'

def emit(name,matrix,nsrc):
 lines=['`timescale 1ns/1ps','// Generated exact GF linear map; primitive0x409, unchanged symbol/state order.','// Each output is a balanced XOR reduction; no serial symbol update chain.',f'module {name}(input wire[{nsrc*10-1}:0]x,output wire[299:0]y);']
 sizes=[]
 for r,row in enumerate(matrix):
  for b in range(10):
   mask=0
   for c,coef in enumerate(row):
    for k in range(10):
     if (gmul(coef,1<<k)>>b)&1:mask|=1<<((nsrc-1-c)*10+k)
   sizes.append(mask.bit_count());lines.append(f"assign y[{(29-r)*10+b}]=^(x & {nsrc*10}'h{mask:x});")
 lines+=['endmodule'];(OUT/(name+'.sv')).write_text('\n'.join(lines)+'\n')
 return {'module':name,'input_bits':nsrc*10,'output_bits':300,'xor_leaf_terms':sum(sizes),'max_terms_per_output':max(sizes),'max_balanced_xor_levels':(max(sizes)-1).bit_length(),'added_registers':0,'added_edges':0}

def main():
 n=82;m=[[int(r==c) for c in range(n)]for r in range(30)]
 for step in range(52):
  fb=m[0][:];fb[30+step]^=1
  m=[[ (m[r+1][c] if r<29 else 0)^gmul(fb[c],G[r+1]) for c in range(n)]for r in range(30)]
 a=emit('ot_hbm_kp4_encode52_map',m,n)
 n=85;m=[]
 for r in range(30):
  row=[0]*n;row[r]=gpow(EXP[r],55)
  for k in range(55):row[30+k]=gpow(EXP[r],54-k)
  m.append(row)
 b=emit('ot_hbm_kp4_syndrome55_map',m,n)
 stats={'schema':'ot.hbm.kp4.linear_cones.v1','primitive':hex(0x409),'generator_coefficients':G,'encoder':a,'decoder_syndrome':b,'qualification':'Exact source cone construction only; full legacy RTL equivalence/mutants and actual native physical gate required. ExistingS81sources unmodified.'}
 (ROOT/'results/arch/hbm_io_native_1014/gf_cones.json').write_text(json.dumps(stats,indent=2)+'\n')
 for which,array_name,idx,src,spc in [('enc','rem','ph','e_m',52),('dec','S','sc','sb',55)]:
  text=(ROOT/f'rtl/dsrom_sys/s81_link/ot_s81_kp4_{which}.sv').read_text().replace(f'module ot_s81_kp4_{which}',f'module ot_hbm_kp4_{which}_linear')
  ns='nrem' if which=='enc' else 'nS';pat=f'    always @* begin\n        for (';start=text.index(pat)
  end=text.index('    reg [299:0] par;',start) if which=='enc' else text.index('    wire s_fin',start)
  old=text[start:end];outbits=spc*10;total=5140 if which=='enc' else 5440
  block=[f'    wire[{299+outbits}:0]linear_input;', '    wire[299:0]linear_output;',f'    reg[{outbits-1}:0]linear_symbols;',f'    always @* case({idx})']
  for phase in range(10):
   first=spc*phase-6;zero=max(0,-first)*10;valid=outbits-zero;msb=total-1-max(first,0)*10
   expr=f"{{{zero}'d0,{src}[{msb}-:{valid}]}}" if zero else f'{src}[{msb}-:{valid}]'
   block.append(f"    4'd{phase}:linear_symbols={expr};")
  block.extend([f"    default:linear_symbols={outbits}'d0;",'    endcase','    genvar lm;generate for(lm=0;lm<30;lm=lm+1)begin:g_linear',f'    assign linear_input[{outbits}+(29-lm)*10+:10]={array_name}[lm];',f'    always @* {ns}[lm]=linear_output[(29-lm)*10+:10];','    end endgenerate',f'    assign linear_input[{outbits-1}:0]=linear_symbols;',f"    ot_hbm_kp4_{'encode52' if which=='enc' else 'syndrome55'}_map u_map(.x(linear_input),.y(linear_output));",''])
  text=text[:start]+'\n'.join(block)+text[end:];(OUT/f'ot_hbm_kp4_{which}_linear.sv').write_text(text)
 print(json.dumps(stats['encoder']));print(json.dumps(stats['decoder_syndrome']))
if __name__=='__main__':main()
