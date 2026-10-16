`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cseq (s81-suhc-hier-1011 comb v2, 2026-10-11): the sequencer of the HC combine region (hard tile, top row;
// N face to the centre pin tile, W / E faces to the outer column roots).  It holds the dsfd_sp_ctrl engine adapter
// (ot_s81_engine_adapter QD 8, cck / sk CDC, command pin flops on cck), the job sequencer of ot_s81_hc_hroot (job
// intake, VM read slots, POST / NORM / HSTORE / HLOAD / COEF / GAIN issue, done / tag, faults), the y credit view
// (beats available = accept notices - beats taken) and the norm's scalar tail (ss from ot_s81_hc_cntree -> RW relay ->
// / D -> + eps -> rsqrt -> the r broadcast beat).  Output flops: the forward bus to both outer roots (w_fv / w_fd /
// e_fv / e_fd) and its centre copy c_fv / c_fd (= stage 1 of the centre chain's forward pad), the pin-tile status.
// HSTORE / NORM end on the writer's count (ot_s81_hc_crx wdone); POST counts the return's outbound events (forwarded
// by crx).  The done pulse still waits DW cycles before the adapter (the last write leaves before its done).
// MUT (bench negative controls, 0 in silicon) as ot_s81_hc_hroot; AMUT is the adapter's.
// PIPE = 1 (rom-layer-tput 2026-10-13, POST issue-order done): a POST ends PD cycles after its LAST y beat left on the
// forward bus instead of after the last write-back event has come back over the return chain.  The chains are
// fixed-latency pulse buses and every tile applies forward events in issue order, so a job issued behind the POST
// (COEF, NORM, H_STORE) reaches each tile after that tile's last hc_post write-back as long as PD >= the tile's
// beat -> write-back latency (26-27 cycles; PD 40).  The return's outbound events are still counted (pob_out, fault
// code 6 on an event nobody issued); late hnz / pflt flags stay sticky faults as before.  PIPE 0: unchanged.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_cseq #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer MUT = 0, AMUT = 0, RF = 1, RT = 1, RW = 2, YD = 16, HALF = 0, RLY = 1, DW = 3 + RW,
    parameter integer PIPE = 1, PD = 40
) (
    input  wire                 cck, crs, sk, srs,
    input  wire                 n_cmd_v,
    input  wire [83:0]          n_cmd_d,
    output wire                 n_done_v,
    output wire [7:0]           n_done_tag,
    input  wire                 n_inp,
    output reg  [S_RD-1:0]      n_rq_v,
    output reg  [S_RD*14-1:0]   n_rq_row,
    input  wire [S_RD-1:0]      n_rs_v,
    input  wire [S_RD*512-1:0]  n_rs_d,
    output reg                  n_flt,
    output reg                  n_online,
    output reg  [3:0]           n_fcode,
    input  wire                 n_yacc,
    output reg                  n_ypop,
    input  wire                 w_flt, e_flt,
    output reg  [FVW-1:0]       w_fv, e_fv, c_fv,
    output reg  [FSW-1:0]       w_fd, e_fd, c_fd,
    // ot_s81_hc_cntree
    output reg                  ngo,
    input  wire                 t_ssv,
    input  wire [31:0]          t_ss,
    input  wire                 t_flt,
    // ot_s81_hc_crx
    output reg                  j_v,
    output reg  [2:0]           kind,
    output reg  [13:0]          base,
    output reg                  f_q, f_y,
    output reg                  j_end,
    output reg                  fault,
    output reg                  j_civ,
    input  wire                 x_wdone, x_pob, x_f1, x_f4,
    // ot_s81_hc_ccf
    input  wire                 c_yfl
);
    reg trace_scalar_mut; initial trace_scalar_mut=$test$plusargs("TRACE_UNUSED_MUT");
    // the comb's geometry (identical to ot_s81_hc_comb; defaults = the hardened NG 256 HIER=1 configuration)
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    localparam integer HOP = 2 + RLY;                             // registers a sub-tile hop (each bus)
    localparam integer PAD = HOP * (NP - L1) * (HALF ? 2 : 1);    // the centre chain is short by NP - L1 octets
    localparam integer FP = 2 + RF + PAD;                         // forward: send + capture + RF + padding
    localparam integer RP = RT + 2 + PAD;                         // return: relay + send + capture + padding
    reg [1:0] rsr;                                                // tile-local reset relay (2 flops at the pin)
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    reg [1:0] crsr;                                      // same for the controller-clock reset
    always @(posedge cck) crsr <= {crsr[0], crs};
    wire crs_n = crsr[1];
    localparam integer N     = 4 * NG;
    localparam integer NR    = D / NG;
    localparam integer NV    = D / N;
    localparam integer HROWS = NR * NG / 8;
    localparam integer GROWS = D / 16;
    localparam integer LA = AL, LM = ML;
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_PB = O_RC + S_RD * 16, O_NG = O_PB + 20,
                       O_NV = O_NG + 6, O_R = O_NV + 8, O_HS = O_R + 32;
    localparam [2:0] K_HLOAD = 0, K_HSTORE = 1, K_COEF = 2, K_POST = 3, K_NORM = 4, K_GAIN = 5;

    // ---------------------------------------------------------------- adapter
    wire e_v, e_r, a_flt, online;
    wire [83:0] e_d;
    reg         d_v;
    reg  [7:0]  d_t;
    reg  inp_q;
    always @(posedge sk or negedge rs_n) if (!rs_n) inp_q <= 1'b0; else inp_q <= n_inp;
    reg        cv_q;
    reg [83:0] cd_q;
    always @(posedge cck or negedge crs_n) if (!crs_n) cv_q <= 1'b0; else cv_q <= n_cmd_v;
    always @(posedge cck) cd_q <= n_cmd_d;
    wire [8:0] dd;
    ot_hdc_delay #(.W(9), .D(DW), .RESET(1)) u_dd (.clk(sk), .rst_n(rs_n), .d({d_v, d_t}), .q(dd));
    wire       cdv;
    wire [7:0] cdt;
    ot_s81_engine_adapter #(.QD(8), .MUT(AMUT)) u_ad (
        .c_clk(cck), .c_rst_n(crs_n), .c_cmd_v(cv_q), .c_cmd_d(cd_q), .c_done_v(cdv), .c_done_tag(cdt),
        .fault(a_flt), .online(online),
        .e_clk(sk), .e_rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(inp_q),
        .e_done_v(dd[8]), .e_done_tag(dd[7:0]));
    reg       dv_q;
    reg [7:0] dt_q;
    always @(posedge cck or negedge crs_n) if (!crs_n) dv_q <= 1'b0; else dv_q <= cdv;
    always @(posedge cck) dt_q <= cdt;
    assign n_done_v = dv_q;
    assign n_done_tag = dt_q;

    // ---------------------------------------------------------------- seam captures
    reg  [S_RD-1:0]     rs_v;
    reg  [S_RD*512-1:0] rs_d;
    reg                 ya, wfl, efl, yfl, ssq_v, tf_q, wd_q, pob_q, f1_q, f4_q;
    reg  [31:0]         ssq;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin
            rs_v <= 0; ya <= 1'b0; wfl <= 1'b0; efl <= 1'b0; yfl <= 1'b0; ssq_v <= 1'b0; tf_q <= 1'b0;
            wd_q <= 1'b0; pob_q <= 1'b0; f1_q <= 1'b0; f4_q <= 1'b0;
        end else begin
            rs_v <= n_rs_v; ya <= n_yacc; wfl <= w_flt; efl <= e_flt; yfl <= c_yfl; ssq_v <= t_ssv; tf_q <= t_flt;
            wd_q <= x_wdone; pob_q <= x_pob; f1_q <= x_f1; f4_q <= x_f4;
        end
    always @(posedge sk) begin rs_d <= n_rs_d; ssq <= t_ss ^ (trace_scalar_mut ? 32'h01000000 : 32'd0); end

    // ---------------------------------------------------------------- y credit view
    reg  [7:0] avail;
    reg        run;
    reg [15:0] ci, cr, post_ob;
    wire       y_v = (avail != 0);
    wire       y_rdy = run && (kind == K_POST) && (ci < NR) && !fault;
    wire       y_take = y_v && y_rdy;
    always @(posedge sk or negedge rs_n) if (!rs_n) avail <= 0; else avail <= avail + ya - y_take;

    // ---------------------------------------------------------------- norm scalar tail
    wire [32:0] ssw;
    ot_hdc_delay #(.W(33), .D(RW), .RESET(1)) u_rw (.clk(sk), .rst_n(rs_n), .d({ssq_v, ssq}), .q(ssw));
    function automatic integer tz(input integer x);
        integer t;
        begin t = 0; while (t < 31 && ((x >> t) & 1) == 0) t = t + 1; tz = t; end
    endfunction
    localparam integer DK = tz(D);
    localparam integer DF = D >> DK;
    wire [31:0] mq, me, rr_;
    wire        mq_v, rr_v, f_div, f_eps, f_rsq;
    reg  [31:0] n_eps;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(sk), .rst_n(rs_n), .v(ssw[32]), .x(ssw[31:0]), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(sk), .rst_n(rs_n), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (sk, rs_n, mq_v, mq, n_eps, me, f_eps);
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(sk), .rst_n(rs_n), .v(ve[LA]), .x(me), .y(rr_), .vo(rr_v), .fault(f_rsq));

    // ---------------------------------------------------------------- sequencer
    reg         jslot;
    reg  [7:0]  jtag;
    reg  [1:0]  gsel;
    reg         st0;
    reg  [31:0] cf_eps [0:1];
    reg  [S_RD-1:0]    rq_v;
    reg  [S_RD*14-1:0] rq_row;
    reg  [FVW-1:0]     fv;
    reg  [FSW-1:0]     fd;
    reg  [3:0]         fault_code;
    reg  [7:0]         pdc;                 // PIPE: cycles since the POST's last beat was issued
    reg  [15:0]        pob_out;             // PIPE: write-back events issued and not yet returned
    assign e_r = !run && !fault;
    wire take = e_v && e_r;
    wire [23:0] c_arg = e_d[30:7];
    wire hs = (MUT == 2 && (kind == K_POST || kind == K_NORM)) ? ~jslot : jslot;
    wire tail_f = tf_q || f_div || f_eps || f_rsq || f1_q;
    integer s;
    always @(posedge sk or negedge rs_n) begin
        if (!rs_n) begin
            run <= 1'b0; kind <= 0; jslot <= 0; jtag <= 0; base <= 0; gsel <= 0; f_q <= 0; f_y <= 0; st0 <= 0;
            d_v <= 1'b0; d_t <= 0; fault <= 1'b0; fault_code <= 0;
            ci <= 0; cr <= 0; post_ob <= 0; rq_v <= 0; fv <= 0; ngo <= 1'b0; j_v <= 1'b0; j_end <= 1'b0; j_civ <= 1'b0;
            pdc <= 0; pob_out <= 0;
        end else begin
            d_v <= 1'b0; rq_v <= 0; fv <= 0; ngo <= 1'b0; j_v <= 1'b0; j_end <= 1'b0;
            j_civ <= (ci == NV + 1);
            if (tail_f) begin fault <= 1'b1; if (!fault) fault_code <= 4'd1; end
            if (f4_q) begin fault <= 1'b1; if (!fault) fault_code <= 4'd4; end
            if (rs_v != 0 && !(run && (kind == K_HLOAD || kind == K_COEF || kind == K_GAIN))) begin
                fault <= 1'b1; if (!fault) fault_code <= 4'd2;
            end
            if (take) begin
                run <= 1'b1; kind <= c_arg[22:20]; jslot <= e_d[83]; jtag <= {e_d[83], e_d[6:0]};
                base <= c_arg[13:0]; gsel <= c_arg[19:18]; f_q <= c_arg[14]; f_y <= c_arg[15]; st0 <= 1'b0;
                ci <= 0; cr <= 0; post_ob <= 0; j_v <= 1'b1; pdc <= 0;
                if (c_arg[23] || c_arg[22:20] > 3'd5 || (c_arg[22:20] == K_NORM && !c_arg[14] && !c_arg[15])) begin
                    fault <= 1'b1; fault_code <= 4'd3;
                end
            end
            // HSTORE / NORM: the writer's count (ot_s81_hc_crx) ends the job
            if (wd_q && run && (kind == K_HSTORE || kind == K_NORM) && !fault) begin
                run <= 1'b0; d_v <= 1'b1; d_t <= (MUT == 5) ? (jtag ^ 8'h01) : jtag; j_end <= 1'b1;
            end
            if (rr_v) begin fv[S_RD + 3] <= 1'b1; fd[O_R +: 32] <= rr_; end
            if (PIPE != 0) begin
                // outstanding write-back events: + 1 a beat issued (with write-back), - 1 an event returned
                pob_out <= pob_out + ((run && !fault && kind == K_POST && y_take) ? 16'd1 : 16'd0)
                                   - (pob_q ? 16'd1 : 16'd0);
                if (pob_q && pob_out == 0 && !(run && kind == K_POST && y_take)) begin
                    fault <= 1'b1; if (!fault) fault_code <= 4'd6;
                end
            end
            if (run && !fault) begin
                case (kind)
                K_HLOAD, K_COEF, K_GAIN: begin
                    for (s = 0; s < S_RD; s = s + 1)
                        if (ci + s < ((kind == K_HLOAD) ? HROWS : (kind == K_COEF) ? 2 : GROWS)) begin
                            rq_v[s] <= 1'b1; rq_row[14 * s +: 14] <= base + ci + s;
                        end
                    ci <= ci + S_RD;
                    begin : rsp
                        reg [15:0] cc;
                        cc = cr;
                        fd[O_RK +: 2] <= (kind == K_HLOAD) ? 2'd0 : (kind == K_GAIN) ? 2'd1 : 2'd2;
                        fd[O_RS] <= (kind == K_HLOAD) ? hs : jslot;
                        fd[O_RG +: 2] <= gsel;
                        for (s = 0; s < S_RD; s = s + 1)
                            if (rs_v[s]) begin
                                fv[s] <= 1'b1; fd[O_RC + 16 * s +: 16] <= cc; fd[O_D + 512 * s +: 512] <= rs_d[512 * s +: 512];
                                if (kind == K_COEF && cc == 1) cf_eps[jslot] <= rs_d[512 * s + 256 +: 32];
                                cc = cc + 1;
                            end
                        cr <= cc;
                        if (cc == ((kind == K_HLOAD) ? HROWS : (kind == K_COEF) ? 2 : GROWS)) begin
                            run <= 1'b0; d_v <= 1'b1; d_t <= (MUT == 5) ? (jtag ^ 8'h01) : jtag; j_end <= 1'b1;
                        end
                    end
                end
                K_HSTORE: if (!st0) begin fv[S_RD + 4] <= 1'b1; fd[O_HS] <= hs; st0 <= 1'b1; end
                K_POST: begin
                    if (y_take) begin
                        fv[S_RD] <= 1'b1;
                        fd[O_PB] <= (ci == 0); fd[O_PB + 1] <= (MUT != 1); fd[O_PB + 2] <= hs; fd[O_PB + 3] <= jslot;
                        fd[O_PB + 4 +: 16] <= ci;
                        ci <= ci + 1;
                    end
                    if (PIPE != 0) begin
                        // issue-order done: every beat is on the forward bus and PD cycles have passed
                        if (ci == NR) begin
                            if (pdc >= PD) begin
                                run <= 1'b0; d_v <= 1'b1; d_t <= (MUT == 5) ? (jtag ^ 8'h01) : jtag; j_end <= 1'b1;
                            end else pdc <= pdc + 8'd1;
                        end
                    end else if (pob_q) begin
                        post_ob <= post_ob + 1;
                        if (post_ob + 1 == NR - ((MUT == 4) ? 1 : 0)) begin
                            run <= 1'b0; d_v <= 1'b1; d_t <= (MUT == 5) ? (jtag ^ 8'h01) : jtag; j_end <= 1'b1;
                        end
                    end
                end
                K_NORM: begin
                    if (MUT == 3) begin
                        run <= 1'b0; d_v <= 1'b1; d_t <= jtag; j_end <= 1'b1;
                    end else if (ci == 0) begin
                        fv[S_RD + 1] <= 1'b1; ngo <= 1'b1; n_eps <= cf_eps[jslot];
                        fd[O_NG] <= hs; fd[O_NG + 1] <= jslot; fd[O_NG + 2 +: 2] <= gsel; fd[O_NG + 4] <= f_q; fd[O_NG + 5] <= f_y;
                        ci <= 1;
                    end else if (ci < NV + 1) begin
                        fv[S_RD + 2] <= 1'b1; fd[O_NV +: 8] <= ci[7:0] - 8'd1;
                        ci <= ci + 1;
                    end
                end
                default: ;
                endcase
            end
        end
    end

    // ---------------------------------------------------------------- sends (output flops)
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin
            n_rq_v <= 0; n_flt <= 1'b0; n_online <= 1'b0; n_fcode <= 0; n_ypop <= 1'b0; w_fv <= 0; e_fv <= 0; c_fv <= 0;
        end else begin
            n_rq_v <= rq_v; n_flt <= a_flt | fault | wfl | efl | yfl; n_online <= online; n_fcode <= fault_code;
            n_ypop <= fv[S_RD];
            w_fv <= fv; e_fv <= fv; c_fv <= fv;
        end
    always @(posedge sk) begin n_rq_row <= rq_row; w_fd <= fd; e_fd <= fd; c_fd <= fd; end
endmodule
