module ot_s81_engram_reset(input wire clk,arst_n,output wire rst_n);
 reg [1:0] sync;
 always @(posedge clk or negedge arst_n)if(!arst_n)sync<=0;else sync<={sync[0],1'b1};
 assign rst_n=sync[1];
endmodule
module ot_s81_engram_capture_slice #(parameter integer W=1,parameter [W-1:0] RESET_MASK={W{1'b1}})(
 input wire clk,arst_n,input wire [W-1:0] d,output wire [W-1:0] q);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 genvar b;generate for(b=0;b<W;b=b+1)begin:bit_ff
  reg value;
  if(RESET_MASK[b])begin always @(posedge clk or negedge rn)if(!rn)value<=0;else value<=d[b];end
  else begin always @(posedge clk)value<=d[b];end
  assign q[b]=value;
 end endgenerate
endmodule
module ot_s81_engram_rly_split #(parameter integer MUT=0)(
 input wire [17:0] ck,input wire arst_n,input wire [68:0] up_i,input wire [35:0] dn_i,
 output wire [68:0] up_o,output wire [35:0] dn_status,output wire [127:0] gate_local);
 genvar g;generate
 for(g=0;g<8;g=g+1)begin:mul
  wire local_ck=(MUT==27&&g==1)?1'b0:ck[g];
  ot_s81_engram_capture_slice #(.W(2)) u(local_ck,arst_n,{up_i[61+g],up_i[53+g]},{up_o[61+g],up_o[53+g]});
 end
 for(g=0;g<4;g=g+1)begin:add
  ot_s81_engram_capture_slice #(.W(4)) u(ck[8+g],arst_n,{up_i[45+2*g+:2],up_i[41+g],up_i[37+g]},
   {up_o[45+2*g+:2],up_o[41+g],up_o[37+g]});
  ot_s81_engram_capture_slice #(.W(32),.RESET_MASK(32'b0)) gate_capture(ck[13+g],arst_n,dn_i[35:4],gate_local[32*g+:32]);
 end
 endgenerate
 ot_s81_engram_capture_slice #(.W(37),.RESET_MASK({5'b11111,32'b0})) shell_up(ck[12],arst_n,up_i[36:0],up_o[36:0]);
 ot_s81_engram_capture_slice #(.W(4)) shell_dn(ck[17],arst_n,dn_i[3:0],dn_status[3:0]);
 assign dn_status[35:4]=gate_local[31:0]; // Legacy observation only; add leaves bind their own local slice.
endmodule
module ot_s81_engram_rly(input wire clk,arst_n,input wire [68:0] up_i,input wire [35:0] dn_i,
 output reg [68:0] up_o,output reg [35:0] dn_o);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 // up: {mvalid 8, mfault 8, add_copy 8, avalid 4, af 4, go, phase, in_v, copy 2, scale 32}; dn: {a_gate 32, gate_v, gate_copy 2, fault}
 always @(posedge clk or negedge rn)if(!rn)begin up_o[68:37]<=0;up_o[36:32]<=0;dn_o[3:0]<=0;end
 else begin up_o[68:32]<=up_i[68:32];dn_o[3:0]<=dn_i[3:0];end
 always @(posedge clk)begin up_o[31:0]<=up_i[31:0];dn_o[35:4]<=dn_i[35:4];end
endmodule