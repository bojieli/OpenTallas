// HBM-CORES-KITS-21: g_seed (H == 0) of ot_hidx_score_hcol, old (main f0972bc4b) vs new, plus head-1 csi_p register.
module seed_old(input ck, input [15:0] tm, input tf, output reg [31:0] csi_p, output reg cf_o, output reg [31:0] cs_o);
    wire [32:0] seed_d;
    ot_hdc_delay #(.W(33), .D(7)) u_sd (.clk(ck), .rst_n(1'b1),
        .d({tf, (tm[14:0] == 15'd0) ? 32'd0 : {tm, 16'd0}}), .q(seed_d));
    always @(posedge ck) begin cs_o <= seed_d[31:0]; cf_o <= seed_d[32]; csi_p <= cs_o; end
endmodule
module seed_new(input ck, input [15:0] tm, input tf, output reg [31:0] csi_p, output reg cf_o, output reg [31:0] cs_o);
    wire [16:0] seed_d;
    ot_hdc_delay #(.W(17), .D(7)) u_sd (.clk(ck), .rst_n(1'b1),
        .d({tf, (tm[14:0] == 15'd0) ? 16'd0 : tm}), .q(seed_d));
    always @(posedge ck) begin cs_o <= {seed_d[15:0], 16'd0}; cf_o <= seed_d[16]; csi_p <= cs_o; end
endmodule
module seed_mut(input ck, input [15:0] tm, input tf, output reg [31:0] csi_p, output reg cf_o, output reg [31:0] cs_o);
    wire [16:0] seed_d;   // negative control: drops the zero-mantissa flush (tm passed even when tm[14:0]==0)
    ot_hdc_delay #(.W(17), .D(7)) u_sd (.clk(ck), .rst_n(1'b1), .d({tf, tm}), .q(seed_d));
    always @(posedge ck) begin cs_o <= {seed_d[15:0], 16'd0}; cf_o <= seed_d[16]; csi_p <= cs_o; end
endmodule
module miter_A_B(input ck, input [15:0] tm, input tf, output trigger);
    wire [31:0] pa, pb, oa, ob; wire fa, fb;
    seed_A ua(.ck(ck), .tm(tm), .tf(tf), .csi_p(pa), .cf_o(fa), .cs_o(oa));
    seed_B ub(.ck(ck), .tm(tm), .tf(tf), .csi_p(pb), .cf_o(fb), .cs_o(ob));
    assign trigger = (pa != pb) || (fa != fb) || (oa != ob);
endmodule
module lowchk(input ck, input [15:0] tm, input tf, output bad);
    wire [31:0] p, o; wire f;
    seed_new u(.ck(ck), .tm(tm), .tf(tf), .csi_p(p), .cf_o(f), .cs_o(o));
    assign bad = (p[15:0] != 16'd0) || (o[15:0] != 16'd0);
endmodule
