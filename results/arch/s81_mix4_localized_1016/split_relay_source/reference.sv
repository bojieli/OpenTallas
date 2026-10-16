module ot_s81_engram_reset(input wire clk,arst_n,output wire rst_n);
 reg [1:0] sync;
 always @(posedge clk or negedge arst_n)if(!arst_n)sync<=0;else sync<={sync[0],1'b1};
 assign rst_n=sync[1];
endmodule
module ot_s81_engram_rly(input wire clk,arst_n,input wire [68:0] up_i,input wire [35:0] dn_i,
 output reg [68:0] up_o,output reg [35:0] dn_o);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 // up: {mvalid 8, mfault 8, add_copy 8, avalid 4, af 4, go, phase, in_v, copy 2, scale 32}; dn: {a_gate 32, gate_v, gate_copy 2, fault}
 always @(posedge clk or negedge rn)if(!rn)begin up_o[68:37]<=0;up_o[36:32]<=0;dn_o[3:0]<=0;end
 else begin up_o[68:32]<=up_i[68:32];dn_o[3:0]<=dn_i[3:0];end
 always @(posedge clk)begin up_o[31:0]<=up_i[31:0];dn_o[35:4]<=dn_i[35:4];end
endmodule