`timescale 1ns/1ps
// KV-ING-8 11-07 vH2 conservative wrapper of qkd_hr_ingest_eng.  Same ports as r3.  PIN CYCLES (declared): in_v/in_data, d_v/d_data -> engine +1; engine -> w_* +1;
// done_v, done_tag, n_sectors +1 on top of that (mid hop towards the top-left pins); stream done additionally waits for the write face to drain; busy falls later accordingly.
// Faces: every in_data/d_data pin = one free-running flop.  w_rdy reaches only the port register band and the skid count.  Reset: one relay flop, as RF-KV1; the flow's reset replicas fan it out.
module qkd_hr_ingest_eng (
    input  wire         ck,
    output wire         busy,
    input  wire [255:0] d_data,
    output wire         d_rdy,
    input  wire         d_v,
    output wire [7:0]   done_tag,
    output wire         done_v,
    input  wire [511:0] in_data,
    output wire         in_rdy,
    input  wire         in_v,
    output wire [31:0]  n_sectors,
    output wire [31:0]  r_addr,
    output wire         r_v,
    input  wire [255:0] rd_data,
    input  wire         rd_v,
    input  wire         rst_n,
    output wire [31:0]  w_addr,
    output wire [255:0] w_data,
    input  wire         w_rdy,
    output wire         w_v
);
    assign r_v = 1'b0;
    assign r_addr = 32'd0;
    (* keep = 1 *) reg rf_rst_q__rst_n;
    always @(posedge ck or negedge rst_n) if (!rst_n) rf_rst_q__rst_n <= 1'b0; else rf_rst_q__rst_n <= 1'b1;
    wire rq = rf_rst_q__rst_n;

    // -- input face flops -------------------------------------------------------------------------------------------
    (* keep = 1 *) reg [511:0] fc_in;
    (* keep = 1 *) reg [255:0] fc_d;
    reg fc_in_v, fc_d_v;
    wire e_in_rdy, e_d_rdy;
    assign in_rdy = e_in_rdy;
    assign d_rdy = e_d_rdy;
    wire in_acc = in_v && e_in_rdy, d_acc = d_v && e_d_rdy;
    always @(posedge ck) begin fc_in <= in_data; fc_d <= d_data; end
    always @(posedge ck or negedge rq)
        if (!rq) begin fc_in_v <= 1'b0; fc_d_v <= 1'b0; end
        else begin fc_in_v <= in_acc; fc_d_v <= d_acc; end

    // -- engine -----------------------------------------------------------------------------------------------------
    wire         e_wv, e_last, e_busy, sd_fire, er_n;
    wire [7:0]   e_tag, sd_tag;
    wire [31:0]  e_addr;
    wire [255:0] e_data;
    wire         face_idle;
    qkd_host_native_engine_ing4 u_eng (.clk(ck), .rst_n(rq),
        .p_d_v(fc_d_v), .p_d_rdy(e_d_rdy), .p_d_data(fc_d),
        .p_in_v(fc_in_v), .p_in_rdy(e_in_rdy), .p_in_data(fc_in),
        .e_wv(e_wv), .er_n(er_n), .w_addr(e_addr), .w_data(e_data), .e_last(e_last), .e_tag(e_tag),
        .face_idle(face_idle), .sd_fire(sd_fire), .sd_tag(sd_tag), .p_busy(e_busy));

    // -- write face: skid S[0:1] + port register ----------------------------------------------------------------------
    // S data is written on every accepted beat and needs no w_rdy; the count and pointers decide whether it counts.
    localparam integer FW = 297;
    reg          er_w;                          // same D as the engine's copies
    wire [FW-1:0] e_all = {e_last, e_tag, e_addr, e_data};
    reg  [FW-1:0] s0, s1;
    (* keep = 1 *) reg [287:0] o_pin;           // {w_addr, w_data}: reaches only the pins
    (* keep = 1 *) reg [287:0] o_h;             // the same value, holds the register (face guard: a port flop has no internal load)
    reg  [8:0]   o_dn;                          // {last, tag}
    reg          o_v, o_vp, s_wp, s_rp;
    reg  [1:0]   s_n;
    wire         push = e_wv && er_w;
    wire         ld_o = !o_v || w_rdy;
    wire         s_nz = s_n != 2'd0;
    wire         s_keep = push && !(ld_o && !s_nz);
    wire         s_take = ld_o && s_nz;
    wire [FW-1:0] s_h = s_rp ? s1 : s0;
    wire [FW-1:0] o_n = s_nz ? s_h : e_all;
    assign er_n = ({2'd0, o_v} + {1'b0, s_n} + {2'd0, push}) <= 3'd2;
    assign face_idle = !o_v && !s_nz;
    assign w_v = o_vp;
    assign w_addr = o_pin[287:256];
    assign w_data = o_pin[255:0];
    always @(posedge ck) begin
        if (push && !s_wp) s0 <= e_all;
        if (push && s_wp) s1 <= e_all;
        o_pin <= ld_o ? o_n[287:0] : o_h;
        o_h <= ld_o ? o_n[287:0] : o_h;
        if (ld_o) o_dn <= o_n[296:288];
    end
    wire         fire = o_v && w_rdy;
    always @(posedge ck or negedge rq)
        if (!rq) begin o_v <= 1'b0; o_vp <= 1'b0; s_wp <= 1'b0; s_rp <= 1'b0; s_n <= 2'd0; er_w <= 1'b0; end
        else begin
            er_w <= er_n;
            if (ld_o) begin o_v <= s_nz || push; o_vp <= s_nz || push; end
            if (s_keep) s_wp <= !s_wp;
            if (s_take) s_rp <= !s_rp;
            s_n <= s_n + {1'b0, s_keep} - {1'b0, s_take};
        end

    // -- done, n_sectors: one hop towards the top-left pins ----------------------------------------------------------
    reg  wf_a, wf_b, dn_a, dn_b, dn_q;
    reg  [7:0] tg_a, tg_b, tg_q;
    reg  [15:0] nsec_lo, nsec_hi;
    (* keep = 1 *) reg [31:0] nsec_o;           // port flops, same D as the counter
    reg  nsec_lf;
    wire [15:0] nsec_lo_n = wf_b ? nsec_lo + 16'd1 : nsec_lo;
    wire [15:0] nsec_hi_n = (wf_b && nsec_lf) ? nsec_hi + 16'd1 : nsec_hi;
    assign done_v = dn_q;
    assign done_tag = tg_q;
    assign n_sectors = nsec_o;
    always @(posedge ck) begin
        tg_a <= (fire && o_dn[8]) ? o_dn[7:0] : sd_tag;
        tg_b <= tg_a; tg_q <= tg_b;
    end
    always @(posedge ck or negedge rq)
        if (!rq) begin
            wf_a <= 1'b0; wf_b <= 1'b0; dn_a <= 1'b0; dn_b <= 1'b0; dn_q <= 1'b0;
            nsec_lo <= 16'd0; nsec_hi <= 16'd0; nsec_lf <= 1'b0; nsec_o <= 32'd0;
        end else begin
            wf_a <= fire; wf_b <= wf_a;
            dn_a <= (fire && o_dn[8]) || sd_fire; dn_b <= dn_a; dn_q <= dn_b;
            nsec_lo <= nsec_lo_n; nsec_hi <= nsec_hi_n; nsec_o <= {nsec_hi_n, nsec_lo_n};
            if (wf_b) nsec_lf <= nsec_lo == 16'hfffe;
        end

    // -- busy ---------------------------------------------------------------------------------------------------------
    reg  busy_q;
    assign busy = busy_q;
    always @(posedge ck or negedge rq)
        if (!rq) busy_q <= 1'b0;
        else busy_q <= e_busy || in_acc || d_acc || fc_in_v || fc_d_v || o_v || s_nz || push || wf_a || wf_b || dn_a || dn_b;
endmodule
