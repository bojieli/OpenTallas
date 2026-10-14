`timescale 1ns/1ps
module tb_hfd_tkm_reservation;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;reg[39:0]control=0;
 wire[3:0]reserve;reg[3:0]expect0=0,expect1=0;integer i,cycles=0,checked=0;
 ot_hfd_tkm_reservation_rx #(.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.control(control),.del_reserve(reserve));
 always @(posedge clk)begin
  cycles=cycles+1;
  expect0<=rst_n&&(control[39:38]==0)&&(control[37:32]==62)?control[3:0]:4'b0;expect1<=expect0;
  if(rst_n&&cycles>10)begin
   if(reserve!==expect1)$fatal(1,"RESERVATION FAIL lane bitmap got=%b expected=%b",reserve,expect1);
   checked=checked+1;
  end
 end
 initial begin
  repeat(8)@(negedge clk);rst_n=1;
  for(i=0;i<2048;i=i+1)begin
   case(i%7)
    0:control={2'b00,6'd62,32'(i)};
    1:control={2'b01,6'd62,32'(i)};
    2:control={2'b10,6'd62,32'(i)};
    3:control={2'b00,6'd0,32'(i)};
    4:control={2'b00,6'd62,32'(i)};
    default:control={2'b00,6'd62,32'(i*13)};
   endcase
   @(negedge clk);
  end
  control=0;repeat(4)@(negedge clk);
  $display("RESERVATION PASS checked=%0d all16bitmaps=1",checked);$finish;
 end
endmodule
