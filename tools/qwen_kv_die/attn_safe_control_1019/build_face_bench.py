from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
ins={'rst_n':1,'cfg_f_dly':8,'running':1,'start_qk':1,'age':16,'ep':16,'layer':6,'cal':176,'root_local_fault':1,'root_io_fault':1,'f_valid':1,'f_beat':5,'f_data':512,'f_epoch':16,'unit_fault':10}
outs={'result_valid':1,'result_beat':5,'result_data':512,'result_epoch':16,'result_layer':6,'result_done':1,'service_fault':1,'result_fault':1,'hdr_l':8}
s=['`timescale 1ns/1ps','module tb_face;','reg ck=0; always #0.416667 ck=~ck;']
for n,w in ins.items():s.append(f'reg [{w-1}:0] {n}=0;')
for n,w in outs.items():s.append(f'wire [{w-1}:0] old_{n},dut_{n};')
for typ,prefix in [('qkd_attn_result_face_sb','old'),('qkd_attn_result_face_sc','dut')]:s.append(typ+' #(.NF(10),.RESULT_RELAY(0),.F_DLY(127),.CAL_PIPE(1),.MUT(0)) '+prefix+'(.ck(ck),'+','.join(f'.{n}({n})' for n in ins)+','+','.join(f'.{n}({prefix}_{n})' for n in outs)+');')
s+=['integer checks=0; reg [63:0] rng=64\'hcacaceed23894577;','function automatic [31:0] draw; rng=rng^(rng<<13); rng=rng^(rng>>7); rng=rng^(rng<<17); return rng[31:0]; endfunction','reg q,d,sel,expect_q;','initial begin',' for(int v=0;v<8;v++)begin q=v[0];d=v[1];sel=v[2];expect_q=sel?d:q; if((q^(sel&(q^d)))!==expect_q)$fatal(1,"BOOLEAN");end',' for(int trial=0;trial<128;trial++)begin',' @(negedge ck); rst_n=0;',' for(int k=0;k<16;k++)begin old.rdata[k*32+:32]=draw();dut.rdata[k*32+:32]=old.rdata[k*32+:32];end',' repeat(4)@(negedge ck); rst_n=1;',' for(int cycle=0;cycle<96;cycle++)begin',' @(negedge ck);']
for n,w in ins.items():
 if n=='rst_n':continue
 for k in range(0,w,32):s.append(f'{n}[{k} +: {min(32,w-k)}]=draw();')
s+=[' // Binary initial-state and idle activity are deliberately unconstrained.',' #0.6;']
for n in outs:s.append(f' if(old_{n}!==dut_{n})begin $display("ATTN_FACE_MISMATCH {n} trial=%0d cycle=%0d",trial,cycle);$fatal(1);end')
s+=[' checks++;',' end',' end','$display("ATTN_FACE_EXACT PASS checks=%0d all_outputs=9 binary_initial_states=128",checks);$finish;end','endmodule']
(o/'tb_face.sv').write_text('\n'.join(s)+'\n')
