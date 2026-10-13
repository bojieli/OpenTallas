`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SM.MATVEC x plane, REAL JOIN (owner 10-13 redesign, step 5; spec el1013-hbm-redesign-smmv.log).  P = 1 (production).
//   ot_hgi_xp_load  : loader top, port-compatible with ot_hgi_sm_xload's BW8 use (x_* command side, xw_* out, the low 8
//                     lanes of wrq / wrq_cr / wrr).  Cursor (one wave an edge, wave order below) -> T1 ot_hgi_xp_rd ->
//                     T2 ot_hgi_xp_pack -> xw.  Command-pipelined: one command waits while the cursor runs another and
//                     earlier ones are still in the reader / pipe / buffers (>= 3 loads in flight); x_done in command
//                     order, XDD edges after the command's last beat left (the spine and the SM's own write stages).
//   ot_hgi_xp_pack  : T2, feed-forward, one wave an edge, no back-pressure inside: 2 x ot_hdc_actquant (UNCHANGED; it
//                     is a 13-stage feed-forward pipe, one block an edge) for block-dot, 64 x RNE to_bf16 (+ the "0 past
//                     K" mask) for BF16, then a ring of NBF 3 UNIT buffers (8,192 b each) and the beat emitter.
//   ot_hgi_xp_spine : T3, the registered x-write broadcast, one stage an SM pitch, SM s taps stage s.
// WAVE ORDER / UNITS (smh fragment layout, ot_hgi_sm_xload header):
//   block-dot (fmt 1 FP8 LA 4, fmt 2 FP4 LA 8): unit = tpair (g, tp) = fragment addresses (g, 2 tp), (g, 2 tp + 1);
//     wave j < LA = blocks b0 = (g LA + j) 8 + 2 tp and b0 + 1 (sectors 4 b0 .. 4 b0 + 7) -> lane j of the two
//     addresses; a unit emits 4 beats (address parity x beat 0 / 1).  Waves past K are not read (wave 0 of a unit
//     always is, as a NULL wave if empty, so every address of the op is written).
//   BF16 (fmt 0 / 3): unit = group g = addresses (g, 0 .. 7); wave w < 8 = sectors 64 g + 8 w .. + 7 = lanes 8 w .. 8 w
//     + 7, sector word t -> address (g, t).  A unit emits 8 beats: ONLY beat 1 of each address (BF16 lanes sit at
//     fragment bits 2,128 .. 3,151 = beat 1 bits 80 .. 1,103; beat 0 holds block-dot lanes only, which fmt 0 / 3 never
//     reads) -> one beat a wave, the SAME rate as block-dot, on the same 8 lanes.
// RATE PROOF (no stall after the reader's pop): a unit's LAST wave pops >= UB edges (4 block-dot, 8 BF16 = the unit's
//   beats) after the previous unit's (pace counter on the tag head; never binds on full units, which have >= UB
//   waves), the pipe is fixed-latency within a class, so completions are >= UB apart; a complete buffer is free <= UB + 1
//   edges after its completion (induction over the chained emitter) -> at most 2 complete + 1 filling = NBF 3.  An
//   overrun (a unit opening on a busy buffer) raises fault (fail closed).  A class change (block-dot <-> BF16, different
//   pipe depth) waits for the pipe to drain.
// Refusals (x_fault, sticky): A not VM, A.base not 8-SECTOR aligned (compiler obligation: lane = sector[2:0]), P != 1,
//   K = 0, block-dot K not a multiple of 32, a non-finite block-dot element, reader fault, buffer overrun.
// Mutants: MUT_WDROP (the 11th wave never reaches the pack stage), MUT_BEAT (the 37th beat never leaves: a beat 0, which carries
//          block-dot lanes 0 .. 7; the 38th was a beat 1, which an FP8 load (lanes 0 .. 3 only) never reads -> not killed),
//          MUT_LANE (block-dot waves land one lane off).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_xp_pack #(parameter integer NBF = 3, parameter integer TW = 25, parameter integer MUT_BEAT = 0, parameter integer MUT_LANE = 0) (
    input  wire              clk,
    input  wire              rst,
    input  wire              wave_v,
    input  wire [2047:0]     wave_d,
    input  wire [TW-1:0]     wave_t,      // {tp 2, ab 7, nel 7, jw 3, hi, lo, bf, lastc, last, first}
    output reg               xw_en,
    output reg  [6:0]        xw_addr,
    output reg  [6:0]        xw_grp,
    output reg  [2047:0]     xw_data,
    output reg               xw_eop,      // with xw_en: the command's last beat
    output wire              busy,        // a wave between the reader and the buffers
    output reg               fault
);
    localparam integer AQL = 13;
    function automatic [15:0] bf16(input [31:0] x);
        reg [31:0] r;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) bf16 = x[31:16] | 16'h0040;
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; bf16 = r[31:16]; end
        end
    endfunction
    function automatic [1:0] nx(input [1:0] b); nx = (b == 2'(NBF - 1)) ? 2'd0 : b + 2'd1; endfunction
    wire t_bf = wave_t[3], t_lo = wave_t[4], t_hi = wave_t[5];
    // ---- block-dot: two quantisers (lo = block t, hi = block t + 1), tags in a 13-deep shift (fixed latency)
    wire [1:0] qvo, qf; wire [255:0] qq [0:1]; wire signed [9:0] qe [0:1];
    ot_hdc_actquant u_aq0 (.clk(clk), .rst_n(!rst), .v(wave_v && !t_bf && t_lo), .fp4(1'b0), .x(wave_d[1023:0]), .vo(qvo[0]),
                           .q(qq[0]), .e(qe[0]), .y(), .fault(qf[0]));
    ot_hdc_actquant u_aq1 (.clk(clk), .rst_n(!rst), .v(wave_v && !t_bf && t_hi), .fp4(1'b0), .x(wave_d[2047:1024]), .vo(qvo[1]),
                           .q(qq[1]), .e(qe[1]), .y(), .fault(qf[1]));
    reg [AQL-1:0] tv; reg [TW-1:0] tt [0:AQL-1];
    // ---- BF16: one RNE stage (+ the element mask: 8 l + t < nel)
    reg b_v; reg [TW-1:0] b_t; reg [1023:0] b_d;
    // ---- merge, per-buffer write copy
    reg m_v, m_f; reg [TW-1:0] m_t; reg [1023:0] m_d;
    reg [NBF-1:0] w_v; reg [TW-1:0] w_t [0:NBF-1]; reg [1023:0] w_d [0:NBF-1]; reg [1:0] wb;
    // ---- buffers: st 0 free, 1 filling, 2 complete (waiting / emitting)
    reg [8191:0] fl [0:NBF-1]; reg [1:0] st [0:NBF-1]; reg [6:0] mab [0:NBF-1]; reg [1:0] mtp [0:NBF-1];
    reg [NBF-1:0] mbf, mlc;
    reg e_act; reg [1:0] eb; reg [2:0] ecnt;
    reg [2047:0] ob [0:NBF-1]; reg e1_v, e1_eop; reg [6:0] e1_addr, e1_grp;
    reg [15:0] nbeat;
    assign busy = wave_v || (|tv) || b_v || m_v || (|w_v);
    wire [2:0] elast = mbf[eb] ? 3'd7 : 3'd3;
    integer l, t, b, j;
    always @(posedge clk) begin
        // tag shift / BF16 convert
        tv <= {tv[AQL-2:0], wave_v && !t_bf};
        tt[0] <= wave_t;
        for (l = 1; l < AQL; l = l + 1) tt[l] <= tt[l-1];
        b_v <= wave_v && t_bf; b_t <= wave_t;
        for (l = 0; l < 8; l = l + 1) for (t = 0; t < 8; t = t + 1)
            b_d[t*128 + l*16 +: 16] <= ({1'b0, 3'(l), 3'(t)} < wave_t[15:9]) ? bf16(wave_d[l*256 + t*32 +: 32]) : 16'd0;
        // merge
        m_v <= tv[AQL-1] || b_v;
        m_t <= b_v ? b_t : tt[AQL-1];
        m_d <= b_v ? b_d : {492'd0, qe[1], qq[1], qe[0], qq[0]};
        m_f <= (tv[AQL-1] && b_v) || (tv[AQL-1] && (qvo != {tt[AQL-1][5], tt[AQL-1][4]} || (|qf))) || (!tv[AQL-1] && (|qvo));
        if (m_f) fault <= 1'b1;
        // write copies; the write pointer moves with the unit's last wave
        for (b = 0; b < NBF; b = b + 1) begin w_v[b] <= m_v && wb == 2'(b); w_t[b] <= m_t; w_d[b] <= m_d; end
        if (m_v && m_t[1]) wb <= nx(wb);
        // emission: the complete buffer at eb shifts its beats out (block-dot 2,048 b a beat, BF16 1,024 b at bit 80)
        e1_v <= 1'b0;
        for (b = 0; b < NBF; b = b + 1) ob[b] <= 2048'd0;
        if (e_act) begin
            e1_v <= 1'b1; e1_eop <= (ecnt == elast) && mlc[eb];
            e1_addr <= mbf[eb] ? mab[eb] + {4'd0, ecnt} : mab[eb] + {4'd0, mtp[eb], ecnt[1]};
            e1_grp <= mbf[eb] ? 7'd1 : {6'd0, ecnt[0]};
            for (b = 0; b < NBF; b = b + 1) if (eb == 2'(b)) begin
                ob[b] <= mbf[b] ? {944'd0, fl[b][1023:0], 80'd0} : fl[b][2047:0];
                fl[b] <= mbf[b] ? {1024'd0, fl[b][8191:1024]} : {2048'd0, fl[b][8191:2048]};
            end
            if (ecnt == elast) begin st[eb] <= 2'd0; eb <= nx(eb); ecnt <= 3'd0; e_act <= st[nx(eb)] == 2'd2; end
            else ecnt <= ecnt + 3'd1;
        end else if (st[eb] == 2'd2) begin e_act <= 1'b1; ecnt <= 3'd0; end
        // buffer write (a unit's first wave opens the buffer cleared)
        for (b = 0; b < NBF; b = b + 1) if (w_v[b]) begin
            if (w_t[b][0]) begin
                if (st[b] != 2'd0) fault <= 1'b1;
                mab[b] <= w_t[b][22:16]; mtp[b] <= w_t[b][24:23]; mbf[b] <= w_t[b][3]; mlc[b] <= 1'b0;
            end else if (st[b] != 2'd1) fault <= 1'b1;
            if (w_t[b][2]) mlc[b] <= 1'b1;
            st[b] <= w_t[b][1] ? 2'd2 : 2'd1;
            if (w_t[b][3]) begin
                for (j = 0; j < 8; j = j + 1) for (t = 0; t < 8; t = t + 1)
                    if (w_t[b][8:6] == 3'(j)) fl[b][t*1024 + j*128 +: 128] <= w_d[b][t*128 +: 128];
                    else if (w_t[b][0]) fl[b][t*1024 + j*128 +: 128] <= 128'd0;
            end else begin
                if (w_t[b][0]) fl[b] <= 8192'd0;
                for (j = 0; j < 8; j = j + 1) if ((w_t[b][8:6] ^ 3'(MUT_LANE != 0)) == 3'(j)) begin
                    if (w_t[b][4]) fl[b][266*j +: 266] <= w_d[b][265:0];
                    if (w_t[b][5]) fl[b][4096 + 266*j +: 266] <= w_d[b][531:266];
                end
            end
        end
        // xw pin flops
        xw_en <= e1_v && !(MUT_BEAT != 0 && nbeat == 16'd36); xw_addr <= e1_addr; xw_grp <= e1_grp; xw_eop <= e1_v && e1_eop;
        xw_data <= ob[0] | ob[1] | ob[2];
        if (e1_v) nbeat <= nbeat + 16'd1;
        if (rst) begin
            tv <= '0; b_v <= 1'b0; m_v <= 1'b0; m_f <= 1'b0; w_v <= '0; wb <= 2'd0; e_act <= 1'b0; eb <= 2'd0; ecnt <= 3'd0;
            e1_v <= 1'b0; xw_en <= 1'b0; xw_eop <= 1'b0; fault <= 1'b0; nbeat <= 16'd0; mbf <= '0; mlc <= '0;
            for (b = 0; b < NBF; b = b + 1) st[b] <= 2'd0;
        end
    end
endmodule

// T3: registered x-write broadcast.  Stage s drives SM s's x-write pins (one stage an SM pitch, <= 500 um a hop).
// PRE = relay stages between T2 and SM 0 (placement: the quadrant's VM slice is 7 - 17 mm from its SMs).
module ot_hgi_xp_spine #(parameter integer NS = 8, parameter integer PRE = 0) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 i_en,
    input  wire [6:0]           i_addr,
    input  wire [6:0]           i_grp,
    input  wire [2047:0]        i_data,
    output wire [NS-1:0]        o_en,
    output wire [NS*7-1:0]      o_addr,
    output wire [NS*7-1:0]      o_grp,
    output wire [NS*2048-1:0]   o_data
);
    genvar s;
    wire p_en; wire [6:0] p_addr, p_grp; wire [2047:0] p_data;
    generate if (PRE == 0) begin : g_np
        assign p_en = i_en; assign p_addr = i_addr; assign p_grp = i_grp; assign p_data = i_data;
    end else begin : g_pre
        reg [PRE-1:0] ren; reg [6:0] rad [0:PRE-1], rgr [0:PRE-1]; reg [2047:0] rda [0:PRE-1];
        integer k;
        always @(posedge clk) begin
            ren[0] <= i_en && !rst; rad[0] <= i_addr; rgr[0] <= i_grp; rda[0] <= i_data;
            for (k = 1; k < PRE; k = k + 1) begin ren[k] <= ren[k-1] && !rst; rad[k] <= rad[k-1]; rgr[k] <= rgr[k-1]; rda[k] <= rda[k-1]; end
        end
        assign p_en = ren[PRE-1]; assign p_addr = rad[PRE-1]; assign p_grp = rgr[PRE-1]; assign p_data = rda[PRE-1];
    end endgenerate
    generate for (s = 0; s < NS; s = s + 1) begin : g_s
        (* keep = 1 *) reg en; (* keep = 1 *) reg [6:0] ad, gr; (* keep = 1 *) reg [2047:0] da;
        if (s == 0) begin : g_first
            always @(posedge clk) begin en <= p_en && !rst; ad <= p_addr; gr <= p_grp; da <= p_data; end
        end else begin : g_next
            always @(posedge clk) begin en <= g_s[s-1].en && !rst; ad <= g_s[s-1].ad; gr <= g_s[s-1].gr; da <= g_s[s-1].da; end
        end
        assign o_en[s] = en; assign o_addr[s*7 +: 7] = ad; assign o_grp[s*7 +: 7] = gr; assign o_data[s*2048 +: 2048] = da;
    end endgenerate
endmodule

module ot_hgi_xp_load #(
    parameter integer NXC = 4,            // port compatibility only (the packet clients are not used: vmq = 0)
    parameter integer CR = 16,            // landing credits a lane
    parameter integer RQC = 10,           // lane request credits (B2 bank request queue: 10 entries)
    parameter integer XDD = 12,           // x_done after the last beat left: spine stages (8) + the SM's write stages (3) + 1
    parameter integer MUT_WDROP = 0,
    parameter integer MUT_BEAT = 0,
    parameter integer MUT_LANE = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               x_v,
    output wire               x_rdy,
    input  wire [39:0]        x_base,
    input  wire [20:0]        x_n,
    input  wire [3:0]         x_p,
    input  wire [31:0]        x_stride,
    input  wire [1:0]         x_space,
    input  wire [1:0]         x_fmt,
    input  wire [6:0]         x_xb,
    output reg                x_done,
    output reg                x_fault,
    output wire               xw_en,
    output wire [6:0]         xw_addr,
    output wire [6:0]         xw_grp,
    output wire [2047:0]      xw_data,
    output wire [NXC*338-1:0] vmq,
    input  wire [NXC*274-1:0] vmr,
    output wire               rg_req,
    input  wire               rg_gnt,
    output wire [32*16-1:0]   wrq,
    input  wire [31:0]        wrq_cr,
    input  wire [32*257-1:0]  wrr
);
    localparam integer TW = 25, TD = 32;
    reg rst; always @(posedge clk) rst <= !rst_n;
    assign vmq = '0; assign rg_req = 1'b0;
    // ---- command register (decoded on the way in)
    reg q_v, q_bf; reg [3:0] q_la; reg [15:0] q_nbk; reg [17:0] q_nsk; reg [20:0] q_k; reg [7:0] q_gn; reg [14:0] q_bs; reg [6:0] q_ab;
    assign x_rdy = !q_v;
    wire i_bd = x_fmt == 2'd1 || x_fmt == 2'd2;
    wire i_bad = x_space != 2'd1 || (|x_base[5:0]) || x_p != 4'd1 || x_n == 21'd0 || (i_bd && (|x_n[4:0]));
    // ---- cursor
    reg c_act, c_bf, c_cls_v, c_cls; reg [3:0] c_la; reg [15:0] c_nbk; reg [17:0] c_nsk; reg [20:0] c_k; reg [7:0] c_gn, c_g;
    reg [14:0] c_bs; reg [6:0] c_ab; reg [1:0] c_tp; reg [3:0] c_j; reg [12:0] c_gj, c_g0;
    // ---- tag FIFO (cursor -> pop)
    reg [TW-1:0] tq [0:TD-1]; reg [4:0] tqh, tqt; reg [5:0] tqn;
    wire [TW-1:0] th = tq[tqh];
    reg [2:0] pace; reg [TW-1:0] t_r; reg [15:0] nwave;
    wire rd_rdy, rd_fault, wave_v, wave_pop, pk_busy, pk_fault, pk_en, pk_eop; wire [2047:0] wave_d;
    wire [7:0] rq_v; wire [7:0][14:0] rq_sec; wire [7:0] rs_v; wire [7:0][255:0] rs_d;
    // block-dot step
    wire [15:0] b0 = {c_gj, 3'd0} + {13'd0, c_tp, 1'b0};
    wire d_lo = b0 < c_nbk, d_hi = (b0 + 16'd1) < c_nbk;
    wire d_lastu = (c_j == c_la - 4'd1) || ((b0 + 16'd8) >= c_nbk);
    // BF16 step
    wire [17:0] s0 = {4'd0, c_g, 6'd0} + {11'd0, c_j, 3'd0};
    wire f_val = s0 < c_nsk; wire [17:0] f_rem = c_nsk - s0; wire [20:0] f_kel = c_k - {s0, 3'd0};
    wire f_lastu = (c_j == 4'd7) || ((s0 + 18'd8) >= c_nsk);
    wire lastu = c_bf ? f_lastu : d_lastu;
    wire lastg = c_g == c_gn - 8'd1;
    wire lastc = lastu && lastg && (c_bf || c_tp == 2'd3);
    wire [3:0] nsec = c_bf ? (!f_val ? 4'd0 : (f_rem >= 18'd8) ? 4'd8 : f_rem[3:0]) : (d_hi ? 4'd8 : d_lo ? 4'd4 : 4'd0);
    wire [6:0] nel = !f_val ? 7'd0 : (f_kel >= 21'd64) ? 7'd64 : f_kel[6:0];
    wire [14:0] sec = c_bs + (c_bf ? s0[14:0] : {b0[12:0], 2'd0});
    wire step = c_act && rd_rdy && tqn < 6'(TD - 1);
    wire [TW-1:0] tag = {c_tp, c_ab, c_bf ? nel : 7'd0, c_j[2:0], !c_bf && d_hi, !c_bf && d_lo, c_bf, lastc, lastu, c_j == 4'd0};
    // a class change waits for the pipe to drain (block-dot and BF16 have different pipe depths)
    wire drained = tqn == 6'd0 && !wave_v && !pk_busy;
    wire c_load = q_v && !c_act && (!c_cls_v || c_cls == q_bf || drained);
    wire wave_rdy = !(th[1] && pace != 3'd0);
    ot_hgi_xp_rd #(.CR(CR), .XQ(4), .RQC(RQC)) u_rd (.clk(clk), .rst(rst), .cmd_v(step), .cmd_rdy(rd_rdy), .cmd_sec(sec),
        .cmd_nsec({7'd0, nsec}), .cmd_id(4'd0), .rq_v(rq_v), .rq_sec(rq_sec), .rs_v(rs_v), .rs_d(rs_d), .rq_cr(wrq_cr[7:0]),
        .wave_rdy(wave_rdy), .wave_pop(wave_pop), .wave_v(wave_v), .wave_d(wave_d), .wave_n(), .wave_last(), .wave_id(),
        .wave_idx(), .fault(rd_fault));
    genvar ln;
    generate for (ln = 0; ln < 32; ln = ln + 1) begin : g_ln
        if (ln < 8) begin : g_u
            assign wrq[ln*16 +: 16] = {rq_v[ln], rq_sec[ln]};
            assign rs_v[ln] = wrr[ln*257 + 256]; assign rs_d[ln] = wrr[ln*257 +: 256];
        end else begin : g_z
            assign wrq[ln*16 +: 16] = 16'd0;
        end
    end endgenerate
    wire pk_wave_v = wave_v && !(MUT_WDROP != 0 && nwave == 16'd10);
    ot_hgi_xp_pack #(.TW(TW), .MUT_BEAT(MUT_BEAT), .MUT_LANE(MUT_LANE)) u_pk (.clk(clk), .rst(rst), .wave_v(pk_wave_v), .wave_d(wave_d),
        .wave_t(t_r), .xw_en(pk_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .xw_eop(pk_eop), .busy(pk_busy),
        .fault(pk_fault));
    assign xw_en = pk_en;
    reg [XDD-1:0] dd;
    always @(posedge clk) begin
        x_done <= dd[XDD-1]; dd <= {dd[XDD-2:0], pk_eop};
        if (rd_fault || pk_fault) x_fault <= 1'b1;
        if (x_v && x_rdy) begin
            if (i_bad) x_fault <= 1'b1;
            else begin
                q_v <= 1'b1; q_bf <= !i_bd; q_la <= (x_fmt == 2'd1) ? 4'd4 : 4'd8; q_nbk <= x_n[20:5]; q_k <= x_n;
                q_nsk <= 18'((x_n + 21'd7) >> 3); q_bs <= x_base[17:3]; q_ab <= x_xb;
                q_gn <= !i_bd ? 8'((x_n + 21'd511) >> 9) : (x_fmt == 2'd1) ? 8'(({5'd0, x_n[20:5]} + 21'd31) >> 5)
                                                                            : 8'(({5'd0, x_n[20:5]} + 21'd63) >> 6);
            end
        end
        if (c_load) begin
            q_v <= 1'b0; c_act <= 1'b1; c_bf <= q_bf; c_cls_v <= 1'b1; c_cls <= q_bf; c_la <= q_la; c_nbk <= q_nbk; c_nsk <= q_nsk;
            c_k <= q_k; c_gn <= q_gn; c_bs <= q_bs; c_ab <= q_ab; c_g <= 8'd0; c_tp <= 2'd0; c_j <= 4'd0; c_gj <= 13'd0; c_g0 <= 13'd0;
        end
        if (step) begin
            tq[tqt] <= tag; tqt <= tqt + 5'd1;
            if (!lastu) begin c_j <= c_j + 4'd1; c_gj <= c_gj + 13'd1; end
            else begin
                c_j <= 4'd0;
                if (c_bf || c_tp == 2'd3) begin
                    c_tp <= 2'd0; c_g <= c_g + 8'd1; c_ab <= c_ab + 7'd8; c_g0 <= c_g0 + {9'd0, c_la}; c_gj <= c_g0 + {9'd0, c_la};
                    if (lastg) c_act <= 1'b0;
                end else begin c_tp <= c_tp + 2'd1; c_gj <= c_g0; end
            end
        end
        tqn <= tqn + {5'd0, step} - {5'd0, wave_pop};
        if (wave_pop) begin
            tqh <= tqh + 5'd1; t_r <= th;
            if (th[1]) pace <= th[3] ? 3'd7 : 3'd3;
        end
        if (pace != 3'd0 && !(wave_pop && th[1])) pace <= pace - 3'd1;
        if (wave_v) nwave <= nwave + 16'd1;
        if (rst) begin
            q_v <= 1'b0; c_act <= 1'b0; c_cls_v <= 1'b0; tqh <= 5'd0; tqt <= 5'd0; tqn <= 6'd0; pace <= 3'd0; nwave <= 16'd0;
            x_done <= 1'b0; dd <= '0;
        end
        if (!rst_n) x_fault <= 1'b0;
    end
endmodule
`default_nettype wire
