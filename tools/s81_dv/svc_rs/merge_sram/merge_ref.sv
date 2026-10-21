// Exact baseline d4a246de4 merge_x body; module name only changed.
module ot_hdc_v41x_attn_merge_x_ref #(
    parameter integer H = 16,
    parameter integer DPT = 16,
    parameter integer MLEV = 4,
    parameter integer FPL = 3,
    parameter integer F12 = 0          // 1: FP32 adds are the 1.2 GHz f12 units (rtl/hdc/ot_hdc_fp32_f12.sv)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              iv,
    input  wire              ifin,
    input  wire [MLEV-1:0]   iblk,
    input  wire [H*32-1:0]   iy,
    input  wire [H-1:0]      if_,
    output wire              ov,
    output wire [H*32-1:0]   oy,
    output wire [H-1:0]      of_
);
    // per level, per head: control copies {v, fin, live, blk}
    wire [(MLEV+1)*H-1:0]      cv, cfin, clive;
    wire [(MLEV+1)*H*MLEV-1:0] cblk;
    wire [(MLEV+1)*H*32-1:0]   lx;
    wire [(MLEV+1)*H-1:0]      lf;
    genvar gl, gh;
    generate
        // level 0: registered input, one control copy per head
        reg [H*32-1:0] r_iy;
        reg [H-1:0]    r_if;
        always @(posedge clk) begin r_iy <= iy; r_if <= if_; end
        assign lx[0 +: H*32] = r_iy;
        assign lf[0 +: H] = r_if;
        for (gh = 0; gh < H; gh = gh + 1) begin : g_c0
            wire c_v, c_fin;
            wire [MLEV-1:0] c_blk;
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_cv (.clk(clk), .rst_n(rst_n), .d(iv), .q(c_v));
            ot_hdc_v41x_kreg #(.W(1 + MLEV), .R(0)) u_ct (.clk(clk), .rst_n(rst_n), .d({ifin, iblk}), .q({c_fin, c_blk}));
            assign cv[gh] = c_v;
            assign cfin[gh] = c_fin;
            assign clive[gh] = 1'b1;
            assign cblk[gh*MLEV +: MLEV] = c_blk;
        end
        for (gl = 0; gl < MLEV; gl = gl + 1) begin : g
            // the level's tags, from head 0's copies (all copies are equal), FPL - 1 shared stages + per-head copy
            wire v0 = cv[gl*H];
            wire fin0 = cfin[gl*H];
            wire live0 = clive[gl*H];
            wire [MLEV-1:0] blk0 = cblk[(gl*H)*MLEV +: MLEV];
            wire dv;
            wire [MLEV+1:0] dt;
            ot_hdc_v41x_vdly #(.D(FPL - 1)) u_dv (.clk(clk), .rst_n(rst_n), .d(v0), .q(dv));
            ot_hdc_v41x_dly #(.W(2 + MLEV), .D(FPL - 1)) u_dt (.clk(clk), .d({fin0, live0 && (blk0[gl] || fin0), blk0}),
                .q(dt));
            for (gh = 0; gh < H; gh = gh + 1) begin : g_h
                wire v = cv[gl*H+gh];
                wire fin = cfin[gl*H+gh];
                wire live = clive[gl*H+gh];
                wire [MLEV-1:0] blk = cblk[(gl*H+gh)*MLEV +: MLEV];
                wire use_ = blk[gl];
                wire store = v && live && !fin && !use_;
                reg [32:0] ring [0:DPT-1];
                wire [32:0] head = ring[0];
                integer i;
                always @(posedge clk)
                    if (v) begin
                        for (i = 0; i < DPT - 1; i = i + 1) ring[i] <= ring[i+1];
                        ring[DPT-1] <= store ? {lf[gl*H+gh], lx[(gl*H+gh)*32 +: 32]} : head;
                    end
                wire [31:0] a = use_ ? head[31:0] : 32'd0;
                wire [31:0] y;
                wire af;
                ot_hdc_v41x_qaddf #(.LAT(FPL), .F12(F12)) u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(a),
                                 .b(lx[(gl*H+gh)*32 +: 32]), .y(y), .fault(af));
                wire fdq;
                ot_hdc_v41x_dly #(.W(1), .D(FPL)) u_fd (.clk(clk), .d(lf[gl*H+gh] | (use_ & head[32])), .q(fdq));
                assign lx[((gl+1)*H+gh)*32 +: 32] = y;
                assign lf[(gl+1)*H+gh] = fdq | af;
                // next level's control copy for this head
                wire n_v, n_fin, n_live;
                wire [MLEV-1:0] n_blk;
                ot_hdc_v41x_kreg #(.W(1), .R(1)) u_nv (.clk(clk), .rst_n(rst_n), .d(dv), .q(n_v));
                ot_hdc_v41x_kreg #(.W(2 + MLEV), .R(0)) u_nt (.clk(clk), .rst_n(rst_n), .d(dt), .q({n_fin, n_live, n_blk}));
                assign cv[(gl+1)*H+gh] = n_v;
                assign cfin[(gl+1)*H+gh] = n_fin;
                assign clive[(gl+1)*H+gh] = n_live;
                assign cblk[((gl+1)*H+gh)*MLEV +: MLEV] = n_blk;
            end
        end
    endgenerate
    assign ov = cv[MLEV*H] && cfin[MLEV*H] && clive[MLEV*H];
    assign oy = lx[MLEV*H*32 +: H*32];
    assign of_ = lf[MLEV*H +: H];
endmodule


