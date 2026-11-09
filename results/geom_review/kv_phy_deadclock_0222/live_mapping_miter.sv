module old0(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new0(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old1(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new1(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old2(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new2(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old3(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new3(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old4(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new4(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old5(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new5(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old6(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new6(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old7(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new7(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old8(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new8(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old9(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new9(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old10(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new10(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module old11(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [15:0] tx_fhN;
reg [15:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<={w_core_pi0[11:0], w_core_fh0[3:0]}; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [288:0] tx_piN;
reg [288:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_fh1[3:0], w_core_rh0[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [288:0] tx_piN_d1;
reg [288:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<={w_core_rh1[3:0], w_core_pi1[288:4]}; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [288:0] tx_piN_d2;
reg [288:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<={w_core_pi2[284:0], w_core_fh2[3:0]}; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [288:0] tx_piN_d3;
reg [288:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_fh3[3:0], w_core_rh2[3:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [15:0] tx_rhN;
reg [15:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<={w_core_rh3[3:0], w_core_pi3[288:277]}; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[288:12]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[288:4]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[288:285]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[15:4]}};
endmodule

module new11(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);
reg [11:0] tx_fhN;
reg [11:0] i_phy_Q__sN_fhN_q;
always @(posedge clk) begin tx_fhN<=w_core_pi0[11:0]; i_phy_Q__sN_fhN_q<=tx_fhN; end
reg [280:0] tx_piN;
reg [280:0] i_phy_Q__sN_piN_q;
always @(posedge clk) begin tx_piN<={w_core_pi1[3:0], w_core_pi0[288:12]}; i_phy_Q__sN_piN_q<=tx_piN; end
reg [284:0] tx_piN_d1;
reg [284:0] i_phy_Q__sN_piN_d1_q;
always @(posedge clk) begin tx_piN_d1<=w_core_pi1[288:4]; i_phy_Q__sN_piN_d1_q<=tx_piN_d1; end
reg [284:0] tx_piN_d2;
reg [284:0] i_phy_Q__sN_piN_d2_q;
always @(posedge clk) begin tx_piN_d2<=w_core_pi2[284:0]; i_phy_Q__sN_piN_d2_q<=tx_piN_d2; end
reg [280:0] tx_piN_d3;
reg [280:0] i_phy_Q__sN_piN_d3_q;
always @(posedge clk) begin tx_piN_d3<={w_core_pi3[276:0], w_core_pi2[288:285]}; i_phy_Q__sN_piN_d3_q<=tx_piN_d3; end
reg [11:0] tx_rhN;
reg [11:0] i_phy_Q__sN_rhN_q;
always @(posedge clk) begin tx_rhN<=w_core_pi3[288:277]; i_phy_Q__sN_rhN_q<=tx_rhN; end
assign result={{i_phy_Q__sN_rhN_q[11:0], i_phy_Q__sN_piN_d3_q[280:4]},{i_phy_Q__sN_piN_d3_q[3:0], i_phy_Q__sN_piN_d2_q[284:0]},{i_phy_Q__sN_piN_d1_q[284:0], i_phy_Q__sN_piN_q[280:277]},{i_phy_Q__sN_piN_q[276:0], i_phy_Q__sN_fhN_q[11:0]}};
endmodule

module tb;reg clk=0;always #5 clk=~clk;reg[288:0]p0,p1,p2,p3;wire[3:0]c={4{clk}};integer failures=0;integer hits[0:11];integer n,j;
function automatic[288:0] random_payload(input integer unused);integer k;begin for(k=0;k<9;k=k+1)random_payload[k*32+:32]=$urandom;random_payload[288]=$urandom_range(0,1);end endfunction
wire[1155:0]a0,b0,m0;old0 oa0(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a0));new0 nb0(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b0));new0 nm0(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m0));
wire[1155:0]a1,b1,m1;old1 oa1(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a1));new1 nb1(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b1));new1 nm1(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m1));
wire[1155:0]a2,b2,m2;old2 oa2(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a2));new2 nb2(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b2));new2 nm2(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m2));
wire[1155:0]a3,b3,m3;old3 oa3(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a3));new3 nb3(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b3));new3 nm3(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m3));
wire[1155:0]a4,b4,m4;old4 oa4(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a4));new4 nb4(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b4));new4 nm4(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m4));
wire[1155:0]a5,b5,m5;old5 oa5(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a5));new5 nb5(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b5));new5 nm5(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m5));
wire[1155:0]a6,b6,m6;old6 oa6(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a6));new6 nb6(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b6));new6 nm6(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m6));
wire[1155:0]a7,b7,m7;old7 oa7(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a7));new7 nb7(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b7));new7 nm7(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m7));
wire[1155:0]a8,b8,m8;old8 oa8(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a8));new8 nb8(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b8));new8 nm8(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m8));
wire[1155:0]a9,b9,m9;old9 oa9(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a9));new9 nb9(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b9));new9 nm9(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m9));
wire[1155:0]a10,b10,m10;old10 oa10(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a10));new10 nb10(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b10));new10 nm10(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m10));
wire[1155:0]a11,b11,m11;old11 oa11(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(a11));new11 nb11(.clk(clk),.w_core_pi0(p0),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(b11));new11 nm11(.clk(clk),.w_core_pi0(p0^289'd1),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),.w_core_fh0(c),.w_core_fh1(c),.w_core_fh2(c),.w_core_fh3(c),.w_core_rh0(c),.w_core_rh1(c),.w_core_rh2(c),.w_core_rh3(c),.result(m11));
initial begin for(j=0;j<12;j=j+1)hits[j]=0; p0=0;p1=0;p2=0;p3=0;for(n=0;n<1000;n=n+1)begin @(negedge clk);p0=random_payload(0);p1=random_payload(0);p2=random_payload(0);p3=random_payload(0);@(posedge clk);#1;if(n>3)begin
if(a0!==b0)failures=failures+1;if(a0!==m0)hits[0]=hits[0]+1;
if(a1!==b1)failures=failures+1;if(a1!==m1)hits[1]=hits[1]+1;
if(a2!==b2)failures=failures+1;if(a2!==m2)hits[2]=hits[2]+1;
if(a3!==b3)failures=failures+1;if(a3!==m3)hits[3]=hits[3]+1;
if(a4!==b4)failures=failures+1;if(a4!==m4)hits[4]=hits[4]+1;
if(a5!==b5)failures=failures+1;if(a5!==m5)hits[5]=hits[5]+1;
if(a6!==b6)failures=failures+1;if(a6!==m6)hits[6]=hits[6]+1;
if(a7!==b7)failures=failures+1;if(a7!==m7)hits[7]=hits[7]+1;
if(a8!==b8)failures=failures+1;if(a8!==m8)hits[8]=hits[8]+1;
if(a9!==b9)failures=failures+1;if(a9!==m9)hits[9]=hits[9]+1;
if(a10!==b10)failures=failures+1;if(a10!==m10)hits[10]=hits[10]+1;
if(a11!==b11)failures=failures+1;if(a11!==m11)hits[11]=hits[11]+1;
end end for(j=0;j<12;j=j+1)if(hits[j]==0)failures=failures+1;if(failures)$fatal(1,"MAPPING_FAIL %0d",failures);$display("MAPPING_LOCKSTEP_PASS cases=12 cycles=1000; LIVE_PI_MUTANT_CAUGHT cases=12");$finish;end endmodule
