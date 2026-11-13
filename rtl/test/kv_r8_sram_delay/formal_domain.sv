module formal_domain #(parameter integer BASE=2, DMAX=24, CW=5)(
 input wire clk,input wire d,input wire [CW-1:0] strap_cnt
);
 localparam integer TOTAL=BASE+DMAX;
 wire [5:0] selected=(strap_cnt>CW'(DMAX))?6'(DMAX):6'(strap_cnt);
 wire [5:0] depth=6'(BASE)+selected;
 wire q;
 ot_dp_dly_cnt_sram #(.W(1),.BASE(BASE),.DMAX(DMAX),.CW(CW)) dut(
  .clk(clk),.strap_cnt(strap_cnt),.d(d),.q(q));
 reg [TOTAL-1:0] history;
 reg [5:0] age=0;
 wire gold=depth==0?d:history[depth-1];
 always @(posedge clk) begin
  if (!$initstate) assume($stable(strap_cnt));
  history[0]<=d;
  for(integer j=1;j<TOTAL;j=j+1) history[j]<=history[j-1];
  if(age<6'd40)age<=age+6'd1;
  if(age>=depth)assert(q==gold);
 end
endmodule
