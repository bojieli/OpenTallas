`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// kv-die 2026-10-09 (review-1149 KV14): the KV-die LANDING WRITE QUEUE of one stack (die master qkd_land).  The new
// position's K / V rows (posted by the KV-die sequencer: {v, g}, t = T-1, layer, HD x FP8 = 1,024 b) are written to the
// stack's HBM through the per-PC STREAM4 CDCs' write side (ot_qwen_stream4_cdc_pc w_v / w_sec / w_data / w_tag,
// w_room, write-done wd_v / wd_tag) and, on the HBM clock side, the per-PC port's KVW = 2 write path
// (ot_qfd_emb_pcport: kw_v / kw_d = the CDC's h_cv / h_cdata, SECDED-encoded into the PHY write data).
//
// KV layout (one row = 4 sectors of 256 b, sector q = bytes 32q .. 32q + 31; the stack holds t with t[8:7] = S):
//   pc  = {q[1:0], t[2:0]}                                  32 PCs: a row's 4 sectors on 4 PCs, 8 positions spread
//   sec = {7'b0, layer[5:0], g, v, t[13:9], t[6:3]}         unique per (layer, g, v, t, q) within the stack
// The near-HBM read side (qkd_land read crossbar) uses the same map (CONTRACT v1.1 section 2).
//
// Flow: a QD-row queue with credits to the sender (kvw_cr: one per row taken); the head row's 4 sectors are pushed to
// their PCs in parallel, each when its PC reports room (w_room is registered in the CDC; one push per PC per cycle);
// tag = {row slot, q}.  Write-done: every wd tag of a PC is checked against an outstanding sector of that PC; when all
// 4 sectors of a row are done the row leaves the queue and rw_v pulses with its {layer, vg, t} (the write is durable
// in HBM from here; the read fence of KV4 does not need it -- the merge serves the row until then).
// Every input is captured at the pin, every output is a flop.  The head row is a registered stage (qkd_kvwq_a
// route: reg2reg -988 ps from the queue pointer through the head mux, the PC map and the 32-way room select): the
// decisions start at flops (head, its one-hot PC lane, the per-quarter room bits), +1 cycle a row, posted.
// Faults (sticky): a row pushed into a full queue (credit violation), a write-done tag with no outstanding sector.
// MUT (bench mutants, must FAIL): 1 = sectors 1 and 2 swap PCs; 2 = sector data taken from the wrong quarter (q ^ 1);
//   3 = quarter 0 never pushed (the row never becomes durable: the bench times out).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kv_wq #(
    parameter integer HD   = 128,
    parameter integer NPC  = 32,
    parameter integer QD   = 4,            // rows held (>= the sender's credit loop: rows arrive 4 a layer)
    parameter integer TAGW = 9,
    parameter integer MUT  = 0
) (
    input  wire                  clk,
    input  wire                  rst_n,
    // posted rows from the KV-die sequencer (credit flow)
    input  wire                  kvw_v,
    input  wire [1:0]            kvw_vg,
    input  wire [13:0]           kvw_t,
    input  wire [5:0]            kvw_layer,
    input  wire [HD*8-1:0]       kvw_d,
    output reg                   kvw_cr,
    // per-PC CDC write side (core clock)
    output reg  [NPC-1:0]        w_v,
    output reg  [24*NPC-1:0]     w_sec,
    output reg  [256*NPC-1:0]    w_data,
    output reg  [TAGW*NPC-1:0]   w_tag,
    input  wire [NPC-1:0]        w_room,
    input  wire [NPC-1:0]        wd_v,
    input  wire [TAGW*NPC-1:0]   wd_tag,
    // row durable in HBM
    output reg                   rw_v,
    output reg  [21:0]           rw_id,     // {layer, vg, t}
    output reg                   fault
);
    localparam integer QA = (QD > 1) ? $clog2(QD) : 1;
    // sector q of a row goes to the PCs of quarter group swq(q) (MUT 1 swaps groups 1 and 2), lane t[2:0] in the group
    function automatic [1:0] swq(input [1:0] q);
        swq = (MUT == 1 && q == 2'd1) ? 2'd2 : (MUT == 1 && q == 2'd2) ? 2'd1 : q;
    endfunction
    function automatic [23:0] sec_of(input [5:0] layer, input [1:0] vg, input [13:0] t);
        sec_of = {7'd0, layer, vg[0], vg[1], t[13:9], t[6:3]};      // {layer, g, v, t-hi, t-lo}
    endfunction
    // ---- pin capture ----
    reg              iv;
    reg  [1:0]       ivg;
    reg  [13:0]      it;
    reg  [5:0]       il;
    reg  [HD*8-1:0]  id;
    reg  [NPC-1:0]   room_r, wdv_r;
    reg  [TAGW*NPC-1:0] wdt_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iv <= 1'b0; room_r <= 0; wdv_r <= 0; end
        else begin iv <= kvw_v; room_r <= w_room; wdv_r <= wd_v; end
    always @(posedge clk) begin ivg <= kvw_vg; it <= kvw_t; il <= kvw_layer; id <= kvw_d; wdt_r <= wd_tag; end
    // ---- row queue (rows waiting behind the head) ----
    reg  [HD*8-1:0]  qd  [0:QD-1];
    reg  [21:0]      qid [0:QD-1];
    reg  [QA:0]      qw, qr;
    wire             q_empty = (qw == qr);
    wire             q_full = (qw[QA-1:0] == qr[QA-1:0]) && (qw[QA] != qr[QA]);
    // ---- the head row, registered (timing successor: every decision below starts at a flop) ----
    reg              hv;
    reg  [HD*8-1:0]  hrow;
    reg  [21:0]      hid;
    reg  [QA-1:0]    hslot;            // tag slot of the head (its queue slot, as before)
    reg  [7:0]       hsel;             // one-hot t[2:0]: the PC lane of every quarter group
    reg  [23:0]      hsec;
    reg  [3:0]       sent, done;
    reg  [3:0]       room_q;           // registered: room of the PC of each quarter
    wire             retire = hv && (done == 4'hF);
    wire             hload = (!hv || retire) && !q_empty;
    integer q_, p_;
    reg  [3:0]       push_q;
    always @* begin
        for (q_ = 0; q_ < 4; q_ = q_ + 1)
            push_q[q_] = hv && !sent[q_] && room_q[q_] && !(MUT == 3 && q_ == 0);
    end
    // a PC pushes when its quarter group's sector is pushed and it is the head's lane
    reg  [NPC-1:0]   push;
    reg  [1:0]       gq;
    always @* begin
        push = 0;
        for (p_ = 0; p_ < NPC; p_ = p_ + 1) begin
            gq = p_ >> 3;
            for (q_ = 0; q_ < 4; q_ = q_ + 1)
                if (swq(q_[1:0]) == gq && push_q[q_] && hsel[p_ & 7]) push[p_] = 1'b1;
        end
    end
    // write-done: every PC of quarter group g reports for the sector swq^-1(g) of the head (one row in flight)
    reg  [3:0]       wd_q;
    reg              wd_bad;
    always @* begin
        wd_q = 0; wd_bad = 1'b0;
        for (p_ = 0; p_ < NPC; p_ = p_ + 1)
            if (wdv_r[p_])
                for (q_ = 0; q_ < 4; q_ = q_ + 1)
                    if (swq(q_[1:0]) == (p_ >> 3)) begin
                        wd_q[q_] = 1'b1;
                        if (wdt_r[TAGW*p_ +: 2] != q_[1:0] || wdt_r[TAGW*p_ + 2 +: QA] != hslot) wd_bad = 1'b1;
                    end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qw <= 0; qr <= 0; kvw_cr <= 1'b0; w_v <= 0; rw_v <= 1'b0; fault <= 1'b0; hv <= 1'b0; sent <= 4'd0;
            done <= 4'd0; room_q <= 4'd0;
        end else begin
            kvw_cr <= 1'b0; rw_v <= 1'b0;
            if (iv) begin
                if (q_full) fault <= 1'b1;
                qw <= qw + 1'b1;
            end
            w_v <= push;
            sent <= sent | push_q;
            if (wd_bad || (|(wd_q & done)) || (|(wd_q & ~sent))) fault <= 1'b1;
            done <= done | wd_q;
            for (q_ = 0; q_ < 4; q_ = q_ + 1) room_q[q_] <= room_r[{swq(q_[1:0]), hid[2:0]}] && !push_q[q_];
            if (retire) begin
                hv <= 1'b0; kvw_cr <= 1'b1; rw_v <= 1'b1; rw_id <= hid;
            end
            if (hload) begin
                hv <= 1'b1; qr <= qr + 1'b1; sent <= 4'd0; done <= 4'd0; room_q <= 4'd0;
            end
        end
    end
    always @(posedge clk) begin
        if (iv) begin qd[qw[QA-1:0]] <= id; qid[qw[QA-1:0]] <= {il, ivg, it}; end
        if (hload) begin
            hrow <= qd[qr[QA-1:0]]; hid <= qid[qr[QA-1:0]]; hslot <= qr[QA-1:0];
            hsel <= 8'd1 << qid[qr[QA-1:0]][2:0];
            hsec <= sec_of(qid[qr[QA-1:0]][21:16], qid[qr[QA-1:0]][15:14], qid[qr[QA-1:0]][13:0]);
        end
        for (p_ = 0; p_ < NPC; p_ = p_ + 1)
            if (push[p_]) begin
                w_sec[24*p_ +: 24] <= hsec;
                // the PC of quarter group g carries sector swq^-1(g) (MUT 2: the next quarter's bytes)
                for (q_ = 0; q_ < 4; q_ = q_ + 1)
                    if (swq(q_[1:0]) == (p_ >> 3)) begin
                        w_data[256*p_ +: 256] <= hrow[256*((MUT == 2) ? (q_ ^ 1) : q_) +: 256];
                        w_tag[TAGW*p_ +: TAGW] <= TAGW'({hslot, q_[1:0]});
                    end
            end
    end
endmodule
