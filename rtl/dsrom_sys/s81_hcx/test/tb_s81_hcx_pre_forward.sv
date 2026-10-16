`timescale 1ns/1ps
module tb_s81_hcx_pre_forward;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,iv=0,start=0,done=0,wv=0;
 reg[127:0]incoming=128'h3f8000033f8000023f8000013f800000;
 reg[13:0]base=2560,row=0;reg[15:0]mask=0;reg[511:0]data=0;
 wire[511:0]out;wire ov,fault;wire[127:0]opre;
 reg[127:0]prev,computed;integer checks=0;
 ot_s81_hcx_pre_forward #(.MUT_CURRENT_PRE(MUT))u(.clk(clk),.rst_n(rn),.incoming_v(iv),.incoming_pre(incoming),
  .start(start),.done(done),.coef_base_row(base),.i_v(wv),.i_row(row),.i_mask(mask),.i_data(data),
  .o_data(out),.outgoing_v(ov),.outgoing_pre(opre),.fault(fault));
 task automatic block_job(input integer b);
  @(negedge clk);base=14'(2560+16*b);start=1;
  @(negedge clk);start=0;
  computed=128'h3e8000033e8000023e8000013e800000+128'(b*16);
  // Tail packet 0 contains current pre+post. Only pre must be forwarded.
  @(negedge clk);wv=1;row=base+1;mask=16'h00ff;data={256'd0,128'h3f1234563f2345673f3456783f456789,computed};
  #1;if(out[127:0]!==prev || out[511:128]!==data[511:128])$fatal(1,"PRE_FORWARD mismatch block%0d",b);checks++;
  @(negedge clk);row=base;mask=16'h00ff;data=512'h0123456789abcdef;
  #1;if(out!==data)$fatal(1,"COMB low modified");checks++;
  @(negedge clk);mask=16'hff00;data=512'h9876543210abcdef;
  #1;if(out!==data)$fatal(1,"COMB high modified");checks++;
  @(negedge clk);row=base+1;mask=16'hff00;data=512'h1e3ce50800000000;
  #1;if(out!==data)$fatal(1,"EPS modified");checks++;
  @(negedge clk);wv=0;repeat(4)@(negedge clk);done=1;
  @(negedge clk);done=0;
  if(!ov || opre!==computed || fault)$fatal(1,"PRE_FORWARD done block%0d",b);checks++;
  prev=computed;
 endtask
 initial begin
  repeat(3)@(negedge clk);rn=1;iv=1;prev=incoming;
  @(negedge clk);iv=0;
  block_job(0);block_job(1);
  // Next token/layer carries its actual incoming quartet through this port.
  @(negedge clk);incoming=128'h3d8000033d8000023d8000013d800000;iv=1;prev=incoming;
  @(negedge clk);iv=0;block_job(2);
  $display("HCX_PRE_FORWARD PASS checks=%0d jobs=3 cycles_added=0 writes_added=0",checks);$finish;
 end
endmodule
