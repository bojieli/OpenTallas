`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Routed-expert fetch path of the V4.1 HBM comparator (W19 B2): the router's
// selected expert ids -> per-SM bulk-copy descriptors -> HBM reads -> each
// SM's SMEM staging ring, released to the SM's tensor core in stream order.
//
// LAYOUT (static, pre-swizzled at load time).  At TP-96 each die holds 1/96
// of every expert (w1 and w3: 24 rows x 5,120 FP4 + UE8M0 scales; w2: 53-54
// rows x 2,304).  The die's rows are assigned to its SMs; SM j's part of
// expert e (its w1 rows, then w3 rows, then w2 rows, codes + scales) is ONE
// contiguous run of cfg_lines[j] 128-B lines at
//     line  cfg_base + e * cfg_exp_lines + cfg_off[j]
// in the HBM stack nearest the SM (this block serves the NSM SMs homed on one
// stack), so one descriptor per (expert, SM) covers it.
//
// FLOW.
//   ids      one id a cycle (e_valid/e_ready), in the order the SMs consume
//            them (ascending id, the golden's expert order); the shared
//            expert is resident and never passes here;
//   descr    an id writes one descriptor into every SM's queue (DQ deep) the
//            cycle it is accepted (ot_gpu_bulk_copy's descriptor semantics);
//   issue    each SM walks its active descriptor like ot_gpu_bulk_copy: a
//            line is issued only against a free staging slot (the ring is the
//            run-ahead bound) and while fewer than MAX_OUT lines are in
//            flight.  The HBM request port takes one request a cycle, so the
//            SMs are served round robin and a grant carries up to RUN
//            consecutive lines of one SM (RUN x 128 B; RUN = 8 -> 1 KB, which
//            the 1.0 TB/s stack needs at 1.2 GHz: 833 B a cycle);
//   landing  the controller returns 32-B sectors on NPC pseudo-channel ports,
//            in any order across and (FR-FCFS) within pseudo-channels.  The
//            tag {SM, first slot} and the beat number give the sector's ring
//            slot and its quarter; each SM's ring is 8 line banks (slot mod 8:
//            the 8 lines of a 1-KB request sit on 8 pseudo-channels and land in
//            8 banks), each written with one sector a cycle, and an SM lands at
//            most LAND = 4 sectors (128 B, its ingest) a cycle, picked with a
//            rotating port priority; the other ports are held (rsp_rdy low);
//   release  a slot whose four sectors have landed is released in stream
//            order, one line a cycle (s_valid/s_ready), and freed.
// Tags with the top bit set are not this block's (background traffic).
// ---------------------------------------------------------------------------
module ot_hbm_accel_expert_fetch #(
    parameter integer ENABLE=0,
    parameter integer NSM     = 8,
    parameter integer NPC     = 32,
    parameter integer DEPTH   = 1024,     // staging lines a SM (128 KB)
    parameter integer MAX_OUT = 512,      // lines in flight a SM
    parameter integer RUN     = 8,        // lines a request (<= 2^(LENW-1) / 4)
    parameter integer DQ      = 64,
    parameter integer LAND    = 4,        // sectors landed a SM a cycle (128 B, the SM's ingest)
    parameter integer AW      = 24,       // sector address
    parameter integer LENW    = 6,
    parameter integer TAGW    = 16,
    parameter integer BEATW   = 5,
    parameter integer IW      = 9
) (
    input  wire                    clk,
    input  wire                    rst_n,
    // configuration (static)
    input  wire [AW-3:0]           cfg_base,        // lines
    input  wire [15:0]             cfg_exp_lines,
    input  wire [NSM*16-1:0]       cfg_off,
    input  wire [NSM*16-1:0]       cfg_lines,
    // expert ids
    input  wire                    e_valid,
    output wire                    e_ready,
    input  wire [IW-1:0]           e_id,
    // HBM controller
    output wire                    req_v,
    input  wire                    req_rdy,
    output wire [AW-1:0]           req_addr,
    output wire [LENW-1:0]         req_len,
    output wire [TAGW-1:0]         req_tag,
    input  wire [NPC-1:0]          rsp_v,
    output reg  [NPC-1:0]          rsp_rdy,
    input  wire [NPC*TAGW-1:0]     rsp_tag,
    input  wire [NPC*BEATW-1:0]    rsp_beat,
    input  wire [NPC*256-1:0]      rsp_data,
    // SM tensor-core streams
    output wire [NSM-1:0]          s_valid,
    input  wire [NSM-1:0]          s_ready,
    output wire [NSM*1024-1:0]     s_data,
    output wire                    idle
);
    generate if(!ENABLE)begin:baseline
      ot_gpu_expert_fetch #(.NSM(NSM),.NPC(NPC),.DEPTH(DEPTH),.MAX_OUT(MAX_OUT),.RUN(RUN),.DQ(DQ),.LAND(LAND),.AW(AW),.LENW(LENW),.TAGW(TAGW),.BEATW(BEATW),.IW(IW)) unchanged(.clk(clk),.rst_n(rst_n),.cfg_base(cfg_base),.cfg_exp_lines(cfg_exp_lines),.cfg_off(cfg_off),.cfg_lines(cfg_lines),.e_valid(e_valid),.e_ready(e_ready),.e_id(e_id),.req_v(req_v),.req_rdy(req_rdy),.req_addr(req_addr),.req_len(req_len),.req_tag(req_tag),.rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),.rsp_data(rsp_data),.s_valid(s_valid),.s_ready(s_ready),.s_data(s_data),.idle(idle));
    end else begin:selected
    localparam integer SW = $clog2(DEPTH);
    localparam integer MW = $clog2(NSM) > 0 ? $clog2(NSM) : 1;
    localparam integer QW = $clog2(DQ);
    localparam integer LA = AW - 2;
    // ---- per-SM descriptor queues ----
    reg [LA-1:0] q_base [0:NSM-1][0:DQ-1];
    reg [15:0]   q_len  [0:NSM-1][0:DQ-1];
    reg [QW:0]   q_cnt  [0:NSM-1];
    reg [QW-1:0] q_wp   [0:NSM-1], q_rp [0:NSM-1];
    reg          room;
    integer m;
    always @(*) begin
        room = 1'b1;
        for (m = 0; m < NSM; m = m + 1) if (q_cnt[m] >= DQ) room = 1'b0;
    end
    assign e_ready = room;
    wire e_go = e_valid && e_ready;
    // ---- per-SM active descriptor and ring pointers ----
    reg          act    [0:NSM-1];
    reg [LA-1:0] a_addr [0:NSM-1];
    reg [15:0]   a_left [0:NSM-1];
    reg [SW:0]   alloc_p [0:NSM-1], cons_p [0:NSM-1];
    reg [SW+2:0] in_sect [0:NSM-1];                 // sectors in flight (issued, not landed)
    reg [3:0]    mask [0:NSM-1][0:DEPTH-1];
    reg [255:0]  ring [0:NSM-1][0:3][0:DEPTH-1];
    // ---- grant: round robin over SMs with a line to issue ----
    reg [MW-1:0] rr;
    reg          g_v;
    reg [MW-1:0] g_sm;
    reg [15:0]   g_n;
    integer k, s2;
    reg [15:0] n_try, fr, ot;
    always @(*) begin
        g_v = 1'b0; g_sm = 0; g_n = 0;
        for (k = 0; k < NSM; k = k + 1) begin
            s2 = (rr + k) % NSM;
            fr = DEPTH - (alloc_p[s2] - cons_p[s2]);
            ot = MAX_OUT - (in_sect[s2] >> 2);
            n_try = a_left[s2];
            if (n_try > RUN) n_try = RUN;
            if(n_try > 32-(a_addr[s2]&31)) n_try=32-(a_addr[s2]&31);
            if (n_try > fr) n_try = fr;
            if (n_try > ot) n_try = ot;
            if (!g_v && act[s2] && n_try != 0) begin g_v = 1'b1; g_sm = s2; g_n = n_try; end
        end
    end
    assign req_v = g_v;
    assign req_addr = {a_addr[g_sm], 2'b00};
    assign req_len = g_n * 4;
    assign req_tag = {{(TAGW-MW-SW){1'b0}}, g_sm, alloc_p[g_sm][SW-1:0]};
    wire issue = req_v && req_rdy;
    // ---- landing: per SM, 8 line banks (slot mod 8), one sector a bank a cycle, at most LAND sectors a SM ----
    reg [$clog2(NPC)-1:0] prio;
    reg          l_v    [0:NSM-1][0:7];
    reg [SW-1:0] l_slot [0:NSM-1][0:7];
    reg [1:0]    l_q    [0:NSM-1][0:7];
    reg [255:0]  l_data [0:NSM-1][0:7];
    integer      l_n    [0:NSM-1];
    integer p, pp, qk;
    reg [TAGW-1:0] t;
    reg [BEATW-1:0] bt;
    reg [SW-1:0] sl;
    always @(*) begin
        rsp_rdy = {NPC{1'b0}};
        for (m = 0; m < NSM; m = m + 1) begin
            l_n[m] = 0;
            for (qk = 0; qk < 8; qk = qk + 1) begin
                l_v[m][qk] = 1'b0; l_slot[m][qk] = 0; l_q[m][qk] = 0; l_data[m][qk] = 256'd0;
            end
        end
        for (pp = 0; pp < NPC; pp = pp + 1) begin
            p = (prio + pp) % NPC;
            t = rsp_tag[p*TAGW +: TAGW];
            bt = rsp_beat[p*BEATW +: BEATW];
            if (rsp_v[p] && !t[TAGW-1]) begin
                m = t[SW +: MW];
                sl = t[SW-1:0] + (bt >> 2);
                qk = sl & 7;
                if (!l_v[m][qk] && l_n[m] < LAND) begin
                    l_v[m][qk] = 1'b1; l_slot[m][qk] = sl; l_q[m][qk] = bt[1:0];
                    l_data[m][qk] = rsp_data[p*256 +: 256];
                    l_n[m] = l_n[m] + 1;
                    rsp_rdy[p] = 1'b1;
                end
            end
        end
    end
    // ---- release ----
    genvar gs;
    wire [NSM-1:0] take;
        for (gs = 0; gs < NSM; gs = gs + 1) begin : g_out
            wire [SW-1:0] cs = cons_p[gs][SW-1:0];
            assign s_valid[gs] = &mask[gs][cs];
            assign s_data[gs*1024 +: 1024] = {ring[gs][3][cs], ring[gs][2][cs], ring[gs][1][cs], ring[gs][0][cs]};
            assign take[gs] = s_valid[gs] && s_ready[gs];
        end
    reg busy;
    always @(*) begin
        busy = 1'b0;
        for (m = 0; m < NSM; m = m + 1)
            if (act[m] || q_cnt[m] != 0 || alloc_p[m] != cons_p[m]) busy = 1'b1;
    end
    assign idle = !busy;
    // ---- state ----
    integer nl;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rr <= 0; prio <= 0;
            for (m = 0; m < NSM; m = m + 1) begin
                q_cnt[m] <= 0; q_wp[m] <= 0; q_rp[m] <= 0; act[m] <= 1'b0; a_addr[m] <= 0; a_left[m] <= 0;
                alloc_p[m] <= 0; cons_p[m] <= 0; in_sect[m] <= 0;
                for (k = 0; k < DEPTH; k = k + 1) mask[m][k] <= 4'd0;
            end
        end else begin
            prio <= prio + 1'b1;
            if (issue) rr <= (g_sm + 1) % NSM;
            for (m = 0; m < NSM; m = m + 1) begin
                // descriptor queue
                if (e_go && cfg_lines[m*16 +: 16] != 0) begin
                    q_base[m][q_wp[m]] <= cfg_base + e_id * cfg_exp_lines + cfg_off[m*16 +: 16];
                    q_len[m][q_wp[m]] <= cfg_lines[m*16 +: 16];
                    q_wp[m] <= q_wp[m] + 1'b1;
                end
                if (!act[m] && q_cnt[m] != 0) begin
                    act[m] <= 1'b1; a_addr[m] <= q_base[m][q_rp[m]]; a_left[m] <= q_len[m][q_rp[m]];
                    q_rp[m] <= q_rp[m] + 1'b1;
                end else if (issue && g_sm == m) begin
                    a_addr[m] <= a_addr[m] + g_n;
                    a_left[m] <= a_left[m] - g_n;
                    if (a_left[m] == g_n) act[m] <= 1'b0;
                end
                q_cnt[m] <= q_cnt[m] + ((e_go && cfg_lines[m*16 +: 16] != 0) ? 1 : 0)
                            - ((!act[m] && q_cnt[m] != 0) ? 1 : 0);
                if (issue && g_sm == m) alloc_p[m] <= alloc_p[m] + g_n;
                nl = 0;
                for (qk = 0; qk < 8; qk = qk + 1)
                    if (l_v[m][qk]) begin
                        ring[m][l_q[m][qk]][l_slot[m][qk]] <= l_data[m][qk];
                        mask[m][l_slot[m][qk]][l_q[m][qk]] <= 1'b1;
                        nl = nl + 1;
                    end
                in_sect[m] <= in_sect[m] + ((issue && g_sm == m) ? g_n * 4 : 0) - nl;
                if (take[m]) begin
                    cons_p[m] <= cons_p[m] + 1'b1;
                    mask[m][cons_p[m][SW-1:0]] <= 4'd0;
                end
            end
        end
    end
    end endgenerate
endmodule
