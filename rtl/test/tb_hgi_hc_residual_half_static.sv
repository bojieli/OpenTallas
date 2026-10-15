`timescale 1ns/1ps
module tb_hgi_hc_residual_half_static;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,wv=0,rv=0;reg[9:0]wa=0,ra=0;reg[255:0]wd=0;
 wire valid,fault;wire[255:0]data;
 ot_hgi_hc_residual_half_static dut(.clk(clk),.rst_n(rst_n),.write_v(wv),.write_word(wa),.write_data(wd),.read_v(rv),.read_word(ra),.read_valid(valid),.fault(fault),.residual_data(data));
 reg[255:0]golden[0:639],e[0:2];reg[2:0]v=0;reg enable=0;
 reg prev_v=0;reg[9:0]prev_a=0;reg[255:0]prev_d=0;
 integer n,l,checks=0,commits=0;
 always @(posedge clk)begin
  if(rst_n)begin
   if(dut.u_residual.w_ce_in!==prev_v)$fatal(1,"RESIDUAL_HALF write_phase mismatch");
   if(prev_v)begin
    if(dut.u_residual.w_addr_in!==prev_a||dut.u_residual.wd_in!==prev_d)$fatal(1,"RESIDUAL_HALF write_payload mismatch");
    commits=commits+1;
   end
  end
  prev_v=wv;prev_a=wa;prev_d=wd;
  e[2]=e[1];e[1]=e[0];e[0]=golden[ra];v={v[1:0],rv&enable};#0.01;
  if(rst_n&&v[2])begin
   if(data!==e[2]||!valid)$fatal(1,"RESIDUAL_HALF read mismatch checks=%0d",checks);
   checks=checks+1;
  end
 end
 initial begin
  for(n=0;n<640;n=n+1)for(l=0;l<8;l=l+1)golden[n][l*32+:32]=32'h3f800000^(n*32'h10011)^(l*32'h221133);
  repeat(3)@(negedge clk);rst_n=1;
  for(n=0;n<640;n=n+1)begin wv=1;wa=10'(n);wd=golden[n];@(negedge clk);end
  wv=0;repeat(3)@(negedge clk);enable=1;
  for(n=0;n<1280;n=n+1)begin rv=1;ra=10'(n%640);@(negedge clk);end
  enable=0;rv=0;repeat(4)@(negedge clk);
  if(fault||commits!=640||checks!=1280)$fatal(1,"RESIDUAL_HALF count/fault mismatch commits=%0d checks=%0d fault=%b",commits,checks,fault);
  $display("RESIDUAL_HALF PASS checks=%0d commits=%0d write_capture_edges=1 read_latency=3 macros=1",checks,commits);$finish;
 end
endmodule
