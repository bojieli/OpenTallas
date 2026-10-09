`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// CLAUDE S81-PH collector, TILED (redesign pass 2026-10-06, DESIGN SIMPLIFICATION RULES).  col_m2 (ot_s81ph_col_core
// as one 5270 x 881 view) reached post-CTS -2288 ps: one clock tree over the 5.3 mm slab (path depth 56-66, skew
// 1.1 ns) and 7 transport stages per lane inside the view.  Split into hardened tiles:
//
//   dsfd_colt_lane  one per stack (x4, the E pair placed MY-mirrored): pin flop on the die lane, the frame parser, the
//                   2 x 256x256 SRAM frame FIFO (macro outputs land in the FIFO's output registers), a frame sender
//                   that forwards only COMPLETE frames, word by word under credits, and a sticky fault sideband.
//                   Every output leaves from a flop; every input is captured at its pin.
//   dsfd_colt_mrg   the merger at the slab centre: per lane a DM-entry landing FIFO (flops, head at entry 0) that
//                   returns one credit per pop, the unchanged frame-atomic round-robin merge / 4-way DONE merge /
//                   fault logic of ot_s81ph_col_core on the landing heads, the paced vd word from a pin flop, vf.
//   ot_s81ph_col_t  composition: lane tiles at the W / E faces, merger at the centre, HOPS registered stations per
//                   direction on each lane (die stations, <= ~430 um each; the generator places them).
//
// Exactness is transaction-level (tb_s81ph_col: every frame bit-exact and whole, each stack's frames in order, DONE
// after all of a job's frames, fault cases fail closed, pace >= 2).  Changes vs ot_s81ph_col_core: a frame's words
// reach the merger through the credit loop, so a slot inside a frame can be a bubble (no word; the frame stays
// atomic); the fault bits travel on the sideband ahead of the FIFO, so a fault is known at the merger before any
// later DONE word of that lane (rule 4: no commit can pass an earlier fault).
// ---------------------------------------------------------------------------------------------------------------

// SRAM frame FIFO of the lane tile (redesign r2, colt_lane cd3337221: macro rd_out -> ot_fifo_sram_fwft ob write mux
// -4.3 ps, wp -> bypass -> ob -1.7 ps at 18 levels).  Rule 5: the macro output is registered AT the macro (rq_r), the
// head buffer is an OBD-entry shift register written from flops only, no bypass, and the read issue depends only on
// registered occupancy (never on this cycle's pop).  In-order, lossless while not overflowed; a push into a full array
// is dropped and latches ovf (fail closed).  Push -> head latency 4 cycles (fwft bypass: 1).
module ot_s81ph_colt_fifo #(
    parameter integer W     = 512,
    parameter integer DEPTH = 256,           // 256 (2 x ot_sram_1r1w_256x256_m2_r2c2)
    parameter integer RING = 0,
    parameter integer OBD   = 4
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          push,
    input  wire [W-1:0]  wdata,
    input  wire          pop,
    output wire          hv,
    output wire [W-1:0]  head,
    output reg           ovf
);
    // r4 (colt_lane c25065335-d: macro rd_out -> rq_r -25.7 ps at 511 ps SS clk->q): reads at II 2.  A read is issued
    // only every other cycle and its rd_out is captured TWO edges later (rq_r enabled by f2), so the macro output has
    // two periods (tiles/colt_lane_mcp.sdc: multicycle -setup 2 / -hold 1 through the macro rd_out pins; no read is
    // issued in between, so rd_out is stable over both).  0.5 word / cycle = the merger's PACE-2 drain rate.
    localparam integer AW = $clog2(DEPTH);
    localparam integer NT = (W + 255) / 256;
    localparam integer OW = $clog2(OBD + 1);
    reg  [AW:0]   wp, rp, cnt;
    reg           ne, f1, f2, f3, rph;
    reg  [OW-1:0] oc;
    wire          wr  = push && cnt != DEPTH;
    wire          rd  = ne && !rph && !f1 && ({1'b0, oc} + f2 + f3) < OBD - 1;
    wire [NT*256-1:0] rq;
    reg  [W-1:0]  rq_r;
    genvar t;
    generate for (t = 0; t < NT; t = t + 1) begin : g_m
        wire [255:0] wd = {{(NT*256-W){1'b0}}, wdata} >> (t * 256);
        ot_sram_1r1w_256x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(rd), .r_addr_in(rp[AW-1:0]), .rd_out(rq[t*256 +: 256]),
            .w_ce_in(wr), .w_addr_in(wp[AW-1:0]), .wd_in(wd), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    always @(posedge clk) if (f2) rq_r <= rq[W-1:0];
    reg  [W-1:0]  ob [0:OBD-1];
    wire          dpop = pop && oc != 0;
    wire [AW:0]   cnt_n = cnt + (wr ? 1'b1 : 1'b0) - (rd ? 1'b1 : 1'b0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            wp <= 0; rp <= 0; cnt <= 0; ne <= 1'b0; f1 <= 1'b0; f2 <= 1'b0; f3 <= 1'b0; rph <= 1'b0; oc <= 0; ovf <= 1'b0;
        end else begin
            if (wr) wp <= wp + 1'b1;
            if (rd) rp <= rp + 1'b1;
            cnt <= cnt_n; ne <= cnt_n != 0;
            f1 <= rd; f2 <= f1; f3 <= f2;
            rph <= rd;
            oc <= oc + (f3 ? 1'b1 : 1'b0) - (dpop ? 1'b1 : 1'b0);
            if (push && cnt == DEPTH) ovf <= 1'b1;
        end
    generate if (!RING) begin : g_shift
    integer e;
    always @(posedge clk)
        for (e = 0; e < OBD; e = e + 1) begin
            if (dpop) begin
                if (f3 && e == oc - 1) ob[e] <= rq_r;
                else if (e + 1 < OBD) ob[e] <= ob[(e + 1) % OBD];
            end else if (f3 && e == oc) ob[e] <= rq_r;
        end
    assign head = ob[0];
    end else begin : g_ring
        localparam integer PW = (OBD > 1) ? $clog2(OBD) : 1;
        reg [PW-1:0] hr, tr;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin hr <= 0; tr <= 0; end
            else begin
                if (dpop) hr <= (hr == OBD-1) ? 0 : hr + 1'b1;
                if (f3) tr <= (tr == OBD-1) ? 0 : tr + 1'b1;
            end
        always @(posedge clk) if (f3) begin
`ifdef OT_S81PH_COLT_MUT_RING
            ob[(tr + 1) % OBD] <= rq_r;
