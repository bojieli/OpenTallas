`timescale 1ns/1ps
module tb_tree3;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg reset_q=0;reg [5:0]rawlnk=0;reg [15:0]lf=0,lpv=0;
 wire exact;
 prove_tree3 #(.MUT(MUT)) m(.clk(clk),.reset_q(reset_q),.rawlnk(rawlnk),.lf(lf),.lpv(lpv),.exact(exact));
 integer checks=0,edges=0,valid_sweeps=0,onehot_cases=0,n,r,k,l,t;
 reg [15:0]fault_lanes_seen=0;
 reg [63:0]lnk_patterns_seen=0;
 reg [1:0]reset_seen=0;
 reg [8:0]last_q;
 function [15:0]valid_pattern(input integer n);
 begin case(n%8)
  0:valid_pattern=0;1:valid_pattern=16'hffff;2:valid_pattern=16'hfff0;3:valid_pattern=16'h000f;
  4:valid_pattern=16'h0200;5:valid_pattern=16'h1111;6:valid_pattern=16'h8000;7:valid_pattern=16'h5555;
 endcase end endfunction
 task step(input reg rst,input reg[5:0]lnk,input reg[15:0]faults,valids);
 begin
  @(negedge clk);
  last_q={m.newglobal,m.newf,m.newp};
  reset_q=rst;rawlnk=lnk;lf=faults;lpv=valids;
  #1;
  if(edges>=3&&{m.newglobal,m.newf,m.newp}!==last_q)$fatal(1,"BAND_TREE FAIL output changes without capture edge MUT=%0d",MUT);
  @(posedge clk);#1;edges=edges+1;
  if(edges>=3)begin
   if(exact!==1'b1)$fatal(1,"BAND_TREE FAIL edge/function/reset MUT=%0d edge=%0d new=%h original_delayed=%h",MUT,edges,{m.newglobal,m.newf,m.newp},m.delay2);
   if(m.newglobal!==( |m.newf))$fatal(1,"BAND_TREE FAIL global union MUT=%0d edge=%0d",MUT,edges);
   checks=checks+1;
  end
  reset_seen[rst]=1;lnk_patterns_seen[lnk]=1;
 end endtask
 initial begin
  // Targeted negatives before exhaustive coverage, including reset as data.
  repeat(8)step(0,6'h3f,16'hffff,16'hffff);
  for(n=0;n<16;n=n+1)step(1,0,16'b1<<n,0);
  repeat(4)step(1,0,0,16'hfff0); // uniform inside each quarter, mismatch between quarters
  repeat(4)step(1,0,0,16'h0200); // mismatch only in quarter2, all reps zero
  repeat(4)step(1,6'h3f,0,0);
  for(n=0;n<8;n=n+1)step(n%2,0,n%2?16'h8000:16'hffff,n%2?16'hffff:16'h5555);
  // Every 16-bit valid pattern, each reset value, with and without lane/link faults.
  for(r=0;r<2;r=r+1)for(k=0;k<2;k=k+1)for(n=0;n<65536;n=n+1)begin
   step(r,k?6'h3f:0,k?(16'b1<<(n%16)):0,n);
   valid_sweeps=valid_sweeps+1;
  end
  // Every onehot fault lane x every rawlink pattern x both resets x8valid shapes.
  for(r=0;r<2;r=r+1)for(l=0;l<16;l=l+1)for(k=0;k<64;k=k+1)for(t=0;t<8;t=t+1)begin
   step(r,k,16'b1<<l,valid_pattern(t));onehot_cases=onehot_cases+1;fault_lanes_seen[l]=1;
  end
  repeat(4)step(0,0,0,0);
  if(valid_sweeps!=262144||onehot_cases!=16384||fault_lanes_seen!=16'hffff||lnk_patterns_seen!=64'hffffffffffffffff||reset_seen!=3)$fatal(1,"BAND_TREE FAIL coverage");
  $display("BAND_TREE PASS checks=%0d edges=%0d valid_sweeps=%0d onehot_x_lnk_x_reset_x_valid=%0d lanes=%h lnk=%h reset=%b fixededges=3 addededges=2",checks,edges,valid_sweeps,onehot_cases,fault_lanes_seen,lnk_patterns_seen,reset_seen);
  $finish;
 end
endmodule
