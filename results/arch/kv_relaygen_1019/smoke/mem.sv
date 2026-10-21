module mem (input wire ck, input wire rst_n, input wire [599:0] d, output wire [599:0] q);
  reg [599:0] r; reg [7:0] s; reg [63:0] e;
  always @(posedge ck or negedge rst_n) if (!rst_n) r <= 0; else r <= d;
  always @(posedge ck or negedge rst_n) if (!rst_n) e <= 64'h5; else if (d[3]) e <= d[63:0] ^ e;
  always @(posedge ck) s <= rst_n ? d[7:0] : 8'h0;
  assign q = r ^ {528'b0, e, s};
endmodule
module mem_rr (input wire ck, input wire rst_n, input wire [599:0] d, output wire [599:0] q);
  wire [2:0] rst_c; wire rst_q;
  ot_rst_relay #(.REGIONS(3),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst_relay(.clk(ck),.rst_n_in(rst_n),.rst_n(rst_c));
  assign rst_q = rst_c[0];
  mem u_m(.ck(ck),.rst_n(rst_q),.d(d),.q(q));
endmodule
module top (input wire ck, input wire host_rst_n, input wire ld_rst_n, input wire [599:0] d, output wire [599:0] q, output wire [599:0] q2);
  mem_rr u_a(.ck(ck),.rst_n(host_rst_n),.d(d),.q(q));
  mem u_b(.ck(ck),.rst_n(ld_rst_n),.d(~d),.q(q2));
endmodule
