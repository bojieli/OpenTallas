`timescale 1ns/1ps
module tb_qwen_a_gateway_equivalence;
 parameter integer INT8=1,FULL=1;
 localparam SW=64,AW=24,NW=18;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start_idle=0,su_go=0,a_src=0;
 reg[NW-1:0]token=0,tok_r=0;
 reg[SW-1:0]a_re=0;reg[SW*AW-1:0]a_addr=0;
 reg[SW*32-1:0]vm_q=0;reg[511:0]embed_code_q=0;reg[15:0]embed_scale_q=16'h3f80;
 wire[2047:0]n_q,r_q;wire[63:0]n_vm,r_vm,n_fault,r_fault;
 wire[1535:0]n_addr,r_addr;wire n_cr,r_cr,n_sr,r_sr;
 wire[23:0]n_ca,r_ca;wire[17:0]n_sa,r_sa;
 ot_qwen_a_operand_gateway_v1 #(.INT8_EMBED(INT8),.QWEN_FULLSHAPE(FULL)) dut(
 .clk(clk),.rst_n(rst_n),.start_idle(start_idle),.su_go(su_go),.a_src(a_src),.token(token),.tok_r(tok_r),
 .a_re(a_re),.a_addr(a_addr),.a_q(n_q),.vm_re(n_vm),.vm_addr(n_addr),.vm_q(vm_q),
 .embed_code_re(n_cr),.embed_code_addr(n_ca),.embed_code_q(embed_code_q),
 .embed_scale_re(n_sr),.embed_scale_addr(n_sa),.embed_scale_q(embed_scale_q),.embed_faults(n_fault));
 qwen_a_gateway_frozen_inline #(.INT8_EMBED(INT8),.QWEN_FULLSHAPE(FULL)) ref_dut(
 .clk(clk),.rst_n(rst_n),.start_idle(start_idle),.su_go(su_go),.a_src(a_src),.token(token),.tok_r(tok_r),
 .a_re(a_re),.a_addr(a_addr),.a_q(r_q),.vm_re(r_vm),.vm_addr(r_addr),.vm_q(vm_q),
 .embed_code_re(r_cr),.embed_code_addr(r_ca),.embed_code_q(embed_code_q),
 .embed_scale_re(r_sr),.embed_scale_addr(r_sa),.embed_scale_q(embed_scale_q),.embed_faults(r_fault));
 integer k,l,checks=0,embed_edges=0,vm_edges=0,bad_edges=0;reg[31:0]rng=32'h73570cb1;
 task check;
 begin
 if({n_q,n_vm,n_addr,n_cr,n_ca,n_sr,n_sa,n_fault} !== {r_q,r_vm,r_addr,r_cr,r_ca,r_sr,r_sa,r_fault})
  $fatal(1,"GATEWAY_MISMATCH edge=%0d int8=%0d full=%0d",k,INT8,FULL);
 checks=checks+1;
 end endtask
 initial begin
 for(k=0;k<1024;k=k+1)begin
 @(negedge clk);
 rng=(rng<<1)^{32{rng[31]}}&32'h04c11db7;
 rst_n=(k>2 && k!=511 && k!=512);start_idle=(k%37==3);su_go=(k%17==5);a_src=(k/17)%2;
 token=(k%2)?18'd151935:18'd65537;tok_r=(k%3)?token:18'd262143;
 embed_scale_q=(k%29==0)?16'h7f80:16'h3c01;
 for(l=0;l<64;l=l+1)begin
 a_re[l]=rng[l%32]^(k%7==0);
 a_addr[l*24+:24]=(tok_r*4096)+((k*13+l*7)&4095);
 vm_q[l*32+:32]=rng^(32'habcdef01+l+k);embed_code_q[l*8+:8]=l*7+k;
 end
 #1;check();@(posedge clk);#1;check();
 if(n_cr)embed_edges=embed_edges+1;if(|n_vm)vm_edges=vm_edges+1;if(|n_fault)bad_edges=bad_edges+1;
 end
 if(checks!=2048||vm_edges==0||(INT8&&(embed_edges==0||bad_edges==0)))$fatal(1,"COVERAGE_MISSING");
 $display("PASS_GATEWAY_EQ checks=%0d embedding=%0d vm=%0d invalid_scale=%0d int8=%0d full=%0d",checks,embed_edges,vm_edges,bad_edges,INT8,FULL);$finish;
 end
endmodule