`else
            ob[tr] <= rq_r;
`endif
        end
        assign head = ob[hr];
    end endgenerate
    assign hv = oc != 0;
endmodule

module dsfd_colt_lane #(
    parameter integer DEPTH = 256,
`ifdef OT_S81PH_COLT_RING
    parameter integer RING = 1,
`else
    parameter integer RING = 0,
`endif
    parameter integer DM    = 8              // merger landing FIFO depth = initial credits
) (
    input  wire [0:0]   ck,
    input  wire [0:0]   rst,                 // die reset net (active low)
    input  wire [514:0] c_in,                // die lane {fault, live, data 512, valid}
    input  wire [0:0]   f_cr,                // credit return (one pulse per merger pop)
    output wire [512:0] t_w,                 // {data 512, valid}
    output wire [3:0]   t_f                  // sticky {svc fault frame, link, format, overflow}
);
    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // pin flops
    reg [514:0] w; reg cr;
    always @(posedge ck[0]) w <= c_in;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) cr <= 1'b0; else cr <= f_cr[0];
    wire         v   = w[0];
    wire [511:0] d   = w[512:1];
    wire [3:0]   typ = d[511:508];
    wire [11:0]  len = d[491:480];
    // ---- parser (ot_s81ph_col_in)
    reg          inf, drop, push, fc_inc, e_fmt, e_link, e_svc;
    reg  [11:0]  rem;
    reg  [511:0] pd;
    always @(posedge ck[0] or negedge rst_n) begin
        if (!rst_n) begin
            inf <= 1'b0; drop <= 1'b0; rem <= 12'd0; push <= 1'b0; fc_inc <= 1'b0;
            e_fmt <= 1'b0; e_link <= 1'b0; e_svc <= 1'b0;
        end else begin
            push <= 1'b0; fc_inc <= 1'b0; e_fmt <= 1'b0; e_svc <= 1'b0;
            e_link <= w[514] | (v & ~w[513]);
            if (v) begin
                if (inf) begin
                    push <= ~drop;
                    rem <= rem - 1'b1;
                    if (rem == 12'd1) begin inf <= 1'b0; fc_inc <= ~drop; drop <= 1'b0; end
                end else begin
                    case (typ)
                        4'd1, 4'd2, 4'd3, 4'd5: begin
                            if (typ == 4'd5) e_svc <= 1'b1;
                            if (len > DEPTH - 1) begin
                                e_fmt <= 1'b1; drop <= 1'b1; inf <= (len != 12'd0); rem <= len;
                            end else begin
                                push <= 1'b1; drop <= 1'b0;
                                if (len == 12'd0) fc_inc <= 1'b1;
                                else begin inf <= 1'b1; rem <= len; end
                            end
                        end
                        4'd4: begin
                            if (len != 12'd0) begin e_fmt <= 1'b1; drop <= 1'b1; inf <= 1'b1; rem <= len; end
                            else begin push <= 1'b1; fc_inc <= 1'b1; end
                        end
                        default: e_fmt <= 1'b1;
                    endcase
                end
            end
        end
    end
    always @(posedge ck[0]) pd <= d;
    wire hv, ovf; wire [511:0] head;
    reg  pop;
    ot_s81ph_colt_fifo #(.W(512), .DEPTH(DEPTH), .RING(RING)) u_q (.clk(ck[0]), .rst_n(rst_n), .push(push), .wdata(pd),
        .pop(pop), .hv(hv), .head(head), .ovf(ovf));
    // ---- frame sender: starts a frame only when it is complete in the FIFO, then sends its words under credits
    localparam integer FW = $clog2(DEPTH + 1);
    localparam integer CW = $clog2(DM + 1);
    reg  [FW-1:0] fc;
    reg  [CW-1:0] crd;
    reg           snd;              // inside a frame
    reg  [11:0]   srem;             // its data words still to send
    wire          fc_dec = !snd && pop && (head[491:480] == 12'd0) || snd && pop && (srem == 12'd1);
    always @(*) pop = hv && (crd != 0) && (snd || fc != 0);
    reg  [512:0]  ow;
    reg  [3:0]    flt;
    always @(posedge ck[0] or negedge rst_n) begin
        if (!rst_n) begin
            fc <= {FW{1'b0}}; crd <= DM[CW-1:0]; snd <= 1'b0; srem <= 12'd0; ow <= 513'd0; flt <= 4'd0;
        end else begin
            fc <= fc + (fc_inc ? 1'b1 : 1'b0) - (fc_dec ? 1'b1 : 1'b0);
            crd <= crd + (cr ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            if (pop) begin
                if (!snd) begin srem <= head[491:480]; snd <= head[491:480] != 12'd0; end
                else begin srem <= srem - 1'b1; if (srem == 12'd1) snd <= 1'b0; end
            end
            ow <= {head, pop};
            flt <= flt | {e_svc, e_link, e_fmt, ovf};
        end
    end
    assign t_w = ow;
    assign t_f = flt;
endmodule

module dsfd_colt_mrg #(
    parameter integer DM   = 8,
    parameter integer PACE = 2
) (
    input  wire [0:0]       ck,
    input  wire [0:0]       rst,
    input  wire [4*513-1:0] f_w,             // per lane {data, valid}: lane 0 SW, 1 SE, 2 NW, 3 NE
    input  wire [4*4-1:0]   f_f,             // per lane sticky fault sideband
    output wire [3:0]       t_cr,            // per lane credit return
    output wire [513:0]     vd,
    output wire [0:0]       vf
);
    localparam integer Q = 4;
    localparam integer CW = $clog2(DM + 1);
`ifndef SYNTHESIS
    initial if (PACE < 2) $fatal(1, "dsfd_colt_mrg: PACE must be >= 2 (registered merge decision)");
