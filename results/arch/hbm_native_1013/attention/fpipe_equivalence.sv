module gold_fpipe #(parameter integer W = 1, parameter integer N = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    genvar s;
    generate if (N == 0) begin : g0
        assign q = d;
    end else begin : gn
        wire [W-1:0] st [0:N];
        assign st[0] = d;
        for (s = 0; s < N; s = s + 1) begin : g_s
            (* keep = "true" *) ot_attn_rp_reg #(.W(W)) u_r (.clk(clk), .d(st[s]), .q(st[s+1]));
        end
        assign q = st[N];
    end endgenerate
endmodule
module ot_attn_rp_reg #(parameter integer W = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule
module bank136(input clk, input [135:0] d, output reg [135:0] q); always @(posedge clk) q<=d; endmodule
module padded(input clk,input [38:0] d, output [38:0] q);
wire [135:0] s[0:4]; assign s[0]={97'b0,d};
genvar i; generate for(i=0;i<4;i=i+1) begin:g bank136 u(clk,s[i],s[i+1]); end endgenerate
assign q=s[4][38:0]; endmodule
module proof(input clk,input [38:0] d,output good);
wire [38:0] a,b;gold_fpipe #(.W(39),.N(4)) u0(clk,d,a);padded u1(clk,d,b);
`ifdef MUTANT
assign good=(a=={b[38:1],~b[0]});
`else
assign good=(a==b);
`endif
endmodule
