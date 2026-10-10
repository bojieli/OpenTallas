`timescale 1ns/1ps
`default_nettype none
// HGI-1 VM-512 tile (hgi-1010/f, 2026-10-10): the hardened element of the vector memory, replicated 128 times.
//
// Tile t holds banks 4t .. 4t+3 of the 512-bank VM (sector s -> bank s[8:0], tile s[8:2], slot s[1:0], row s[SB-1:9]).
// A bank is one 1R1W row of 8 FP32 words, each (39,32) SECDED = 312 bits = two ot_sram_1r1w_128x256_m1_r2c2 (the low
// macro holds bits 255:0, the high macro bits 311:256).  A read and a write to one bank in one cycle never conflict.
//
// DMA lane (from the DMA front, this tile only; spec 2.4 VM microarchitecture):
//   dl {v [302], fmt [301:299], row [298:292], c0 [291:288] (signed), wm [287:256] (8 a slot), raw [255:0]}.
//   Slot j (bank 4t + j) receives chunk k = c0 + j of the raw source sector when wm[8j +: 8] != 0; 0 <= k < e is
//   required (e = 1 FP32/U32, 2 BF16, 4 FP8/INT8/UE8M0, 8 FP4), else the beat faults (dl_fault) and that slot is
//   not written.  The beat enters a 2-entry skid (the front holds 2 credits; dl_cr returns one when the skid head
//   leaves).  The head leaves when every slot it writes has room in its bank queue (QD entries, counting entries in
//   flight); it is converted (stage C), SECDED-encoded into the bank queue (stage E), and each bank writes its queue
//   head whenever no edge write takes the bank's write port.  dl_wn = dest sectors written into the macros this cycle.
// Edge writes (ew_*) and edge reads (er_*) arrive scheduled by ot_hgi_vm512's edge: at most one of each a bank a cycle;
//   an edge write always wins the bank's write port (the DMA queue waits).  ew_d is already encoded (312 b).
// Read data: rd_d (raw 312, decoded at the edge) with rd_sid, 3 edges after er_v (pins, macro, capture).
// MUT (bench): 3 DMA queue overrides an edge write (the edge write is lost); 4 DMA ignores its word mask;
//   8 the reservation ignores beats in flight (bank queue overflow drops a chunk).
module ot_hgi_vm_tile #(
    parameter integer RB  = 6,           // row bits used (SB - 9)
    parameter integer QD  = 4,           // bank queue depth (DMA chunks, counting the 2 in flight)
    parameter integer SW  = 2,           // read slot id width (edge read slot)
    parameter integer MUT = 0
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire [302:0]     dl,
    output reg              dl_cr,
    output reg  [2:0]       dl_wn,
    output reg              dl_fault,
    input  wire [3:0]       ew_v,
    input  wire [4*7-1:0]   ew_row,
    input  wire [4*312-1:0] ew_d,
    input  wire [4*8-1:0]   ew_m,
    input  wire [3:0]       er_v,
    input  wire [4*7-1:0]   er_row,
    input  wire [4*SW-1:0]  er_sid,
    output reg  [3:0]       rd_v,
    output reg  [4*SW-1:0]  rd_sid,
    output reg  [4*312-1:0] rd_d,
    input  wire             inj_v,       // bench only: flip inj_mask in word inj_word of slot inj_slot's next write
    input  wire [1:0]       inj_slot,
    input  wire [2:0]       inj_word,
    input  wire [38:0]      inj_mask
);
    // ---------------------------------------------------------------- skid (2 entries, credit return on pop)
    reg [301:0] sk [0:1]; reg [1:0] sk_n; reg sk_h;
    wire [301:0] hd = sk[sk_h];
    wire [2:0]  h_fmt = hd[301:299];
    wire [6:0]  h_row = hd[298:292];
    wire signed [4:0] h_c0 = {hd[291], hd[291:288]};
    wire [31:0] h_wm = hd[287:256];
    wire [255:0] h_raw = hd[255:0];
    wire [3:0]  h_e = (h_fmt == 3'd0 || h_fmt == 3'd5) ? 4'd1 : (h_fmt == 3'd1) ? 4'd2 : (h_fmt == 3'd3) ? 4'd8 : 4'd4;
    reg  [3:0]  h_use, h_bad; reg [2:0] h_k [0:3];
    always @* for (integer j = 0; j < 4; j = j + 1) begin : g_hk
        reg signed [5:0] kk;
        kk = {h_c0[4], h_c0} + 6'(j);
        h_k[j] = kk[2:0];
        h_use[j] = (h_wm[j*8 +: 8] != 8'd0) && kk >= 0 && kk < $signed({2'd0, h_e});
        h_bad[j] = (h_wm[j*8 +: 8] != 8'd0) && !(kk >= 0 && kk < $signed({2'd0, h_e}));
    end
    // reservation: entries in a bank queue + chunks in flight towards it (stage C, stage E)
    reg [3:0] res [0:3];
    reg [3:0] qn  [0:3];
    reg room;
    always @* begin
        room = 1'b1;
        for (integer j = 0; j < 4; j = j + 1)
            if (h_use[j] && ((MUT == 8) ? (qn[j] >= 4'(QD)) : (res[j] >= 4'(QD)))) room = 1'b0;
    end
    wire take = (sk_n != 2'd0) && room;
    // ---------------------------------------------------------------- stage C: convert
    wire [255:0] cvt [0:3];
    genvar gj;
    for (gj = 0; gj < 4; gj = gj + 1) begin : g_cv
        ot_hgi_vm_conv8 #(.MUT(MUT)) u_cv (.raw(h_raw), .fmt(h_fmt), .k(h_k[gj]), .o(cvt[gj]));
    end
    reg [3:0] c_v; reg [6:0] c_row; reg [7:0] c_wm [0:3]; reg [255:0] c_d [0:3];
    // ---------------------------------------------------------------- stage E: encode into the bank queue
    wire [311:0] c_enc [0:3];
    for (gj = 0; gj < 4; gj = gj + 1) begin : g_en
        ot_hgi_vm_enc8 u_en (.d(c_d[gj]), .q(c_enc[gj]));
    end
    reg [6:0]   q_row [0:3][0:QD-1];
    reg [311:0] q_d   [0:3][0:QD-1];
    reg [7:0]   q_wm  [0:3][0:QD-1];
    reg [$clog2(QD)-1:0] q_h [0:3], q_t [0:3];
    // ---------------------------------------------------------------- bank port selection
    reg [3:0] wsel_e, wsel_q;            // this cycle: edge write / queue write
    always @* for (integer j = 0; j < 4; j = j + 1) begin
        if (MUT == 3) begin wsel_q[j] = qn[j] != 4'd0; wsel_e[j] = ew_v[j] && !wsel_q[j]; end
        else begin wsel_e[j] = ew_v[j]; wsel_q[j] = !ew_v[j] && qn[j] != 4'd0; end
    end
    // macro pins
    reg [3:0] m_we, m_re; reg [6:0] m_wa [0:3]; reg [6:0] m_ra [0:3]; reg [311:0] m_wd [0:3]; reg [311:0] m_wm [0:3];
    reg [3:0] m_wq;                      // the pin write is a DMA chunk (counted on dl_wn when it reaches the macro)
    reg [3:0] p_rv; reg [SW-1:0] p_sid [0:3];   // p_sid: with the pins; p_rv: rd_out holds the read (after the macro edge)
    reg [SW-1:0] a_sid [0:3];                   // a_sid: the sid of the read whose data rd_out holds
    reg [3:0] inj_p; reg [2:0] inj_w [0:3]; reg [38:0] inj_m [0:3];   // bench: pending injection a slot
    wire [511:0] m_rd [0:3];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sk_n <= 2'd0; sk_h <= 1'b0; dl_cr <= 1'b0; dl_wn <= 3'd0; dl_fault <= 1'b0; c_v <= 4'd0;
            m_we <= 4'd0; m_re <= 4'd0; m_wq <= 4'd0; p_rv <= 4'd0; rd_v <= 4'd0; inj_p <= 4'd0;
            for (integer j = 0; j < 4; j = j + 1) begin res[j] <= 4'd0; qn[j] <= 4'd0; q_h[j] <= '0; q_t[j] <= '0; end
        end else begin : seq
            reg [3:0] wn;
            // ---- skid
            if (dl[302]) begin
                if (sk_n == 2'd2 && !take) dl_fault <= 1'b1;                 // credit violation
                else sk[(sk_n == 2'd1) ? ~sk_h : sk_h] <= dl[301:0];      // the tail (sk_n 2 + take: the freed head)
            end
            if (take) begin
                sk_h <= ~sk_h;
                if (|h_bad) dl_fault <= 1'b1;
            end
            sk_n <= sk_n + {1'b0, dl[302] && !(sk_n == 2'd2 && !take)} - {1'b0, take};
            dl_cr <= take;
            // ---- stage C
            c_v <= take ? h_use : 4'd0;
            if (take) begin
                c_row <= h_row;
                for (integer j = 0; j < 4; j = j + 1) begin c_wm[j] <= h_wm[j*8 +: 8]; c_d[j] <= cvt[j]; end
            end
            // ---- stage E (queue push) and bank port
            wn = 4'd0;
            for (integer j = 0; j < 4; j = j + 1) begin
                if (c_v[j]) begin
                    if (qn[j] < 4'(QD) || wsel_q[j]) begin
                        q_row[j][q_t[j]] <= c_row; q_d[j][q_t[j]] <= c_enc[j]; q_wm[j][q_t[j]] <= c_wm[j];
                        q_t[j] <= q_t[j] + 1'b1;
                    end else dl_fault <= (MUT == 8) ? dl_fault : 1'b1;       // cannot happen with the reservation
                end
                m_we[j] <= wsel_e[j] || wsel_q[j];
                m_wq[j] <= wsel_q[j];
                if (wsel_e[j]) begin
                    m_wa[j] <= ew_row[j*7 +: 7];
                    m_wd[j] <= ew_d[j*312 +: 312] ^ (inj_p[j] ? (312'(inj_m[j]) << (39 * inj_w[j])) : 312'd0);
                    for (integer w = 0; w < 8; w = w + 1) m_wm[j][w*39 +: 39] <= {39{ew_m[j*8 + w]}};
                end else if (wsel_q[j]) begin
                    m_wa[j] <= q_row[j][q_h[j]];
                    m_wd[j] <= q_d[j][q_h[j]] ^ (inj_p[j] ? (312'(inj_m[j]) << (39 * inj_w[j])) : 312'd0);
                    for (integer w = 0; w < 8; w = w + 1) m_wm[j][w*39 +: 39] <= {39{q_wm[j][q_h[j]][w] | (MUT == 4)}};
                    q_h[j] <= q_h[j] + 1'b1;
                end
                qn[j] <= qn[j] + {3'd0, c_v[j] && (qn[j] < 4'(QD) || wsel_q[j])} - {3'd0, wsel_q[j]};
                res[j] <= res[j] + {3'd0, take && h_use[j]} - {3'd0, wsel_q[j]};
                if (inj_v && inj_slot == 2'(j)) begin inj_p[j] <= 1'b1; inj_w[j] <= inj_word; inj_m[j] <= inj_mask; end
                else if (wsel_e[j] || wsel_q[j]) inj_p[j] <= 1'b0;
                // reads
                m_re[j] <= er_v[j];
                if (er_v[j]) begin m_ra[j] <= er_row[j*7 +: 7]; p_sid[j] <= er_sid[j*SW +: SW]; end
                if (m_wq[j]) wn = wn + 4'd1;
            end
            dl_wn <= wn[2:0];
            p_rv <= m_re;
            rd_v <= p_rv;
            for (integer j = 0; j < 4; j = j + 1) begin
                if (m_re[j]) a_sid[j] <= p_sid[j];
                if (p_rv[j]) begin rd_d[j*312 +: 312] <= m_rd[j][311:0]; rd_sid[j*SW +: SW] <= a_sid[j]; end
            end
        end
    end
    // read timing: er_v in cycle T -> pins at edge 1 -> macro samples at edge 2 (rd_out valid, p_rv) -> rd_d at edge 3.
    for (gj = 0; gj < 4; gj = gj + 1) begin : g_bank
        wire [511:0] wd = {200'd0, m_wd[gj]};
        wire [511:0] wm = {200'd0, m_wm[gj]};
        ot_sram_1r1w_128x256_m1_r2c2 u_lo (.clk(clk), .r_ce_in(m_re[gj]), .r_addr_in(m_ra[gj]), .rd_out(m_rd[gj][255:0]),
            .w_ce_in(m_we[gj]), .w_addr_in(m_wa[gj]), .wd_in(wd[255:0]), .w_mask_in(wm[255:0]),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_128x256_m1_r2c2 u_hi (.clk(clk), .r_ce_in(m_re[gj]), .r_addr_in(m_ra[gj]), .rd_out(m_rd[gj][511:256]),
            .w_ce_in(m_we[gj]), .w_addr_in(m_wa[gj]), .wd_in(wd[511:256]), .w_mask_in(wm[511:256]),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end
endmodule
`default_nettype wire