`endif
    reg [1:0] rst_s;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // pin flops
    reg [4*513-1:0] fw; reg [15:0] ff;
    always @(posedge ck[0]) fw <= f_w;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) ff <= 16'd0; else ff <= f_f;
    // ---- landing FIFOs (head at entry 0)
    reg  [511:0] lq [0:Q-1][0:DM-1];
    reg  [CW-1:0] lc [0:Q-1];
    reg  [Q-1:0] pop;
    wire [Q-1:0] hv;
    wire [512*Q-1:0] hd;
    integer l, e;
    genvar g;
    generate for (g = 0; g < Q; g = g + 1) begin : g_h
        assign hv[g] = lc[g] != 0;
        assign hd[512 * g +: 512] = lq[g][0];
    end endgenerate
    always @(posedge ck[0] or negedge rst_n)
        if (!rst_n) for (l = 0; l < Q; l = l + 1) lc[l] <= {CW{1'b0}};
        else for (l = 0; l < Q; l = l + 1) lc[l] <= lc[l] + (fw[513 * l] ? 1'b1 : 1'b0) - ((pop[l] && hv[l]) ? 1'b1 : 1'b0);
    always @(posedge ck[0])
        for (l = 0; l < Q; l = l + 1)
            for (e = 0; e < DM; e = e + 1) begin
                if (pop[l] && hv[l]) begin
                    if (fw[513 * l] && e == lc[l] - 1) lq[l][e] <= fw[513 * l + 1 +: 512];
                    else if (e + 1 < DM) lq[l][e] <= lq[l][(e + 1) % DM];
                end else if (fw[513 * l] && e == lc[l]) lq[l][e] <= fw[513 * l + 1 +: 512];
            end
    reg [Q-1:0] crq;
    always @(posedge ck[0] or negedge rst_n) if (!rst_n) crq <= {Q{1'b0}}; else crq <= pop & hv;
    assign t_cr = crq;

    wire [Q-1:0] hdone;
    wire [7:0]   htag [0:Q-1];
    generate for (g = 0; g < Q; g = g + 1) begin : g_t
        assign hdone[g] = hd[512 * g + 508 +: 4] == 4'd4;
        assign htag[g]  = hd[512 * g + 500 +: 8];
    end endgenerate
    // ---- merger (ot_s81ph_col_core on the landing heads: a head outside a frame is a complete frame's header)
    reg  [$clog2(PACE+1)-1:0] pc;
    wire          pre  = (pc == PACE - 1);
    wire          slot = (pc == 0);
    reg           busy;
    reg  [1:0]    cl;
    reg  [11:0]   rem;
    reg  [1:0]    rr;
    reg  [4:0]    flt, flt_rep;
    reg           halt;
    reg  [7:0]    ltag;
    localparam [2:0] D_NONE = 0, D_BEAT = 1, D_HDR = 2, D_DONE = 3, D_FAULT = 4, D_PAD = 5;
    reg  [2:0]    dec;
    reg  [1:0]    dl;
    wire [4:0]    flt_new = flt & ~flt_rep;
    reg           e_tag;
    reg  [1:0]    pk;
    reg           pk_ok;
    integer k;
    always @(*) begin
        pk = rr; pk_ok = 1'b0;
        for (k = Q; k >= 1; k = k - 1)
            if (hv[(rr + k) % Q] && !hdone[(rr + k) % Q]) begin
                pk = (rr + k) % Q; pk_ok = 1'b1;
            end
    end
    wire all_done = &(hv & hdone);
    wire tags_eq  = (htag[0] == htag[1]) && (htag[0] == htag[2]) && (htag[0] == htag[3]);
    wire [10:0] dcode = hd[0 +: 11] | hd[512 +: 11] | hd[1024 +: 11] | hd[1536 +: 11];
    wire [3:0] lf = ff[3:0] | ff[7:4] | ff[11:8] | ff[15:12];      // {svc, link, fmt, ovf}
    reg          ov;
    reg  [511:0] od;
    always @(*) begin
        pop = {Q{1'b0}};
        if (slot)
            case (dec)
                D_BEAT: if (hv[dl]) pop[dl] = 1'b1;
                D_HDR:  pop[dl] = 1'b1;
                D_DONE: pop = {Q{1'b1}};
                default: ;
            endcase
    end
    always @(posedge ck[0] or negedge rst_n) begin
        if (!rst_n) begin
            pc <= 0; busy <= 1'b0; cl <= 2'd0; rem <= 12'd0; rr <= 2'd3; flt <= 5'd0; flt_rep <= 5'd0;
            halt <= 1'b0; ltag <= 8'd0; dec <= D_NONE; dl <= 2'd0; e_tag <= 1'b0; ov <= 1'b0; od <= 512'd0;
        end else begin
            pc <= (pc == PACE - 1) ? 0 : pc + 1'b1;
            flt <= flt | {lf[3], lf[2], e_tag, lf[1], lf[0]};
            e_tag <= 1'b0;
            if (pre) begin
                dec <= D_NONE;
                if (busy) begin
`ifdef OT_S81PH_COLMUT1
                    if (!(|flt) && pk_ok && pk != cl) begin dec <= D_HDR; dl <= pk; end
                    else
