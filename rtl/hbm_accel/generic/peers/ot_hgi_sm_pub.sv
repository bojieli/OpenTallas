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
// HIER form (el1011-hbm-smh/pub, 2026-10-11; physical spec in claude-takeover-20261007/el1011-hbm-smh.log): the SAME
// publication contract built from 8 hardened slices of 4 SMs (ot_hgi_sm_pub_slice, own clock tree <= ~13k sinks, own
// reset relay, pin flops in, registered out) under a parent (ot_hgi_sm_pub_hier) that only relays the command, merges
// the VM writes per client (2:1) and the STREAM beats (registered 2:1 credit tree) and collects done / fault.
// Selected by ot_hgi_sm_pub HIER = 1 (default 0; `define OT_HGI_PUB_HIER flips the default for the benches).
// Differences from MEM 1 (transaction-level exact): added cycles only; a slice PRE-ARMS (rows that arrive before the
// command reaches it are queued and counted, never dropped).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_pub_slice #(
    parameter integer NSS = 4,             // SMs in the slice
    parameter integer NC = 8,
    parameter integer AD = 4,              // arrival FIFO entries an SM
    parameter integer PQ = 4,              // pending flushes a slot
    parameter integer SD = 8,              // STREAM credits (the parent's input FIFO depth)
    parameter integer SIDW = 3,
    parameter integer MUT_ROW = 0,
    parameter integer MUT_PAR = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,          // raw port reset -> own ot_rst_relay
    input  wire [SIDW-1:0]      sid,            // static strap: slice index (global SM = sid x NSS + local)
    input  wire [NSS-1:0]       sm_en,          // static strap: the local SM exists
    input  wire                 c_go,           // command (the parent's relay): one-edge pulse, fields valid with it
    input  wire                 c_sm,
    input  wire                 c_bf,
    input  wire [17:0]          c_ob,
    input  wire [17:0]          c_ost,
    input  wire [19:0]          c_mm,
    input  wire [12:0]          c_qq,
    input  wire [3:0]           c_pp,
    input  wire [NSS-1:0]       sm_rv,
    input  wire [NSS*12-1:0]    sm_rrow,
    input  wire [NSS*NC*32-1:0] sm_rdata,
    output reg                  w_v,            // one-edge pulse: w_pkt holds a VM sector write (held until w_ack)
    output reg  [278:0]         w_pkt,          // {sector 15, data 256 (BF16-rounded when O.fmt BF16), word mask 8}
    input  wire                 w_ack,          // one-edge pulse: that write was acknowledged
    output reg                  so_v,
    output reg  [19:0]          so_idx,
    output reg  [31:0]          so_data,
    input  wire                 so_cr,          // one-edge pulse: one STREAM credit back
    output reg                  s_done,         // one-edge pulse: this slice's share of the command is complete
    output reg                  s_fault         // sticky: an arrival FIFO overrun
);
    localparam integer LSL = (NSS > 1) ? $clog2(NSS) : 1, ADW = (AD > 1) ? $clog2(AD) : 1, PQW = (PQ > 1) ? $clog2(PQ) : 1;
    localparam integer LNC = (NC > 1) ? $clog2(NC) : 1, SDW = $clog2(SD + 1);
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
    integer s, c, i, p;
    // ---- reset relay (control only)
    wire rn;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    // ---- pin flops: command, SM results, ack / credit
    reg k_go, k_sm, k_bf; reg [17:0] k_ob, k_ost; reg [19:0] k_mm; reg [12:0] k_qq; reg [3:0] k_pp;
    reg [NSS-1:0] rv_q; reg [11:0] rr_q [0:NSS-1]; reg [NC*32-1:0] rd_q [0:NSS-1];
    reg ack_q, cr_q;
    always @(posedge clk) begin
        k_sm <= c_sm; k_bf <= c_bf; k_ob <= c_ob; k_ost <= c_ost; k_mm <= c_mm; k_qq <= c_qq; k_pp <= c_pp;
        for (s = 0; s < NSS; s = s + 1) begin rr_q[s] <= sm_rrow[s*12 +: 12]; rd_q[s] <= sm_rdata[s*NC*32 +: NC*32]; end
    end
    always @(posedge clk or negedge rn)
        if (!rn) begin k_go <= 1'b0; rv_q <= '0; ack_q <= 1'b0; cr_q <= 1'b0; end
        else begin k_go <= c_go; rv_q <= sm_rv; ack_q <= w_ack; cr_q <= so_cr; end
    // ---- the held command and its precomputed offsets
    reg busy, sm_m, obf, nv; reg [19:0] mm; reg [12:0] qq; reg [3:0] pp;
    reg [17:0] pofs [0:NC-1]; reg [19:0] pgi [0:NC-1];
    reg [19:0] sqc [0:NSS-1], need [0:NSS-1], recv [0:NSS-1];
    wire [19:0] sq [0:NSS-1];                         // s x Q of the global SM (MUT_ROW: 0 in the addresses only)
    genvar gsq;
    generate for (gsq = 0; gsq < NSS; gsq = gsq + 1) begin : g_sq
        assign sq[gsq] = MUT_ROW ? 20'd0 : sqc[gsq];
    end endgenerate
    reg [NSS-1:0] rdone; reg all_rows;
    always @* for (s = 0; s < NSS; s = s + 1) rdone[s] = (recv[s] == need[s]);
    // ---- arrival FIFOs (data unreset)
    reg [11:0] af_r [0:NSS-1][0:AD-1]; reg [NC*32-1:0] af_d [0:NSS-1][0:AD-1];
    reg [ADW:0] af_n [0:NSS-1]; reg [ADW-1:0] af_h [0:NSS-1], af_t [0:NSS-1];
    // ---- engine: P (pick) -> R (FIFO read, global row) -> D (addresses; coalesce / emit)
    reg p_v, r_v, d_v; reg [LSL-1:0] p_i, r_i, d_i, rrp; reg [19:0] r_row; reg [NC*32-1:0] r_d, d_d;
    reg [17:0] d_wa [0:NC-1]; reg [19:0] d_gi [0:NC-1]; reg [3:0] d_sp;
    // coalescing state per (local SM, slot)
    reg [14:0] k_sec [0:NSS-1][0:NC-1]; reg [7:0] k_msk [0:NSS-1][0:NC-1];
    reg        k_par [0:NSS-1][0:NC-1]; reg [1:0] k_pf [0:NSS-1][0:NC-1];
    // pending flush FIFOs per slot: {local SM, parity, sector, mask}
    reg [LSL+24-1:0] pq_e [0:NC-1][0:PQ-1]; reg [PQW:0] pq_n [0:NC-1]; reg [PQW-1:0] pq_h [0:NC-1], pq_t [0:NC-1];
    // SRAM write / read ports (registered); write data = the word replicated, mask = the word lane
    reg [NC-1:0] m_we, m_re; reg [6:0] m_wa [0:NC-1], m_ra [0:NC-1]; reg [31:0] m_wd [0:NC-1]; reg [2:0] m_ww [0:NC-1];
    wire [255:0] m_rd [0:NC-1];
    reg [255:0] m_cap [0:NC-1];                       // capture register at every macro output (no logic before it)
    genvar gq;
    generate for (gq = 0; gq < NC; gq = gq + 1) begin : g_m
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(m_re[gq]), .r_addr_in(m_ra[gq]), .rd_out(m_rd[gq]),
            .w_ce_in(m_we[gq]), .w_addr_in(m_wa[gq]), .wd_in({8{m_wd[gq]}}), .w_mask_in({224'd0, 32'hFFFF_FFFF} << {m_ww[gq], 5'd0}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // drain: pick (registered) -> SRAM read -> capture -> 2-entry row FIFO -> write packet
    reg dr_v, dr_v2, dr_v3; reg [LNC-1:0] dr_q, dr_q2, dr_q3, dr_rr; reg [LSL+24-1:0] dr_e, dr_e2, dr_e3;
    reg [255:0] hq_d [0:1]; reg [14:0] hq_s [0:1]; reg [7:0] hq_m [0:1]; reg [1:0] hq_n; reg hq_h, hq_t;
    reg tok;                                            // a write is out, not yet acknowledged
    reg [SDW-1:0] cr;                                   // STREAM credits
    reg sweep; reg [LSL:0] sw_i;
    reg pend_any, open_q;
    always @* begin
        pend_any = dr_v || dr_v2 || dr_v3 || hq_n != 0 || p_v || r_v || d_v;
        for (c = 0; c < NC; c = c + 1) if (pq_n[c] != 0) pend_any = 1'b1;
        for (s = 0; s < NSS; s = s + 1) if (af_n[s] != 0) pend_any = 1'b1;
    end
    reg arr_empty;
    always @* begin arr_empty = 1'b1; for (s = 0; s < NSS; s = s + 1) if (af_n[s] != 0) arr_empty = 1'b0; end
    // data-only registers (no reset)
    always @(posedge clk) for (c = 0; c < NC; c = c + 1) if (dr_v2 && dr_q2 == c) m_cap[c] <= m_rd[c];
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            busy <= 1'b0; sm_m <= 1'b0; obf <= 1'b0; nv <= 1'b0; all_rows <= 1'b0; s_done <= 1'b0; s_fault <= 1'b0;
            w_v <= 1'b0; so_v <= 1'b0; tok <= 1'b0; cr <= SDW'(SD); sweep <= 1'b0; sw_i <= '0; open_q <= 1'b0;
            p_v <= 1'b0; r_v <= 1'b0; d_v <= 1'b0; rrp <= '0; d_sp <= 4'd0; m_we <= '0; m_re <= '0;
            dr_v <= 1'b0; dr_v2 <= 1'b0; dr_v3 <= 1'b0; dr_rr <= '0; hq_n <= 2'd0; hq_h <= 1'b0; hq_t <= 1'b0;
            for (s = 0; s < NSS; s = s + 1) begin af_n[s] <= '0; af_h[s] <= '0; af_t[s] <= '0; recv[s] <= '0; need[s] <= '0; end
            for (i = 0; i < NSS; i = i + 1) for (p = 0; p < NC; p = p + 1) begin
                k_msk[i][p] <= 8'd0; k_par[i][p] <= 1'b0; k_pf[i][p] <= 2'b00; end
            for (c = 0; c < NC; c = c + 1) begin pq_n[c] <= '0; pq_h[c] <= '0; pq_t[c] <= '0; end
        end else begin : main
            reg [ADW:0] an [0:NSS-1]; reg [PQW:0] qn_ [0:NC-1]; reg [1:0] pf_ [0:NSS-1][0:NC-1];
            reg ok, d_stall, r_hold, beat, dr_go, done_now; integer sl;
            s_done <= 1'b0; w_v <= 1'b0; so_v <= 1'b0; m_we <= '0; m_re <= '0;
            for (s = 0; s < NSS; s = s + 1) an[s] = af_n[s];
            for (c = 0; c < NC; c = c + 1) qn_[c] = pq_n[c];
            for (i = 0; i < NSS; i = i + 1) for (p = 0; p < NC; p = p + 1) pf_[i][p] = k_pf[i][p];
            begin : opn
                reg o; o = 1'b0;
                for (i = 0; i < NSS; i = i + 1) for (p = 0; p < NC; p = p + 1) if (k_msk[i][p] != 0) o = 1'b1;
                open_q <= o;
            end
            // ---- the command (fields from the pin flops); need follows one edge later
            nv <= busy;
            all_rows <= nv && busy && &rdone;
            if (k_go) begin
                busy <= 1'b1; sm_m <= k_sm; obf <= k_bf; mm <= k_mm; qq <= k_qq; pp <= k_pp; nv <= 1'b0; all_rows <= 1'b0;
                sweep <= 1'b0;
                for (p = 0; p < NC; p = p + 1) begin pofs[p] <= k_ob + 18'(p * k_ost); pgi[p] <= 20'(p * k_mm); end
                for (s = 0; s < NSS; s = s + 1) sqc[s] <= 20'(({17'd0, sid} * NSS + s) * {7'd0, k_qq});
            end
            if (busy && !nv)
                for (s = 0; s < NSS; s = s + 1) begin : nd
                    reg [19:0] r0; r0 = sqc[s];
                    need[s] <= !sm_en[s] ? 20'd0 : (mm > r0) ? (((mm - r0) > {7'd0, qq}) ? {7'd0, qq} : mm - r0) : 20'd0;
                end
            // ---- arrivals (pre-armed: counted and queued whether or not the command has arrived)
            for (s = 0; s < NSS; s = s + 1) if (rv_q[s]) begin
                recv[s] <= recv[s] + 20'd1;
                if (an[s] == AD) s_fault <= 1'b1;                           // overrun: fail closed
                else begin af_r[s][af_t[s]] <= rr_q[s]; af_d[s][af_t[s]] <= rd_q[s]; af_t[s] <= af_t[s] + 1'b1; an[s] = an[s] + 1'b1; end
            end
            // ---- D: coalesce (VM) / emit (STREAM)
            ok = 1'b1; beat = 1'b0;
            if (d_v && !sm_m) begin
                for (p = 0; p < NC; p = p + 1) if (p < pp) begin : chk
                    reg [14:0] sc; reg ch; reg np;
                    sc = d_wa[p][17:3]; ch = (k_msk[d_i][p] != 0) && (k_sec[d_i][p] != sc);
                    np = MUT_PAR ? k_par[d_i][p] : !k_par[d_i][p];
                    if (ch && (qn_[p] == PQ || pf_[d_i][p][np])) ok = 1'b0;
                end
                if (ok) begin
                    for (p = 0; p < NC; p = p + 1) if (p < pp) begin : co
                        reg [14:0] sc; reg [2:0] w; reg ch; reg par;
                        sl = d_i; sc = d_wa[p][17:3]; w = d_wa[p][2:0];
                        ch = (k_msk[sl][p] != 0) && (k_sec[sl][p] != sc);
                        par = k_par[sl][p];
                        if (ch) begin                                       // the old sector -> a pending flush
                            pq_e[p][pq_t[p]] <= {LSL'(sl), par, k_sec[sl][p], k_msk[sl][p]};
                            pq_t[p] <= pq_t[p] + 1'b1; qn_[p] = qn_[p] + 1'b1;
                            pf_[sl][p][par] = 1'b1;
                            par = MUT_PAR ? par : !par;
                            k_par[sl][p] <= par;
                        end
                        m_we[p] <= 1'b1; m_wa[p] <= 7'({LSL'(sl), par}); m_wd[p] <= d_d[32*p +: 32]; m_ww[p] <= w;
                        k_sec[sl][p] <= sc;
                        k_msk[sl][p] <= (ch || k_msk[sl][p] == 0) ? (8'd1 << w) : (k_msk[sl][p] | (8'd1 << w));
                    end
                    d_v <= 1'b0;
                end
            end else if (d_v && sm_m) begin
                ok = 1'b0;
                if (cr != 0) begin                                          // one beat an edge, against a credit
                    beat = 1'b1;
                    so_v <= 1'b1; so_idx <= d_gi[d_sp]; so_data <= rb(d_d[32*d_sp +: 32], obf);
                    if (d_sp + 4'd1 >= pp) begin d_v <= 1'b0; d_sp <= 4'd0; ok = 1'b1; end
                    else d_sp <= d_sp + 4'd1;
                end
            end
            cr <= cr - (beat ? 1'b1 : 1'b0) + (cr_q ? 1'b1 : 1'b0);
            d_stall = d_v && !ok;
            r_hold = r_v && d_stall;
            // ---- R -> D: the P addresses
            if (r_v && !d_stall) begin
                d_v <= 1'b1; d_i <= r_i; d_d <= r_d;
                for (p = 0; p < NC; p = p + 1) begin d_wa[p] <= pofs[p] + r_row[17:0]; d_gi[p] <= pgi[p] + r_row; end
                r_v <= 1'b0;
            end
            // ---- P -> R: read (and pop) the picked SM's FIFO head
            if (p_v && !r_hold) begin
                r_v <= 1'b1; r_i <= p_i; r_d <= af_d[p_i][af_h[p_i]]; r_row <= sq[p_i] + {8'd0, af_r[p_i][af_h[p_i]]};
                af_h[p_i] <= af_h[p_i] + 1'b1; an[p_i] = an[p_i] - 1'b1;
                p_v <= 1'b0;
            end
            // ---- P: pick an SM with a queued row (round robin), once the command (and sq) is in
            if (busy && !k_go && !(p_v && r_hold)) begin : pick
                reg f; reg [LSL-1:0] ix; integer q2;
                f = 1'b0; ix = '0;
                for (i = 0; i < NSS; i = i + 1) begin
                    q2 = (rrp + 1 + i) % NSS;
                    if (!f && an[q2] != 0) begin f = 1'b1; ix = LSL'(q2); end
                end
                if (f) begin p_v <= 1'b1; p_i <= ix; rrp <= ix; end
            end
            for (s = 0; s < NSS; s = s + 1) af_n[s] <= an[s];
            // ---- end sweep (VM): every open sector -> a pending flush (a local SM an edge)
            if (busy && !sm_m && nv && all_rows && &rdone && arr_empty && !p_v && !r_v && !d_v && !sweep) begin
                sweep <= 1'b1; sw_i <= '0;
            end
            if (sweep && sw_i < NSS) begin : swp
                reg go; sl = sw_i; go = 1'b1;
                for (p = 0; p < NC; p = p + 1) if (k_msk[sl][p] != 0 && qn_[p] == PQ) go = 1'b0;
                if (go) begin
                    for (p = 0; p < NC; p = p + 1) if (k_msk[sl][p] != 0) begin
                        pq_e[p][pq_t[p]] <= {LSL'(sl), k_par[sl][p], k_sec[sl][p], k_msk[sl][p]};
                        pq_t[p] <= pq_t[p] + 1'b1; qn_[p] = qn_[p] + 1'b1;
                        pf_[sl][p][k_par[sl][p]] = 1'b1; k_msk[sl][p] <= 8'd0;
                    end
                    sw_i <= sw_i + 1'b1;
                end
            end
            // ---- drain: issue the row FIFO head (one write out at a time); capture; read; pick
            begin : dr
                reg taken; reg [1:0] n_;
                taken = hq_n != 0 && !tok;
                if (taken) begin
                    w_v <= 1'b1; w_pkt <= {hq_s[hq_h], rb8(hq_d[hq_h], obf), hq_m[hq_h]}; tok <= 1'b1; hq_h <= ~hq_h;
                end
                if (ack_q) tok <= 1'b0;
                n_ = hq_n - (taken ? 2'd1 : 2'd0);
                if (dr_v3) begin                                            // the captured row -> the row FIFO
                    hq_d[hq_t] <= m_cap[dr_q3]; hq_s[hq_t] <= dr_e3[22:8]; hq_m[hq_t] <= dr_e3[7:0]; hq_t <= ~hq_t;
                    n_ = n_ + 2'd1;
                end
                if (dr_v2) begin : clr                                      // the row is read (capture this edge): free it
                    reg [LSL-1:0] lsl; lsl = dr_e2[LSL+23:24]; pf_[lsl][dr_q2][dr_e2[23]] = 1'b0;
                end
                hq_n <= n_;
                dr_v3 <= dr_v2; dr_q3 <= dr_q2; dr_e3 <= dr_e2;
                dr_v2 <= dr_v; dr_q2 <= dr_q; dr_e2 <= dr_e; dr_v <= 1'b0;
                dr_go = ({1'b0, n_} + (dr_v ? 3'd1 : 3'd0) + (dr_v2 ? 3'd1 : 3'd0)) < 3'd2;   // room for every read in flight
            end
            if (dr_go) begin : pk
                reg f; integer q_; f = 1'b0;
                for (c = 0; c < NC; c = c + 1) begin q_ = (dr_rr + 1 + c) % NC;
                    if (!f && pq_n[q_] != 0) begin
                        f = 1'b1; dr_rr <= LNC'(q_); dr_q <= LNC'(q_); dr_e <= pq_e[q_][pq_h[q_]]; dr_v <= 1'b1;
                        m_re[q_] <= 1'b1; m_ra[q_] <= 7'({pq_e[q_][pq_h[q_]][LSL+23:24], pq_e[q_][pq_h[q_]][23]});
                        pq_h[q_] <= pq_h[q_] + 1'b1; qn_[q_] = qn_[q_] - 1'b1;
                    end
                end
            end
            for (c = 0; c < NC; c = c + 1) pq_n[c] <= qn_[c];
            for (i = 0; i < NSS; i = i + 1) for (p = 0; p < NC; p = p + 1) k_pf[i][p] <= pf_[i][p];
            // ---- done: every row in, swept (VM) / emitted (STREAM), nothing pending, the write acknowledged
            done_now = busy && !k_go && nv && all_rows && &rdone && !pend_any && !tok && !w_v && !so_v &&
                       (sm_m || (sweep && sw_i >= NSS && !open_q));
            if (done_now) begin
                busy <= 1'b0; s_done <= 1'b1; sweep <= 1'b0; nv <= 1'b0;
                for (s = 0; s < NSS; s = s + 1) recv[s] <= rv_q[s] ? 20'd1 : 20'd0;
            end
        end
    end
endmodule

// STREAM merge node of the HIER parent: two 8-deep credit FIFOs (an upstream sends only against a credit; a credit
// returns, registered, on every pop), a registered 2:1 round-robin pick into the output register (against the
// downstream's credits; ROOT: no backpressure).  a_out: the time-aligned busy snapshot (own state delayed LVL - 1
// edges, OR the children's), so the parent's done never needs a one-cycle OR across the die.
module ot_hgi_sm_pub_smrg #(
    parameter integer D = 8,
    parameter integer W = 52,
    parameter integer ROOT = 0,
    parameter integer LVL = 1
) (
    input  wire           clk,
    input  wire           rn,
    input  wire [1:0]     i_v,
    input  wire [2*W-1:0] i_d,
    output reg  [1:0]     i_cr,
    output reg            o_v,
    output reg  [W-1:0]   o_d,
    input  wire           o_cr,
    input  wire           xb,          // ROOT: the relay after this node holds a beat
    input  wire [1:0]     a_in,
    output reg            a_out
);
    localparam integer DW = (D > 1) ? $clog2(D) : 1, CW = $clog2(D + 1);
    reg [W-1:0] f0 [0:D-1]; reg [W-1:0] f1 [0:D-1];
    reg [DW:0] n0, n1; reg [DW-1:0] h0, h1, t0, t1; reg [CW-1:0] cr; reg rr;
    reg [LVL:0] bd;                                    // bd[d - 1] = own busy d edges ago
    wire bz = (n0 != 0) || (n1 != 0) || o_v || xb;
    always @(posedge clk) begin
        if (i_v[0]) f0[t0] <= i_d[0 +: W];
        if (i_v[1]) f1[t1] <= i_d[W +: W];
    end
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            n0 <= '0; n1 <= '0; h0 <= '0; h1 <= '0; t0 <= '0; t1 <= '0; cr <= CW'(D); rr <= 1'b0; o_v <= 1'b0; i_cr <= 2'b00;
            bd <= '0; a_out <= 1'b0;
        end else begin : m
            reg go, s1, p0, p1;
            go = (ROOT != 0) || (cr != 0);
            // round robin: rr = the input served last
            s1 = (n1 != 0) && (rr == 1'b0 || n0 == 0);
            p0 = go && !s1 && (n0 != 0);
            p1 = go && s1;
            o_v <= p0 || p1; i_cr <= {p1, p0};
            if (p0) begin o_d <= f0[h0]; h0 <= h0 + 1'b1; rr <= 1'b0; end
            if (p1) begin o_d <= f1[h1]; h1 <= h1 + 1'b1; rr <= 1'b1; end
            if (i_v[0]) t0 <= t0 + 1'b1;
            if (i_v[1]) t1 <= t1 + 1'b1;
            n0 <= n0 + (i_v[0] ? 1'b1 : 1'b0) - (p0 ? 1'b1 : 1'b0);
            n1 <= n1 + (i_v[1] ? 1'b1 : 1'b0) - (p1 ? 1'b1 : 1'b0);
            if (ROOT == 0) cr <= cr - ((p0 || p1) ? 1'b1 : 1'b0) + (o_cr ? 1'b1 : 1'b0);
            bd <= {bd[LVL-1:0], bz};
            a_out <= |a_in || ((LVL == 1) ? bz : bd[(LVL >= 2) ? LVL - 2 : 0]);
        end
    end
endmodule

// The HIER parent: command pin flops + relay chain, slices, per-client VM merge, STREAM credit tree, done / fault.
module ot_hgi_sm_pub_hier #(
    parameter integer NSM = 32,
    parameter integer NC = 8,
    parameter integer NPC = 4,
    parameter integer MUT_ROW = 0,
    parameter integer MUT_PAR = 0,
    parameter integer NSS = 4,
    parameter integer SD = 8
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
    output wire [NPC*338-1:0] vmq,
    input  wire [NPC*274-1:0] vmr,
    output reg                s0_v,
    output reg  [19:0]        s0_idx,
    output reg  [31:0]        s0_data
);
    localparam integer NSL = (NSM + NSS - 1) / NSS;            // slices
    localparam integer NCOL = (NSL + 1) / 2;                   // columns (slice k: column k % NCOL; N row k < NCOL)
    localparam integer NIN = (NSL + NPC - 1) / NPC;            // slices a VM client (slice k -> client k % NPC)
    localparam integer LV = (NSL <= 2) ? 1 : $clog2(NSL);      // STREAM tree levels
    localparam integer NLF = 1 << LV;                          // tree leaves (leaf 2c = slice c, 2c + 1 = slice c + NCOL)
    localparam integer W = 52, CW = 76;
    localparam integer NSMP = NSL * NSS;
    integer k, j;
    wire rn;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    // ---- command: pin flops, accept processed one edge after the handshake
    reg rel, busy, acc_q; reg [39:0] pf_b; reg [31:0] pf_s; reg [1:0] pf_sp; reg [19:0] pf_m; reg [12:0] pf_q;
    reg [3:0] pf_p; reg pf_bf;
    assign pub_rdy = rel && !busy && !acc_q;
    always @(posedge clk) begin pf_b <= pub_base; pf_s <= pub_stride; pf_sp <= pub_space; pf_m <= pub_m; pf_q <= pub_q;
                                pf_p <= pub_p; pf_bf <= pub_bf16; end
    // command chain: cp[0] at the command port, one relay a column
    // {sm, bf, ob 18, ost 18, mm 20, qq 13, pp 4} fields (no reset) and the go pulse (reset), one stage a column
    reg [NCOL*(CW-1)-1:0] cfd; reg [NCOL-1:0] cgo;
    reg r1_v; reg [W-1:0] r1_d; reg agg_r;
    always @(posedge clk) begin
        if (acc_q) cfd[0 +: CW-1] <= {pf_sp == 2'd2, pf_bf, pf_b[17:0], pf_s[17:0], pf_m, pf_q, pf_p};
        for (j = 1; j < NCOL; j = j + 1) cfd[j*(CW-1) +: CW-1] <= cfd[(j-1)*(CW-1) +: CW-1];
    end
    // ---- slices
    wire [NSMP-1:0] rv_p = NSMP'(sm_rv);
    wire [NSMP*12-1:0] rr_p = (NSMP*12)'(sm_rrow);
    wire [NSMP*NC*32-1:0] rd_p = (NSMP*NC*32)'(sm_rdata);
    wire [NSL-1:0] s_wv, s_sov, s_dn, s_ft; wire [NSL*279-1:0] s_wp; wire [NSL*W-1:0] s_sod;
    wire [NSL-1:0] s_cr;
    genvar gk, gl, gn, gc, gj;
    generate for (gk = 0; gk < NSL; gk = gk + 1) begin : g_s
        localparam integer COL = gk % NCOL;
        localparam integer NE_ = (NSM - gk * NSS >= NSS) ? NSS : NSM - gk * NSS;
        localparam [NSS-1:0] EN = NSS'((1 << NE_) - 1);
        wire [CW-1:0] ci = {cgo[COL], cfd[COL*(CW-1) +: CW-1]};
`ifdef SYNTHESIS
        ot_hgi_sm_pub_slice u (
`else
        ot_hgi_sm_pub_slice #(.NSS(NSS), .NC(NC), .SD(SD), .MUT_ROW(MUT_ROW), .MUT_PAR(MUT_PAR)) u (
`endif
            .clk(clk), .rst_n(rst_n), .sid(3'(gk)), .sm_en(EN), .c_go(ci[CW-1]), .c_sm(ci[CW-2]), .c_bf(ci[CW-3]),
            .c_ob(ci[72:55]), .c_ost(ci[54:37]), .c_mm(ci[36:17]), .c_qq(ci[16:4]), .c_pp(ci[3:0]),
            .sm_rv(rv_p[gk*NSS +: NSS]), .sm_rrow(rr_p[gk*NSS*12 +: NSS*12]), .sm_rdata(rd_p[gk*NSS*NC*32 +: NSS*NC*32]),
            .w_v(s_wv[gk]), .w_pkt(s_wp[gk*279 +: 279]), .w_ack(s_ack[gk]),
            .so_v(s_sov[gk]), .so_idx(s_sod[gk*W+32 +: 20]), .so_data(s_sod[gk*W +: 32]), .so_cr(s_cr[gk]),
            .s_done(s_dn[gk]), .s_fault(s_ft[gk]));
    end endgenerate
    // ---- done / fault return: col + 1 relays a slice
    wire [NSL-1:0] dn_l, ft_l;
    generate for (gk = 0; gk < NSL; gk = gk + 1) begin : g_ret
        localparam integer DL = gk % NCOL + 1;
        reg [DL:0] dq, fq;
        always @(posedge clk or negedge rn)
            if (!rn) begin dq <= '0; fq <= '0; end
            else begin dq <= {dq[DL-1:0], s_dn[gk]}; fq <= {fq[DL-1:0], s_ft[gk]}; end
        assign dn_l[gk] = dq[DL-1]; assign ft_l[gk] = fq[DL-1];
    end endgenerate
    // ---- VM: one merge node a client (its slices' held packets; one write out a client, as MEM 1)
    wire [NPC-1:0] vq_vw; wire [NSL-1:0] s_ack;
    localparam integer OWW = (NIN > 1) ? $clog2(NIN) : 1;
    generate for (gc = 0; gc < NPC; gc = gc + 1) begin : g_c
        reg [NIN-1:0] pend, ak; reg bsy, n_v, va_q, vq_v; reg [278:0] n_p, vq_p; reg [OWW-1:0] own, rr;
        assign vq_vw[gc] = vq_v;
        assign vmq[gc*338 +: 338] = {vq_v, 1'b1, 12'd0, vq_p[278:264], 5'd0, vq_p[263:8],
            {{4{vq_p[7]}}, {4{vq_p[6]}}, {4{vq_p[5]}}, {4{vq_p[4]}}, {4{vq_p[3]}}, {4{vq_p[2]}}, {4{vq_p[1]}}, {4{vq_p[0]}}},
            16'h5042};
        always @(posedge clk) if (n_v) vq_p <= n_p;
        always @(posedge clk or negedge rn) begin
            if (!rn) begin pend <= '0; ak <= '0; bsy <= 1'b0; n_v <= 1'b0; va_q <= 1'b0; vq_v <= 1'b0; own <= '0; rr <= '0; end
            else begin : nd
                reg f; integer q_, jj; reg [NIN-1:0] pn;
                va_q <= vmr[gc*274 + 273] && vmr[gc*274 + 256];           // port pin flop (MEM 1: vr[273] && vr[256])
                vq_v <= n_v; n_v <= 1'b0; ak <= '0;
                pn = pend;
                for (q_ = 0; q_ < NIN; q_ = q_ + 1) if (gc + q_ * NPC < NSL) if (s_wv[gc + q_ * NPC]) pn[q_] = 1'b1;
                f = 1'b0;
                if (!bsy) for (jj = 0; jj < NIN; jj = jj + 1) begin q_ = (rr + 1 + jj) % NIN;
                    if (!f && pend[q_]) begin
                        f = 1'b1; pn[q_] = 1'b0; own <= OWW'(q_); rr <= OWW'(q_); bsy <= 1'b1; n_v <= 1'b1;
                        n_p <= s_wp[(gc + q_ * NPC) * 279 +: 279];
                    end
                end
                if (bsy && va_q) begin bsy <= 1'b0; ak[own] <= 1'b1; end    // acknowledged: back to the owning slice
                pend <= pn;
            end
        end
        for (gj = 0; gj < NIN; gj = gj + 1) begin : g_a
            if (gc + gj * NPC < NSL) begin : g_ae assign s_ack[gc + gj * NPC] = ak[gj]; end
        end
    end endgenerate
    // ---- STREAM: credit tree of 2:1 nodes (level 0 = the slices)
    wire [(LV+1)*NLF-1:0] t_v, t_cr, t_a; wire [(LV+1)*NLF*W-1:0] t_d;
    generate
        for (gn = 0; gn < NLF; gn = gn + 1) begin : g_lf
            localparam integer SK = (gn % 2 == 0) ? gn / 2 : gn / 2 + NCOL;
            if (gn / 2 < NCOL && SK < NSL) begin : g_e
                assign t_v[gn] = s_sov[SK]; assign t_d[gn*W +: W] = s_sod[SK*W +: W]; assign s_cr[SK] = t_cr[gn];
            end else begin : g_z
                assign t_v[gn] = 1'b0; assign t_d[gn*W +: W] = '0;
            end
            assign t_a[gn] = 1'b0;
        end
        for (gl = 1; gl <= LV; gl = gl + 1) begin : g_l
            for (gn = 0; gn < (NLF >> gl); gn = gn + 1) begin : g_n
                localparam integer B = gl * NLF + gn, C0 = (gl - 1) * NLF + 2 * gn;
                ot_hgi_sm_pub_smrg #(.D(SD), .W(W), .ROOT(gl == LV), .LVL(gl)) u (
                    .clk(clk), .rn(rn), .i_v(t_v[C0 +: 2]), .i_d(t_d[C0*W +: 2*W]), .i_cr(t_cr[C0 +: 2]),
                    .o_v(t_v[B]), .o_d(t_d[B*W +: W]), .o_cr((gl == LV) ? 1'b0 : t_cr[B]), .xb((gl == LV) ? r1_v : 1'b0),
                    .a_in(t_a[C0 +: 2]), .a_out(t_a[B]));
            end
            for (gn = (NLF >> gl); gn < NLF; gn = gn + 1) begin : g_u
                assign t_v[gl*NLF + gn] = 1'b0; assign t_d[(gl*NLF + gn)*W +: W] = '0; assign t_a[gl*NLF + gn] = 1'b0;
                if (gl < LV) begin : g_uc assign t_cr[gl*NLF + gn] = 1'b0; end
            end
        end
        for (gn = 0; gn < NLF; gn = gn + 1) begin : g_tc
            assign t_cr[LV*NLF + gn] = 1'b0;
        end
    endgenerate
    // root -> relay -> s0 (the port register); the root's busy snapshot relayed to the collector
    always @(posedge clk) begin if (t_v[LV*NLF]) r1_d <= t_d[LV*NLF*W +: W]; if (r1_v) begin s0_idx <= r1_d[51:32]; s0_data <= r1_d[31:0]; end end
    // ---- control
    reg [NSL-1:0] sdn; reg [7:0] allc;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            rel <= 1'b0; busy <= 1'b0; acc_q <= 1'b0; pub_done <= 1'b0; pub_fault <= 1'b0; s0_v <= 1'b0; r1_v <= 1'b0;
            agg_r <= 1'b0; sdn <= '0; allc <= 8'd0; cgo <= '0;
        end else begin
            rel <= 1'b1;
            acc_q <= pub_v && pub_rdy;
            pub_done <= 1'b0; cgo <= {cgo, 1'b0};
            r1_v <= t_v[LV*NLF]; s0_v <= r1_v; agg_r <= t_a[LV*NLF];
            if (|ft_l) pub_fault <= 1'b1;                                   // a slice overrun: fail closed
            if (acc_q) begin
                if (!(pf_sp == 2'd1 || pf_sp == 2'd2) || pf_p == 4'd0 || pf_p > NC) pub_fault <= 1'b1;
                else begin
                    busy <= 1'b1; sdn <= '0; allc <= 8'd0;
                    cgo[0] <= 1'b1;
                end
            end else if (busy) begin
                sdn <= sdn | dn_l;
                if (&sdn && allc != 8'hFF) allc <= allc + 8'd1;
                if (&sdn && allc >= 8'(LV + 1) && !agg_r && vq_vw == 0) begin busy <= 1'b0; pub_done <= 1'b1; end
            end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_sm_pub: the publication peer. MEM = 1 (default, hgi-1010/d): the banked-SRAM form ot_hgi_sm_pub_mem; MEM = 0:
// the flop form ot_hgi_sm_pub_ff (kept as the reference of tb_hgi_pub_lock).  Same ports and transaction contract.
// HIER = 1 (el1011-hbm-smh/pub, opt-in, default 0; `define OT_HGI_PUB_HIER makes it the default for benches): the
// hierarchical form ot_hgi_sm_pub_hier (hardened 4-SM slices; needs rtl/lib/ot_rst_relay.sv).
// ---------------------------------------------------------------------------------------------------------------------
`ifdef OT_HGI_PUB_HIER
`define OT_HGI_PUB_HIER_DEF 1
`else
`define OT_HGI_PUB_HIER_DEF 0
`endif
module ot_hgi_sm_pub #(
    parameter integer NSM = 32,
    parameter integer NC = 8,
    parameter integer NPC = 4,
    parameter integer MUT_ROW = 0,
    parameter integer MEM = 1,
    parameter integer NE = 2,
    parameter integer MUT_PAR = 0,
    parameter integer HIER = `OT_HGI_PUB_HIER_DEF
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
    generate if (HIER) begin : g_hier
        ot_hgi_sm_pub_hier #(.NSM(NSM), .NC(NC), .NPC(NPC), .MUT_ROW(MUT_ROW), .MUT_PAR(MUT_PAR)) u (
            .clk(clk), .rst_n(rst_n), .pub_v(pub_v), .pub_rdy(pub_rdy), .pub_base(pub_base), .pub_stride(pub_stride),
            .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16), .pub_done(pub_done),
            .pub_fault(pub_fault), .sm_rv(sm_rv), .sm_rrow(sm_rrow), .sm_rdata(sm_rdata), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
            .s0_idx(s0_idx), .s0_data(s0_data));
    end else if (MEM) begin : g_mem
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
