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
    output reg  [31:0]        s0_data,
    output reg  [NSM-1:0]     sm_cr          // smmv 2026-10-11: one pulse per arrival entry consumed, per SM (row credits)
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
    always @(posedge clk) sm_cr <= rv_q;                     // the flop form takes a row on its arrival edge
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
    output reg  [31:0]        s0_data,
    output reg  [NSM-1:0]     sm_cr          // smmv 2026-10-11: one pulse per arrival entry consumed, per SM (row credits)
);
    localparam integer NSL = NSM / NE, LSL = (NSL > 1) ? $clog2(NSL) : 1, ADW = (AD > 1) ? $clog2(AD) : 1, PQW = $clog2(PQ);
    // smmv-b 10-12: AD 1 used to die at build on a zero-width cast (ADW 0); ADW is floored at 1 so the refusal below is
    // the clean one.  The arrival FIFO pointers wrap by width, so AD must be a power of two >= 2 (the credit rule wants
    // AD >= the SM issue wave SIL 8; ot_hgi_sm_record refuses that).
    initial if (AD < 2 || (AD & (AD - 1)) != 0)
        $fatal(1, "ot_hgi_sm_pub_mem: AD %0d refused: arrival depth must be a power of two >= 2 (credit rule: >= SIL 8)", AD);
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
            sm_cr <= '0;
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
            reg ok, dr_go; integer e, q_, sl; reg [NSM-1:0] crp;
            crp = '0;
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
                        s = e + NE * d_i[e]; atk[s] = atk[s] - 1'b1; an[s] = an[s] - 1'b1; crp[s] = 1'b1;  // consumed
                    end
                end else if (d_v[e] && sm_m) begin
                    ok = 1'b0;
                    if (s_req[e]) begin                           // granted this edge (below): one beat out
                        if (d_sp[e] + 4'd1 >= pp) begin d_v[e] <= 1'b0; d_sp[e] <= 4'd0; ok = 1'b1;
                            s = e + NE * d_i[e]; atk[s] = atk[s] - 1'b1; an[s] = an[s] - 1'b1; crp[s] = 1'b1; end
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
            sm_cr <= crp;
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
    parameter integer AD = 32,             // arrival FIFO entries an SM (smmv 10-11: = ot_hgi_sm_record AD; row credits)
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
    output reg                  s_fault,        // sticky: an arrival FIFO overrun
    output reg  [NSS-1:0]       sm_cr           // smmv 10-11: registered pulse per arrival entry consumed (row credit), per SM
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
    // round 4 (class 5): 5-edge start sequence (one-hot so[1..5]); every add >= 18 b is split in two halves over two
    // edges with a registered carry; s x Q = sid x 4Q + s x Q.  so[1]: p x stride, p x M, sid x 4Q, s x Q; so[2]: + O.base,
    // sQ; so[3]: low halves (bases, M - sQ); so[4]: high halves; so[5]: need clamp -> nv
    reg busy, sm_m, obf, nv; reg [5:1] so; reg [19:0] mm; reg [12:0] qq; reg [3:0] pp;
    reg [17:0] ob_h, ost_h; reg [17:0] pm [0:NC-1]; reg [19:0] pg [0:NC-1];
    reg [17:0] pofs [0:NC-1]; reg [19:0] pgi [0:NC-1]; reg [19:0] sq_a; reg [19:0] sq_b [0:NSS-1];
    reg [20:0] dif [0:NSS-1]; reg dif_c [0:NSS-1];
    reg [17:0] bs_a [0:NSS-1][0:NC-1]; reg [19:0] bs_g [0:NSS-1][0:NC-1];   // O-address / global-index base per (SM, slot)
    reg bs_ac [0:NSS-1][0:NC-1], bs_gc [0:NSS-1][0:NC-1];
    reg [19:0] sqc [0:NSS-1], need [0:NSS-1], recv [0:NSS-1];
    wire [19:0] sq [0:NSS-1];                         // s x Q of the global SM (MUT_ROW: 0 in the addresses only)
    genvar gsq;
    generate for (gsq = 0; gsq < NSS; gsq = gsq + 1) begin : g_sq
        assign sq[gsq] = MUT_ROW ? 20'd0 : sqc[gsq];
    end endgenerate
    reg [NSS-1:0] rdone; reg all_rows;
    always @* for (s = 0; s < NSS; s = s + 1) rdone[s] = (recv[s] == need[s]);
    // ---- arrival FIFOs (smmv 10-11, AD 32): data in one 1R1W SRAM pair a local SM (2 x ot_sram_1r1w_32x128_m1: one
    // arrival write + at most one engine read an edge, each its own macro -> no write mux, no 128:1 read mux); the
    // 12-b row index stays in flops.  The read is issued on the P->R transfer; R holds the macro output; R->C captures
    // it next to the macros (zero unless this SM was read) and C ORs the four captures.
    reg [11:0] af_r [0:NSS-1][0:AD-1];
    wire [NC*32-1:0] af_q [0:NSS-1]; reg [NC*32-1:0] af_c [0:NSS-1];
    reg [ADW:0] af_n [0:NSS-1]; reg [ADW-1:0] af_h [0:NSS-1], af_t [0:NSS-1];
    // ---- engine: P (pick) -> R (FIFO read) -> A (base select) -> D (base + row; sector-change flags) -> E (decide, commit)
    // every stage accepts only when empty at the edge (registered transfer conditions x_*): one record / 2 edges / slice
    reg p_v, r_v, c_v, a_v, d_v, e_v; reg [LSL-1:0] p_i, r_i, c_i, a_i, d_i, e_i, rrp; reg [11:0] r_row, c_row, a_row;
    reg [NC*32-1:0] a_d, d_d, e_d;
    reg [17:0] a_ba [0:NC-1], d_wa [0:NC-1], e_wa [0:NC-1]; reg [19:0] a_bg [0:NC-1], d_gi [0:NC-1], e_gi [0:NC-1];
    reg [3:0] e_sp; reg [NC-1:0] e_ch;
    // coalescing state per (local SM, slot)
    reg [14:0] k_sec [0:NSS-1][0:NC-1]; reg [7:0] k_msk [0:NSS-1][0:NC-1];
    reg        k_par [0:NSS-1][0:NC-1]; reg [1:0] k_pf [0:NSS-1][0:NC-1];
    // pending flush FIFOs per slot: {local SM, parity, sector, mask}; registered full / non-empty flags
    reg [LSL+24-1:0] pq_e [0:NC-1][0:PQ-1]; reg [PQW:0] pq_n [0:NC-1]; reg [PQW-1:0] pq_h [0:NC-1], pq_t [0:NC-1];
    reg [NC-1:0] pq_f, pq_ne;
    // SRAM write / read ports (registered); write data = the word replicated, mask = the word lane
    reg [NC-1:0] m_we, m_re; reg [6:0] m_wa [0:NC-1], m_ra [0:NC-1]; reg [31:0] m_wd [0:NC-1]; reg [2:0] m_ww [0:NC-1];
    wire [255:0] m_rd [0:NC-1];
    reg [255:0] m_cap [0:NC-1];                       // capture at every macro output: the read row, else zero
    genvar gq;
    generate for (gq = 0; gq < NC; gq = gq + 1) begin : g_m
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(m_re[gq]), .r_addr_in(m_ra[gq]), .rd_out(m_rd[gq]),
            .w_ce_in(m_we[gq]), .w_addr_in(m_wa[gq]), .wd_in({8{m_wd[gq]}}), .w_mask_in({224'd0, 32'hFFFF_FFFF} << {m_ww[gq], 5'd0}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // drain: K1 (grant on the registered non-empty flags, pop) -> K2 (entry, SRAM read) -> capture -> row FIFO -> packet
    reg dk_v; reg [LNC-1:0] dk_q; reg [PQW-1:0] dk_h;
    reg dr_v, dr_v2, dr_v3; reg [LNC-1:0] dr_q, dr_q2, dr_q3, dr_rr; reg [LSL+24-1:0] dr_e, dr_e2, dr_e3;
    reg [255:0] hq_d [0:1]; reg [14:0] hq_s [0:1]; reg [7:0] hq_m [0:1]; reg [1:0] hq_n; reg hq_h, hq_t;
    reg tok;                                            // a write is out, not yet acknowledged
    reg [SDW-1:0] cr;                                   // STREAM credits
    // end sweep: phase 0 latches one local SM's slot states, phase 1 pushes them (on the registered full flags)
    reg sweep, sw_ph; reg [LSL:0] sw_i; reg [LSL-1:0] sw_l; reg [7:0] sw_m [0:NC-1]; reg [14:0] sw_s [0:NC-1]; reg [NC-1:0] sw_p;
    reg pend_any, open_q;
    always @* begin
        pend_any = dk_v || dr_v || dr_v2 || dr_v3 || hq_n != 0 || p_v || r_v || c_v || a_v || d_v || e_v || pq_ne != 0;
        for (s = 0; s < NSS; s = s + 1) if (af_n[s] != 0) pend_any = 1'b1;
    end
    wire [NC-1:0] d_ch;
    genvar gch;
    generate for (gch = 0; gch < NC; gch = gch + 1) begin : g_ch
        assign d_ch[gch] = (gch < pp) && (k_msk[d_i][gch] != 0) && (k_sec[d_i][gch] != d_wa[gch][17:3]);
    end endgenerate
    reg arr_empty;
    always @* begin arr_empty = 1'b1; for (s = 0; s < NSS; s = s + 1) if (af_n[s] != 0) arr_empty = 1'b0; end
    // ---- transfer / decision terms (registered inputs only)
    wire x_pr = p_v && !r_v, x_rc = r_v && !c_v, x_ra = c_v && !a_v && nv, x_ad = a_v && !d_v, x_de = d_v && !e_v;
    // arrival SRAMs: write = the pin-flopped arrival (no logic but the full check), read = the P->R transfer
    genvar ga;
    generate for (ga = 0; ga < NSS; ga = ga + 1) begin : g_af
        wire we = rv_q[ga] && af_n[ga] != (ADW+1)'(AD), re = x_pr && p_i == LSL'(ga);
        wire [4:0] wa = 5'(af_t[ga]), ra = 5'(af_h[ga]);
        ot_sram_1r1w_32x128_m1 u_lo (.clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(af_q[ga][127:0]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(rd_q[ga][127:0]), .w_mask_in({128{1'b1}}));
        ot_sram_1r1w_32x128_m1 u_hi (.clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(af_q[ga][255:128]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(rd_q[ga][255:128]), .w_mask_in({128{1'b1}}));
    end endgenerate
`ifndef SYNTHESIS
    initial if (AD > 32 || (AD & (AD - 1)) != 0 || NC != 8) $fatal(1, "ot_hgi_sm_pub_slice: AD must be a power of two <= 32 and NC 8 (32x128 macro pair)");
`endif
    reg [NC*32-1:0] c_or;
    always @* begin : cro
        integer j; c_or = '0; for (j = 0; j < NSS; j = j + 1) c_or = c_or | af_c[j];
    end
    wire x_bt = e_v && sm_m && cr != 0;                 // a STREAM beat
    reg e_ok;
    always @* begin : eok
        integer q; e_ok = 1'b1;
        for (q = 0; q < NC; q = q + 1)
            if (e_ch[q] && (pq_f[q] || k_pf[e_i][q][MUT_PAR ? k_par[e_i][q] : !k_par[e_i][q]])) e_ok = 1'b0;
    end
    wire e_cm = e_v && !sm_m && e_ok;                   // E commits (VM)
    wire sw_a = sweep && !sw_ph && sw_i < NSS;          // sweep phase 0
    reg sw_go;
    always @* begin : swg
        integer q; sw_go = sweep && sw_ph;
        for (q = 0; q < NC; q = q + 1) if (sw_m[q] != 0 && pq_f[q]) sw_go = 1'b0;
    end
    reg [NC-1:0] q_push, q_pop; reg k1_f; reg [LNC-1:0] k1_q; reg tk; reg [1:0] hn;
    always @* begin : qpp
        integer q, q_; reg go;
        for (q = 0; q < NC; q = q + 1) q_push[q] = (e_cm && e_ch[q]) || (sw_go && sw_m[q] != 0);
        tk = hq_n != 0 && !tok;
        hn = hq_n - (tk ? 2'd1 : 2'd0) + (dr_v3 ? 2'd1 : 2'd0);
        go = ({1'b0, hn} + (dk_v ? 3'd1 : 3'd0) + (dr_v ? 3'd1 : 3'd0) + (dr_v2 ? 3'd1 : 3'd0)) < 3'd2;   // room for every read in flight
        k1_f = 1'b0; k1_q = '0;
        for (q = 0; q < NC; q = q + 1) begin q_ = (dr_rr + 1 + q) % NC;
            if (go && !k1_f && pq_ne[q_]) begin k1_f = 1'b1; k1_q = LNC'(q_); end
        end
        for (q = 0; q < NC; q = q + 1) q_pop[q] = k1_f && k1_q == LNC'(q);
    end
    reg [255:0] cap_or;
    always @* begin : cor
        integer q; cap_or = '0; for (q = 0; q < NC; q = q + 1) cap_or = cap_or | m_cap[q];
    end
    // ---- data-only registers (no reset: rn reaches control flops only)
    always @(posedge clk) begin : dat
        integer q, j;
        for (q = 0; q < NC; q = q + 1) m_cap[q] <= (dr_v2 && dr_q2 == LNC'(q)) ? m_rd[q] : 256'd0;
        for (j = 0; j < NSS; j = j + 1) if (rv_q[j] && af_n[j] != AD) af_r[j][af_t[j]] <= rr_q[j];
        if (x_rc) for (j = 0; j < NSS; j = j + 1) af_c[j] <= (r_i == LSL'(j)) ? af_q[j] : '0;   // capture at the macros
        // start sequence arithmetic
        if (so[1]) begin
            for (q = 0; q < NC; q = q + 1) begin pm[q] <= 18'(q * ost_h); pg[q] <= 20'(q * mm); end
            sq_a <= 20'({17'd0, sid} * {5'd0, qq, 2'b00});
            for (j = 0; j < NSS; j = j + 1) sq_b[j] <= 20'(j * {7'd0, qq});
        end
        if (so[2]) begin
            for (q = 0; q < NC; q = q + 1) begin pofs[q] <= ob_h + pm[q]; pgi[q] <= pg[q]; end
            for (j = 0; j < NSS; j = j + 1) sqc[j] <= sq_a + sq_b[j];
        end
        if (so[3]) for (j = 0; j < NSS; j = j + 1) begin
            {dif_c[j], dif[j][9:0]} <= {1'b0, mm[9:0]} - {1'b0, sqc[j][9:0]};
            for (q = 0; q < NC; q = q + 1) begin
                {bs_ac[j][q], bs_a[j][q][8:0]} <= {1'b0, pofs[q][8:0]} + {1'b0, sq[j][8:0]};
                {bs_gc[j][q], bs_g[j][q][9:0]} <= {1'b0, pgi[q][9:0]} + {1'b0, sq[j][9:0]};
            end
        end
        if (so[4]) for (j = 0; j < NSS; j = j + 1) begin
            dif[j][20:10] <= {1'b0, mm[19:10]} - {1'b0, sqc[j][19:10]} - {10'd0, dif_c[j]};
            for (q = 0; q < NC; q = q + 1) begin
                bs_a[j][q][17:9] <= pofs[q][17:9] + sq[j][17:9] + {8'd0, bs_ac[j][q]};
                bs_g[j][q][19:10] <= pgi[q][19:10] + sq[j][19:10] + {9'd0, bs_gc[j][q]};
            end
        end
        // engine records
        if (x_pr) begin r_i <= p_i; r_row <= af_r[p_i][af_h[p_i]]; end
        if (x_rc) begin c_i <= r_i; c_row <= r_row; end
        if (x_ra) begin
            a_i <= c_i; a_d <= c_or; a_row <= c_row;
            for (q = 0; q < NC; q = q + 1) begin a_ba[q] <= bs_a[c_i][q]; a_bg[q] <= bs_g[c_i][q]; end
        end
        if (x_ad) begin
            d_i <= a_i; d_d <= a_d;
            for (q = 0; q < NC; q = q + 1) begin d_wa[q] <= a_ba[q] + {6'd0, a_row}; d_gi[q] <= a_bg[q] + {8'd0, a_row}; end
        end
        if (x_de) begin
            e_i <= d_i; e_d <= d_d; e_ch <= d_ch;
            for (q = 0; q < NC; q = q + 1) begin e_wa[q] <= d_wa[q]; e_gi[q] <= d_gi[q]; end
        end else if (x_bt) begin                         // STREAM: word 0 is always the next beat
            so_idx <= e_gi[0]; so_data <= rb(e_d[31:0], obf); e_d <= {32'd0, e_d[NC*32-1:32]};
            for (q = 0; q < NC - 1; q = q + 1) e_gi[q] <= e_gi[q + 1];
        end
        // SRAM write port: data / lane / row every edge (m_we alone gates the write)
        for (q = 0; q < NC; q = q + 1) begin
            m_wd[q] <= e_d[32*q +: 32]; m_ww[q] <= e_wa[q][2:0];
            m_wa[q] <= 7'({e_i, e_ch[q] ? (MUT_PAR ? k_par[e_i][q] : !k_par[e_i][q]) : k_par[e_i][q]});
            if (e_cm && q < pp) k_sec[e_i][q] <= e_wa[q][17:3];
        end
        // pending flush entries
        for (q = 0; q < NC; q = q + 1) if (q_push[q])
            pq_e[q][pq_t[q]] <= sweep ? {sw_l, sw_p[q], sw_s[q], sw_m[q]} : {e_i, k_par[e_i][q], k_sec[e_i][q], k_msk[e_i][q]};
        if (sw_a) begin
            sw_l <= LSL'(sw_i);
            for (q = 0; q < NC; q = q + 1) begin sw_m[q] <= k_msk[LSL'(sw_i)][q]; sw_s[q] <= k_sec[LSL'(sw_i)][q]; sw_p[q] <= k_par[LSL'(sw_i)][q]; end
        end
        // drain
        if (k1_f) begin dk_q <= k1_q; dk_h <= pq_h[k1_q]; end
        if (dk_v) begin dr_q <= dk_q; dr_e <= pq_e[dk_q][dk_h]; end
        for (q = 0; q < NC; q = q + 1) m_ra[q] <= 7'({pq_e[q][dk_h][LSL+23:24], pq_e[q][dk_h][23]});
        dr_q3 <= dr_q2; dr_e3 <= dr_e2; dr_q2 <= dr_q; dr_e2 <= dr_e;
        if (dr_v3) begin hq_d[hq_t] <= cap_or; hq_s[hq_t] <= dr_e3[22:8]; hq_m[hq_t] <= dr_e3[7:0]; end
        if (tk) w_pkt <= {hq_s[hq_h], rb8(hq_d[hq_h], obf), hq_m[hq_h]};
    end
    // ---- control (reset)
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            busy <= 1'b0; sm_m <= 1'b0; obf <= 1'b0; nv <= 1'b0; so <= '0; all_rows <= 1'b0; s_done <= 1'b0; s_fault <= 1'b0;
            w_v <= 1'b0; so_v <= 1'b0; tok <= 1'b0; cr <= SDW'(SD); sweep <= 1'b0; sw_ph <= 1'b0; sw_i <= '0; open_q <= 1'b0;
            p_v <= 1'b0; r_v <= 1'b0; c_v <= 1'b0; a_v <= 1'b0; sm_cr <= '0; d_v <= 1'b0; e_v <= 1'b0; rrp <= '0; e_sp <= 4'd0; m_we <= '0; m_re <= '0;
            dk_v <= 1'b0; dr_v <= 1'b0; dr_v2 <= 1'b0; dr_v3 <= 1'b0; dr_rr <= '0; hq_n <= 2'd0; hq_h <= 1'b0; hq_t <= 1'b0;
            pq_f <= '0; pq_ne <= '0;
            for (s = 0; s < NSS; s = s + 1) begin af_n[s] <= '0; af_h[s] <= '0; af_t[s] <= '0; recv[s] <= '0; need[s] <= '0; end
            for (i = 0; i < NSS; i = i + 1) for (p = 0; p < NC; p = p + 1) begin
                k_msk[i][p] <= 8'd0; k_par[i][p] <= 1'b0; k_pf[i][p] <= 2'b00; end
            for (c = 0; c < NC; c = c + 1) begin pq_n[c] <= '0; pq_h[c] <= '0; pq_t[c] <= '0; end
        end else begin : main
            reg [ADW:0] an [0:NSS-1]; reg [1:0] pf_ [0:NSS-1][0:NC-1];
            reg done_now;
            s_done <= 1'b0; w_v <= 1'b0; so_v <= 1'b0; m_re <= '0;
            for (s = 0; s < NSS; s = s + 1) an[s] = af_n[s];
            for (i = 0; i < NSS; i = i + 1) for (p = 0; p < NC; p = p + 1) pf_[i][p] = k_pf[i][p];
            begin : opn
                reg o; o = 1'b0;
                for (i = 0; i < NSS; i = i + 1) for (p = 0; p < NC; p = p + 1) if (k_msk[i][p] != 0) o = 1'b1;
                open_q <= o;
            end
            // ---- the command (fields from the pin flops); the start sequence -> nv
            all_rows <= nv && busy && &rdone;
            so <= {so[4:1], 1'b0};
            if (k_go) begin
                busy <= 1'b1; sm_m <= k_sm; obf <= k_bf; mm <= k_mm; qq <= k_qq; pp <= k_pp; nv <= 1'b0; so <= 5'b00001;
                ob_h <= k_ob; ost_h <= k_ost; all_rows <= 1'b0; sweep <= 1'b0;
            end
            if (so[5]) begin
                for (s = 0; s < NSS; s = s + 1)
                    need[s] <= (!sm_en[s] || dif[s][20] || dif[s] == 21'd0) ? 20'd0 : (dif[s][19:0] > {7'd0, qq}) ? {7'd0, qq} : dif[s][19:0];
                nv <= 1'b1;
            end
            // ---- arrivals (pre-armed: counted and queued whether or not the command has arrived)
            for (s = 0; s < NSS; s = s + 1) if (rv_q[s]) begin
                recv[s] <= recv[s] + 20'd1;
                if (an[s] == AD) s_fault <= 1'b1;                           // overrun: fail closed
                else begin af_t[s] <= af_t[s] + 1'b1; an[s] = an[s] + 1'b1; end
            end
            // ---- E: commit (VM) / emit (STREAM)
            for (p = 0; p < NC; p = p + 1) m_we[p] <= e_cm && (p < pp);
            if (e_cm) begin
                for (p = 0; p < NC; p = p + 1) if (p < pp) begin : co
                    reg [2:0] w; reg par;
                    w = e_wa[p][2:0]; par = k_par[e_i][p];
                    if (e_ch[p]) begin                                     // the old sector -> a pending flush
                        pf_[e_i][p][par] = 1'b1;
                        k_par[e_i][p] <= MUT_PAR ? par : !par;
                    end
                    k_msk[e_i][p] <= (e_ch[p] || k_msk[e_i][p] == 0) ? (8'd1 << w) : (k_msk[e_i][p] | (8'd1 << w));
                end
                e_v <= 1'b0;
            end
            if (x_bt) begin
                so_v <= 1'b1;
                if (e_sp + 4'd1 >= pp) begin e_v <= 1'b0; e_sp <= 4'd0; end
                else e_sp <= e_sp + 4'd1;
            end
            cr <= cr - (x_bt ? 1'b1 : 1'b0) + (cr_q ? 1'b1 : 1'b0);
            if (x_de) begin e_v <= 1'b1; d_v <= 1'b0; end
            if (x_ad) begin d_v <= 1'b1; a_v <= 1'b0; end
            if (x_ra) begin a_v <= 1'b1; c_v <= 1'b0; end
            if (x_rc) begin c_v <= 1'b1; r_v <= 1'b0; end
            sm_cr <= '0;
            if (x_pr) sm_cr[p_i] <= 1'b1;                                     // the entry is free: one row credit
`ifdef OT_PUB_MUT_CR
            sm_cr <= rv_q;                                                    // MUTANT: credit on arrival, not consumption
`endif
            if (x_pr) begin
                r_v <= 1'b1; af_h[p_i] <= af_h[p_i] + 1'b1; an[p_i] = an[p_i] - 1'b1; p_v <= 1'b0;
            end
            // ---- P: pick an SM with a queued row (round robin), once the command is in
            if (busy && !k_go && !p_v) begin : pick
                reg f; reg [LSL-1:0] ix; integer q2;
                f = 1'b0; ix = '0;
                for (i = 0; i < NSS; i = i + 1) begin
                    q2 = (rrp + 1 + i) % NSS;
                    if (!f && af_n[q2] != 0) begin f = 1'b1; ix = LSL'(q2); end
                end
                if (f) begin p_v <= 1'b1; p_i <= ix; rrp <= ix; end
            end
            for (s = 0; s < NSS; s = s + 1) af_n[s] <= an[s];
            // ---- end sweep (VM): every open sector -> a pending flush (a local SM / 2 edges)
            if (busy && !sm_m && nv && all_rows && &rdone && arr_empty && !p_v && !r_v && !c_v && !a_v && !d_v && !e_v && !sweep) begin
                sweep <= 1'b1; sw_i <= '0; sw_ph <= 1'b0;
            end
            if (sw_a) sw_ph <= 1'b1;
            if (sw_go) begin
                for (p = 0; p < NC; p = p + 1) if (sw_m[p] != 0) begin pf_[sw_l][p][sw_p[p]] = 1'b1; k_msk[sw_l][p] <= 8'd0; end
                sw_i <= sw_i + 1'b1; sw_ph <= 1'b0;
            end
            // ---- drain: issue the row FIFO head (one write out at a time); capture; read; pick
            if (tk) begin w_v <= 1'b1; tok <= 1'b1; hq_h <= ~hq_h; end
            if (ack_q) tok <= 1'b0;
            if (dr_v3) hq_t <= ~hq_t;
            hq_n <= hn;
            if (dr_v2) pf_[dr_e2[LSL+23:24]][dr_q2][dr_e2[23]] = 1'b0;     // the row is read (capture this edge): free it
            dr_v3 <= dr_v2; dr_v2 <= dr_v; dr_v <= dk_v;
            if (dk_v) m_re[dk_q] <= 1'b1;
            dk_v <= k1_f;
            if (k1_f) dr_rr <= k1_q;
            for (c = 0; c < NC; c = c + 1) begin
                pq_t[c] <= pq_t[c] + (q_push[c] ? 1'b1 : 1'b0);
                pq_h[c] <= pq_h[c] + (q_pop[c] ? 1'b1 : 1'b0);
                case ({q_push[c], q_pop[c]})
                    2'b10: begin pq_n[c] <= pq_n[c] + 1'b1; pq_f[c] <= (pq_n[c] == (PQW+1)'(PQ - 1)); pq_ne[c] <= 1'b1; end
                    2'b01: begin pq_n[c] <= pq_n[c] - 1'b1; pq_f[c] <= 1'b0; pq_ne[c] <= (pq_n[c] != (PQW+1)'(1)); end
                    default: ;
                endcase
            end
            for (i = 0; i < NSS; i = i + 1) for (p = 0; p < NC; p = p + 1) k_pf[i][p] <= pf_[i][p];
            // ---- done: every row in, swept (VM) / emitted (STREAM), nothing pending, the write acknowledged
            done_now = busy && !k_go && nv && all_rows && &rdone && !pend_any && !tok && !w_v && !so_v &&
                       (sm_m || (sweep && sw_i >= NSS && !open_q));
            if (done_now) begin
                busy <= 1'b0; s_done <= 1'b1; sweep <= 1'b0; nv <= 1'b0; so <= '0;
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
// Hard station: command pins, acceptance, completion and column-zero launch.
module ot_hgi_sm_pub_cmd #(parameter integer NSL=8, NPC=4, NC=8, LV=3)(
 input wire clk,rn,pub_v, input wire [39:0] pub_base, input wire [31:0] pub_stride,
 input wire [1:0] pub_space, input wire [19:0] pub_m, input wire [12:0] pub_q,
 input wire [3:0] pub_p, input wire pub_bf16, input wire [NSL-1:0] dn_l,ft_l,
 input wire agg_r, input wire [NPC-1:0] vq_vw,
 output wire pub_rdy, output reg pub_done,pub_fault,cgo, output reg [74:0] cfd);
 reg rel,busy,acc_q; reg [39:0] pf_b; reg [31:0] pf_s; reg [1:0] pf_sp;
 reg [19:0] pf_m; reg [12:0] pf_q; reg [3:0] pf_p; reg pf_bf;
 assign pub_rdy=rel && !busy && !acc_q;
 always @(posedge clk) begin pf_b<=pub_base; pf_s<=pub_stride; pf_sp<=pub_space;
 pf_m<=pub_m; pf_q<=pub_q; pf_p<=pub_p; pf_bf<=pub_bf16; end
    always @(posedge clk) begin
        if (acc_q) cfd <= {pf_sp == 2'd2, pf_bf, pf_b[17:0], pf_s[17:0], pf_m, pf_q, pf_p};
    end
    // ---- control
    reg [NSL-1:0] sdn; reg [7:0] allc;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            rel <= 1'b0; busy <= 1'b0; acc_q <= 1'b0; pub_done <= 1'b0; pub_fault <= 1'b0;
 sdn <= '0; allc <= 8'd0; cgo <= 1'b0;
        end else begin
            rel <= 1'b1;
            acc_q <= pub_v && pub_rdy;
            pub_done <= 1'b0; cgo <= 1'b0;
            if (|ft_l) pub_fault <= 1'b1;                                   // a slice overrun: fail closed
            if (acc_q) begin
                if (!(pf_sp == 2'd1 || pf_sp == 2'd2) || pf_p == 4'd0 || pf_p > NC) pub_fault <= 1'b1;
                else begin
                    busy <= 1'b1; sdn <= '0; allc <= 8'd0;
                    cgo <= 1'b1;
                end
            end else if (busy) begin
                sdn <= sdn | dn_l;
                if (&sdn && allc != 8'hFF) allc <= allc + 8'd1;
                if (&sdn && allc >= 8'(LV + 1) && !agg_r && vq_vw == 0) begin busy <= 1'b0; pub_done <= 1'b1; end
            end
        end
    end
endmodule

module ot_hgi_sm_pub_vmmerge #(parameter integer NIN=2)(
 input wire clk,rn, input wire [NIN-1:0] i_v, input wire [NIN*279-1:0] i_pkt,
 input wire [273:0] vmr, output wire [337:0] vmq, output wire active, output wire [NIN-1:0] ack);
 localparam integer OWW=(NIN>1)?$clog2(NIN):1;
 assign ack=ak;
        reg [NIN-1:0] pend, ak; reg bsy, n_v, va_q, vq_v; reg [278:0] n_p, vq_p; reg [OWW-1:0] own, rr;
        assign active = vq_v;
        assign vmq = {vq_v, 1'b1, 12'd0, vq_p[278:264], 5'd0, vq_p[263:8],
            {{4{vq_p[7]}}, {4{vq_p[6]}}, {4{vq_p[5]}}, {4{vq_p[4]}}, {4{vq_p[3]}}, {4{vq_p[2]}}, {4{vq_p[1]}}, {4{vq_p[0]}}},
            16'h5042};
        always @(posedge clk) if (n_v) vq_p <= n_p;
        always @(posedge clk or negedge rn) begin
            if (!rn) begin pend <= '0; ak <= '0; bsy <= 1'b0; n_v <= 1'b0; va_q <= 1'b0; vq_v <= 1'b0; own <= '0; rr <= '0; end
            else begin : nd
                reg f; integer q_, jj; reg [NIN-1:0] pn;
                va_q <= vmr[273] && vmr[256];           // port pin flop (MEM 1: vr[273] && vr[256])
                vq_v <= n_v; n_v <= 1'b0; ak <= '0;
                pn = pend;
                for (q_ = 0; q_ < NIN; q_ = q_ + 1) if (i_v[q_]) pn[q_] = 1'b1;
                f = 1'b0;
                if (!bsy) for (jj = 0; jj < NIN; jj = jj + 1) begin q_ = (rr + 1 + jj) % NIN;
                    if (!f && pend[q_]) begin
                        f = 1'b1; pn[q_] = 1'b0; own <= OWW'(q_); rr <= OWW'(q_); bsy <= 1'b1; n_v <= 1'b1;
                        n_p <= i_pkt[q_ * 279 +: 279];
                    end
                end
                if (bsy && va_q) begin bsy <= 1'b0; ak[own] <= 1'b1; end    // acknowledged: back to the owning slice
                pend <= pn;
            end
        end

endmodule

module ot_hgi_sm_pub_cmd_relay(input wire clk,rn,i_go,input wire [74:0] i_data,
 output reg o_go,output reg [74:0] o_data);
 always @(posedge clk) o_data<=i_data;
 always @(posedge clk or negedge rn) if(!rn) o_go<=1'b0; else o_go<=i_go;
endmodule

module ot_hgi_sm_pub_return #(parameter integer DL=1)(input wire clk,rn,i_done,i_fault,
 output wire o_done,o_fault);
 reg [DL-1:0] dq,fq;
 always @(posedge clk or negedge rn) if(!rn) begin dq<='0;fq<='0;end
 else begin dq<=(dq<<1)|i_done;fq<=(fq<<1)|i_fault;end
 assign o_done=dq[DL-1];assign o_fault=fq[DL-1];
endmodule

module ot_hgi_sm_pub_credit #(parameter integer NSM=32)(input wire clk,rn,input wire [NSM-1:0] i_cr,
 output reg [NSM-1:0] o_cr);
 always @(posedge clk or negedge rn) if(!rn) o_cr<='0;else o_cr<=i_cr;
endmodule

module ot_hgi_sm_pub_egress(input wire clk,rn,i_v,i_busy,input wire [51:0] i_data,
 output reg relay_v,busy,o_v,output reg [19:0] o_idx,output reg [31:0] o_data);
 reg [51:0] relay_d;
 always @(posedge clk) begin if(i_v) relay_d<=i_data;if(relay_v) begin o_idx<=relay_d[51:32];o_data<=relay_d[31:0];end end
 always @(posedge clk or negedge rn) if(!rn) begin relay_v<=1'b0;busy<=1'b0;o_v<=1'b0;end
 else begin relay_v<=i_v;busy<=i_busy;o_v<=relay_v;end
endmodule

module ot_hgi_sm_pub_hier #(
    parameter integer NSM = 32,
    parameter integer NC = 8,
    parameter integer NPC = 4,
    parameter integer MUT_ROW = 0,
    parameter integer MUT_PAR = 0,
    parameter integer NSS = 4,
    parameter integer SD = 8,
    parameter integer AD = 32              // per-SM arrival entries in every slice (= the slice default; row credits)
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
    output wire                pub_done,
    output wire                pub_fault,
    input  wire [NSM-1:0]     sm_rv,
    input  wire [NSM*12-1:0]  sm_rrow,
    input  wire [NSM*NC*32-1:0] sm_rdata,
    output wire [NPC*338-1:0] vmq,
    input  wire [NPC*274-1:0] vmr,
    output wire                s0_v,
    output wire  [19:0]        s0_idx,
    output wire  [31:0]        s0_data,
    output wire  [NSM-1:0]     sm_cr          // row credits to ot_hgi_sm_record: slice pulses, one output flop
);
    ot_hgi_sm_pub_parent #(.NSM(NSM),.NC(NC),.NPC(NPC),.MUT_ROW(MUT_ROW),.MUT_PAR(MUT_PAR),.NSS(NSS),.SD(SD),.AD(AD)) u_parent (
      .clk_rst(clk),.clk_cmd(clk),.clk_cmd_relay({3{clk}}),.clk_slice({8{clk}}),
      .clk_return({8{clk}}),.clk_vm({4{clk}}),.clk_tree({7{clk}}),.clk_credit({8{clk}}),.clk_egress(clk),
      .rst_n(rst_n),
      .pub_v(pub_v),
      .pub_rdy(pub_rdy),
      .pub_base(pub_base),
      .pub_stride(pub_stride),
      .pub_space(pub_space),
      .pub_m(pub_m),
      .pub_q(pub_q),
      .pub_p(pub_p),
      .pub_bf16(pub_bf16),
      .pub_done(pub_done),
      .pub_fault(pub_fault),
      .sm_rv(sm_rv),
      .sm_rrow(sm_rrow),
      .sm_rdata(sm_rdata),
      .vmq(vmq),
      .vmr(vmr),
      .s0_v(s0_v),
      .s0_idx(s0_idx),
      .s0_data(s0_data),
      .sm_cr(sm_cr));
endmodule

// Wires-only production composition: every hard-child clock has an actual top entry.
module ot_hgi_sm_pub_parent #(
    parameter integer NSM = 32,
    parameter integer NC = 8,
    parameter integer NPC = 4,
    parameter integer MUT_ROW = 0,
    parameter integer MUT_PAR = 0,
    parameter integer NSS = 4,
    parameter integer SD = 8,
    parameter integer AD = 32              // per-SM arrival entries in every slice (= the slice default; row credits)
) (
    input wire clk_rst,clk_cmd,clk_egress,
    input wire [7:0] clk_credit,
    input wire [2:0] clk_cmd_relay,
    input wire [7:0] clk_slice,clk_return,
    input wire [3:0] clk_vm,
    input wire [6:0] clk_tree,
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
    output wire                pub_done,
    output wire                pub_fault,
    input  wire [NSM-1:0]     sm_rv,
    input  wire [NSM*12-1:0]  sm_rrow,
    input  wire [NSM*NC*32-1:0] sm_rdata,
    output wire [NPC*338-1:0] vmq,
    input  wire [NPC*274-1:0] vmr,
    output wire                s0_v,
    output wire  [19:0]        s0_idx,
    output wire  [31:0]        s0_data,
    output wire  [NSM-1:0]     sm_cr          // row credits to ot_hgi_sm_record: slice pulses, one output flop
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
    ot_hgi_sm_pub_reset u_rst (.clk(clk_rst), .rst_n_in(rst_n), .rn(rn));
    wire [NCOL*75-1:0] cfd; wire [NCOL-1:0] cgo;
    wire r1_v, agg_r;
`ifdef SYNTHESIS
    ot_hgi_sm_pub_cmd
`else
    ot_hgi_sm_pub_cmd #(.NSL(NSL),.NPC(NPC),.NC(NC),.LV(LV))
`endif
    u_cmd (
      .clk(clk_cmd),.rn(rn),.pub_v(pub_v),.pub_base(pub_base),.pub_stride(pub_stride),
      .pub_space(pub_space),.pub_m(pub_m),.pub_q(pub_q),.pub_p(pub_p),.pub_bf16(pub_bf16),
      .dn_l(dn_l),.ft_l(ft_l),.agg_r(agg_r),.vq_vw(vq_vw),.pub_rdy(pub_rdy),
      .pub_done(pub_done),.pub_fault(pub_fault),.cgo(cgo[0]),.cfd(cfd[0 +: 75]));
    genvar col;
    generate for(col=1;col<NCOL;col=col+1) begin:g_cmd
      ot_hgi_sm_pub_cmd_relay u (.clk(clk_cmd_relay[col-1]),.rn(rn),.i_go(cgo[col-1]),
        .i_data(cfd[(col-1)*75 +:75]),.o_go(cgo[col]),.o_data(cfd[col*75 +:75]));
    end endgenerate
    // ---- slices
    wire [NSMP-1:0] rv_p = NSMP'(sm_rv);
    wire [NSMP*12-1:0] rr_p = (NSMP*12)'(sm_rrow);
    wire [NSMP*NC*32-1:0] rd_p = (NSMP*NC*32)'(sm_rdata);
    wire [NSL-1:0] s_wv, s_sov, s_dn, s_ft; wire [NSL*279-1:0] s_wp; wire [NSL*W-1:0] s_sod;
    wire [NSL-1:0] s_cr; wire [NSMP-1:0] s_smcr;
    genvar crk;
    generate for(crk=0;crk<NSL;crk=crk+1) begin:g_credit
        wire [NSS-1:0] credit_out;
`ifdef SYNTHESIS
        ot_hgi_sm_pub_credit4 u
`else
        ot_hgi_sm_pub_credit #(.NSM(NSS)) u
`endif
        (.clk(clk_credit[crk]),.rn(rn),.i_cr(s_smcr[crk*NSS +:NSS]),.o_cr(credit_out));
        for(genvar crs=0;crs<NSS;crs=crs+1) begin:g_sm
          if(crk*NSS+crs<NSM) assign sm_cr[crk*NSS+crs]=credit_out[crs];
        end
    end endgenerate
    genvar gk, gl, gn, gc, gj;
    generate for (gk = 0; gk < NSL; gk = gk + 1) begin : g_s
        localparam integer COL = gk % NCOL;
        localparam integer NE_ = (NSM - gk * NSS >= NSS) ? NSS : NSM - gk * NSS;
        localparam [NSS-1:0] EN = NSS'((1 << NE_) - 1);
        wire [CW-1:0] ci = {cgo[COL], cfd[COL*(CW-1) +: CW-1]};
`ifdef SYNTHESIS
        ot_hgi_sm_pub_slice u (
`else
        ot_hgi_sm_pub_slice #(.NSS(NSS), .NC(NC), .SD(SD), .AD(AD), .MUT_ROW(MUT_ROW), .MUT_PAR(MUT_PAR)) u (
`endif
            .clk(clk_slice[gk]), .rst_n(rst_n), .sid(3'(gk)), .sm_en(EN), .c_go(ci[CW-1]), .c_sm(ci[CW-2]), .c_bf(ci[CW-3]),
            .c_ob(ci[72:55]), .c_ost(ci[54:37]), .c_mm(ci[36:17]), .c_qq(ci[16:4]), .c_pp(ci[3:0]),
            .sm_rv(rv_p[gk*NSS +: NSS]), .sm_rrow(rr_p[gk*NSS*12 +: NSS*12]), .sm_rdata(rd_p[gk*NSS*NC*32 +: NSS*NC*32]),
            .w_v(s_wv[gk]), .w_pkt(s_wp[gk*279 +: 279]), .w_ack(s_ack[gk]),
            .so_v(s_sov[gk]), .so_idx(s_sod[gk*W+32 +: 20]), .so_data(s_sod[gk*W +: 32]), .so_cr(s_cr[gk]),
            .s_done(s_dn[gk]), .s_fault(s_ft[gk]), .sm_cr(s_smcr[gk*NSS +: NSS]));
    end endgenerate
    // ---- done / fault return: col + 1 relays a slice
    wire [NSL-1:0] dn_l, ft_l;
    generate for (gk = 0; gk < NSL; gk = gk + 1) begin : g_ret
        localparam integer DL = gk % NCOL + 1;
`ifdef SYNTHESIS
        if(DL==1) begin:g_d1
        ot_hgi_sm_pub_return_d1 u (.clk(clk_return[gk]),.rn(rn),.i_done(s_dn[gk]),
          .i_fault(s_ft[gk]),.o_done(dn_l[gk]),.o_fault(ft_l[gk]));
        end
        else if(DL==2) begin:g_d2
        ot_hgi_sm_pub_return_d2 u (.clk(clk_return[gk]),.rn(rn),.i_done(s_dn[gk]),
          .i_fault(s_ft[gk]),.o_done(dn_l[gk]),.o_fault(ft_l[gk]));
        end
        else if(DL==3) begin:g_d3
        ot_hgi_sm_pub_return_d3 u (.clk(clk_return[gk]),.rn(rn),.i_done(s_dn[gk]),
          .i_fault(s_ft[gk]),.o_done(dn_l[gk]),.o_fault(ft_l[gk]));
        end
        else if(DL==4) begin:g_d4
        ot_hgi_sm_pub_return_d4 u (.clk(clk_return[gk]),.rn(rn),.i_done(s_dn[gk]),
          .i_fault(s_ft[gk]),.o_done(dn_l[gk]),.o_fault(ft_l[gk]));
        end
`else
        ot_hgi_sm_pub_return #(.DL(DL)) u (.clk(clk_return[gk]),.rn(rn),.i_done(s_dn[gk]),
          .i_fault(s_ft[gk]),.o_done(dn_l[gk]),.o_fault(ft_l[gk]));
`endif
    end endgenerate
    // ---- VM: one merge node a client (its slices' held packets; one write out a client, as MEM 1)
    wire [NPC-1:0] vq_vw; wire [NSL-1:0] s_ack;
    localparam integer OWW = (NIN > 1) ? $clog2(NIN) : 1;
    generate for (gc = 0; gc < NPC; gc = gc + 1) begin : g_c
        wire [NIN-1:0] i_v,ak; wire [NIN*279-1:0] i_pkt;
    `ifdef SYNTHESIS
    ot_hgi_sm_pub_vmmerge
`else
    ot_hgi_sm_pub_vmmerge #(.NIN(NIN))
`endif
    u (.clk(clk_vm[gc]),.rn(rn),.i_v(i_v),.i_pkt(i_pkt),
          .vmr(vmr[gc*274 +:274]),.vmq(vmq[gc*338 +:338]),.active(vq_vw[gc]),.ack(ak));
        for(gj=0;gj<NIN;gj=gj+1) begin:g_a
          if(gc+gj*NPC<NSL) begin:g_ae
            assign i_v[gj]=s_wv[gc+gj*NPC]; assign i_pkt[gj*279 +:279]=s_wp[(gc+gj*NPC)*279 +:279];
            assign s_ack[gc+gj*NPC]=ak[gj];
          end else begin:g_az
            assign i_v[gj]=1'b0; assign i_pkt[gj*279 +:279]='0;
          end
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
`ifdef SYNTHESIS
                if(gl==1) begin:g_h1
                ot_hgi_sm_pub_smrg_l1 u (
                    .clk(clk_tree[NLF-(NLF >> (gl-1))+gn]), .rn(rn), .i_v(t_v[C0 +: 2]), .i_d(t_d[C0*W +: 2*W]), .i_cr(t_cr[C0 +: 2]),
                    .o_v(t_v[B]), .o_d(t_d[B*W +: W]), .o_cr((gl == LV) ? 1'b0 : t_cr[B]), .xb((gl == LV) ? r1_v : 1'b0),
                    .a_in(t_a[C0 +: 2]), .a_out(t_a[B]));
                end
                else if(gl==2) begin:g_h2
                ot_hgi_sm_pub_smrg_l2 u (
                    .clk(clk_tree[NLF-(NLF >> (gl-1))+gn]), .rn(rn), .i_v(t_v[C0 +: 2]), .i_d(t_d[C0*W +: 2*W]), .i_cr(t_cr[C0 +: 2]),
                    .o_v(t_v[B]), .o_d(t_d[B*W +: W]), .o_cr((gl == LV) ? 1'b0 : t_cr[B]), .xb((gl == LV) ? r1_v : 1'b0),
                    .a_in(t_a[C0 +: 2]), .a_out(t_a[B]));
                end
                else if(gl==3) begin:g_h3
                ot_hgi_sm_pub_smrg_l3 u (
                    .clk(clk_tree[NLF-(NLF >> (gl-1))+gn]), .rn(rn), .i_v(t_v[C0 +: 2]), .i_d(t_d[C0*W +: 2*W]), .i_cr(t_cr[C0 +: 2]),
                    .o_v(t_v[B]), .o_d(t_d[B*W +: W]), .o_cr((gl == LV) ? 1'b0 : t_cr[B]), .xb((gl == LV) ? r1_v : 1'b0),
                    .a_in(t_a[C0 +: 2]), .a_out(t_a[B]));
                end
`else
                ot_hgi_sm_pub_smrg #(.D(SD), .W(W), .ROOT(gl == LV), .LVL(gl)) u (
                    .clk(clk_tree[NLF-(NLF >> (gl-1))+gn]), .rn(rn), .i_v(t_v[C0 +: 2]), .i_d(t_d[C0*W +: 2*W]), .i_cr(t_cr[C0 +: 2]),
                    .o_v(t_v[B]), .o_d(t_d[B*W +: W]), .o_cr((gl == LV) ? 1'b0 : t_cr[B]), .xb((gl == LV) ? r1_v : 1'b0),
                    .a_in(t_a[C0 +: 2]), .a_out(t_a[B]));
`endif
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
    ot_hgi_sm_pub_egress u_egress (.clk(clk_egress),.rn(rn),.i_v(t_v[LV*NLF]),
      .i_data(t_d[LV*NLF*W +:W]),.i_busy(t_a[LV*NLF]),.relay_v(r1_v),.busy(agg_r),
      .o_v(s0_v),.o_idx(s0_idx),.o_data(s0_data));
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
    parameter integer HIER = `OT_HGI_PUB_HIER_DEF,
    parameter integer AD = 32              // per-SM arrival entries (MEM 1 / HIER 1) = ot_hgi_sm_record AD (row credits)
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
    output wire [31:0]        s0_data,
    output wire [NSM-1:0]     sm_cr          // row credits to ot_hgi_sm_record (CR = 1; its AD must equal this AD)
);
    generate if (HIER) begin : g_hier
        ot_hgi_sm_pub_hier #(.NSM(NSM), .NC(NC), .NPC(NPC), .MUT_ROW(MUT_ROW), .MUT_PAR(MUT_PAR), .AD(AD)) u (
            .clk(clk), .rst_n(rst_n), .pub_v(pub_v), .pub_rdy(pub_rdy), .pub_base(pub_base), .pub_stride(pub_stride),
            .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16), .pub_done(pub_done),
            .pub_fault(pub_fault), .sm_rv(sm_rv), .sm_rrow(sm_rrow), .sm_rdata(sm_rdata), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
            .s0_idx(s0_idx), .s0_data(s0_data), .sm_cr(sm_cr));
    end else if (MEM) begin : g_mem
        ot_hgi_sm_pub_mem #(.NSM(NSM), .NC(NC), .NPC(NPC), .MUT_ROW(MUT_ROW), .NE((NSM % NE == 0) ? NE : 1), .MUT_PAR(MUT_PAR), .AD(AD)) u (
            .clk(clk), .rst_n(rst_n), .pub_v(pub_v), .pub_rdy(pub_rdy), .pub_base(pub_base), .pub_stride(pub_stride),
            .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16), .pub_done(pub_done),
            .pub_fault(pub_fault), .sm_rv(sm_rv), .sm_rrow(sm_rrow), .sm_rdata(sm_rdata), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
            .s0_idx(s0_idx), .s0_data(s0_data), .sm_cr(sm_cr));
    end else begin : g_ff
        ot_hgi_sm_pub_ff #(.NSM(NSM), .NC(NC), .NPC(NPC), .MUT_ROW(MUT_ROW)) u (
            .clk(clk), .rst_n(rst_n), .pub_v(pub_v), .pub_rdy(pub_rdy), .pub_base(pub_base), .pub_stride(pub_stride),
            .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16), .pub_done(pub_done),
            .pub_fault(pub_fault), .sm_rv(sm_rv), .sm_rrow(sm_rrow), .sm_rdata(sm_rdata), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
            .s0_idx(s0_idx), .s0_data(s0_data), .sm_cr(sm_cr));
    end endgenerate
endmodule
module ot_hgi_sm_pub_return_d1(input wire clk,rn,i_done,i_fault,output wire o_done,o_fault);
 ot_hgi_sm_pub_return #(.DL(1)) u(.*);
endmodule

module ot_hgi_sm_pub_return_d2(input wire clk,rn,i_done,i_fault,output wire o_done,o_fault);
 ot_hgi_sm_pub_return #(.DL(2)) u(.*);
endmodule

module ot_hgi_sm_pub_return_d3(input wire clk,rn,i_done,i_fault,output wire o_done,o_fault);
 ot_hgi_sm_pub_return #(.DL(3)) u(.*);
endmodule

module ot_hgi_sm_pub_return_d4(input wire clk,rn,i_done,i_fault,output wire o_done,o_fault);
 ot_hgi_sm_pub_return #(.DL(4)) u(.*);
endmodule

module ot_hgi_sm_pub_smrg_l1(input wire clk,rn,input wire [1:0] i_v,input wire [103:0] i_d,
 output wire [1:0] i_cr,output wire o_v,output wire [51:0] o_d,input wire o_cr,xb,
 input wire [1:0] a_in,output wire a_out);
 ot_hgi_sm_pub_smrg #(.D(8),.W(52),.ROOT(0),.LVL(1)) u(.*);
endmodule

module ot_hgi_sm_pub_smrg_l2(input wire clk,rn,input wire [1:0] i_v,input wire [103:0] i_d,
 output wire [1:0] i_cr,output wire o_v,output wire [51:0] o_d,input wire o_cr,xb,
 input wire [1:0] a_in,output wire a_out);
 ot_hgi_sm_pub_smrg #(.D(8),.W(52),.ROOT(0),.LVL(2)) u(.*);
endmodule

module ot_hgi_sm_pub_smrg_l3(input wire clk,rn,input wire [1:0] i_v,input wire [103:0] i_d,
 output wire [1:0] i_cr,output wire o_v,output wire [51:0] o_d,input wire o_cr,xb,
 input wire [1:0] a_in,output wire a_out);
 ot_hgi_sm_pub_smrg #(.D(8),.W(52),.ROOT(1),.LVL(3)) u(.*);
endmodule

module ot_hgi_sm_pub_credit4(input wire clk,rn,input wire [3:0] i_cr,output wire [3:0] o_cr);
 ot_hgi_sm_pub_credit #(.NSM(4)) u(.*);
endmodule
module ot_hgi_sm_pub_reset(input wire clk,rst_n_in,output wire rn);
 ot_rst_relay #(.REGIONS(1)) u(.clk(clk),.rst_n_in(rst_n_in),.rst_n(rn));
endmodule
`default_nettype wire