`endif
                    begin dec <= (|flt && !hv[cl]) ? D_PAD : D_BEAT; dl <= cl; end
                end else if (|flt_new)
                    dec <= D_FAULT;
                else if (!halt && !(|flt)) begin
`ifdef OT_S81PH_COLMUT2
                    if (|(hv & hdone)) dec <= D_DONE;
`else
                    if (all_done) begin
                        if (tags_eq) dec <= D_DONE; else e_tag <= 1'b1;
                    end
`endif
                    else if (pk_ok) begin dec <= D_HDR; dl <= pk; end
                end
            end
            ov <= 1'b0;
            if (slot)
                case (dec)
                    D_BEAT, D_PAD: if (hv[dl] || dec == D_PAD) begin
                        ov <= 1'b1; od <= (dec == D_PAD) ? 512'd0 : hd[512 * dl +: 512];
                        rem <= rem - 1'b1;
                        if (rem == 12'd1) busy <= 1'b0;
                    end
                    D_HDR: begin
                        ov <= 1'b1; od <= hd[512 * dl +: 512];
                        rr <= dl; cl <= dl;
                        rem <= hd[512 * dl + 480 +: 12];
                        busy <= hd[512 * dl + 480 +: 12] != 12'd0;
                    end
                    D_DONE: begin
                        ov <= 1'b1; od <= {4'd4, htag[0], 484'd0, 5'd0, dcode};
                        ltag <= htag[0];
                    end
                    D_FAULT: begin
                        ov <= 1'b1; od <= {4'd5, ltag, 484'd0, flt, 11'd0};
                        flt_rep <= flt; halt <= 1'b1;
                    end
                    default: ;
                endcase
        end
    end
    reg [513:0] vd_q;
    always @(posedge ck[0]) vd_q <= {od, ov & rst_n, rst_n};
    assign vd = vd_q;
    ot_fwd_clk_inv u_vf (.a(ck[0]), .y(vf[0]));
