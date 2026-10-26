module tb;
parameter WRONG=0;
reg clk=0,d=0;
always #5 clk=~clk;
wire n3,n5,g3,g5;
ot_dp_landing_bank #(.D(WRONG?2:3)) n_3(.clk(clk),.d(d),.q(n3));
ot_dp_landing_bank #(.D(5)) n_5(.clk(clk),.d(d),.q(n5));
ot_dp_dly #(.D(3)) g_3(.clk(clk),.d(d),.q(g3));
ot_dp_dly #(.D(5)) g_5(.clk(clk),.d(d),.q(g5));
integer i,errors=0,checks=0;
reg [31:0] rng=32'h81a39d27;
initial begin
 for(i=0;i<512;i=i+1) begin
  @(negedge clk);rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};d=rng[0];
  @(posedge clk);#1;
  if(i>=6)begin checks=checks+2;if(n3!==g3)errors=errors+1;if(n5!==g5)errors=errors+1;end
 end
 $display("NATIVE_LANDING_BANK checks=%0d errors=%0d",checks,errors);
 if(errors)$fatal(1,"wrong landing delay caught");$finish;
end
endmodule
