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

# Root partitioning is emitted as a separate candidate; the flat exactness
# vehicle and every legacyS81 source remain byte-identical.
def emit_rooted():
 enc=(OUT/'ot_hbm_kp4_enc_linear.sv').read_text().replace('module ot_hbm_kp4_enc_linear','module ot_hbm_kp4_enc_rooted').replace('input  wire          clk,','input wire clk_ctrl,clk_collect,clk_encode,clk_codeword,')
 start=enc.index('    always @(posedge clk or negedge rst_n)')
 end=enc.index('    assign fault = flt;',start)
 body='''    wire frame_strobe=(tx_v||run)&&ph==4'd9;
    // Four actual delivered local-family roots. No common-clock fallback.
    always @(posedge clk_ctrl or negedge rst_n)
      if(!rst_n)begin ph<=0;run<=0;flt<=0;seq<=0;e_v<=0;o_v<=0;p_v<=0;p_d<=0;end
      else begin
        if(tx_v)run<=1;
        if(run&&!tx_v)flt<=1;
        if(tx_v||run)ph<=ph==9?0:ph+1'b1;
        if(frame_strobe)begin seq<=seq+1'b1;e_v<=1;if(e_v)o_v<=1;end
        p_v<=o_v;p_d<=o_v?o_c[5439-544*ph-:544]:544'd0;
      end
    always @(posedge clk_collect)
      if(rst_n&&(tx_v||run))a_b[5119-512*ph-:512]<=tx_d;
    always @(posedge clk_encode or negedge rst_n)
      if(!rst_n)for(i=0;i<NP;i=i+1)rem[i]<=0;
      else begin
        if(e_v)for(i=0;i<NP;i=i+1)rem[i]<=nrem[i];
        if(frame_strobe)begin
          e_m<={4'hA,8'h5C,seq,a_b[5119:512],tx_d};
          for(i=0;i<NP;i=i+1)rem[i]<=0;
        end
      end
    always @(posedge clk_codeword)
      if(rst_n&&frame_strobe&&e_v)o_c<={e_m,par};
'''
 enc=enc[:start]+body+enc[end:];(OUT/'ot_hbm_kp4_enc_rooted.sv').write_text(enc)
 dec=(OUT/'ot_hbm_kp4_dec_linear.sv').read_text().replace('module ot_hbm_kp4_dec_linear','module ot_hbm_kp4_dec_rooted').replace('input  wire          clk,','input wire clk_capture,clk_syndrome,clk_bm0,clk_bm1,clk_bm2,clk_bm3,clk_chien,clk_emit,')
 dec=dec.replace('    genvar u;','    wire[3:0]bm_clock={clk_bm3,clk_bm2,clk_bm1,clk_bm0};\n    genvar u;')
 clocks=['clk_capture','clk_syndrome','bm_clock[u]','clk_syndrome','clk_chien','clk_emit']
 for clock in clocks:dec=dec.replace('always @(posedge clk or negedge rst_n)',f'always @(posedge {clock} or negedge rst_n)',1)
 assert 'posedge clk ' not in dec
 (OUT/'ot_hbm_kp4_dec_rooted.sv').write_text(dec)

if __name__=='__main__':emit_rooted()
