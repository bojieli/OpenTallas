`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Stack endpoint of the PIPELINED local K arbitration
// (ot_chip_v41x_hbm_karb_pipe).
//   request   two-entry ingress queue (k_rdy = its registered room); the head,
//             steered by the monolithic arbiter's pc_of, is dispatched into a
//             register (d_*: payload broadcast, one valid per region) when the
//             endpoint holds a credit of its slice's KQ-entry queue; credits
//             return per PC (kcr, after the trunk's pipeline).  In order: the
//             head waits for its credit.
//   response  one EPCS[g]-entry queue per region, filled from the trunk (regions
//             hold its credits); the consumer sees the lowest-index non-empty
//             queue; each pop returns a credit through a register (s_cr).
//             MERGE2=1 (W18b, 2026-09-30): the eight regions' queues span the
//             750 um block, and one-cycle lowest-index selection across all of
//             them (region counters -> select -> pop -> counters) is -407 ps at
//             SS.  Each half (regions 0-3, 4-7) selects locally into a two-entry
//             registered queue (ot_chip_v41x_karb_q2: registered room, so no
//             ready crosses it), and the root picks the lower half first.  One
//             added cycle on the response path; credits still return on the
//             region pop.
//             HEADREG=1 (with MERGE2): each region queue drains into its own
//             two-entry registered queue first, so the half select reads a
//             2:1 head mux instead of the region queue's DEPTH:1 read mux
//             (rp -> 18:1 x 276 -> 4:1 -> half queue was -212 ps at SS).  A
//             second added response cycle; credits still return when an entry
//             leaves the (credited) region queue.
//   events    registered OR of the regions' K write completions, K grants at
//             ingress, B grant / conflict counts accumulated.
// ---------------------------------------------------------------------------
module ot_chip_v41x_karb_proot #(
    parameter integer NPC   = 32,
    parameter integer AW    = 28,
    parameter integer TAGW  = 16,
    parameter integer LENW  = 4,
    parameter integer BEATW = 4,
    parameter integer DW    = 256,
    parameter integer KQ    = 4,
    parameter integer NREG  = NPC / 4,
    // per-region response queue depth (= the region's credits), 8 bits a region, region 0 in [7:0]
    parameter [8*NREG-1:0] EPCS = {NREG{8'd4}},
    parameter bit     MERGE2 = 1'b1,
    parameter bit     HEADREG = 1'b1,
    // ingress queue pointer copies (ot_chip_v41x_karb_q2r): one per ~43 payload bits
    parameter integer IQREP = 8,
    parameter bit     DLOAD_ON_VALID = 1'b1
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  k_v,
    output wire                  k_rdy,
    input  wire [AW-1:0]         k_addr,
    input  wire [LENW-1:0]       k_len,
    input  wire [TAGW-1:0]       k_tag,
    input  wire                  k_we,
    input  wire [DW-1:0]         k_wdata,
    input  wire [DW/8-1:0]       k_wstrb,
    output reg                   k_wr_done,
    output wire                  k_rsp_v,
    input  wire                  k_rsp_rdy,
    output wire [TAGW-1:0]       k_rsp_tag,
    output wire [BEATW-1:0]      k_rsp_beat,
    output wire [DW-1:0]         k_rsp_data,
    // dispatch register (to the trunks)
    output reg  [NREG-1:0]       d_v,
    output reg  [1:0]            d_lpc,
    output reg  [AW-1:0]         d_addr,
    output reg  [LENW-1:0]       d_len,
    output reg  [TAGW-1:0]       d_tag,
    output reg                   d_we,
    output reg  [DW-1:0]         d_wdata,
    output reg  [DW/8-1:0]       d_wstrb,
    input  wire [NPC-1:0]        kcr,
    // responses (from the trunks)
    input  wire [NREG-1:0]       s_v,
    input  wire [NREG*(TAGW+BEATW+DW)-1:0] s_d,
    output reg  [NREG-1:0]       s_cr,
    input  wire [NREG-1:0]       r_kwd,
    input  wire [NREG*3-1:0]     r_bg,
    input  wire [NREG*3-1:0]     r_ct,
    output wire [31:0]           k_grants,
    output wire [31:0]           b_grants,
    output wire [31:0]           contended
);
    localparam integer LPC  = $clog2(NPC);
    localparam integer LREG = (NREG > 1) ? $clog2(NREG) : 1;
    localparam integer PW   = AW + LENW + TAGW + 1 + DW + DW / 8;
    localparam integer RW   = TAGW + BEATW + DW;
    localparam integer CW   = $clog2(KQ + 1);
    function automatic [LPC-1:0] pc_of(input [AW-1:0] s);
        pc_of = LPC'(((s >> 2) ^ (s >> (2 + LPC)) ^ (s >> (2 + 2 * LPC))) & (NPC - 1));
    endfunction
    wire           iq_v; wire [LPC+PW-1:0] iq_d;
    wire [LPC-1:0] iq_pc = iq_d[LPC+PW-1 -: LPC];
    reg  [CW-1:0]  cred [0:NPC-1];
    wire           disp = iq_v && cred[iq_pc] != 0;
    ot_chip_v41x_karb_q2r #(.W(LPC + PW), .NREP(IQREP)) u_iq (
        .clk(clk), .rst_n(rst_n), .in_v(k_v), .in_rdy(k_rdy),
        .in_d({pc_of(k_addr), k_addr, k_len, k_tag, k_we, k_wdata, k_wstrb}),
        .out_v(iq_v), .out_rdy(disp), .out_d(iq_d));
    integer i;
    // W18b: the dispatch payload register loads the queue head whenever the queue holds one (enable = iq_v, a
    // flop compare), not on disp: d_* is only read while d_v is high, which is exactly the cycle after a disp, and
    // then it holds the dispatched entry.  The 344-bit load no longer waits for the credit lookup (iq_pc -> cred
    // 32:1 -> disp), which with the enable fan-out was the SS-critical path (-179 ps).
    always @(posedge clk) if (DLOAD_ON_VALID ? iq_v : disp) begin
        d_lpc <= iq_pc[1:0];
        {d_addr, d_len, d_tag, d_we, d_wdata, d_wstrb} <= iq_d[PW-1:0];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            d_v <= '0;
            for (i = 0; i < NPC; i = i + 1) cred[i] <= CW'(KQ);
        end else begin
            for (i = 0; i < NREG; i = i + 1) d_v[i] <= disp && (NREG == 1 || (iq_pc >> 2) == i);
            for (i = 0; i < NPC; i = i + 1)
                cred[i] <= cred[i] - CW'(disp && iq_pc == i) + CW'(kcr[i]);
        end
    // responses
    wire [NREG-1:0]    q_v, q_rdy;
    wire [NREG*RW-1:0] q_d;
    wire [NREG-1:0] pop;
    wire [NREG-1:0]    r_v, r_rdy;           // region queue outputs (before the optional head register)
    wire [NREG*RW-1:0] r_d;
    genvar g;
    generate for (g = 0; g < NREG; g = g + 1) begin : g_q
        ot_chip_v41x_karb_qn #(.W(RW), .DEPTH(EPCS[g*8 +: 8])) u_q (
            .clk(clk), .rst_n(rst_n), .in_v(s_v[g]), .in_rdy(q_rdy[g]), .in_d(s_d[g*RW +: RW]),
            .out_v(r_v[g]), .out_rdy(r_rdy[g]), .out_d(r_d[g*RW +: RW]));
        if (MERGE2 && HEADREG) begin : g_hr
            ot_chip_v41x_karb_q2 #(.W(RW)) u_hr (
                .clk(clk), .rst_n(rst_n), .in_v(r_v[g]), .in_rdy(r_rdy[g]), .in_d(r_d[g*RW +: RW]),
                .out_v(q_v[g]), .out_rdy(pop[g]), .out_d(q_d[g*RW +: RW]));
        end else begin : g_nohr
            assign q_v[g] = r_v[g];
            assign r_rdy[g] = pop[g];
            assign q_d[g*RW +: RW] = r_d[g*RW +: RW];
        end
`ifndef SYNTHESIS
        always @(posedge clk) if (rst_n && s_v[g] && !q_rdy[g])
            $error("ot_chip_v41x_karb_proot: region %0d sent without a credit", g);
