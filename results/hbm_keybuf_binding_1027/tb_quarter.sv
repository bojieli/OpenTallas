`timescale 1ns/1ps
module tb #(parameter integer HALF=0, MUT=0);
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0,clear=0,live_v=0,pre_v=0,replay_v=0;
 reg[7:0]live_index=0,pre_index=0,replay_index=0;
 reg[4395:0]key_in=0;
 wire[4395:0]a,b; wire fa,fb;
 ot_hnx_idxn_keybuf #(.NP(4),.RS(0)) gold(.pbase(3'(4*HALF)),.clk(clk),.rst_n(rst_n),.clear(clear),.live_v(live_v),.live_index(live_index),.key_in(key_in),.pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),.key_out(a),.fault(fa));
 ot_hnx_idxn_keybuf_quarter dut(.half(1'(HALF)^1'(MUT)),.clk(clk),.rst_n(rst_n),.clear(clear),.live_v(live_v),.live_index(live_index),.key_in(key_in),.pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),.key_out(b),.fault(fb));
 integer checks=0, errors=0,faultcycles=0,cyc=0;
 always @(negedge clk)if(rst_n)begin
  checks=checks+1;cyc=cyc+1;
  if(a!==b||fa!==fb)begin errors=errors+1;if(errors<4)$display("MISMATCH %0d",cyc);end
  if(fa)faultcycles=faultcycles+1;
 end
 task automatic step;
  @(posedge clk);#0.1;
 endtask
 task automatic randomize_data;
  for(integer z=0;z<4396;z=z+1)key_in[z]=$random;
 endtask
 integer rec,i,row;
 initial begin
  step;step;rst_n=1;
  for(rec=0;rec<3;rec=rec+1)begin
   clear=1;live_v=0;pre_v=0;replay_v=0;step;clear=0;
   for(i=0;i<171;i=i+1)begin live_v=1;live_index=8'(i);randomize_data;step;end
   live_v=0;step;
   for(row=0;row<3;row=row+1)begin
    pre_v=1;pre_index=0;replay_v=0;step;
    for(i=0;i<171;i=i+1)begin
     replay_v=1;replay_index=8'(i);pre_v=i<170;pre_index=8'(i+1);randomize_data;step;
    end
    pre_v=0;replay_v=0;step;
   end
   // Schedule error controls: no PRE, bad address, live/replay collision.
   replay_v=1;replay_index=8'd171;live_v=1;live_index=8'd172;step;
   live_v=0;replay_v=0;pre_v=1;pre_index=8'd200;step;
   pre_v=0;step;
   rst_n=0;step;rst_n=1;step;
  end
  $display("RESULT checks=%0d errors=%0d faultcycles=%0d",checks,errors,faultcycles);
  if(errors||checks<2000||faultcycles==0)$fatal(1,"FAIL");
  $display("NATIVE_QUARTER_KEYBUF PASS half=%0d",HALF);$finish;
 end
endmodule
