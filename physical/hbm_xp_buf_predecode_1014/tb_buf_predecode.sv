`timescale 1ps/1fs
module tb;
 parameter integer MUT=0;
 reg clk=0;always #416.666625 clk=~clk;
 reg rst_n=0,tok0=1,tok_i=0,w_v_i=0;
 reg [24:0] w_t_i=0;reg [1023:0] w_d_i=0;
 wire [2065:0] ref_o,new_o;
 ot_hgi_xp_buf original(.clk(clk),.rst_n(rst_n),.tok0(tok0),.tok_i(tok_i),.w_v_i(w_v_i),.w_t_i(w_t_i),.w_d_i(w_d_i),.tok_o(ref_o[2065]),.ob_v(ref_o[2064]),.ob_eop(ref_o[2063]),.ob_addr(ref_o[2062:2056]),.ob_grp(ref_o[2055:2049]),.ob_d(ref_o[2048:1]),.fault(ref_o[0]));
 ot_hbm_xp_buf_predecode #(.MUT_LANE(MUT)) candidate(.clk(clk),.rst_n(rst_n),.tok0(tok0),.tok_i(tok_i),.w_v_i(w_v_i),.w_t_i(w_t_i),.w_d_i(w_d_i),.tok_o(new_o[2065]),.ob_v(new_o[2064]),.ob_eop(new_o[2063]),.ob_addr(new_o[2062:2056]),.ob_grp(new_o[2055:2049]),.ob_d(new_o[2048:1]),.fault(new_o[0]));
 integer checks=0,beats=0,cycles=0;
 always @(negedge clk)begin
  cycles++;
  if(cycles>8)begin checks++;if(ref_o!==new_o)$fatal(1,"BUF_PREDECODE_MISMATCH cycle%0d ref%h candidate%h",cycles,ref_o,new_o);if(ref_o[2064])beats++;end
 end
 initial begin
  repeat(5)@(negedge clk);rst_n=1;
  repeat(5)@(negedge clk);
  for(integer frame=0;frame<256;frame++)begin
   for(integer wave=0;wave<8;wave++)begin
    @(negedge clk);w_v_i=1;
    w_t_i=0;w_t_i[0]=(wave==0);w_t_i[1]=(wave==7);w_t_i[2]=frame[2];w_t_i[3]=frame[0];w_t_i[4]=1;w_t_i[5]=1;w_t_i[8:6]=3'(wave);w_t_i[22:16]=7'(frame);w_t_i[24:23]=frame[1:0];
    for(integer word=0;word<32;word++)w_d_i[word*32+:32]=32'(frame*104729+wave*65537+word*257);
   end
   @(negedge clk);w_v_i=0;w_t_i=0;tok_i=0;
   repeat(24)@(negedge clk);
   if(frame%31==30)begin rst_n=0;repeat(5)@(negedge clk);rst_n=1;repeat(5)@(negedge clk);end
  end
  repeat(40)@(negedge clk);
  if(beats<1400)$fatal(1,"BUF_PREDECODE_VACUOUS beats%0d",beats);
  $display("BUF_PREDECODE_EXACT_PASS frames256 checks%0d beats%0d",checks,beats);$finish;
 end
endmodule
