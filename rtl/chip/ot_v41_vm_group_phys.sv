`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One LANE GROUP of VM-H as built (the physical tile behind ot_v41_vm_dist_group's behavioural banks;
// results/floorplan/v41_vm_dist_spec.json, results/uarch/w11_vm_options.json option H_rtl).
//
// Storage: NB banks x RC read replicas of ot_sram_1r1w_256x256_m2_r2c2 (256 rows of 8 32-bit words).  The
// group's local word w lives in bank w[3], row w >> 4, column w[2:0]: 8 consecutive local words -- the 8 lanes
// of a unit-stride vector, local or rotated (option H's L and R classes) -- are at most one row of each bank.
//
// Reads, per class c (A, B, C, D, G, X): rd_v[c] with one row address per bank, and per lane of the group a
// {bank, column} select.  The macros read at the edge; the selected words (rd_q) follow combinationally from
// the macros' outputs in the next cycle -- the one-cycle read of the list interface.  A read sees every write
// accepted in an earlier cycle: the rows waiting in the bank's write queue are forwarded (newest wins).
//
// Writes, per bank: up to K masked row writes a cycle (distinct rows; the group's lanes, its return root and
// the trees, merged by row upstream).  They enter the bank's WQD-row queue -- a write to a row already queued
// merges into it -- and the macros (all RC replicas: one row of state) take the oldest row every cycle.
// wq_occ reports the deepest the queue got; `fault` rises if a write finds the queue full.
// ---------------------------------------------------------------------------
module ot_v41_vm_group_phys #(
    parameter integer RC  = 6,
    parameter integer NB  = 2,
    parameter integer RA  = 8,              // row address bits (256 rows)
    parameter integer K   = 2,              // row writes a bank a cycle
    parameter integer WQD = 8               // write-queue rows a bank
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [RC-1:0]        rd_v,
    input  wire [RC*NB*RA-1:0]  rd_row,
    input  wire [RC*8*4-1:0]    rd_sel,     // per class, per lane: {bank (bit 3), column [2:0]}
    output reg  [RC*8*32-1:0]   rd_q,
    input  wire [NB*K-1:0]      wr_v,
    input  wire [NB*K*RA-1:0]   wr_row,
    input  wire [NB*K*256-1:0]  wr_d,
    input  wire [NB*K*8-1:0]    wr_m,
    output reg  [7:0]           wq_occ,
    output reg                  fault
);
    genvar b, c;
    wire [NB-1:0]          m_we;
    wire [NB*RA-1:0]       m_wrow;
    wire [NB*256-1:0]      m_wd;
    wire [NB*256-1:0]      m_wmask;
    wire [NB*WQD-1:0]      q_v;
    wire [NB*WQD*RA-1:0]   q_row;
    wire [NB*WQD*256-1:0]  q_d;
    wire [NB*WQD*8-1:0]    q_m;
    wire [NB-1:0]          q_ovf;
    wire [NB*8-1:0]        q_cnt;
    // ---- write queues --------------------------------------------------------------------------------------
    generate for (b = 0; b < NB; b = b + 1) begin : g_wq
        reg              v   [0:WQD-1];
        reg [RA-1:0]     row [0:WQD-1];
        reg [255:0]      d   [0:WQD-1];
        reg [7:0]        m   [0:WQD-1];
        // the macros take entry 0 at every edge it is valid
        assign m_we[b] = v[0];
        assign m_wrow[b*RA +: RA] = row[0];
        assign m_wd[b*256 +: 256] = d[0];
        genvar e;
        for (e = 0; e < 8; e = e + 1) begin : g_m
            assign m_wmask[b*256 + 32*e +: 32] = {32{m[0][e]}};
        end
        // next state: pop entry 0, then each incoming write merges into the entry holding its row or takes the
        // next free entry.  The K writes of a cycle name distinct rows (the caller merges by row), so a write's
        // target does not depend on the others' data: all targets are one-hot and resolved in parallel.
        wire [WQD-1:0]  pv;                      // entries after the pop
        wire [RA-1:0]   prow [0:WQD-1];
        wire [255:0]    pd   [0:WQD-1];
        wire [7:0]      pm   [0:WQD-1];
        for (e = 0; e < WQD; e = e + 1) begin : g_pop
            if (e < WQD - 1) begin : g_s
                assign pv[e] = v[e+1]; assign prow[e] = row[e+1]; assign pd[e] = d[e+1]; assign pm[e] = m[e+1];
            end else begin : g_z
                assign pv[e] = 1'b0; assign prow[e] = {RA{1'b0}}; assign pd[e] = 256'd0; assign pm[e] = 8'd0;
            end
        end
        // occupancy after the pop (entries are contiguous from 0)
        reg [7:0] pc;
        integer j;
        always @(*) begin
            pc = 0;
            for (j = 0; j < WQD; j = j + 1) pc = pc + (pv[j] ? 8'd1 : 8'd0);
        end
        // per write: hit vector, and its allocation rank among the writes that miss
        reg [WQD-1:0] tgt [0:K-1];
        reg [7:0]     rank;
        reg           ovf;
        integer s2;
        always @(*) begin
            rank = 0; ovf = 1'b0;
            for (s2 = 0; s2 < K; s2 = s2 + 1) begin
                for (j = 0; j < WQD; j = j + 1)
                    tgt[s2][j] = wr_v[b*K + s2] && pv[j] && prow[j] == wr_row[(b*K + s2)*RA +: RA];
                if (wr_v[b*K + s2] && tgt[s2] == {WQD{1'b0}}) begin
                    if (pc + rank < WQD) tgt[s2] = {{(WQD-1){1'b0}}, 1'b1} << (pc + rank);
                    else ovf = 1'b1;
                    rank = rank + 8'd1;
                end
            end
        end
        reg [WQD-1:0]  nv;
        reg [RA-1:0]   nrow [0:WQD-1];
        reg [255:0]    nd   [0:WQD-1];
        reg [7:0]      nm   [0:WQD-1];
        reg [7:0]      ncnt;
        integer t;
        always @(*) begin
            ncnt = 0;
            for (j = 0; j < WQD; j = j + 1) begin
                nv[j] = pv[j]; nrow[j] = prow[j]; nd[j] = pd[j]; nm[j] = pv[j] ? pm[j] : 8'd0;
                for (s2 = 0; s2 < K; s2 = s2 + 1)
                    if (tgt[s2][j]) begin
                        nv[j] = 1'b1;
                        nrow[j] = wr_row[(b*K + s2)*RA +: RA];
                        for (t = 0; t < 8; t = t + 1)
                            if (wr_m[(b*K + s2)*8 + t]) nd[j][32*t +: 32] = wr_d[(b*K + s2)*256 + 32*t +: 32];
                        nm[j] = nm[j] | wr_m[(b*K + s2)*8 +: 8];
                    end
                ncnt = ncnt + (nv[j] ? 8'd1 : 8'd0);
            end
        end
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                for (j = 0; j < WQD; j = j + 1) v[j] <= 1'b0;
            end else begin
                for (j = 0; j < WQD; j = j + 1) v[j] <= nv[j];
            end
        end
        always @(posedge clk) begin
            for (j = 0; j < WQD; j = j + 1) begin row[j] <= nrow[j]; d[j] <= nd[j]; m[j] <= nm[j]; end
        end
        assign q_ovf[b] = ovf;
        assign q_cnt[b*8 +: 8] = ncnt;
        for (e = 0; e < WQD; e = e + 1) begin : g_x
            assign q_v[b*WQD + e] = v[e];
            assign q_row[(b*WQD + e)*RA +: RA] = row[e];
            assign q_d[(b*WQD + e)*256 +: 256] = d[e];
            assign q_m[(b*WQD + e)*8 +: 8] = m[e];
        end
    end endgenerate
    integer fb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin wq_occ <= 0; fault <= 1'b0; end
        else begin
            for (fb = 0; fb < NB; fb = fb + 1) if (q_cnt[fb*8 +: 8] > wq_occ) wq_occ <= q_cnt[fb*8 +: 8];
            if (|q_ovf) fault <= 1'b1;
        end
    end

    // ---- macros: RC replicas of each bank, written together --------------------------------------------------
    wire [RC*NB*256-1:0] mq;
    generate for (c = 0; c < RC; c = c + 1) begin : g_rc
        for (b = 0; b < NB; b = b + 1) begin : g_bk
            ot_sram_1r1w_256x256_m2_r2c2 u_mem (
                .clk(clk), .r_ce_in(rd_v[c]), .r_addr_in(rd_row[(c*NB + b)*RA +: RA]),
                .rd_out(mq[(c*NB + b)*256 +: 256]),
                .w_ce_in(m_we[b]), .w_addr_in(m_wrow[b*RA +: RA]), .wd_in(m_wd[b*256 +: 256]),
                .w_mask_in(m_wmask[b*256 +: 256]), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        end
    end endgenerate

    // ---- forwarding: the queue as it stood at the read edge (entry 0 was being written: the macro's
    // read-during-write returns the old word, so it is forwarded too) ------------------------------------------
    reg [NB*WQD-1:0]      f_v;
    reg [NB*WQD*RA-1:0]   f_row;
    reg [NB*WQD*256-1:0]  f_d;
    reg [NB*WQD*8-1:0]    f_m;
    reg [RC*NB*RA-1:0]    r_row;
    reg [RC*8*4-1:0]      r_sel;
    always @(posedge clk) begin
        r_row <= rd_row; r_sel <= rd_sel; f_row <= q_row; f_d <= q_d; f_m <= q_m;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) f_v <= 0; else f_v <= q_v;
    // per class, per bank: the row as read, with every queued write to that row applied oldest to newest
    // (fixed indices only: a bank's forwarding is one priority chain over its WQD entries)
    wire [RC*NB*256-1:0] fwd;
    genvar q2;
    generate for (c = 0; c < RC; c = c + 1) begin : g_fc
        for (b = 0; b < NB; b = b + 1) begin : g_fb
            wire [RA-1:0] rr = r_row[(c*NB + b)*RA +: RA];
            wire [255:0] ch [0:WQD];
            assign ch[0] = mq[(c*NB + b)*256 +: 256];
            for (q2 = 0; q2 < WQD; q2 = q2 + 1) begin : g_q
                wire hit = f_v[b*WQD + q2] && f_row[(b*WQD + q2)*RA +: RA] == rr;
                genvar t2;
                for (t2 = 0; t2 < 8; t2 = t2 + 1) begin : g_w
                    assign ch[q2+1][32*t2 +: 32] = (hit && f_m[(b*WQD + q2)*8 + t2]) ?
                        f_d[(b*WQD + q2)*256 + 32*t2 +: 32] : ch[q2][32*t2 +: 32];
                end
            end
            assign fwd[(c*NB + b)*256 +: 256] = ch[WQD];
        end
        // per lane: bank, then word
        genvar l2;
        for (l2 = 0; l2 < 8; l2 = l2 + 1) begin : g_l
            wire [3:0] sl = r_sel[(c*8 + l2)*4 +: 4];
            wire [255:0] rowv = (NB > 1 && sl[3]) ? fwd[(c*NB + (NB > 1 ? 1 : 0))*256 +: 256] : fwd[(c*NB)*256 +: 256];
            wire [31:0] wv [0:7];
            genvar t3;
            for (t3 = 0; t3 < 8; t3 = t3 + 1) begin : g_t
                assign wv[t3] = rowv[32*t3 +: 32];
            end
            always @(*) rd_q[(c*8 + l2)*32 +: 32] = wv[sl[2:0]];
        end
    end endgenerate
endmodule
