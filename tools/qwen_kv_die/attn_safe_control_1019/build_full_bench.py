import importlib.util,pathlib
r=pathlib.Path('.');sp=importlib.util.spec_from_file_location('lint',r/'tools/textbook_lint.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
import re
text=(r/'src/rtl/lib/face_land/qkd_kvs_attn_fl_ba4.sv').read_text();ins={};outs={}
for direction,hi,lo,n in re.findall(r'\b(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)',text):
 if n=='ck':continue
 width=abs(int(hi)-int(lo))+1 if hi else 1
 (ins if direction=='input' else outs)[n]=width
assert len(ins)==20 and len(outs)==11,(len(ins),len(outs))
s=['`timescale 1ns/1ps','module tb_full;','reg ck=0;always #0.416667 ck=~ck;']
for n,w in ins.items():s.append(f'reg [{w-1}:0] {n}=0;')
for n,w in outs.items():s.append(f'wire [{w-1}:0] old_{n},dut_{n};')
for typ,pre in [('qkd_kvs_attn_fl_ba4','old'),('qkd_kvs_attn_fl_ba5','dut')]:s.append(typ+' '+pre+'(.ck(ck),'+','.join(f'.{n}({n})' for n in ins)+','+','.join(f'.{n}({pre}_{n})' for n in outs)+');')
s+=['integer checks=0;reg[63:0]rng=64\'hd7daceed23299577;','function automatic[31:0]draw;rng=rng^(rng<<13);rng=rng^(rng>>7);rng=rng^(rng<<17);return rng[31:0];endfunction','initial begin','for(int trial=0;trial<128;trial++)begin','@(negedge ck);rst_n=0;','for(int k=0;k<16;k++)begin old.u_core.u_attn_face.rdata[k*32+:32]=draw();dut.u_core.u_attn_face.rdata[k*32+:32]=old.u_core.u_attn_face.rdata[k*32+:32];end','repeat(8)@(negedge ck);rst_n=1;','for(int cycle=0;cycle<96;cycle++)begin','@(negedge ck);']
for n,w in ins.items():
 if n=='rst_n':continue
 for k in range(0,w,32):s.append(f'{n}[{k}+:{min(32,w-k)}]=draw();')
s+=['#0.6;']
for n in outs:s.append(f'if(old_{n}!==dut_{n})begin $display("ATTN_FULL_MISMATCH {n} trial=%0d cycle=%0d",trial,cycle);$fatal(1);end')
s+=['checks++;end end','$display("ATTN_FULL_EXACT PASS checks=%0d all_public_outputs='+str(len(outs))+'",checks);$finish;end','endmodule'];(r/'full').mkdir(exist_ok=True);(r/'full/tb_full.sv').write_text('\n'.join(s)+'\n')
