module ot_dp_landing_relay (
    input  wire clk,
    input  wire rst_raw_n,
    input  wire d,
    output reg  q
);
    always @(posedge clk) begin
        if (!rst_raw_n) q <= 1'b0;
        else q <= d;
    end
endmodule
module ot_dp_landing_collect #(parameter integer N=1) (
    input wire clk, rst_n,
    input wire [N-1:0] ready_i, fault_i,
    output reg ready_o, fault_o
);
    always @(posedge clk) begin
        if (!rst_n) begin ready_o <= 0; fault_o <= 0; end
        else begin ready_o <= &ready_i; fault_o <= |fault_i; end
    end
endmodule
module ot_dp_rrelay (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule

module tb;
reg clk=0;always #5 clk=~clk;
reg raw=0,din=0;reg[2:0] ready=0,fault=0;reg rst=0;
wire cland_writer_start_x_0,cland_writer_start_x_1;
(* keep = "true" *) ot_dp_landing_relay u_cland_writer_start_x_0 (.clk(clk), .rst_raw_n(raw), .d(din), .q(cland_writer_start_x_0));
(* keep = "true" *) ot_dp_landing_relay u_cland_writer_start_x_1 (.clk(clk), .rst_raw_n(raw), .d(cland_writer_start_x_0), .q(cland_writer_start_x_1));
reg[1:0] wg=0;wire wmut=cland_writer_start_x_0;
reg rp=0,ra=0,rb=0,oldreset=0;
wire newreset;
ot_dp_rrelay rcopy(.clk(clk),.d(rb),.q(newreset));
wire sr0,sf0,sr1,sf1;
ot_dp_landing_collect #(.N(3)) status0(.clk(clk),.rst_n(rst),.ready_i(ready),.fault_i(fault),.ready_o(sr0),.fault_o(sf0));
ot_dp_landing_collect #(.N(1)) status1(.clk(clk),.rst_n(rst),.ready_i(sr0),.fault_i(sf0),.ready_o(sr1),.fault_o(sf1));
reg gr0=0,gf0=0,gr1=0,gf1=0;
integer i,checks=0,wm=0,rm=0,sm=0;
always @(posedge clk)begin
 if(!raw)wg<=0;else wg<={wg[0],din};
 rp<=rst;ra<=rp;rb<=rp;oldreset<=ra;
 if(!rst)begin gr0<=0;gf0<=0;gr1<=0;gf1<=0;end
 else begin gr0<=&ready;gf0<=|fault;gr1<=gr0;gf1<=gf0;end
end
initial begin
 for(i=0;i<8192;i=i+1)begin
 @(negedge clk);
 raw=(i%61)>3;din=$random;rst=(i%83)>5;ready=$random;fault=$random;
 @(posedge clk);#1;
 if(i>5)begin
  if(cland_writer_start_x_1!==wg[1])$fatal(1,"W1 mismatch %0d",i);
  if(oldreset!==newreset)$fatal(1,"R1 reset edge mismatch %0d",i);
  if({sr1,sf1}!=={gr1,gf1})$fatal(1,"R2 status mismatch %0d",i);
  checks=checks+1;
  if(wmut!==wg[1])wm=wm+1;
  if(rb!==oldreset)rm=rm+1;
  if({sr0,sf0}!=={gr1,gf1})sm=sm+1;
 end
 end
 if(wm==0||rm==0||sm==0)$fatal(1,"mutant survived");
 $display("PASS checks=%0d W1_mutant=%0d R1_mutant=%0d R2_mutant=%0d",checks,wm,rm,sm);
 $finish;
end
endmodule
