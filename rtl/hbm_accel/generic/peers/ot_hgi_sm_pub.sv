`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 SM result publication (hgi-adapters, 2026-10-09): the peer of ot_hgi_sm_record's pub port.  Takes every SM's
// EXISTING result port (rv / rrow / rdata = NC x 32 b: column p = slot p) and writes O in VM through NPC hfd_hgi_vm
// packet clients: result (SM s, row r, slot p < P) -> VM word O.base + p x O.stride + s x Q + r.
// Each SM's rows arrive in order; a per-SM, per-slot sector buffer coalesces consecutive rows (8 words a sector write,
// word-masked) and moves to its own one-entry pending-flush register on a sector change or at the end.  STRUCTURE
// (synthesis-friendly, 2026-10-10): every buffer / pending register is indexed statically by (SM, slot); one priority
// grant an edge moves one pending flush (or STREAM beat) into a single-write FIFO drained by the NPC clients, so no
// array takes more than one dynamic write an edge.  pub_done = every row of every active SM
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
    localparam integer NB = NSM * NC, QD = 16;
    reg busy, sm_m; reg [17:0] ob, ost; reg [19:0] mm; reg [12:0] qq; reg [3:0] pp;
    assign pub_rdy = !busy;
    // registered result capture (the SM's output register drives a long wire: land it first)
    reg [NSM-1:0] rv_q; reg [11:0] rr_q [0:NSM-1]; reg [NC*32-1:0] rd_q [0:NSM-1];
    integer s, c;
    always @(posedge clk) for (s = 0; s < NSM; s = s + 1) begin rv_q[s] <= sm_rv[s]; rr_q[s] <= sm_rrow[s*12 +: 12];
                                                                rd_q[s] <= sm_rdata[s*NC*32 +: NC*32]; end
    // per-SM rows expected / received; all_rows registered
    reg [19:0] need [0:NSM-1]; reg [19:0] recv [0:NSM-1]; reg all_rows;
    reg [NSM-1:0] rdone;
    always @* for (s = 0; s < NSM; s = s + 1) rdone[s] = (recv[s] == need[s]);
    // per (SM, slot): buffer, pending flush, STREAM entry (all statically indexed)
    reg [NB-1:0] bval, fv, sv;
    // the granted entry's pending flush / STREAM head, exported flat by every entry (its storage is local to it)
    wire [NB*15-1:0] fsec_v; wire [NB*256-1:0] fdat_v; wire [NB*8-1:0] fmsk_v; wire [NB*52-1:0] shd_v;
    // the grant: the lowest pending entry, when the output FIFO has room
    reg [3:0] qn; reg [3:0] qh, qt;
    reg [14:0] qsec [0:QD-1]; reg [255:0] qdat [0:QD-1]; reg [7:0] qmsk [0:QD-1];
    wire [NB-1:0] req = fv | sv;
    reg gv; integer gk;
    always @* begin gv = 1'b0; gk = 0; for (c = NB - 1; c >= 0; c = c - 1) if (req[c]) begin gv = 1'b1; gk = c; end end
    wire take = gv && (sm_m || qn < QD - 1);
    reg [NPC-1:0] cbusy; reg [273:0] vr [0:NPC-1];
    always @(posedge clk) for (c = 0; c < NPC; c = c + 1) vr[c] <= vmr[c*274 +: 274];
    reg pend_any;
    always @* pend_any = |bval || |fv || |sv;
    reg [NB-1:0] ovr;                      // an overrun this edge (per entry)
    genvar gs, gp;
    generate for (gs = 0; gs < NSM; gs = gs + 1) begin : g_s
        for (gp = 0; gp < NC; gp = gp + 1) begin : g_p
            localparam integer K = gs * NC + gp;
            wire res = busy && rv_q[gs] && (gp < pp);
            wire [31:0] wd = {14'd0, ob} + gp * {14'd0, ost} + (MUT_ROW ? 32'd0 : gs * {19'd0, qq}) + {20'd0, rr_q[gs]};
            wire [19:0] gidx = gp * mm + (MUT_ROW ? 20'd0 : gs * {7'd0, qq}) + {8'd0, rr_q[gs]};
            wire tk = take && gk == K;
            reg [14:0] bsec, fsec; reg [255:0] bdat, fdat; reg [7:0] bmsk, fmsk;
            reg [51:0] sent [0:3];                      // a 4-deep STREAM FIFO (an SM may emit rows back to back)
            reg [1:0] sw_, sr_; reg [2:0] scnt;
            assign fsec_v[K*15 +: 15] = fsec; assign fdat_v[K*256 +: 256] = fdat; assign fmsk_v[K*8 +: 8] = fmsk;
            assign shd_v[K*52 +: 52] = sent[sr_];
            wire chg = res && !sm_m && bval[K] && bsec != wd[17:3];
            wire endf = busy && all_rows && !sm_m && bval[K] && !res && !fv[K];
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin bval[K] <= 1'b0; fv[K] <= 1'b0; sv[K] <= 1'b0; ovr[K] <= 1'b0; sw_ <= 2'd0;
                                  sr_ <= 2'd0; scnt <= 3'd0; end
                else begin
                    ovr[K] <= 1'b0;
                    if (tk && !sm_m) fv[K] <= 1'b0;
                    begin : sq
                        reg push, pop; reg [2:0] n;
                        push = res && sm_m; pop = tk && sm_m; n = scnt;
                        if (push && n == 3'd4 && !pop) ovr[K] <= 1'b1;
                        else if (push) begin sent[sw_] <= {gidx, rd_q[gs][32*gp +: 32]}; sw_ <= sw_ + 2'd1; end
                        if (pop) sr_ <= sr_ + 2'd1;
                        n = n + ((push && !(n == 3'd4 && !pop)) ? 3'd1 : 3'd0) - (pop ? 3'd1 : 3'd0);
                        scnt <= n; sv[K] <= (n != 3'd0);
                    end
                    if (chg || endf) begin                          // the buffer -> its pending flush
                        if (fv[K] && !tk) ovr[K] <= 1'b1;
                        fv[K] <= 1'b1; fsec <= bsec; fdat <= bdat; fmsk <= bmsk;
                        if (endf) bval[K] <= 1'b0;
                    end
                    if (res && !sm_m) begin
                        if (chg || !bval[K]) begin
                            bdat <= {224'd0, rd_q[gs][32*gp +: 32]} << {wd[2:0], 5'd0}; bmsk <= 8'd1 << wd[2:0];
                        end else begin
                            bdat <= bdat | ({224'd0, rd_q[gs][32*gp +: 32]} << {wd[2:0], 5'd0});
                            bmsk <= bmsk | (8'd1 << wd[2:0]);
                        end
                        bsec <= wd[17:3]; bval[K] <= 1'b1;
                    end
                end
            end
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; sm_m <= 1'b0; pub_done <= 1'b0; pub_fault <= 1'b0; qh <= 0; qt <= 0; qn <= 0; cbusy <= 0;
            vmq <= 0; s0_v <= 1'b0; s0_idx <= 20'd0; s0_data <= 32'd0; all_rows <= 1'b0;
            for (s = 0; s < NSM; s = s + 1) begin need[s] <= 0; recv[s] <= 0; end
        end else begin
            pub_done <= 1'b0; s0_v <= 1'b0;
            for (c = 0; c < NPC; c = c + 1) vmq[c*338 + 337] <= 1'b0;
            all_rows <= &rdone;
            if (|ovr) pub_fault <= 1'b1;                                    // overrun: fail closed
            if (pub_v && pub_rdy) begin
                if (!(pub_space == 2'd1 || pub_space == 2'd2) || pub_p == 4'd0 || pub_p > NC) pub_fault <= 1'b1;
                else begin
                    busy <= 1'b1; sm_m <= (pub_space == 2'd2); all_rows <= 1'b0;
                    ob <= pub_base[17:0]; ost <= pub_stride[17:0]; mm <= pub_m; qq <= pub_q; pp <= pub_p;
                    for (s = 0; s < NSM; s = s + 1) begin : nd
                        reg [19:0] r0; r0 = s * pub_q;
                        need[s] <= (pub_m > r0) ? (((pub_m - r0) > {7'd0, pub_q}) ? {7'd0, pub_q} : pub_m - r0) : 20'd0;
                        recv[s] <= 20'd0;
                    end
                end
            end
            for (s = 0; s < NSM; s = s + 1) if (busy && rv_q[s]) recv[s] <= recv[s] + 20'd1;
            // the granted entry: a STREAM beat out, or a flush into the FIFO (one write an edge)
            if (take) begin
                if (sm_m) begin s0_v <= 1'b1; {s0_idx, s0_data} <= shd_v[gk*52 +: 52]; end
                else begin qsec[qt] <= fsec_v[gk*15 +: 15]; qdat[qt] <= fdat_v[gk*256 +: 256]; qmsk[qt] <= fmsk_v[gk*8 +: 8]; end
            end
            // drain: the lowest free client takes the head (one pop an edge)
            begin : dr
                reg taken; taken = 1'b0;
                for (c = 0; c < NPC; c = c + 1)
                    if (!taken && !cbusy[c] && qn != 0) begin
                        vmq[c*338 +: 338] <= {1'b1, 1'b1, 12'd0, qsec[qh], 5'd0, qdat[qh],
                                              {{4{qmsk[qh][7]}}, {4{qmsk[qh][6]}}, {4{qmsk[qh][5]}}, {4{qmsk[qh][4]}},
                                               {4{qmsk[qh][3]}}, {4{qmsk[qh][2]}}, {4{qmsk[qh][1]}}, {4{qmsk[qh][0]}}}, 16'h5042};
                        cbusy[c] <= 1'b1; taken = 1'b1;
                    end
                qh <= qh + (taken ? 4'd1 : 4'd0);
                qt <= qt + ((take && !sm_m) ? 4'd1 : 4'd0);
                qn <= qn + ((take && !sm_m) ? 4'd1 : 4'd0) - (taken ? 4'd1 : 4'd0);
            end
            for (c = 0; c < NPC; c = c + 1) if (cbusy[c] && vr[c][273] && vr[c][256]) cbusy[c] <= 1'b0;
            if (busy && all_rows && &rdone && !pend_any && !take && qn == 0 && cbusy == 0) begin
                busy <= 1'b0; pub_done <= 1'b1; end
        end
    end
endmodule
`default_nettype wire
