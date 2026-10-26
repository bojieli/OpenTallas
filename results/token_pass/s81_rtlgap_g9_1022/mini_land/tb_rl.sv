`timescale 1ns/1ps
module ot_dvrly_ckinv (input wire a, output wire y); assign y = ~a; endmodule
module mtb;
  parameter integer GD=48, RD=46, N=38, F=3, K=4, W=8, RL=0, KW=3, D=4;
  reg ck=0; always #0.4165 ck=~ck;
  reg rst_n=1; integer cyc=-1;
  // reset release chains: ena releases GD edges after root, rs RD edges
  reg [255:0] sh;
  always @(posedge ck or negedge rst_n) if(!rst_n) sh<=0; else sh<={sh[254:0],1'b1};
  wire ena = sh[GD-1]; wire rs = sh[RD-1];
  wire gck; ICGx4_ASAP7_75t_R g(.CLK(ck),.ENA(ena),.SE(1'b0),.GCLK(gck));
  wire [N:0] fck; wire [W-1:0] d [0:N];
  assign fck[0]=gck; assign d[0]=cyc[W-1:0];
  genvar h; generate for(h=0;h<N;h=h+1) begin:gh
    ot_dvrly_st #(.W(W),.HC(1)) st(.ck(fck[h]),.rs(rs),.i(d[h]),.o(d[h+1]),.ck_o(fck[h+1])); end endgenerate
  wire ckf; wire [W-1:0] fi;
  dv_flight_sim #(.W(W),.F(F)) fl(.ck_in(fck[N]),.rs(rs),.i_in(d[N]),.ck_out(ckf),.i_out(fi));
  wire [W-1:0] o; wire fault;
  reg [7:0] rl=0; always @(posedge ck) rl<={rl[6:0],rs}; wire rs_t=(RL==0)?rs:rl[RL-1];
  ot_s81_land #(.W(W),.D(D),.KW(KW)) l(.k(K[KW-1:0]),.ck_f(ckf),.i(fi),.ck(ck),.rs(rs_t),.o(o),.fault(fault));
  always @(posedge ck) if(rst_n) cyc=cyc+1;
  integer nf=0;
  always @(negedge ck) if (rst_n && fault) nf=nf+1;
  initial begin #0.1 rst_n=0; repeat(8) @(posedge ck); @(negedge ck); rst_n=1; repeat(400) @(posedge ck); @(negedge ck);
    $display("RES GD=%0d RD=%0d N=%0d F=%0d K=%0d fault_cycles=%0d o=%0d cyc=%0d", GD,RD,N,F,K,nf,o,cyc); $finish; end
endmodule
