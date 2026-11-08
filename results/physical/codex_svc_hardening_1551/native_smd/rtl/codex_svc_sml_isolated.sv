module codex_svc_sml_isolated #(
    parameter integer NVMAX = 40, LM = 5, LA = 4
) (
    input  wire        clk,
    input  wire        rst_in,
    input  wire        sk_en,                          // cfg: this lane also runs the head's sink exp (lane 0)
    input  wire        i_cv,                           // SE configuration
    input  wire [6:0]  i_nv,
    input  wire [31:0] i_scale,
    input  wire [31:0] i_sink,
    input  wire        i_sv,                           // score
    input  wire [31:0] i_s,
    input  wire        i_mv,                           // -mb of the head
    input  wire [31:0] i_nmb,
    output reg         o_mxv,                          // the lane's row max (final)
    output wire [31:0] o_mx,
    output reg         o_ev,                           // e (o_es: the sink's exp, o_el: the row's last vector)
    output reg         o_es,
    output reg         o_el,
    output reg  [31:0] o_e
);
    localparam integer D_EXP = 7 * LM + 8 * LA + 4;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    function automatic [31:0] okey(input [31:0] x);
        okey = x[31] ? ~x : {1'b1, x[30:0]};
    endfunction

    // pin flops
    reg        cv, sv, mv, ske;
    reg [6:0]  nv_p; reg [31:0] scale_p, sink_p, s_p, nmb_p;
    always @(posedge clk) begin nv_p <= i_nv; scale_p <= i_scale; sink_p <= i_sink; s_p <= i_s; nmb_p <= i_nmb; ske <= sk_en; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cv <= 1'b0; sv <= 1'b0; mv <= 1'b0; end else begin cv <= i_cv; sv <= i_sv; mv <= i_mv; end
    reg [6:0]  nv; reg [31:0] scale, sink;
    always @(posedge clk) if (cv) begin nv <= nv_p; scale <= scale_p; sink <= sink_p; end

    // A. s = s_raw * scale -> buffer; running max
    wire [LM:0] smv;
    ot_hdc_vline #(.D(LM)) u_smv (.clk(clk), .rst_n(rst_n), .v(sv), .vd(smv));
    wire [31:0] s_m, s_m_raw;
    wire fm;
    wire [LM:0] s_inactive;
    ot_hdc_vline #(.D(LM)) u_s_inactive (.clk(clk), .rst_n(rst_n),
        .v(sv && s_p == 32'hff800000), .vd(s_inactive));
    // The finite-domain multiplier does not implement IEEE infinity. Carry the
    // compiler's mask around it and retain the sentinel in the score store/max.
    ot_dsrom_su_softmax_mul #(LM) u_m (clk, rst_n, sv,
        s_p == 32'hff800000 ? 32'd0 : s_p, scale, s_m_raw, fm);
    assign s_m = s_inactive[LM] ? 32'hff800000 : s_m_raw;
    reg [31:0] sbuf [0:NVMAX-1];
    reg [6:0]  wcnt;
    reg        s_mlast, a_done, fv, ff;
    reg [31:0] s_q, rmax;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin wcnt <= 7'd0; a_done <= 1'b0; s_mlast <= 1'b0; fv <= 1'b0; ff <= 1'b0; end
        else begin
            a_done <= s_mlast;
            s_mlast <= smv[LM] && (wcnt + 7'd1 == nv);
            fv <= smv[LM]; ff <= (wcnt == 7'd0);
            if (smv[LM]) wcnt <= (wcnt + 7'd1 == nv) ? 7'd0 : wcnt + 7'd1;
        end
    end
    always @(posedge clk) if (smv[LM]) sbuf[wcnt] <= s_m;
    always @(posedge clk) s_q <= s_m;
    wire ge;
    ot_hdc_kge #(.W(32), .K(1)) u_ge (.a(okey(rmax)), .b(okey(s_q)), .ge(ge));
    always @(posedge clk) if (fv) rmax <= (ff || !ge) ? s_q : rmax;
    always @(posedge clk or negedge rst_n) if (!rst_n) o_mxv <= 1'b0; else o_mxv <= a_done;
    reg [31:0] mx_local;
    always @(posedge clk) if (a_done) mx_local <= rmax;
    wire [31:0] mx_next = a_done ? rmax : mx_local;
    // Duplicate the existing state edge. The output Q has no hold-mux feedback.
    generate for(genvar cp=0;cp<32;cp=cp+1)begin:g_face_mx
        (* keep=1, keep_hierarchy=1 *) codex_svc_face_state_bit u_copy
            (.clk(clk),.d(mx_next[cp]),.q(o_mx[cp]));
    end endgenerate

    // B. (sink one slot ahead on sk_en) re-read s, e = exp(s + (-mb))
    reg [31:0] mbn, s_rd;
    reg [6:0]  rcnt;
    reg        rd_on, rv, rlast, skg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rd_on <= 1'b0; rcnt <= 7'd0; rv <= 1'b0; rlast <= 1'b0; skg <= 1'b0; end
        else begin
            rv <= rd_on;
            rlast <= rd_on && (rcnt + 7'd1 == nv);
            skg <= mv && ske;
            if (mv) begin rd_on <= 1'b1; rcnt <= 7'd0; end
            else if (rd_on) begin
                rcnt <= rcnt + 7'd1;
                if (rcnt + 7'd1 == nv) rd_on <= 1'b0;
            end
        end
    end
    always @(posedge clk) begin
        if (mv) mbn <= nmb_p;
        if (rd_on) s_rd <= sbuf[rcnt];
        else if (mv) s_rd <= sink;
    end
    wire av = rv || skg;
    wire [LA+D_EXP:0] bv, bl, bs;
    ot_hdc_vline #(.D(LA + D_EXP)) u_bv (.clk(clk), .rst_n(rst_n), .v(av), .vd(bv));
    ot_hdc_vline #(.D(LA + D_EXP)) u_bl (.clk(clk), .rst_n(rst_n), .v(rlast), .vd(bl));
    ot_hdc_vline #(.D(LA + D_EXP)) u_bs (.clk(clk), .rst_n(rst_n), .v(skg), .vd(bs));
    wire [31:0] bd, be;
    wire fa, fe;
    ot_dsrom_su_softmax_add #(.ADD6(0), .LA(LA)) u_a (clk, rst_n, av, s_rd, mbn, bd, fa);
    ot_hdc_v41x_exp #(.LM(LM), .LA(LA)) u_e (.clk(clk), .rst_n(rst_n), .v(bv[LA]), .x(bd), .y(be), .vo(), .fault(fe));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_ev <= 1'b0; o_es <= 1'b0; o_el <= 1'b0; end
        else begin o_ev <= bv[LA + D_EXP]; o_es <= bs[LA + D_EXP]; o_el <= bl[LA + D_EXP]; end
    // -Inf is the compiler's inactive score-lane sentinel.  The polynomial exp
    // clamps its input to -87, so it MUST NOT supply the inactive lane's value.
    // Delay the mask on the same fixed add/exp timeline; no execution gating.
    wire [LA+D_EXP:0] inactive;
    ot_hdc_vline #(.D(LA + D_EXP)) u_inactive (.clk(clk), .rst_n(rst_n),
        .v(rv && s_rd == 32'hff800000), .vd(inactive));
    always @(posedge clk) o_e <= inactive[LA + D_EXP] ? 32'd0 : be;
endmodule
(* keep_hierarchy=1 *) module codex_svc_face_state_bit(input clk,d,output reg q);
 always @(posedge clk) q<=d;
endmodule
