`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 SM result publication (hgi-adapters, 2026-10-09): the peer of ot_hgi_sm_record's pub port.  Takes every SM's
// EXISTING result port (rv / rrow / rdata = NC x 32 b: column p = slot p) and writes O in VM through NPC hfd_hgi_vm
// packet clients: result (SM s, row r, slot p < P) -> VM word O.base + p x O.stride + s x Q + r.
// Each SM's rows arrive in order; a per-SM, per-slot sector buffer coalesces consecutive rows (8 words a sector write,
// word-masked), flushed on a sector change, at pub_done time, or when the buffer would be overwritten.  Flushes queue
// in a ready FIFO drained by the NPC clients (one write in flight each).  pub_done = every row of every active SM
// (rows R_s = clamp(M - s Q, 0, Q)) received AND every write acknowledged.  The SM result port has no ready, so the
// per-SM buffers (one sector + one pending flush a slot) bound the absorbable rate: a row every 8 / (P x NSM / NPC)
// cycles is sustained; a faster stream raises pub_fault (overrun, fail closed; never a silent drop).
// O VM: O.base + p O.stride 8-aligned is NOT required.  O STREAM (space 2, the Qwen head: SM -> SU stream 0): every
// result (slot p, global row g) leaves as one STREAM 0 beat {s0_v, s0_idx = p M + g, s0_data} through a SQ-entry FIFO,
// one beat an edge, in arrival order (the SU unit lands beats by index, so order is free); overrun faults.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_pub #(
    parameter integer NSM = 32,
    parameter integer NC = 8,
    parameter integer NPC = 4,
    parameter integer MUT_ROW = 0          // mutant: the global row ignores s x Q
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               pub_v,
    output wire               pub_rdy,
    input  wire [39:0]        pub_base,
    input  wire [31:0]        pub_stride,
    input  wire [1:0]         pub_space,
    input  wire [19:0]        pub_m,
    input  wire [12:0]        pub_q,
    input  wire [3:0]         pub_p,
    output reg                pub_done,
    output reg                pub_fault,
    input  wire [NSM-1:0]     sm_rv,
    input  wire [NSM*12-1:0]  sm_rrow,
    input  wire [NSM*NC*32-1:0] sm_rdata,
    output reg  [NPC*338-1:0] vmq,
    input  wire [NPC*274-1:0] vmr,
    output reg                s0_v,
    output reg  [19:0]        s0_idx,
    output reg  [31:0]        s0_data
);
    localparam integer SQ = 64;
    reg sm_m; reg [51:0] sfq [0:SQ-1]; reg [6:0] sh, stt; wire [6:0] sn = stt - sh; integer spush;
    reg busy; reg [17:0] ob; reg [17:0] ost; reg [19:0] mm; reg [12:0] qq; reg [3:0] pp;
    assign pub_rdy = !busy;
    // registered result capture (the SM's output register drives a long wire: land it first)
    reg [NSM-1:0] rv_q; reg [11:0] rr_q [0:NSM-1]; reg [NC*32-1:0] rd_q [0:NSM-1];
    integer s, p, c;
    always @(posedge clk) for (s = 0; s < NSM; s = s + 1) begin rv_q[s] <= sm_rv[s]; rr_q[s] <= sm_rrow[s*12 +: 12];
                                                                rd_q[s] <= sm_rdata[s*NC*32 +: NC*32]; end
    // per-SM rows expected / received
    reg [19:0] need [0:NSM-1]; reg [19:0] recv [0:NSM-1];
    // per (SM, slot) sector buffer: sector address (word >> 3), data, word mask, valid
    reg [14:0] bsec [0:NSM*NC-1]; reg [255:0] bdat [0:NSM*NC-1]; reg [7:0] bmsk [0:NSM*NC-1]; reg bval [0:NSM*NC-1];
    // flush FIFO
    localparam integer QD = 64;
    reg [14:0] qsec [0:QD-1]; reg [255:0] qdat [0:QD-1]; reg [7:0] qmsk [0:QD-1];
    reg [6:0] qh, qt; wire [6:0] qn = qt - qh;
    reg [NPC-1:0] cbusy; reg [9:0] wout;
    reg [273:0] vr [0:NPC-1];
    always @(posedge clk) for (c = 0; c < NPC; c = c + 1) vr[c] <= vmr[c*274 +: 274];
    reg all_rows;
    always @* begin all_rows = 1'b1; for (s = 0; s < NSM; s = s + 1) if (recv[s] != need[s]) all_rows = 1'b0; end
    reg any_buf;
    always @* begin any_buf = 1'b0; for (s = 0; s < NSM * NC; s = s + 1) if (bval[s]) any_buf = 1'b1; end
    reg [31:0] wd; reg [14:0] sec; reg [2:0] wo; integer k, push;
    reg [19:0] r0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; pub_done <= 1'b0; pub_fault <= 1'b0; qh <= 0; qt <= 0; cbusy <= 0; vmq <= 0;
            sm_m <= 1'b0; sh <= 0; stt <= 0; s0_v <= 1'b0; s0_idx <= 20'd0; s0_data <= 32'd0;
            for (s = 0; s < NSM * NC; s = s + 1) bval[s] <= 1'b0;
            for (s = 0; s < NSM; s = s + 1) begin need[s] <= 0; recv[s] <= 0; end
        end else begin
            pub_done <= 1'b0;
            for (c = 0; c < NPC; c = c + 1) vmq[c*338 + 337] <= 1'b0;
            if (pub_v && pub_rdy) begin
                if (!(pub_space == 2'd1 || pub_space == 2'd2) || pub_p == 4'd0 || pub_p > NC) pub_fault <= 1'b1;
                else begin
                    busy <= 1'b1; sm_m <= (pub_space == 2'd2); ob <= pub_base[17:0]; ost <= pub_stride[17:0]; mm <= pub_m; qq <= pub_q; pp <= pub_p;
                    for (s = 0; s < NSM; s = s + 1) begin
                        r0 = s * pub_q;
                        need[s] <= (pub_m > r0) ? (((pub_m - r0) > {7'd0, pub_q}) ? {7'd0, pub_q} : pub_m - r0) : 20'd0;
                        recv[s] <= 20'd0;
                    end
                end
            end
            // results -> sector buffers (flush on a sector change: one push a buffer a cycle at most)
            push = 0; spush = 0;
            for (s = 0; s < NSM; s = s + 1)
                if (busy && sm_m && rv_q[s]) begin                                // STREAM: one beat a result
                    recv[s] <= recv[s] + 20'd1;
                    for (p = 0; p < NC; p = p + 1)
                        if (p < pp) begin
                            sfq[(stt + spush) % SQ] <= {p * mm + (MUT_ROW ? 20'd0 : s * {7'd0, qq}) + {8'd0, rr_q[s]},
                                                        rd_q[s][32*p +: 32]};
                            spush = spush + 1;
                        end
                end
                else if (busy && rv_q[s]) begin
                    recv[s] <= recv[s] + 20'd1;
                    for (p = 0; p < NC; p = p + 1)
                        if (p < pp) begin
                            wd = {14'd0, ob} + p * {14'd0, ost} + (MUT_ROW ? 32'd0 : s * {19'd0, qq}) + {20'd0, rr_q[s]};
                            sec = wd[17:3]; wo = wd[2:0];
                            k = s * NC + p;
                            if (bval[k] && bsec[k] != sec) begin                   // flush the old sector
                                qsec[qt + push] <= bsec[k]; qdat[qt + push] <= bdat[k]; qmsk[qt + push] <= bmsk[k];
                                push = push + 1;
                                bdat[k] <= {224'd0, rd_q[s][32*p +: 32]} << {wo, 5'd0}; bmsk[k] <= 8'd1 << wo;
                            end else begin
                                bdat[k] <= (bval[k] ? bdat[k] : 256'd0) | ({224'd0, rd_q[s][32*p +: 32]} << {wo, 5'd0});
                                bmsk[k] <= (bval[k] ? bmsk[k] : 8'd0) | (8'd1 << wo);
                            end
                            bsec[k] <= sec; bval[k] <= 1'b1;
                        end
                end
            // when every row arrived: flush the remaining buffers (one a cycle)
            if (busy && all_rows && push == 0) begin : fl
                reg done1; done1 = 1'b0;
                for (s = 0; s < NSM * NC; s = s + 1)
                    if (!done1 && bval[s]) begin
                        qsec[qt] <= bsec[s]; qdat[qt] <= bdat[s]; qmsk[qt] <= bmsk[s]; bval[s] <= 1'b0; push = 1; done1 = 1'b1;
                    end
            end
            if (qn + push > QD - 1) pub_fault <= 1'b1;                       // overrun: fail closed
            if (sn + spush > SQ - 1) pub_fault <= 1'b1;
            s0_v <= 1'b0;
            if (sn != 0) begin s0_v <= 1'b1; {s0_idx, s0_data} <= sfq[sh % SQ]; end
            stt <= stt + spush[6:0]; sh <= sh + ((sn != 0) ? 7'd1 : 7'd0);
            // drain: the lowest free client takes the head
            begin : dr
                reg taken; taken = 1'b0;
                for (c = 0; c < NPC; c = c + 1)
                    if (!taken && !cbusy[c] && qn != 0) begin
                        vmq[c*338 +: 338] <= {1'b1, 1'b1, 12'd0, qsec[qh], 5'd0, qdat[qh],
                                              {{4{qmsk[qh][7]}}, {4{qmsk[qh][6]}}, {4{qmsk[qh][5]}}, {4{qmsk[qh][4]}},
                                               {4{qmsk[qh][3]}}, {4{qmsk[qh][2]}}, {4{qmsk[qh][1]}}, {4{qmsk[qh][0]}}}, 16'h5042};
                        cbusy[c] <= 1'b1; qh <= qh + 7'd1; taken = 1'b1;
                    end
            end
            for (c = 0; c < NPC; c = c + 1) if (cbusy[c] && vr[c][273] && vr[c][256]) cbusy[c] <= 1'b0;
            qt <= qt + push[6:0];
            if (busy && all_rows && !any_buf && push == 0 && qn == 0 && cbusy == 0 && spush == 0 && sn == 0) begin
                busy <= 1'b0; pub_done <= 1'b1; end
        end
    end
endmodule
`default_nettype wire
