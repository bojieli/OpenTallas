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
// O.fmt BF16 (pub_bf16, hgi-1010/d: the DS block-dot records' output, hgi_sim SM: out = to_bf16(csum)): each word is
// rounded to BF16 (RNE, NaN quieted, the golden to_bf16) as it leaves for VM / STREAM, stored as the BF16-valued FP32
// word (VM words are FP32); FP32 O words pass unchanged.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_pub_ff #(
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
    input  wire               pub_bf16,      // hgi-1010/d: O.fmt = BF16: every published word is to_bf16 (RNE) of the sum
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
    reg obf;
    function automatic [31:0] rb(input [31:0] x, input en);     // to_bf16 (RNE), as a BF16-valued FP32 word
        reg [31:0] r;
        begin
            if (!en) rb = x;
            else if (x[30:23] == 8'hFF && x[22:0] != 0) rb = {x[31:16] | 16'h0040, 16'd0};
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; rb = {r[31:16], 16'd0}; end
        end
    endfunction
    function automatic [255:0] rb8(input [255:0] x, input en);
        integer q; for (q = 0; q < 8; q = q + 1) rb8[32*q +: 32] = rb(x[32*q +: 32], en);
    endfunction
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
                    busy <= 1'b1; sm_m <= (pub_space == 2'd2); all_rows <= 1'b0; obf <= pub_bf16;
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
                if (sm_m) begin s0_v <= 1'b1; s0_idx <= shd_v[gk*52 + 32 +: 20]; s0_data <= rb(shd_v[gk*52 +: 32], obf); end
                else begin qsec[qt] <= fsec_v[gk*15 +: 15]; qdat[qt] <= fdat_v[gk*256 +: 256]; qmsk[qt] <= fmsk_v[gk*8 +: 8]; end
            end
            // drain: the lowest free client takes the head (one pop an edge)
            begin : dr
                reg taken; taken = 1'b0;
                for (c = 0; c < NPC; c = c + 1)
                    if (!taken && !cbusy[c] && qn != 0) begin
                        vmq[c*338 +: 338] <= {1'b1, 1'b1, 12'd0, qsec[qh], 5'd0, rb8(qdat[qh], obf),
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

// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_sm_pub_mem (hgi-1010/d, 2026-10-10): the SAME publication contract as ot_hgi_sm_pub_ff, built from banked SRAM
// with registered selects (feasibility review 67b2d0326: the flop form keeps 256 (SM, slot) sector buffers + pending
// flushes in flops behind a 256-way one-cycle grant).
//   Arrivals: every SM's result lands in its own AD-entry arrival FIFO (an SM result port has no ready: a full FIFO is an
//   overrun -> pub_fault, fail closed).  NE drain ENGINES, engine e owning SMs s == e (mod NE), each take ONE record an
//   edge through a 3-stage pipeline: B picks an SM (round robin, registered), C reads its FIFO head (registered index)
//   and forms the P word addresses O.base + p O.stride + s Q + r, D coalesces.
//   Coalescing: per (engine, slot p) ONE 128x256 SRAM, row = (SM local index, parity): the word is a masked write into
//   the (s, p) sector's current row; the sector's {sector, word mask, parity} live in flops.  A sector change enqueues
//   the old row as a pending flush (per (engine, slot) FIFO of row handles) and flips the parity; the row a flip lands on
//   must be flushed already (else D waits).
//   Drain: one pending flush an edge (round robin over the (engine, slot) FIFOs, registered pick), its row read from the
//   SRAM, the sector written to VM (word-masked, BF16-rounded when O.fmt BF16) on the lowest free packet client.
//   End: when every row arrived and the engines are empty, every open sector is swept into the pending FIFOs.
//   STREAM (O space 2): D emits the record's P beats {s0_idx = p M + g, data}, one an edge (one engine at a time).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_pub_mem #(
    parameter integer NSM = 32,
    parameter integer NC = 8,
    parameter integer NPC = 4,
    parameter integer MUT_ROW = 0,         // mutant: the global row ignores s x Q
    parameter integer NE = 2,              // drain engines (NSM a multiple of NE)
    parameter integer AD = 4,              // arrival FIFO entries an SM
    parameter integer PQ = 4,              // pending flushes an (engine, slot)
    parameter integer MUT_PAR = 0          // mutant: a sector change does not flip the parity (the new sector's words land
                                           //   in the row still waiting to be flushed)
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
    input  wire               pub_bf16,
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
    localparam integer NSL = NSM / NE, LSL = (NSL > 1) ? $clog2(NSL) : 1, ADW = $clog2(AD), PQW = $clog2(PQ);
    localparam integer NQ = NE * NC;                       // pending FIFOs
    reg busy, sm_m, obf; reg [17:0] ob, ost; reg [19:0] mm; reg [12:0] qq; reg [3:0] pp;
    assign pub_rdy = !busy;
    function automatic [31:0] rb(input [31:0] x, input en);
        reg [31:0] r;
        begin
            if (!en) rb = x;
            else if (x[30:23] == 8'hFF && x[22:0] != 0) rb = {x[31:16] | 16'h0040, 16'd0};
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; rb = {r[31:16], 16'd0}; end
        end
    endfunction
    function automatic [255:0] rb8(input [255:0] x, input en);
        integer q; for (q = 0; q < 8; q = q + 1) rb8[32*q +: 32] = rb(x[32*q +: 32], en);
    endfunction
    integer s, c, i, p;
    // ---- capture (registered) and the per-SM arrival FIFOs
    reg [NSM-1:0] rv_q; reg [11:0] rr_q [0:NSM-1]; reg [NC*32-1:0] rd_q [0:NSM-1];
    always @(posedge clk) for (s = 0; s < NSM; s = s + 1) begin rv_q[s] <= sm_rv[s]; rr_q[s] <= sm_rrow[s*12 +: 12];
                                                                rd_q[s] <= sm_rdata[s*NC*32 +: NC*32]; end
    reg [11:0] af_r [0:NSM-1][0:AD-1]; reg [NC*32-1:0] af_d [0:NSM-1][0:AD-1];
    reg [ADW:0] af_n [0:NSM-1]; reg [ADW-1:0] af_h [0:NSM-1], af_t [0:NSM-1], af_k [0:NSM-1];  // count, head, tail, taken
    reg [ADW:0] af_tk [0:NSM-1];                           // entries taken by an engine, not yet consumed
    reg [19:0] need [0:NSM-1], recv [0:NSM-1]; reg all_rows; reg [NSM-1:0] rdone;
    always @* for (s = 0; s < NSM; s = s + 1) rdone[s] = (recv[s] == need[s]);
    reg ovr;
    // per-SM s x Q (registered at the command)
    reg [19:0] sq [0:NSM-1];
    // ---- engines
    reg  [NE-1:0] b_v, c_v, d_v, d_stall;
    reg  [LSL-1:0] b_i [0:NE-1], c_i [0:NE-1], d_i [0:NE-1], rrp [0:NE-1];
    reg  [ADW-1:0] b_h [0:NE-1];
    reg  [11:0] c_r [0:NE-1]; reg [NC*32-1:0] c_d [0:NE-1], d_d [0:NE-1];
    reg  [17:0] d_wa [0:NE-1][0:NC-1]; reg [19:0] d_gi [0:NE-1][0:NC-1];
    reg  [3:0] d_sp [0:NE-1];                              // STREAM: the next slot to emit
    // coalescing state per (engine, local SM, slot): sector, mask, parity; pending flag per parity row
    reg  [14:0] k_sec [0:NE-1][0:NSL-1][0:NC-1]; reg [7:0] k_msk [0:NE-1][0:NSL-1][0:NC-1];
    reg         k_par [0:NE-1][0:NSL-1][0:NC-1]; reg [1:0] k_pf [0:NE-1][0:NSL-1][0:NC-1];
    // pending flush FIFOs per (engine, slot): {local SM, parity, sector, mask}
    reg  [LSL+24-1:0] pq_e [0:NQ-1][0:PQ-1]; reg [PQW:0] pq_n [0:NQ-1]; reg [PQW-1:0] pq_h [0:NQ-1], pq_t [0:NQ-1];
    // SRAM ports per (engine, slot)
    reg  [NQ-1:0] m_we, m_re; reg [6:0] m_wa [0:NQ-1], m_ra [0:NQ-1]; reg [255:0] m_wd [0:NQ-1], m_wm [0:NQ-1];
    wire [255:0] m_rd [0:NQ-1];
    genvar gq;
    generate for (gq = 0; gq < NQ; gq = gq + 1) begin : g_m
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(m_re[gq]), .r_addr_in(m_ra[gq]), .rd_out(m_rd[gq]),
            .w_ce_in(m_we[gq]), .w_addr_in(m_wa[gq]), .wd_in(m_wd[gq]), .w_mask_in(m_wm[gq]), .rr_en(2'b00),
            .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // drain: the registered pick of a pending FIFO, its row read, then the client issue
    reg dr_v; reg [$clog2(NQ > 1 ? NQ : 2)-1:0] dr_q, dr_rr; reg [LSL+24-1:0] dr_e;
    reg dr_v2; reg [$clog2(NQ > 1 ? NQ : 2)-1:0] dr_q2; reg [LSL+24-1:0] dr_e2;   // the SRAM read in flight (its port registered)
    // read rows waiting for a client: a 4-entry FIFO, so a read in flight always has a place (a pick needs room for every
    // read in flight; the SRAM's output register is never relied on past its edge)
    reg [255:0] hq_d [0:3]; reg [14:0] hq_s [0:3]; reg [7:0] hq_m [0:3]; reg [2:0] hq_n; reg [1:0] hq_h, hq_t;
    wire dh_v = hq_n != 0; wire [255:0] dh_d = hq_d[hq_h]; wire [14:0] dh_sec = hq_s[hq_h]; wire [7:0] dh_msk = hq_m[hq_h];
    reg [NPC-1:0] cbusy; reg [273:0] vr [0:NPC-1];
    always @(posedge clk) for (c = 0; c < NPC; c = c + 1) vr[c] <= vmr[c*274 +: 274];
    // sweep at the end
    reg sweep; reg [LSL:0] sw_i [0:NE-1];
    // STREAM arbitration: one engine's beat an edge
    reg [NE-1:0] s_req; reg [$clog2(NE > 1 ? NE : 2)-1:0] s_rr;
    reg pend_any;
    always @* begin
        pend_any = 1'b0;
        for (c = 0; c < NQ; c = c + 1) if (pq_n[c] != 0) pend_any = 1'b1;
        if (dr_v || dr_v2 || dh_v || |b_v || |c_v || |d_v) pend_any = 1'b1;
        for (s = 0; s < NSM; s = s + 1) if (af_n[s] != 0) pend_any = 1'b1;
    end
    reg arr_empty;
    always @* begin arr_empty = 1'b1; for (s = 0; s < NSM; s = s + 1) if (af_n[s] != 0) arr_empty = 1'b0; end
    reg sw_all;
    always @* begin sw_all = 1'b1; for (c = 0; c < NE; c = c + 1) if (sw_i[c] < NSL) sw_all = 1'b0; end
    reg open_any;                                          // any (engine, SM, slot) sector still open
    always @* begin
        open_any = 1'b0;
        for (c = 0; c < NE; c = c + 1) for (i = 0; i < NSL; i = i + 1) for (p = 0; p < NC; p = p + 1)
            if (k_msk[c][i][p] != 0) open_any = 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; sm_m <= 1'b0; obf <= 1'b0; pub_done <= 1'b0; pub_fault <= 1'b0; vmq <= '0; s0_v <= 1'b0;
            s0_idx <= '0; s0_data <= '0; all_rows <= 1'b0; ovr <= 1'b0; cbusy <= '0; dr_v <= 1'b0; dr_rr <= '0;
            dr_v2 <= 1'b0; hq_n <= 3'd0; hq_h <= 2'd0; hq_t <= 2'd0;
            b_v <= '0; c_v <= '0; d_v <= '0; sweep <= 1'b0; s_rr <= '0; m_we <= '0; m_re <= '0;
            for (s = 0; s < NSM; s = s + 1) begin af_n[s] <= '0; af_h[s] <= '0; af_t[s] <= '0; af_tk[s] <= '0; af_k[s] <= '0;
                                                  need[s] <= '0; recv[s] <= '0; end
            for (c = 0; c < NE; c = c + 1) begin rrp[c] <= '0; d_sp[c] <= 4'd0; sw_i[c] <= '0;
                for (i = 0; i < NSL; i = i + 1) for (p = 0; p < NC; p = p + 1) begin
                    k_msk[c][i][p] <= 8'd0; k_par[c][i][p] <= 1'b0; k_pf[c][i][p] <= 2'b00; end end
            for (c = 0; c < NQ; c = c + 1) begin pq_n[c] <= '0; pq_h[c] <= '0; pq_t[c] <= '0; end
        end else begin : main
            reg [ADW:0] an [0:NSM-1]; reg [ADW:0] atk [0:NSM-1]; reg [PQW:0] qn_ [0:NQ-1];
            reg [1:0] pf_ [0:NE-1][0:NSL-1][0:NC-1];
            reg ok, dr_go; integer e, q_, sl;
            pub_done <= 1'b0; s0_v <= 1'b0; m_we <= '0; m_re <= '0;
            for (c = 0; c < NPC; c = c + 1) vmq[c*338 + 337] <= 1'b0;
            all_rows <= &rdone;
            for (s = 0; s < NSM; s = s + 1) begin an[s] = af_n[s]; atk[s] = af_tk[s]; end
            for (c = 0; c < NQ; c = c + 1) qn_[c] = pq_n[c];
            for (e = 0; e < NE; e = e + 1) for (i = 0; i < NSL; i = i + 1) for (p = 0; p < NC; p = p + 1)
                pf_[e][i][p] = k_pf[e][i][p];
            // ---- a command
            if (pub_v && pub_rdy) begin
                if (!(pub_space == 2'd1 || pub_space == 2'd2) || pub_p == 4'd0 || pub_p > NC) pub_fault <= 1'b1;
                else begin
                    busy <= 1'b1; sm_m <= (pub_space == 2'd2); all_rows <= 1'b0; obf <= pub_bf16; sweep <= 1'b0;
                    ob <= pub_base[17:0]; ost <= pub_stride[17:0]; mm <= pub_m; qq <= pub_q; pp <= pub_p;
                    for (s = 0; s < NSM; s = s + 1) begin : nd
                        reg [19:0] r0; r0 = s * pub_q;
                        need[s] <= (pub_m > r0) ? (((pub_m - r0) > {7'd0, pub_q}) ? {7'd0, pub_q} : pub_m - r0) : 20'd0;
                        recv[s] <= 20'd0; sq[s] <= MUT_ROW ? 20'd0 : r0;
                    end
                end
            end
            // ---- arrivals
            for (s = 0; s < NSM; s = s + 1) if (busy && rv_q[s]) begin
                recv[s] <= recv[s] + 20'd1;
                if (an[s] == AD) pub_fault <= 1'b1;               // overrun: fail closed
                else begin af_r[s][af_t[s]] <= rr_q[s]; af_d[s][af_t[s]] <= rd_q[s]; af_t[s] <= af_t[s] + 1'b1; an[s] = an[s] + 1'b1; end
            end
            // ---- STREAM: one engine's beat an edge (registered round robin)
            for (e = 0; e < NE; e = e + 1) s_req[e] = 1'b0;
            begin : sarb
                reg f; f = 1'b0;
                for (e = 0; e < NE; e = e + 1) begin q_ = (s_rr + 1 + e) % NE;
                    if (!f && d_v[q_] && sm_m) begin f = 1'b1; s_rr <= q_; s_req[q_] = 1'b1;
                        s0_v <= 1'b1; s0_idx <= d_gi[q_][d_sp[q_]]; s0_data <= rb(d_d[q_][32*d_sp[q_] +: 32], obf);
                    end
                end
            end
            // ---- engines
            for (e = 0; e < NE; e = e + 1) begin
                // D: coalesce (VM) / emit (STREAM); may stall
                ok = 1'b1;
                if (d_v[e] && !sm_m) begin
                    for (p = 0; p < NC; p = p + 1) if (p < pp) begin : chk
                        reg [14:0] sc; reg ch; reg np;
                        sc = d_wa[e][p][17:3]; ch = (k_msk[e][d_i[e]][p] != 0) && (k_sec[e][d_i[e]][p] != sc);
                        np = MUT_PAR ? k_par[e][d_i[e]][p] : !k_par[e][d_i[e]][p];
                        if (ch && (qn_[e*NC + p] == PQ || pf_[e][d_i[e]][p][np])) ok = 1'b0;
                    end
                    if (ok) begin
                        for (p = 0; p < NC; p = p + 1) if (p < pp) begin : co
                            reg [14:0] sc; reg [2:0] w; reg ch; reg par; integer qx;
                            qx = e * NC + p; sl = d_i[e];
                            sc = d_wa[e][p][17:3]; w = d_wa[e][p][2:0];
                            ch = (k_msk[e][sl][p] != 0) && (k_sec[e][sl][p] != sc);
                            par = k_par[e][sl][p];
                            if (ch) begin                          // the old sector -> a pending flush; flip the parity
                                pq_e[qx][pq_t[qx]] <= {LSL'(sl), par, k_sec[e][sl][p], k_msk[e][sl][p]};
                                pq_t[qx] <= pq_t[qx] + 1'b1; qn_[qx] = qn_[qx] + 1'b1;
                                pf_[e][sl][p][par] = 1'b1;
                                par = MUT_PAR ? par : !par;
                                k_par[e][sl][p] <= par;
                            end
                            m_we[qx] <= 1'b1; m_wa[qx] <= 7'({LSL'(sl), par});
                            m_wd[qx] <= {8{d_d[e][32*p +: 32]}}; m_wm[qx] <= {224'd0, 32'hFFFF_FFFF} << {w, 5'd0};
                            k_sec[e][sl][p] <= sc;
                            k_msk[e][sl][p] <= (ch || k_msk[e][sl][p] == 0) ? (8'd1 << w) : (k_msk[e][sl][p] | (8'd1 << w));
                        end
                        d_v[e] <= 1'b0;
                        s = e + NE * d_i[e]; atk[s] = atk[s] - 1'b1; an[s] = an[s] - 1'b1;     // the entry is consumed
                    end
                end else if (d_v[e] && sm_m) begin
                    ok = 1'b0;
                    if (s_req[e]) begin                           // granted this edge (below): one beat out
                        if (d_sp[e] + 4'd1 >= pp) begin d_v[e] <= 1'b0; d_sp[e] <= 4'd0; ok = 1'b1;
                            s = e + NE * d_i[e]; atk[s] = atk[s] - 1'b1; an[s] = an[s] - 1'b1; end
                        else d_sp[e] <= d_sp[e] + 4'd1;
                    end
                end
                d_stall[e] = d_v[e] && !ok;
                // C -> D: the FIFO head (registered index) and its P addresses
                if (c_v[e] && !d_stall[e]) begin
                    s = e + NE * c_i[e];
                    d_v[e] <= 1'b1; d_i[e] <= c_i[e]; d_d[e] <= af_d[s][b_h[e]];
                    for (p = 0; p < NC; p = p + 1) begin
                        d_wa[e][p] <= ob + 18'(p * ost) + sq[s][17:0] + {6'd0, af_r[s][b_h[e]]};
                        d_gi[e][p] <= 20'(p * mm) + sq[s] + {8'd0, af_r[s][b_h[e]]};
                    end
                    c_v[e] <= 1'b0;
                end
                // B -> C: pick an SM with an untaken entry (round robin from rrp)
                if (!(c_v[e] && d_stall[e])) begin : pick
                    reg f; reg [LSL-1:0] ix;
                    f = 1'b0; ix = '0;
                    for (i = 0; i < NSL; i = i + 1) begin
                        sl = (rrp[e] + 1 + i) % NSL; s = e + NE * sl;
                        if (!f && an[s] > atk[s] && busy) begin f = 1'b1; ix = LSL'(sl); end
                    end
                    if (f) begin
                        s = e + NE * ix;
                        c_v[e] <= 1'b1; c_i[e] <= ix; b_h[e] <= af_k[s]; af_k[s] <= af_k[s] + 1'b1; atk[s] = atk[s] + 1'b1;
                        rrp[e] <= ix;
                    end
                end
            end
            // consumed entries leave the FIFO head
            for (s = 0; s < NSM; s = s + 1) begin
                af_h[s] <= af_h[s] + ADW'(af_n[s] - an[s] + ((busy && rv_q[s] && af_n[s] != AD) ? 1 : 0));
                af_n[s] <= an[s]; af_tk[s] <= atk[s];
            end
            // ---- end sweep: every open sector -> a pending flush (an (engine, slot) a row an edge)
            if (busy && !sm_m && all_rows && &rdone && arr_empty && c_v == 0 && d_v == 0 && !sweep) begin
                sweep <= 1'b1; for (e = 0; e < NE; e = e + 1) sw_i[e] <= '0;
            end
            if (sweep) for (e = 0; e < NE; e = e + 1) if (sw_i[e] < NSL) begin : swp
                reg go; sl = sw_i[e]; go = 1'b1;
                for (p = 0; p < NC; p = p + 1) if (k_msk[e][sl][p] != 0 && qn_[e*NC + p] == PQ) go = 1'b0;
                if (go) begin
                    for (p = 0; p < NC; p = p + 1) if (k_msk[e][sl][p] != 0) begin : sp
                        integer qx; qx = e * NC + p;
                        pq_e[qx][pq_t[qx]] <= {LSL'(sl), k_par[e][sl][p], k_sec[e][sl][p], k_msk[e][sl][p]};
                        pq_t[qx] <= pq_t[qx] + 1'b1; qn_[qx] = qn_[qx] + 1'b1;
                        pf_[e][sl][p][k_par[e][sl][p]] = 1'b1; k_msk[e][sl][p] <= 8'd0;
                    end
                    sw_i[e] <= sw_i[e] + 1'b1;
                end
            end
            // ---- drain: issue the held row to a free client; read the picked row; pick the next pending FIFO
            begin : dr
                reg taken; taken = 1'b0;
                if (dh_v) for (c = 0; c < NPC; c = c + 1)
                    if (!taken && !cbusy[c]) begin
                        vmq[c*338 +: 338] <= {1'b1, 1'b1, 12'd0, dh_sec, 5'd0, rb8(dh_d, obf),
                                              {{4{dh_msk[7]}}, {4{dh_msk[6]}}, {4{dh_msk[5]}}, {4{dh_msk[4]}},
                                               {4{dh_msk[3]}}, {4{dh_msk[2]}}, {4{dh_msk[1]}}, {4{dh_msk[0]}}}, 16'h5042};
                        cbusy[c] <= 1'b1; taken = 1'b1;
                    end
                // the SRAM row read (registered port: issued one edge after the pick, data the edge after) -> the FIFO
                begin : mv
                    reg [2:0] n_;
                    n_ = hq_n - (taken ? 3'd1 : 3'd0);
                    if (taken) hq_h <= hq_h + 2'd1;
                    if (dr_v2) begin
                        hq_d[hq_t] <= m_rd[dr_q2]; hq_s[hq_t] <= dr_e2[22:8]; hq_m[hq_t] <= dr_e2[7:0]; hq_t <= hq_t + 2'd1;
                        n_ = n_ + 3'd1;
                        begin : clr reg [LSL-1:0] lsl; integer ee, pp2; ee = dr_q2 / NC; pp2 = dr_q2 % NC;
                            lsl = dr_e2[LSL+23:24]; pf_[ee][lsl][pp2][dr_e2[23]] = 1'b0; end
                    end
                    hq_n <= n_;
                    dr_v2 <= dr_v; dr_q2 <= dr_q; dr_e2 <= dr_e; dr_v <= 1'b0;
                    // a pick needs room for itself and the reads in flight
                    dr_go = (n_ + (dr_v ? 3'd1 : 3'd0)) < 3'd4;
                end
                if (dr_go) begin : pk
                    reg f; f = 1'b0;
                    for (c = 0; c < NQ; c = c + 1) begin q_ = (dr_rr + 1 + c) % NQ;
                        if (!f && pq_n[q_] != 0) begin
                            f = 1'b1; dr_rr <= q_; dr_q <= q_; dr_e <= pq_e[q_][pq_h[q_]]; dr_v <= 1'b1;
                            m_re[q_] <= 1'b1; m_ra[q_] <= 7'({pq_e[q_][pq_h[q_]][LSL+23:24], pq_e[q_][pq_h[q_]][23]});
                            pq_h[q_] <= pq_h[q_] + 1'b1; qn_[q_] = qn_[q_] - 1'b1;
                        end
                    end
                end
            end
            for (c = 0; c < NPC; c = c + 1) if (cbusy[c] && vr[c][273] && vr[c][256]) cbusy[c] <= 1'b0;
            for (c = 0; c < NQ; c = c + 1) pq_n[c] <= qn_[c];
            for (e = 0; e < NE; e = e + 1) for (i = 0; i < NSL; i = i + 1) for (p = 0; p < NC; p = p + 1)
                k_pf[e][i][p] <= pf_[e][i][p];
            // ---- done: every row in, swept (VM) / emitted (STREAM), nothing pending, every write acknowledged
            if (busy && all_rows && &rdone && !pend_any && cbusy == 0 && (sm_m || (sweep && !open_any && sw_all))) begin
                busy <= 1'b0; pub_done <= 1'b1; sweep <= 1'b0;
            end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_sm_pub: the publication peer. MEM = 1 (default, hgi-1010/d): the banked-SRAM form ot_hgi_sm_pub_mem; MEM = 0:
// the flop form ot_hgi_sm_pub_ff (kept as the reference of tb_hgi_pub_lock).  Same ports and transaction contract.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_pub #(
    parameter integer NSM = 32,
    parameter integer NC = 8,
    parameter integer NPC = 4,
    parameter integer MUT_ROW = 0,
    parameter integer MEM = 1,
    parameter integer NE = 2,
    parameter integer MUT_PAR = 0
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
    input  wire               pub_bf16,
    output wire               pub_done,
    output wire               pub_fault,
    input  wire [NSM-1:0]     sm_rv,
    input  wire [NSM*12-1:0]  sm_rrow,
    input  wire [NSM*NC*32-1:0] sm_rdata,
    output wire [NPC*338-1:0] vmq,
    input  wire [NPC*274-1:0] vmr,
    output wire               s0_v,
    output wire [19:0]        s0_idx,
    output wire [31:0]        s0_data
);
    generate if (MEM) begin : g_mem
        ot_hgi_sm_pub_mem #(.NSM(NSM), .NC(NC), .NPC(NPC), .MUT_ROW(MUT_ROW), .NE((NSM % NE == 0) ? NE : 1), .MUT_PAR(MUT_PAR)) u (
            .clk(clk), .rst_n(rst_n), .pub_v(pub_v), .pub_rdy(pub_rdy), .pub_base(pub_base), .pub_stride(pub_stride),
            .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16), .pub_done(pub_done),
            .pub_fault(pub_fault), .sm_rv(sm_rv), .sm_rrow(sm_rrow), .sm_rdata(sm_rdata), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
            .s0_idx(s0_idx), .s0_data(s0_data));
    end else begin : g_ff
        ot_hgi_sm_pub_ff #(.NSM(NSM), .NC(NC), .NPC(NPC), .MUT_ROW(MUT_ROW)) u (
            .clk(clk), .rst_n(rst_n), .pub_v(pub_v), .pub_rdy(pub_rdy), .pub_base(pub_base), .pub_stride(pub_stride),
            .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16), .pub_done(pub_done),
            .pub_fault(pub_fault), .sm_rv(sm_rv), .sm_rrow(sm_rrow), .sm_rdata(sm_rdata), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
            .s0_idx(s0_idx), .s0_data(s0_data));
    end endgenerate
endmodule
`default_nettype wire
