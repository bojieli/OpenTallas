module write_cut #(parameter WRITE_PREDECODE=0) (input clk, rst_n, input [1:0] gh, input [4:0] gk, input [7:0] gid,ld_grp, input ld_v,ld_mode,ld_w2v,
input [2:0] ld_bank, input [1023:0] ld_w, input [255:0] ld_wp,
output [79:0] weights);
localparam HG=4,TD=32,R=2,BW=3,PWORDS=2,NBANK=5;
wire rst_l=rst_n;
wire [7:0] gid_m=gid;
genvar gc;
generate
            wire [BW-1:0] r_ld_bank;
            wire [PWORDS*TD*16-1:0] r_ld_w;
            wire [R*16-1:0] pcol, pcol2;
            wire [TD-1:0] we;
            wire [TD*16-1:0] wd;
            if (WRITE_PREDECODE != 0) begin : g_predecode
            ot_hdc_v41x_kreg #(.W(BW), .R(0)) u_rc (.clk(clk), .rst_n(rst_l),
                .d(ld_bank), .q(r_ld_bank));
            ot_hdc_v41x_kreg #(.W(PWORDS*TD*16), .R(0)) u_rw (.clk(clk), .rst_n(rst_l), .d(ld_w), .q(r_ld_w));
            wire [PWORDS*R*16-1:0] r_ld_wp;
            ot_hdc_v41x_kreg #(.W(PWORDS*R*16), .R(0)) u_rp (.clk(clk), .rst_n(rst_l),
                .d(ld_wp[gh*PWORDS*R*16 +: PWORDS*R*16]), .q(r_ld_wp));
            assign pcol = r_ld_wp[0 +: R*16];
            assign pcol2 = r_ld_wp[R*16 +: R*16];
            // Decode stationary write classes before the existing R0 edge.
            // The old raw mode R0 drove 512 data-mux bits/head; graph copies
            // exposed 132 D loads on the raw mode port. Register the actual
            // normal/low/high write predicates instead. Data and bank still
            // cross precisely the same R0 edge and ab captures at R0+1.
            wire write_normal;
            wire [7:0] head_id = gid_m * HG + gh;
            wire n_raw = ld_v && !ld_mode && (ld_grp == head_id);
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_wn (.clk(clk), .rst_n(rst_l),
                .d(n_raw), .q(write_normal));
            wire [TD/R-1:0] write_low, write_high;
            for (gc = 0; gc < TD/R; gc = gc + 1) begin : g_wdecode
                wire lo_raw = ld_v && ld_mode && (ld_grp == gc);
                wire hi_raw = ld_v && ld_mode && ld_w2v && ((ld_grp + 8'd1) == gc);
                ot_hdc_v41x_kreg #(.W(2), .R(1)) u_wc (.clk(clk), .rst_n(rst_l),
                    .d({hi_raw, lo_raw}), .q({write_high[gc], write_low[gc]}));
            end

                assign we = {TD{1'b0}};
                assign wd = {TD*16{1'b0}};
            end else begin : g_original
            wire             r_ld_v, r_ld_mode;
            wire [7:0]       r_ld_grp;
            wire             r_ld_w2v;
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_rv (.clk(clk), .rst_n(rst_l), .d(ld_v), .q(r_ld_v));
            ot_hdc_v41x_kreg #(.W(1 + BW + 8 + 1), .R(0)) u_rc (.clk(clk), .rst_n(rst_l),
                .d({ld_mode, ld_bank, ld_grp, ld_w2v}), .q({r_ld_mode, r_ld_bank, r_ld_grp, r_ld_w2v}));
            ot_hdc_v41x_kreg #(.W(PWORDS*TD*16), .R(0)) u_rw (.clk(clk), .rst_n(rst_l), .d(ld_w), .q(r_ld_w));
            reg [7:0] hh;
            always @(posedge clk) hh <= gid_m * HG + gh;
            wire [PWORDS*R*16-1:0] r_ld_wp;
            ot_hdc_v41x_kreg #(.W(PWORDS*R*16), .R(0)) u_rp (.clk(clk), .rst_n(rst_l),
                .d(ld_wp[gh*PWORDS*R*16 +: PWORDS*R*16]), .q(r_ld_wp));
            assign pcol = r_ld_wp[0 +: R*16];
            assign pcol2 = r_ld_wp[R*16 +: R*16];
            for (gc = 0; gc < TD; gc = gc + 1) begin : g_w
                wire lo = (r_ld_grp == (gc / R));
                wire hi = r_ld_w2v && ((r_ld_grp + 8'd1) == (gc / R));
                assign wd[gc*16 +: 16] = !r_ld_mode ? r_ld_w[gc * 16 +: 16] :
                                         hi ? pcol2[(gc % R) * 16 +: 16] : pcol[(gc % R) * 16 +: 16];
                assign we[gc] = r_ld_v && (r_ld_mode ? (lo || hi) : (r_ld_grp == hh));
            end

            end


                reg [NBANK*16-1:0] ab;
                integer bb;
                if (WRITE_PREDECODE != 0) begin : g_prewrite
                always @(posedge clk)
                    for (bb = 0; bb < NBANK; bb = bb + 1)
                        if (r_ld_bank == bb) begin
                            if (g_predecode.write_normal) ab[bb*16 +: 16] <= r_ld_w[gk*16 +: 16];
                            else if (g_predecode.write_high[gk/R]) ab[bb*16 +: 16] <= pcol2[(gk%R)*16 +: 16];
                            else if (g_predecode.write_low[gk/R]) ab[bb*16 +: 16] <= pcol[(gk%R)*16 +: 16];
                        end
                end else begin : g_oldwrite
                    always @(posedge clk)
                        for (bb = 0; bb < NBANK; bb = bb + 1)
                            if (we[gk] && (r_ld_bank == bb)) ab[bb*16 +: 16] <= wd[gk*16 +: 16];
                end
assign weights=ab;
endgenerate
endmodule
module write_miter (input clk, rst_n, input [1:0] gh, input [4:0] gk, input [7:0] gid,ld_grp, input ld_v,ld_mode,ld_w2v,
input [2:0] ld_bank, input [1023:0] ld_w, input [255:0] ld_wp,
output same_state);
wire[79:0] a,b;
write_cut #(.WRITE_PREDECODE(0)) gold (.clk(clk),.rst_n(rst_n),.gh(gh),.gk(gk),.gid(gid),.ld_grp(ld_grp),.ld_v(ld_v),.ld_mode(ld_mode),.ld_w2v(ld_w2v),.ld_bank(ld_bank),.ld_w(ld_w),.ld_wp(ld_wp),.weights(a));
write_cut #(.WRITE_PREDECODE(1)) cand (.clk(clk),.rst_n(rst_n),.gh(gh),.gk(gk),.gid(gid),.ld_grp(ld_grp),.ld_v(ld_v),.ld_mode(ld_mode),.ld_w2v(ld_w2v),.ld_bank(ld_bank),.ld_w(ld_w),.ld_wp(ld_wp),.weights(b));
assign same_state=a==b;
endmodule