endmodule

// composition reference (bench and die generator): lanes {NE, NW, SE, SW} as dsfd_bk_collector
module ot_s81ph_col_t #(
    parameter integer HOPS  = 5,             // station registers per direction between a lane tile and the merger
    parameter integer DEPTH = 256,
    parameter integer DM    = 8,
    parameter integer PACE  = 2
) (
    input  wire          ck, rst,
    input  wire [4*515-1:0] lanes,           // {NE, NW, SE, SW}
    output wire [513:0]  vd,
    output wire          vf
);
    localparam integer Q = 4;
    wire [Q*513-1:0] tw, fw;
    wire [Q*4-1:0]   tf, ff;
    wire [Q-1:0]     tcr, fcr;
    genvar g;
    generate for (g = 0; g < Q; g = g + 1) begin : g_l
        dsfd_colt_lane #(.DEPTH(DEPTH), .DM(DM)) u_l (.ck(ck), .rst(rst), .c_in(lanes[515 * g +: 515]), .f_cr(fcr[g]),
            .t_w(tw[513 * g +: 513]), .t_f(tf[4 * g +: 4]));
        // die stations (common clock), HOPS each way
        reg [512:0] sw [0:HOPS]; reg [3:0] sf [0:HOPS]; reg sc [0:HOPS];
        integer h;
        always @(*) begin sw[0] = tw[513 * g +: 513]; sf[0] = tf[4 * g +: 4]; sc[0] = tcr[g]; end
        always @(posedge ck) for (h = 1; h <= HOPS; h = h + 1) begin sw[h] <= sw[h-1]; sf[h] <= sf[h-1]; sc[h] <= sc[h-1]; end
        assign fw[513 * g +: 513] = sw[HOPS]; assign ff[4 * g +: 4] = sf[HOPS]; assign fcr[g] = sc[HOPS];
    end endgenerate
    dsfd_colt_mrg #(.DM(DM), .PACE(PACE)) u_m (.ck(ck), .rst(rst), .f_w(fw), .f_f(ff), .t_cr(tcr), .vd(vd), .vf(vf));
endmodule