`endif
    end endgenerate
    if (MERGE2 && NREG >= 2 && NREG % 2 == 0) begin : g_m2
        localparam integer NH = NREG / 2;
        localparam integer LH = (NH > 1) ? $clog2(NH) : 1;
        wire [1:0]    h_v, h_rdy;
        wire [2*RW-1:0] h_d;
        reg  [LH-1:0] hsel [0:1];
        reg  [1:0]    hany;
        integer j;
        always @(*) begin
            for (j = 0; j < 2; j = j + 1) begin hsel[j] = '0; hany[j] = 1'b0; end
            for (j = NH - 1; j >= 0; j = j - 1) begin
                if (q_v[j])      begin hsel[0] = LH'(j); hany[0] = 1'b1; end
                if (q_v[NH + j]) begin hsel[1] = LH'(j); hany[1] = 1'b1; end
            end
        end
        for (g = 0; g < NREG; g = g + 1) begin : g_pop
            assign pop[g] = (g < NH) ? (hany[0] && h_rdy[0] && hsel[0] == LH'(g))
                                     : (hany[1] && h_rdy[1] && hsel[1] == LH'(g - NH));
        end
        wire [1:0] h_pop;
        assign h_pop[0] = h_v[0] && k_rsp_rdy;
        assign h_pop[1] = !h_v[0] && h_v[1] && k_rsp_rdy;
        for (g = 0; g < 2; g = g + 1) begin : g_h
            ot_chip_v41x_karb_q2 #(.W(RW)) u_h (
                .clk(clk), .rst_n(rst_n), .in_v(hany[g]), .in_rdy(h_rdy[g]),
                .in_d(q_d[(g * NH + hsel[g]) * RW +: RW]),
                .out_v(h_v[g]), .out_rdy(h_pop[g]), .out_d(h_d[g*RW +: RW]));
        end
        assign k_rsp_v = |h_v;
        assign {k_rsp_tag, k_rsp_beat, k_rsp_data} = h_v[0] ? h_d[0 +: RW] : h_d[RW +: RW];
    end else begin : g_m1
        reg  [LREG-1:0]    esel; reg eany;
        always @(*) begin
            esel = '0; eany = 1'b0;
            for (i = NREG - 1; i >= 0; i = i - 1) if (q_v[i]) begin esel = LREG'(i); eany = 1'b1; end
        end
        for (g = 0; g < NREG; g = g + 1) begin : g_pop
            assign pop[g] = eany && k_rsp_rdy && esel == g;
        end
        assign k_rsp_v = eany;
        assign {k_rsp_tag, k_rsp_beat, k_rsp_data} = q_d[esel*RW +: RW];
    end
    reg [LPC+2:0] bsum, csum;
    always @(*) begin
        bsum = '0; csum = '0;
        for (i = 0; i < NREG; i = i + 1) begin
            bsum = bsum + (LPC+3)'(r_bg[i*3 +: 3]);
            csum = csum + (LPC+3)'(r_ct[i*3 +: 3]);
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            s_cr <= '0; k_wr_done <= 1'b0;
        end else begin
            s_cr <= r_v & r_rdy;
            k_wr_done <= |r_kwd;

        end
    // statistics counters: split 16+16 with a registered carry (one cycle late, exact)
    ot_chip_v41x_stat_ctr32 #(.IW(1))       u_kg (.clk(clk), .rst_n(rst_n), .inc(k_v && k_rdy), .q(k_grants));
    ot_chip_v41x_stat_ctr32 #(.IW(LPC + 3)) u_bg (.clk(clk), .rst_n(rst_n), .inc(bsum), .q(b_grants));
    ot_chip_v41x_stat_ctr32 #(.IW(LPC + 3)) u_ct (.clk(clk), .rst_n(rst_n), .inc(csum), .q(contended));
endmodule
