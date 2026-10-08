`timescale 1ns/1ps
module root_adapter_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [131:0] tree_return=0;
 reg [1:0] upstream_fault=0;
 wire [1:0] r_v,r_e,root_fault;
 wire [31:0] r_row,r_bf16;
 wire [5:0] r_pos;
 wire [63:0] r_fp32;
 ot_s81_pq_root_adapter #(.R(2)) dut(.*);
 integer checked=0,cycle=0, sent=0;
 integer expected_row[0:1][0:99];
 reg [31:0] expected_data[0:1][0:99];
 reg [2:0] expected_pos[0:1][0:99];
 reg expected_err[0:1][0:99];
 integer n[0:1]; integer wr[0:1];integer k,j;
 reg [32:0] rb;
 always @(posedge clk) begin
  #1;cycle=cycle+1;
  if(rst_n)for(integer r=0;r<2;r=r+1)if(r_v[r])begin
   if(n[r]>=wr[r])$fatal(1,"unexpected root publication");
   rb={1'b0,expected_data[r][n[r]]}+33'h7fff+expected_data[r][n[r]][16];
   if(r_row[16*r+:16]!==expected_row[r][n[r]][15:0] ||
      r_pos[3*r+:3]!==expected_pos[r][n[r]] ||
      r_fp32[32*r+:32]!==expected_data[r][n[r]] ||
      r_bf16[16*r+:16]!==rb[31:16] ||r_e[r]!==expected_err[r][n[r]])
      $fatal(1,"ABI mismatch region%0d index%0d row%h data%h",r,n[r],r_row[16*r+:16],r_fp32[32*r+:32]);
   n[r]=n[r]+1;checked=checked+1;
  end
 end
 task expect_row(input integer r,input integer row,input [2:0]pos,input[31:0]data,input err);
 begin expected_row[r][wr[r]]=row;expected_pos[r][wr[r]]=pos;
 expected_data[r][wr[r]]=data;expected_err[r][wr[r]]=err;wr[r]=wr[r]+1;end
 endtask
 task send(input integer r,input[15:0]row,input[2:0]pos,input[4:0]lo,input[4:0]ns,input[31:0]d,input e);
 reg[31:0]tag;begin tag={pos,row,lo,3'd0,ns};tree_return[66*r+:66]={e,d,tag,1'b1};end
 endtask
 initial begin
  n[0]=0;n[1]=0;wr[0]=0;wr[1]=0;
  repeat(3)@(negedge clk);rst_n=1;
  for(k=0;k<64;k=k+1)begin
   @(negedge clk);
   for(j=0;j<2;j=j+1)begin
    expect_row(j,16'h8000+j*256+k,(k+j)%8,32'h3f800000+k*65536+32'h8000,k%7==0);
    send(j,16'h8000+j*256+k,(k+j)%8,0,1,32'h3f800000+k*65536+32'h8000,k%7==0);
   end
  end
  @(negedge clk);tree_return=0;repeat(5)@(negedge clk);
  // Right sibling arrives first. Preserve the native golden pairing and RNE.
  for(j=0;j<2;j=j+1)begin expect_row(j,16'hc123+j,7-j,32'h40400000,j==1);
   send(j,16'hc123+j,7-j,1,2,32'h40000000,j==1);end
  @(negedge clk);
  for(j=0;j<2;j=j+1)send(j,16'hc123+j,7-j,0,2,32'h3f800000,0);
  @(negedge clk);tree_return=0;repeat(20)@(negedge clk);
  if(checked!=130)$fatal(1,"missing publications %0d",checked);
  upstream_fault=2'b10;#1;if(root_fault!==2'b10)$fatal(1,"upstream fault lost");
  @(negedge clk);rst_n=0;upstream_fault=0;repeat(3)@(negedge clk);rst_n=1;
  repeat(5)@(negedge clk);if(r_v!==0 || root_fault!==0)$fatal(1,"reset leaked publication");
  $display("PASS root adapter 130 rows, 2 regions, ROOTD128, 66-to69 ABI, RNE, reordered siblings, error and reset");$finish;
 end
 initial begin #100000;$fatal(1,"test deadline");end
endmodule
