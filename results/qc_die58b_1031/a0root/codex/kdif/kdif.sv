// Isolated production-width K-step-limit calculator, NW=18, group1. No production RTL uses this candidate.
module ot_kdif_reference(input wire [31:0] gb, input wire [17:0] kt, input wire [3:0] sa, sd, output wire [18:0] q);
  wire [31:0] gbi = gb + 32'd1;
  wire [31:0] c32 = gbi & ((32'd1 << sa) - 32'd1);
  wire [31:0] kext = {14'd0, kt};
  wire [31:0] diff = kext - {13'd0, c32[18:0]} + ((32'd1 << sd) - 32'd1);
  assign q = (kext > c32) ? diff[18:0] : 19'd0;
endmodule

module ot_kdif_candidate #(parameter integer MUT=0)
 (input wire [31:0] gb, input wire [17:0] kt, input wire [3:0] sa, sd, output wire [18:0] q);
  // sa<=15: only the low15 bits of gb+1 can reach c32. Avoid a32-bit shift-minus-one carry chain.
  wire [15:0] gbi = gb[15:0] + 16'd1;
  wire [15:0] c16;
  assign c16[15] = 1'b0;
  genvar j;
  generate for(j=0;j<15;j=j+1) begin: g_mask
    localparam [3:0] J = 4'(j);
    assign c16[j] = gbi[j] & (sa > J);
  end endgenerate
  wire [18:0] a = {1'b0, kt};
  wire [18:0] b = ~{3'd0, c16};
  wire [18:0] c = 19'd1 << sd;
  // Mod2^19: kt-c32+(2^sd-1) == kt+(~c32)+2^sd.
  wire [18:0] s = a ^ b ^ c;
  wire [18:0] maj = (a & b) | (a & c) | (b & c);
  wire [18:0] carry0 = {maj[17:0],1'b0};
  // Seeded control: drop the bit8 carry; SAT must find a visible counterexample.
  wire [18:0] carry = MUT == 0 ? carry0 : carry0 & 19'h7feff;
  wire [18:0] pg [0:5];
  wire [18:0] gg [0:5];
  assign pg[0] = s ^ carry;
  assign gg[0] = s & carry;
  genvar l,k;
  generate for(l=0;l<5;l=l+1) begin: g_level
    localparam integer D = 32'd1 << l;
    for(k=0;k<19;k=k+1) begin: g_bit
      if(k>=D) begin: g_join
        assign gg[l+1][k] = gg[l][k] | (pg[l][k] & gg[l][k-D]);
        assign pg[l+1][k] = pg[l][k] & pg[l][k-D];
      end else begin: g_copy
        assign gg[l+1][k] = gg[l][k];
        assign pg[l+1][k] = pg[l][k];
      end
    end
  end endgenerate
  wire [18:0] result;
  assign result[0] = pg[0][0];
  generate for(j=1;j<19;j=j+1) begin: g_sum
    assign result[j] = pg[0][j] ^ gg[5][j-1];
  end endgenerate
  assign q = (a > {3'd0,c16}) ? result : 19'd0;
endmodule

module ot_kdif_miter #(parameter integer MUT=0)
 (input wire [31:0] gb,input wire [17:0] kt,input wire [3:0] sa,sd,output wire eq);
 wire [18:0] gold, cand;
 ot_kdif_reference u_g(.gb(gb),.kt(kt),.sa(sa),.sd(sd),.q(gold));
 ot_kdif_candidate #(.MUT(MUT)) u_c(.gb(gb),.kt(kt),.sa(sa),.sd(sd),.q(cand));
 assign eq = (gold == cand);
endmodule
