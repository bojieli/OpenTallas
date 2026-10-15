`timescale 1ns/1ps
module tb_smh_static_north_hard;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 wire [79:0] data_clk={80{clk}};wire [8:0] ctrl_clk={9{clk}};wire [3:0] row_clk={4{clk}};
 reg rst_n=0,xw_en=0;
 reg [6:0] xw_addr=0,xw_grp=0;
 reg [2047:0] xw_data=0;
 reg [817:0] row0=0;
 wire [2068:0] fx_b,bl0,br0,ref_fx,ref_bl,ref_br;
 wire [817:0] rl0,rr0,ref_rl,ref_rr;
 ot_smh_static_north_hard #(.MUT(MUT)) dut(.*);
 ot_hbm_accel_smh_front_n original(.clk(clk),.rst_n(rst_n),
 .start(1'b0),.start_ready(),.op_rows(13'd0),.op_c(16'd0),.op_g(8'd0),.op_gs(1'b0),.op_fmt(2'd0),.op_xb(7'd0),
 .busy(),.xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),.arrive(),.release_in(1'b0),.released(),
 .rout_l0(ref_rl),.rout_r0(ref_rr),.bout_l0(ref_bl),.bout_r0(ref_br),.fs_v(),.fs_d(),.fs_ret(1'b0),
 .fx_b(ref_fx),.fr_rl(),.fi_row0(row0),.fi_pbz(3'd0));
 integer i,k;
 initial begin
   repeat(10)@(negedge clk);rst_n=1;
   for(i=0;i<4096;i=i+1)begin
     @(negedge clk);xw_en=(i%5!=0);xw_addr=7'(i);xw_grp=7'(i%19);
     for(k=0;k<64;k=k+1)xw_data[k*32+:32]=32'(i*997+k*5437);
     for(k=0;k<818;k=k+1)row0[k]=(i+k*17)%7>3;
     @(posedge clk);#1;
     if(fx_b!==ref_fx || bl0!==ref_bl || br0!==ref_br || rl0!==ref_rl || rr0!==ref_rr)
       $fatal(1,"STATIC NORTH original fullwidth/edge mismatch %0d",i);
   end
   $display("STATIC NORTH EXACT PASS 4096 II1 unchanged4/6xwrite2rowedges 23950FF93roots allfields");$finish;
 end
endmodule
