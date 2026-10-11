`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_sp_vm v2 -- the S81 layer-die VM master (s81-vm-1011 under ds-1010, 2026-10-11).  Serial (0.9 GHz) domain
// plus the stream (1.2 GHz) side of the dsfd_sp_ctrl ports.
//
// The banked memory is the CLOSED systolic tile dsfd_vm_bgq (rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv, NSTG 2, DW
// 128) at NP = 24 / NPR = 8 (opt-in tile parameters: 16 write-only capture ports, no return lanes on them):
// NS = 4 bit-sliced columns of 4 tiles, 32 banks x 512 rows x 512 b = 16,384 rows (8 Mb, 128 macros; sizing
// results/rtl/s81_ph_20261006/vm/record.json: worst layer 186,048 elements = 71 %), stall-free fixed latency,
// every op takes effect in global (issue cycle, port) order.  This file adds the two hard blocks of the master:
//   dsfd_vm_fe (N of the columns): every client's REQUEST side, the order register (stage B) shared by all ports,
//     the capture landing, the row-completion counter, the engine adapter, per-slice copies (stage C).
//   dsfd_vm_be (S of the columns): every client's RESPONSE side.
//
// Port map (NP 24; each port <= 1 op a cycle, never stalls):
//   p0  WFC kit write + even read (dsfd_vm_wfc_ep RD2 m_*)      p1  WFC kit odd read (m1_*)
//   p2  generic row port X2                                     p3 / p4  dsfd_sp_ctrl VM port, lanes A / B
//   p5  P2 lane-0 stream reader (engine op P2RD)                p6 / p7  generic row ports X0 / X1
//   p8 .. p23  capture landing lanes 0 .. 15 (write only)
//
// CAPTURE (dsfd_sp_capture t_vm, 13,376 b, serial domain, NO ready): per root r [104r +: 104] = {row1 {data32,
// addr19}, v1, row0 {data32, addr19}, v0}, [13312 +: 64] status.  The roots run up to 1 row a stream cycle each
// (128 elements / stream cycle = 10.7 rows / serial cycle), so every lane has its own write port: lane g = roots
// 8g .. 8g+7.  ALIGNMENT CONTRACT (compiler): obase and ops are multiples of 256 elements, so (S81 profile: root r
// owns rows 2r, 2r+1 mod 256) every element of lane g lands in a VM row R with R mod 16 = g, i.e. banks g / g+16
// only: the 16 lanes are bank-disjoint.  A violating element (addr[7:4] != g) or addr >= 2^18 -> sticky fault (fail
// closed, element dropped).  Each lane assembles rows in LA fully associative row entries (dsfd_vm_cl): a row is
// written when full (16 elements), when evicted (no free entry), or LTO cycles after its last element (partial
// rows), through a WQ-deep write queue drained by the lane's port one row a cycle (masked row write).  No overflow at
// the production shape and at the worst back-to-back burst (burst bench); a needed eviction into a full queue ->
// sticky fault.
//
// ROW-COMPLETION COUNTER (NSLOT slots): ARM (three engine ops) gives {base row, nrows, nelems}; every write op that
// reaches the order register in [base, base + nrows) adds popcount(mask) (elements).  When nelems have landed the
// slot completes: engine done (tag of its ARMN), t_rdy[slot] (inputs-present level for the consumer engine
// adapters, held until the slot is re-armed) and, with notify, rows-ready {user} to dsfd_vm_mtp_ep.  EARLY-READ
// ASSERTION: a read on any port into an armed, incomplete slot range at the counter stage sets sticky fault bit 0
// (fail closed) and $error()s in simulation.
//
// ENGINE CHANNEL: ot_s81_engine_adapter (QD 8; stream c side = dsfd_sp_ctrl cv[e] / cd[e] / dv[e] / dt[e]; serial e
// side).  Command word = ot_s81_stage_seq layout {slot, user 10, pos 21, tok 21, arg 24, op 7}, done tag {slot, op};
// the VM op is arg[23:21] (compiler-owned native descriptor):
//   1 ARMB  [20:19] cslot [18] notify [13:0] base row          done at once
//   2 ARMR  [20:19] cslot [14:0] nrows                         done at once
//   3 ARMN  [20:19] cslot [18:0] nelems (arms; user = cmd user) done at completion
//   4 P2ID  [20:18] part 0..4 [17:0] {shared, expert 9, identity 74}[18*part +: 18]   done at once
//   5 P2RD  [20:7] base row [6:0] nwords - 1                    done at the last read issued
//   0, 6, 7 -> fault bit 7
// dsfd_sp_ctrl VM port (stream): vwe / vwa / vwd, vre / vra -> two ratio-CDC FIFOs (stream pushes alternate), the
// serial side pops <= 2 a cycle in order onto p3 then p4; read data returns in the same order through two return
// FIFOs (BE) -> vrv / vrq (the controller runs USE_VM_RVALID 1).
//
// Mutants (negative controls, tools/s81_vm/s81_vm_gate.py):
//   OT_SPVM_MUT_STALE    X0 (p6) ops reach the memory one cycle after their order-register position
//   OT_SPVM_MUT_DROPW    the capture landing drops every 61st element (accepted, never written)
//   OT_SPVM_MUT_EARLY    the completion counter completes one element early
//   OT_SPVM_MUT_NOALIGN  the alignment check is removed (a misaligned phase then corrupts silently)
//   OT_SPVM_MUT_NP16     two lanes share each write port (8 capture ports): must overflow under the burst bench
// ---------------------------------------------------------------------------------------------------------------

// ================================================================================================ capture lane
// dsfd_vm_cl v3 (el1011-ds-vm/fe, 2026-10-11): one capture lane (8 roots = 16 element inputs a cycle), rebuilt as a
// 5-stage pipeline so no stage carries the old one-cycle match -> allocate -> evict -> merge -> move chain:
//   C1  decode (registered): alignment / range check, row key = addr[17:8], slot bit = addr[0], batch LEADERS (first
//       element of each distinct key in the batch) and every follower's leader (one-hot)
//   A   match: leader keys vs the entry tags (state) and vs the leaders of the batch now in B (forward of its
//       allocations); miss vector + miss ordinals (prefix count), registered
//   B   allocate: hit -> its entry (forwarded B entry first); the n-th miss -> the n-th free entry (ordinal match, all
//       operands registered); one more miss -> the oldest entry untouched by the batches in A and B is EVICTED (age
//       order precomputed from registered ages); tags / ages / valid owned here
//   M   merge + move: every element writes its slot of its leader's entry (S81 root-slot contract: root i owns slots 2i,
//       2i+1, so each slot is a 2:1 select); one move a cycle into the write queue, all from REGISTERED entry state:
//       eviction, else the lowest full entry, else the lowest timed-out entry (LTO cycles untouched)
//   W   write queue (WQ) -> the lane's port, one row a cycle (registered outputs)
// Races are closed structurally: M never frees an entry hit by the batch in A or B (a moved entry that is hit again
// stays valid and the next merge starts a new partial row, as v2 did for late elements); an eviction victim is never an
// entry hit by the batch in A or B; free entries are therefore never the target of an in-flight hit.
// Contract (checked, fail closed): element k of root i = 8G + k/2 has addr[7:1] == i (S81 profile: root r owns rows
// 2r, 2r+1 mod 256; v2 checked addr[7:4] == G only).  Faults (sticky): [0] alignment, [1] range, [2] allocation (no free
// entry and no victim), [3] write queue full at an eviction.
module dsfd_vm_cl #(
    parameter integer G = 0,            // lane index (static)
    parameter integer LA = 12,          // row entries
    parameter integer LTO = 16,         // partial-row timeout (cycles since last element)
    parameter integer WQ = 2            // write queue depth
) (
    input  wire          clk, rn,       // rn: this lane's relayed reset (control only)
    input  wire [15:0]   ev,
    input  wire [16*19-1:0] ea,
    input  wire [16*32-1:0] ed,
    input  wire          slot_ok,       // this cycle's port slot is the lane's (MUT_NP16: every other cycle)
    output reg           w_v,           // masked row write to the order register
    output reg  [13:0]   w_row,
    output reg  [15:0]   w_m,
    output reg  [511:0]  w_d,
    output reg  [3:0]    flt
);
    localparam integer AW = $clog2(LTO + 1);
    localparam integer OB = 5;          // ordinal width (0 .. 16)
    localparam integer QB = (WQ > 1) ? $clog2(WQ) : 1;
    // ------------------------------------------------------------------ C1: decode, leaders
    reg [15:0] d_ok, d_ld; reg [15:0] d_fol [0:15]; reg d_fal, d_frg;
    always @* begin : p_dec integer k, j; reg [15:0] eq;
        d_ok = 16'd0; d_fal = 1'b0; d_frg = 1'b0;
        for (k = 0; k < 16; k = k + 1) if (ev[k]) begin
            if (ea[19*k + 18]) d_frg = 1'b1;
`ifndef OT_SPVM_MUT_NOALIGN
            else if (ea[19*k + 1 +: 7] != {G[3:0], k[3:1]}) d_fal = 1'b1;
`endif
            else d_ok[k] = 1'b1;
        end
        for (k = 0; k < 16; k = k + 1) begin
            eq = 16'd0;
            for (j = 0; j < k; j = j + 1) eq[j] = d_ok[j] && ea[19*j + 8 +: 10] == ea[19*k + 8 +: 10];
            d_ld[k] = d_ok[k] && eq == 16'd0;
            d_fol[k] = 16'd0;
            for (j = k; j >= 0; j = j - 1) if ((j == k) ? (eq == 16'd0) : eq[j]) d_fol[k] = 16'd1 << j;
            if (!d_ok[k]) d_fol[k] = 16'd0;
        end
    end
    reg [15:0] s1_ld, s1_b; reg [9:0] s1_k [0:15]; reg [31:0] s1_d [0:15]; reg [15:0] s1_fol [0:15];
    always @(posedge clk) begin : p_s1 integer k;
        for (k = 0; k < 16; k = k + 1) begin
            s1_k[k] <= ea[19*k + 8 +: 10]; s1_d[k] <= ed[32*k +: 32]; s1_fol[k] <= d_fol[k];
        end
        s1_b <= {ea[19*15], ea[19*14], ea[19*13], ea[19*12], ea[19*11], ea[19*10], ea[19*9], ea[19*8],
                 ea[19*7], ea[19*6], ea[19*5], ea[19*4], ea[19*3], ea[19*2], ea[19*1], ea[19*0]};
        if (!rn) s1_ld <= 16'd0; else s1_ld <= d_ld;
    end
    // ------------------------------------------------------------------ entry state
    reg [LA-1:0] V;                     // B: entry holds a key
    reg [9:0]    KEY  [0:LA-1];         // B: tag
    reg [AW-1:0] AGE  [0:LA-1];         // B: cycles since the last touch (saturates at LTO)
    reg [15:0]   MASK [0:LA-1];         // M
    reg [511:0]  DATA [0:LA-1];         // M (no reset)
    reg [9:0]    KEYM [0:LA-1];         // M: tag of the stored row
    // ------------------------------------------------------------------ A: match
    reg [15:0] s2_ld, s2_b, s2_ms; reg [9:0] s2_k [0:15]; reg [31:0] s2_d [0:15]; reg [15:0] s2_fol [0:15];
    reg [LA-1:0] s2_hS [0:15]; reg [15:0] s2_hB [0:15]; reg [OB-1:0] s2_mo [0:15];
    reg [LA-1:0] a_hS [0:15]; reg [15:0] a_hB [0:15]; reg [15:0] a_ms; reg [OB-1:0] a_mo [0:15]; reg [LA-1:0] touchA;
    always @* begin : p_a integer k, e, j; reg [OB-1:0] c;
        touchA = {LA{1'b0}}; c = {OB{1'b0}};
        for (k = 0; k < 16; k = k + 1) begin
            for (e = 0; e < LA; e = e + 1) a_hS[k][e] = s1_ld[k] && V[e] && KEY[e] == s1_k[k];
            for (j = 0; j < 16; j = j + 1) a_hB[k][j] = s1_ld[k] && s2_ld[j] && s2_k[j] == s1_k[k];
            a_ms[k] = s1_ld[k] && a_hS[k] == {LA{1'b0}} && a_hB[k] == 16'd0;
            a_mo[k] = c; c = c + {{(OB-1){1'b0}}, a_ms[k]};
            touchA = touchA | a_hS[k];
        end
    end
    always @(posedge clk) begin : p_s2 integer k;
        for (k = 0; k < 16; k = k + 1) begin
            s2_k[k] <= s1_k[k]; s2_d[k] <= s1_d[k]; s2_fol[k] <= s1_fol[k];
            s2_hS[k] <= a_hS[k]; s2_hB[k] <= a_hB[k]; s2_mo[k] <= a_mo[k];
        end
        s2_b <= s1_b; s2_ms <= a_ms;
        if (!rn) s2_ld <= 16'd0; else s2_ld <= s1_ld;
    end
    // ------------------------------------------------------------------ B: allocate / evict
    reg [LA-1:0] ent_p [0:15];          // entry of each leader of the previous B batch
    reg [LA-1:0] b_ent [0:15];          // entry of each leader of this batch (0: dropped)
    reg [LA-1:0] touchB, b_al, b_ev, vic, cand, fr;
    reg [9:0]    b_ak [0:LA-1];
    reg          b_fal2;
    reg [OB-1:0] fo [0:LA-1]; reg [OB-1:0] nf;
    reg [LA-1:0] older [0:LA-1];
    always @* begin : p_old integer e, f;
        for (e = 0; e < LA; e = e + 1) for (f = 0; f < LA; f = f + 1)
            older[e][f] = (f == e) || AGE[e] > AGE[f] || (AGE[e] == AGE[f] && e < f);
    end
    always @* begin : p_b integer k, e, j; reg [LA-1:0] h; reg [OB-1:0] c;
        fr = ~V; c = {OB{1'b0}};
        for (e = 0; e < LA; e = e + 1) begin fo[e] = c; c = c + {{(OB-1){1'b0}}, fr[e]}; end
        nf = c;
        touchB = {LA{1'b0}};
        for (k = 0; k < 16; k = k + 1) begin
            h = {LA{1'b0}};
            for (j = 0; j < 16; j = j + 1) if (s2_hB[k][j]) h = h | ent_p[j];
            if (s2_hB[k] == 16'd0) h = s2_hS[k];
            b_ent[k] = s2_ld[k] ? h : {LA{1'b0}};
            touchB = touchB | b_ent[k];
        end
        cand = V & ~touchB & ~touchA;
        for (e = 0; e < LA; e = e + 1) vic[e] = cand[e] && ((older[e] | ~cand) == {LA{1'b1}});
        b_al = {LA{1'b0}}; b_ev = {LA{1'b0}}; b_fal2 = 1'b0;
        for (e = 0; e < LA; e = e + 1) b_ak[e] = 10'd0;
        for (k = 0; k < 16; k = k + 1) if (s2_ms[k]) begin
            if (s2_mo[k] < nf) begin
                for (e = 0; e < LA; e = e + 1) if (fr[e] && fo[e] == s2_mo[k]) begin
                    b_ent[k] = b_ent[k] | ({{(LA-1){1'b0}}, 1'b1} << e); b_al[e] = 1'b1; b_ak[e] = b_ak[e] | s2_k[k];
                end
            end else if (s2_mo[k] == nf && cand != {LA{1'b0}}) begin
                b_ent[k] = vic; b_al = b_al | vic; b_ev = vic;
                for (e = 0; e < LA; e = e + 1) if (vic[e]) b_ak[e] = b_ak[e] | s2_k[k];
            end else b_fal2 = 1'b1;
        end
    end
    // M-stage results used by the B-owned valid bits (an entry M frees without new elements)
    reg [LA-1:0] freeM;
    reg [15:0] s3_b; reg [31:0] s3_d [0:15]; reg [15:0] s3_fol [0:15]; reg [LA-1:0] s3_ent [0:15];
    reg [LA-1:0] s3_al, s3_ev; reg [9:0] s3_ak [0:LA-1];
    always @(posedge clk) begin : p_bst integer k, e;
        for (k = 0; k < 16; k = k + 1) begin
            ent_p[k] <= b_ent[k]; s3_ent[k] <= b_ent[k]; s3_d[k] <= s2_d[k]; s3_fol[k] <= s2_fol[k];
        end
        s3_b <= s2_b; s3_ev <= b_ev;
        for (e = 0; e < LA; e = e + 1) begin
            s3_ak[e] <= b_ak[e];
            if (b_al[e]) KEY[e] <= b_ak[e];
            if (b_al[e] || touchB[e]) AGE[e] <= {AW{1'b0}};
            else if (V[e] && AGE[e] != LTO[AW-1:0]) AGE[e] <= AGE[e] + 1'b1;
        end
        if (!rn) begin V <= {LA{1'b0}}; s3_al <= {LA{1'b0}}; end
        else begin V <= b_al | touchB | (V & ~freeM); s3_al <= b_al; end
    end
    // ------------------------------------------------------------------ M: merge + move
    reg [LA-1:0] el [0:15];             // entry of element k (its leader's)
    reg [15:0] hm [0:LA-1]; reg [15:0] hsrc [0:LA-1];   // slot written / from the odd element of the root
    reg [LA-1:0] hany, full, tmo, mvsel;
    reg mv;
    reg [QB:0] qn; reg [QB-1:0] qh, qt;
    reg [9:0] q_t [0:WQ-1]; reg [15:0] q_m [0:WQ-1]; reg [511:0] q_d [0:WQ-1];
    wire q_pop = (qn != 0) && slot_ok;
    wire q_room = (qn - q_pop) < WQ;
    always @* begin : p_m integer k, j, e, i;
        for (k = 0; k < 16; k = k + 1) begin
            el[k] = {LA{1'b0}};
            for (j = 0; j < 16; j = j + 1) if (s3_fol[k][j]) el[k] = el[k] | s3_ent[j];
        end
        for (e = 0; e < LA; e = e + 1) begin
            hm[e] = 16'd0; hsrc[e] = 16'd0;
            for (i = 0; i < 8; i = i + 1) begin
                if (el[2*i][e])   hm[e][2*i + s3_b[2*i]] = 1'b1;
                if (el[2*i+1][e]) begin hm[e][2*i + s3_b[2*i+1]] = 1'b1; hsrc[e][2*i + s3_b[2*i+1]] = 1'b1; end
            end
            hany[e] = hm[e] != 16'd0;
            full[e] = MASK[e] == 16'hffff;
            tmo[e] = V[e] && AGE[e] == LTO[AW-1:0] && MASK[e] != 16'd0;
        end
        // one move a cycle: eviction (old contents, when non-empty), else lowest full, else lowest timed-out
        mvsel = {LA{1'b0}}; mv = 1'b0;
        for (e = LA - 1; e >= 0; e = e - 1) if (tmo[e]) begin mvsel = {{(LA-1){1'b0}}, 1'b1} << e; mv = 1'b1; end
        for (e = LA - 1; e >= 0; e = e - 1) if (full[e]) begin mvsel = {{(LA-1){1'b0}}, 1'b1} << e; mv = 1'b1; end
        for (e = 0; e < LA; e = e + 1) if (s3_ev[e] && MASK[e] != 16'd0) begin mvsel = s3_ev; mv = 1'b1; end
        for (e = 0; e < LA; e = e + 1)
            freeM[e] = mv && q_room && mvsel[e] && !s3_al[e] && !hany[e] && !touchA[e] && !touchB[e];
    end
    reg [9:0] mk; reg [15:0] mm; reg [511:0] md;
    always @* begin : p_mx integer e;
        mk = 10'd0; mm = 16'd0; md = 512'd0;
        for (e = 0; e < LA; e = e + 1) if (mvsel[e]) begin mk = mk | KEYM[e]; mm = mm | MASK[e]; md = md | DATA[e]; end
    end
    wire ev_lost = (s3_ev != {LA{1'b0}}) && mv && (mvsel == s3_ev) && !q_room;
    always @(posedge clk) begin : p_mst integer e, s, i;
        for (e = 0; e < LA; e = e + 1) begin
            for (s = 0; s < 16; s = s + 1) if (hm[e][s])
                DATA[e][32*s +: 32] <= hsrc[e][s] ? s3_d[(s & ~1) + 1] : s3_d[s & ~1];
            if (s3_al[e]) KEYM[e] <= s3_ak[e];
        end
        if (mv && q_room) begin q_t[qt] <= mk; q_m[qt] <= mm; q_d[qt] <= md; end
        if (q_pop) begin w_row <= {q_t[qh], G[3:0]}; w_m <= q_m[qh]; w_d <= q_d[qh]; end
        if (!rn) begin
            for (e = 0; e < LA; e = e + 1) MASK[e] <= 16'd0;
            qn <= 0; qh <= 0; qt <= 0; w_v <= 1'b0; flt <= 4'd0;
        end else begin
            for (e = 0; e < LA; e = e + 1)
                MASK[e] <= (((mv && q_room && mvsel[e]) || s3_ev[e] || s3_al[e]) ? 16'd0 : MASK[e]) | hm[e];
            if (mv && q_room) qt <= (qt == WQ - 1) ? 0 : qt + 1'b1;
            if (q_pop) qh <= (qh == WQ - 1) ? 0 : qh + 1'b1;
            qn <= qn + (mv && q_room) - q_pop;
            w_v <= q_pop;
            if (ev_lost) flt[3] <= 1'b1;
            if (b_fal2) flt[2] <= 1'b1;
            if (d_frg) flt[1] <= 1'b1;
            if (d_fal) flt[0] <= 1'b1;
        end
    end
endmodule

// ================================================================================================ landing lane
// dsfd_vm_ll v3 (el1011-ds-vm/fe): one row lane of a landing producer.  The pin rows and the LARM arm reach the FIFO
// through AL relay stages each (equal latency: the arm / row order at the pins is kept).  Rows queue in a DEPTH-row FIFO
// (an ot_sram_1r1w_64x512 macro at DEPTH 64), each with the row address assigned at arrival (LARM base + OFF, every row
// adds STRIDE).  Drain by GRANT: every written row raises o_av (registered) towards the central drain arbiter; a grant g
// (relayed from the arbiter) reads the head; the macro output is captured with no logic (o_d) two cycles after g.  A row
// arriving at a full FIFO -> sticky ovf (fail closed); room_ok = free rows >= RTH (registered).
module dsfd_vm_ll #(
    parameter integer DEPTH = 64,       // rows (power of 2)
    parameter integer MACRO = 1,
    parameter integer STRIDE = 1,
    parameter integer OFF = 0,
    parameter integer AL = 2,           // input / arm relay stages
    parameter integer RTH = 8
) (
    input  wire         clk, rn,
    input  wire         in_v,
    input  wire [511:0] in_d,
    input  wire         arm_v,
    input  wire [13:0]  arm_base,
    output reg          o_av,
    input  wire         g,
    output reg          o_v,
    output reg  [13:0]  o_row,
    output reg  [511:0] o_d,
    output reg          room_ok,
    output reg          ovf
);
    localparam integer AB = $clog2(DEPTH);
    reg [AL-1:0] rv, ra_v; reg [511:0] rd_ [0:AL-1]; reg [13:0] rb [0:AL-1];
    always @(posedge clk) begin : p_rl integer i;
        rd_[0] <= in_d; rb[0] <= arm_base;
        for (i = 1; i < AL; i = i + 1) begin rd_[i] <= rd_[i-1]; rb[i] <= rb[i-1]; end
        if (!rn) begin rv <= {AL{1'b0}}; ra_v <= {AL{1'b0}}; end
        else begin rv <= {rv[AL-2:0], in_v}; ra_v <= {ra_v[AL-2:0], arm_v}; end
    end
    wire iv = rv[AL-1], av = ra_v[AL-1]; wire [511:0] id = rd_[AL-1]; wire [13:0] ib = rb[AL-1];
    reg [13:0] wp_row;
    reg [13:0] ra [0:DEPTH-1];
    reg [AB-1:0] wp, rp; reg [AB:0] n;
    reg rf; reg [13:0] rf_row;
    wire [511:0] rd;
    wire wr = iv && (n != DEPTH);
    generate if (MACRO && DEPTH == 64) begin : g_m
        (* keep = 1 *) ot_sram_1r1w_64x512_m1_r2c2 u_m (.clk(clk), .r_ce_in(g), .r_addr_in(rp), .rd_out(rd),
            .w_ce_in(wr), .w_addr_in(wp), .wd_in(id), .w_mask_in({512{1'b1}}), .rr_en(2'd0), .rr_addr(12'd0),
            .cr_en(2'd0), .cr_sel(18'd0));
    end else begin : g_f
        reg [511:0] mem [0:DEPTH-1]; reg [511:0] q;
        always @(posedge clk) begin if (wr) mem[wp] <= id; if (g) q <= mem[rp]; end
        assign rd = q;
    end endgenerate
    always @(posedge clk) begin
        o_d <= rd; o_row <= rf_row;
        if (wr) ra[wp] <= av ? ib + OFF : wp_row;
        if (g) rf_row <= ra[rp];
        if (!rn) begin wp <= 0; rp <= 0; n <= 0; rf <= 1'b0; o_v <= 1'b0; o_av <= 1'b0; ovf <= 1'b0; room_ok <= 1'b0; wp_row <= OFF; end
        else begin
            if (av) wp_row <= ib + OFF + (wr ? STRIDE : 0);
            else if (wr) wp_row <= wp_row + STRIDE;
            if (wr) wp <= wp + 1'b1;
            if (g) rp <= rp + 1'b1;
            if (iv && n == DEPTH) ovf <= 1'b1;
            n <= n + wr - g;
            rf <= g; o_v <= rf; o_av <= wr;
            room_ok <= (DEPTH - (n + wr - g)) >= RTH;
        end
    end
endmodule

// ================================================================================================ front end
module dsfd_vm_fe #(
    parameter integer NS = 4,           // bit-sliced memory columns (128 b each)
    parameter integer VF = 13,          // WFC kit link stations (dsfd_vm_wfc_ep VF / VR)
    parameter integer VR = 13,
    parameter integer NSLOT = 4,        // completion-counter slots
    parameter integer P2D = 40,         // BE P2 flit FIFO depth = the reader's credits
    parameter integer CQD = 4,          // P2RD command queue depth
    parameter integer LA = 12,          // capture lane row entries (gold: LA 8 overflowed, 12 / 16 pass)
    parameter integer LTO = 16,         // capture partial-row timeout
    parameter integer NSVC = 1,         // HBM scan services on the die (layer1 1, scan die 4)
    parameter integer LD = 64,          // landing FIFO depth (rows) of every landing lane
    parameter integer NLP = 2,          // shared landing drain ports
    parameter integer LMACRO = 1,
    parameter integer FRL = 2,          // relay stages order register -> slice pins (master MD += FRL)
    parameter integer KD = 1,           // relay stages order register -> completion counter (ARM ops delayed alike)
    parameter integer LAL = 2,          // landing input / LARM relay stages
    parameter integer LGL = 2,          // landing grant relay stages (arbiter -> lane)
    parameter integer LDL = 2           // landing data relay stages (lane -> drain mux)
) (
    input  wire [0:0]    ck,            // serial clock / reset
    input  wire [0:0]    rst,
    input  wire [0:0]    cks,           // stream clock / reset (dsfd_sp_ctrl side)
    input  wire [0:0]    rss,
    // WFC kit VM channels (dsfd_vm_wfc_ep RD2 die side; its response t_srq is produced in the BE)
    input  wire [0:0]    f_swv, input wire [526:0] f_swd, output wire [0:0] t_swg,
    input  wire [0:0]    f_srv, input wire [30:0]  f_srd, output wire [0:0] t_srg,
    output wire [52:0]   t_ks,
    // capture face (dsfd_sp_capture t_vm)
    input  wire [13375:0] f_cap,
    // dsfd_sp_ctrl VM port (request side, stream domain)
    input  wire [0:0]    vwe, input wire [13:0] vwa, input wire [511:0] vwd,
    input  wire [0:0]    vre, input wire [13:0] vra,
    // dsfd_sp_ctrl engine channel (stream domain)
    input  wire [0:0]    cv, input wire [83:0] cd, output wire [0:0] dv, output wire [7:0] dt,
    // landing producers (no back-pressure into the VM; the collective by t_cts room):
    //   f_svc[st]  1027 = HBM scan service st via its r2l end block: [0] v, [1024:1] two rows {a1, a0}, [1025] live, [1026] fault
    //   f_coll     2100 = dsfd_sp_collective t_vm: [0] v, [2:1] type, [9:6] word mask, [41] fault, [2099:52] 4 words
    //   f_sel / f_col 515 = selector / collector via their r2l end blocks: [0] v, [512:1] row, [513] live, [514] fault
    //   f_hc       1026 = HC N half results: {v1, row1, v0, row0}
    input  wire [NSVC*1027-1:0] f_svc,
    input  wire [2099:0] f_coll,
    output reg  [2:0]    t_cts,         // to the collective ts: {0, live, room for >= 8 words on every word lane}
    input  wire [514:0]  f_sel, input wire [514:0] f_col,
    input  wire [1025:0] f_hc,
    // rows-ready to dsfd_vm_mtp_ep (core side c_w*)
    output reg  [0:0]    c_wv, output reg [9:0] c_wd, input wire [0:0] c_wr,
    // inputs-present levels for the consumer engine adapters
    output reg  [NSLOT-1:0] t_rdy,
    // P2 credit return from the BE
    input  wire [0:0]    f_p2c,
    // memory request ports, slice-major (to the tile-0 N faces): slice s = [s*NP*W +: NP*W]
    output wire [NS*28-1:0]     m_v,
    output wire [NS*28-1:0]     m_we,
    output wire [NS*28*14-1:0]  m_row,
    output wire [NS*28*4-1:0]   m_mask,
    output wire [NS*28*128-1:0] m_d,
    output reg  [NS*4-1:0]      m_rf,   // tile-0 status input: bit 3 = FE fault (every slice)
    output reg  [15:0]          fe_flt  // FE sticky fault vector (composition net to the BE)
);
    localparam integer NP = 28, RA = 14, CP = 12;   // capture lanes on ports CP .. CP + 15
    wire clk = ck[0];
    wire rn0, rns;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn0));
    // regional reset relays (el1011-ds-vm/fe): every region (central logic, each capture lane, each landing lane) takes
    // its own kept 2-flop copy of the synchronised reset (same depth everywhere: one release cycle); datapath is reset-free
    (* keep = 1 *) reg [1:0] rr_c;
    always @(posedge clk) rr_c <= {rr_c[0], rn0};
    wire rn = rr_c[1];
    ot_dsrom_mtp_rstsync u_rss (.clk(cks[0]), .rst_n_async(rss[0]), .rst_n(rns));

    // ---------------------------------------------------------------- p0 / p1: WFC kit endpoint (request half)
    wire e_v, e_we, e1_v, e_err; wire [14:0] e_row, e1_row; wire [511:0] e_d;
    dsfd_vm_wfc_ep #(.FLIT(512), .NW(21), .USER_W(10), .VWA(15), .VF(VF), .VR(VR), .PIPE(2), .RD2(1)) u_wfc (
        .ck(ck), .rst(rst),
        .f_swv(f_swv), .f_swd(f_swd), .t_swg(t_swg), .f_srv(f_srv), .f_srd(f_srd), .t_srg(t_srg),
        .t_srq(), .t_err(e_err), .t_ks(t_ks),
        .m_v(e_v), .m_we(e_we), .m_row(e_row), .m_d(e_d), .m_ov(1'b0), .m_od(512'd0), .m_fault(1'b0),
        .m1_v(e1_v), .m1_row(e1_row), .m1_ov(1'b0), .m1_od(512'd0));

    // ---------------------------------------------------------------- capture face: pin register + 16 lanes
    reg [13375:0] cq_p;
    always @(posedge clk) cq_p <= f_cap;
    wire [15:0] cl_v; wire [16*14-1:0] cl_row; wire [16*16-1:0] cl_m; wire [16*512-1:0] cl_d; wire [63:0] cl_f;
    reg np16_ph;                        // MUT_NP16: the lane pair's shared port slot alternates
    always @(posedge clk) if (!rn) np16_ph <= 1'b0; else np16_ph <= ~np16_ph;
    genvar gl, gk;
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_cl
        wire [15:0] lv; wire [16*19-1:0] la; wire [16*32-1:0] ld;
        for (gk = 0; gk < 8; gk = gk + 1) begin : g_r
            localparam integer R = 8 * gl + gk;
            assign lv[2*gk]     = cq_p[104*R];
            assign la[19*(2*gk) +: 19] = cq_p[104*R + 1 +: 19];
            assign ld[32*(2*gk) +: 32] = cq_p[104*R + 20 +: 32];
            assign lv[2*gk + 1] = cq_p[104*R + 52];
            assign la[19*(2*gk+1) +: 19] = cq_p[104*R + 53 +: 19];
            assign ld[32*(2*gk+1) +: 32] = cq_p[104*R + 72 +: 32];
        end
`ifdef OT_SPVM_MUT_DROPW
        // MUTANT: lane 0 drops every 61st accepted element (posted write vanishes)
        reg [5:0] dc;
        always @(posedge clk) if (!rn) dc <= 6'd0; else if (gl == 0 && lv[0]) dc <= (dc == 6'd60) ? 6'd0 : dc + 6'd1;
        wire [15:0] lvx = (gl == 0 && dc == 6'd60) ? (lv & 16'hfffe) : lv;
`else
        wire [15:0] lvx = lv;
`endif
`ifdef OT_SPVM_MUT_NP16
        wire sok = np16_ph == gl[0];
`else
        wire sok = 1'b1;
`endif
        (* keep = 1 *) reg [1:0] rr_l;
        always @(posedge clk) rr_l <= {rr_l[0], rn0};
        dsfd_vm_cl #(.G(gl), .LA(LA), .LTO(LTO)) u_l (.clk(clk), .rn(rr_l[1]), .ev(lvx), .ea(la), .ed(ld), .slot_ok(sok),
            .w_v(cl_v[gl]), .w_row(cl_row[14*gl +: 14]), .w_m(cl_m[16*gl +: 16]), .w_d(cl_d[512*gl +: 512]),
            .flt(cl_f[4*gl +: 4]));
    end endgenerate
    wire cap_src_flt = cq_p[13312 + 3];

    // ---------------------------------------------------------------- ctrl VM port: stream pins -> 2 ratio CDC FIFOs
    reg s_we, s_re, s_tg; reg [13:0] s_wa, s_ra; reg [511:0] s_wd;
    always @(posedge cks[0]) begin
        if (!rns) begin s_we <= 1'b0; s_re <= 1'b0; end else begin s_we <= vwe[0]; s_re <= vre[0]; end
        s_wa <= vwa; s_ra <= vra; s_wd <= vwd;
    end
    // up to two ops a stream cycle (a write and a read: the write is ordered first).  Ops alternate between the two
    // FIFOs (s_tg = the FIFO of the next op); the serial side drains <= 2 a cycle, so the controller's VM op rate must
    // stay <= 1.5 a stream cycle on average (8-entry FIFOs); beyond -> sticky overflow fault (fail closed).
    wire [526:0] s_wo = {1'b1, s_wa, s_wd}, s_ro = {1'b0, s_ra, 512'd0};   // {we, row, data}
    wire s_f = s_we | s_re;                       // first op of the cycle
    wire s_s = s_we & s_re;                       // second op (the read)
    wire [526:0] s_fd = s_we ? s_wo : s_ro;
    wire [1:0] sw_v = {(s_f && s_tg) || (s_s && !s_tg), (s_f && !s_tg) || (s_s && s_tg)};
    wire [526:0] sw_d0 = (s_f && !s_tg) ? s_fd : s_ro;
    wire [526:0] sw_d1 = (s_f && s_tg) ? s_fd : s_ro;
    always @(posedge cks[0]) if (!rns) s_tg <= 1'b0; else if (s_f && !s_s) s_tg <= ~s_tg;
    wire [1:0] cw_rdy, cr_v, cw_live; wire [526:0] cr_d0, cr_d1; reg [1:0] cr_take; reg s_ovf;
    ot_ratio_cdc_fifo #(.W(527), .DEPTH(8)) u_cc0 (.wclk(cks[0]), .wrst_n(rns), .w_v(sw_v[0]), .w_rdy(cw_rdy[0]), .w_d(sw_d0),
        .rclk(clk), .rrst_n(rn), .r_v(cr_v[0]), .r_rdy(cr_take[0]), .r_d(cr_d0), .w_live(cw_live[0]), .r_live());
    ot_ratio_cdc_fifo #(.W(527), .DEPTH(8)) u_cc1 (.wclk(cks[0]), .wrst_n(rns), .w_v(sw_v[1]), .w_rdy(cw_rdy[1]), .w_d(sw_d1),
        .rclk(clk), .rrst_n(rn), .r_v(cr_v[1]), .r_rdy(cr_take[1]), .r_d(cr_d1), .w_live(cw_live[1]), .r_live());
    always @(posedge cks[0]) if (!rns) s_ovf <= 1'b0;
        else if ((sw_v[0] && !cw_rdy[0]) || (sw_v[1] && !cw_rdy[1])) s_ovf <= 1'b1;   // incl. ops before the crossing is up
    // serial side: pop in alternation order, <= 2 a cycle: first -> lane A (p3), second -> lane B (p4)
    reg c_nx;                           // FIFO holding the next op
    reg ca_v, cb_v; reg [526:0] ca_d, cb_d;
    always @* begin
        cr_take = 2'b00;
        if (cr_v[c_nx]) begin
            cr_take[c_nx] = 1'b1;
            if (cr_v[~c_nx]) cr_take[~c_nx] = 1'b1;
        end
    end
    always @(posedge clk) begin
        if (!rn) c_nx <= 1'b0; else if (cr_take == 2'b01 || cr_take == 2'b10) c_nx <= ~c_nx;
    end
    always @* begin
        ca_v = cr_v[c_nx]; ca_d = c_nx ? cr_d1 : cr_d0;
        cb_v = cr_v[c_nx] && cr_v[~c_nx]; cb_d = c_nx ? cr_d0 : cr_d1;
    end
    // crossing faults (stream side) to the serial domain: sticky, two flops
    reg [1:0] so_s;
    always @(posedge clk) begin so_s <= {so_s[0], s_ovf}; end

    reg a_p2c;
    always @(posedge clk) if (!rn) a_p2c <= 1'b0; else a_p2c <= f_p2c[0];

    // ---------------------------------------------------------------- engine adapter (stream c side, serial e side)
    wire ad_v, ad_r; wire [83:0] ad_d; wire ad_flt, ad_on;
    reg ed_v; reg [7:0] ed_t;
    ot_s81_engine_adapter #(.QD(8)) u_ad (
        .c_clk(cks[0]), .c_rst_n(rss[0]), .c_cmd_v(cv[0]), .c_cmd_d(cd), .c_done_v(dv[0]), .c_done_tag(dt),
        .fault(ad_flt), .online(ad_on),
        .e_clk(clk), .e_rst_n(rst[0]), .e_cmd_v(ad_v), .e_cmd_d(ad_d), .e_cmd_ready(ad_r), .e_inputs_present(1'b1),
        .e_done_v(ed_v), .e_done_tag(ed_t));
    wire [2:0] vop = ad_d[30:28];       // arg[23:21]
    wire [23:0] arg = ad_d[30:7];
    wire [7:0] ctag = {ad_d[83], ad_d[6:0]};
    reg imm_v; reg [7:0] imm_t;         // one immediate done waiting for the done output
    reg [$clog2(CQD+1)-1:0] cq_n;
    wire [2:0] xp_c = arg[20:18];        // X op: streamer index
    wire x_go = arg[17];
    reg [4:0] x_act;
    wire imm_op = vop == 3'd1 || vop == 3'd2 || vop == 3'd4 || vop == 3'd6 || (vop == 3'd7 && !x_go);
    assign ad_r = !(imm_op && imm_v) && !(vop == 3'd5 && cq_n == CQD) && !(vop == 3'd7 && x_go && xp_c < 3'd5 && x_act[xp_c]);
    wire acc = ad_v && ad_r;
    wire is_armb = acc && vop == 3'd1, is_armr = acc && vop == 3'd2, is_arm = acc && vop == 3'd3;
    wire is_pid = acc && vop == 3'd4, is_prd = acc && vop == 3'd5;
    wire [1:0] arm_s = arg[20:19];
    wire is_larm = acc && vop == 3'd6, is_xmap = acc && vop == 3'd7 && !x_go, is_xgo = acc && vop == 3'd7 && x_go;
    wire is_bad = acc && (vop == 3'd0 || (vop == 3'd7 && xp_c > 3'd4));
    reg [89:0] id_r;                    // {shared, expert 9, identity 74} in parts of 18
    always @(posedge clk) if (!rn) id_r <= 90'd0; else if (is_pid && arg[20:18] <= 3'd4) id_r[18*arg[20:18] +: 18] <= arg[17:0];
    // P2RD queue {identity 74, base 14, nw 7, expert 9, shared 1, tag 8} = 113
    localparam integer QW = 113, QB = (CQD > 1) ? $clog2(CQD) : 1;
    reg [QW-1:0] cq [0:CQD-1];
    reg [QB-1:0] cq_h, cq_t;
    wire [QW-1:0] cq_in = {id_r[73:0], arg[20:7], arg[6:0], id_r[82:74], id_r[83], ctag};
    reg r_act; reg [13:0] r_base; reg [6:0] r_w, r_nw; reg [73:0] r_id; reg [8:0] r_ex; reg r_sh; reg [7:0] r_tag;
    reg [$clog2(P2D+1):0] cr;
    wire r_iss = r_act && cr != 0;
    wire r_last = r_iss && r_w == r_nw;
    wire cq_pop = (!r_act || r_last) && cq_n != 0;
    wire cq_push = is_prd;
    always @(posedge clk) begin
        if (!rn) begin cq_h <= 0; cq_t <= 0; cq_n <= 0; r_act <= 1'b0; cr <= P2D; end
        else begin
            if (cq_push) begin cq[cq_t] <= cq_in; cq_t <= (cq_t == CQD - 1) ? 0 : cq_t + 1'b1; end
            if (cq_pop) cq_h <= (cq_h == CQD - 1) ? 0 : cq_h + 1'b1;
            cq_n <= cq_n + cq_push - cq_pop;
            if (cq_pop) begin
                r_act <= 1'b1; {r_id, r_base, r_nw, r_ex, r_sh, r_tag} <= cq[cq_h]; r_w <= 7'd0;
            end else if (r_last) r_act <= 1'b0;
            if (r_iss && !r_last) r_w <= r_w + 7'd1;
            cr <= cr - r_iss + a_p2c;
        end
    end

    // ---------------------------------------------------------------- X streamers (VM -> consumer die buses)
    // XMAP {xp, bus lane, nrows - 1}, XGO {xp, base}: streamer xp reads base .. base + nrows - 1, one row a cycle, on its
    // port (X0 p6, X1 p7, X2 p2, X3 p8, X4 p9); every read carries its bus lane id down the tile chain (unused write
    // data field) so the BE routes the row to that lane of the die read buses.  Done at the last read issued.
    reg [3:0] x_bus [0:4]; reg [12:0] x_n [0:4], x_c [0:4]; reg [13:0] x_b [0:4]; reg [7:0] x_tag [0:4];
    reg [4:0] x_dp;                       // done pending
    wire [4:0] x_iss = x_act;
    wire [4:0] x_last;
    genvar gx;
    generate for (gx = 0; gx < 5; gx = gx + 1) begin : g_xl
        assign x_last[gx] = x_act[gx] && x_c[gx] == x_n[gx];
    end endgenerate

    always @(posedge clk) begin : p_l507 integer xi;
        if (!rn) x_act <= 5'd0;
        else for (xi = 0; xi < 5; xi = xi + 1) begin
            if (is_xmap && xp_c == xi[2:0]) begin x_bus[xi] <= arg[16:13]; x_n[xi] <= arg[12:0]; end
            if (is_xgo && xp_c == xi[2:0]) begin x_act[xi] <= 1'b1; x_b[xi] <= arg[13:0]; x_c[xi] <= 13'd0; x_tag[xi] <= ctag; end
            else if (x_last[xi]) x_act[xi] <= 1'b0;
            else if (x_act[xi]) x_c[xi] <= x_c[xi] + 13'd1;
        end
    end
    wire [13:0] x_row0 = x_b[0] + {1'b0, x_c[0]}, x_row1 = x_b[1] + {1'b0, x_c[1]}, x_row2 = x_b[2] + {1'b0, x_c[2]},
                x_row3 = x_b[3] + {1'b0, x_c[3]}, x_row4 = x_b[4] + {1'b0, x_c[4]};

    // ---------------------------------------------------------------- landing lanes + shared drain ports
    localparam integer NLL = 2 * NSVC + 8;           // svc 2 / stack, coll 4, sel 1, col 1, hc 2
    reg [NSVC*1027-1:0] q_svc; reg [2099:0] q_coll; reg [514:0] q_sel, q_col; reg [1025:0] q_hc;
    always @(posedge clk) begin q_svc <= f_svc; q_coll <= f_coll; q_sel <= f_sel; q_col <= f_col; q_hc <= f_hc; end
    wire [NLL-1:0] ll_iv, ll_av, ll_ov, ll_arm, ll_ok, ll_ov_v; wire [NLL*512-1:0] ll_id, ll_od; wire [NLL*14-1:0] ll_or;
    reg  [NLL-1:0] ll_tk;
    wire [3:0] larm_g = arg[20:17];
    genvar gs2, gw;
    generate
        for (gs2 = 0; gs2 < NSVC; gs2 = gs2 + 1) begin : g_lsv
            assign ll_iv[2*gs2] = q_svc[1027*gs2]; assign ll_id[512*(2*gs2) +: 512] = q_svc[1027*gs2 + 1 +: 512];
            assign ll_iv[2*gs2+1] = q_svc[1027*gs2]; assign ll_id[512*(2*gs2+1) +: 512] = q_svc[1027*gs2 + 513 +: 512];
            assign ll_arm[2*gs2] = is_larm && larm_g == gs2; assign ll_arm[2*gs2+1] = is_larm && larm_g == gs2;
        end
        for (gw = 0; gw < 4; gw = gw + 1) begin : g_lco
            localparam integer L = 2 * NSVC + gw;
            assign ll_iv[L] = q_coll[0] && q_coll[2:1] != 2'd3 && q_coll[6 + gw];
            assign ll_id[512*L +: 512] = q_coll[52 + 512*gw +: 512];
            assign ll_arm[L] = is_larm && larm_g == 4'd4;
        end
    endgenerate
    assign ll_iv[2*NSVC+4] = q_sel[0]; assign ll_id[512*(2*NSVC+4) +: 512] = q_sel[512:1]; assign ll_arm[2*NSVC+4] = is_larm && larm_g == 4'd5;
    assign ll_iv[2*NSVC+5] = q_col[0]; assign ll_id[512*(2*NSVC+5) +: 512] = q_col[512:1]; assign ll_arm[2*NSVC+5] = is_larm && larm_g == 4'd6;
    assign ll_iv[2*NSVC+6] = q_hc[512]; assign ll_id[512*(2*NSVC+6) +: 512] = q_hc[511:0];  assign ll_arm[2*NSVC+6] = is_larm && larm_g == 4'd7;
    assign ll_iv[2*NSVC+7] = q_hc[1025]; assign ll_id[512*(2*NSVC+7) +: 512] = q_hc[1024:513]; assign ll_arm[2*NSVC+7] = is_larm && larm_g == 4'd7;
    // landing drain by grant (el1011-ds-vm/fe): lanes report written rows (o_av, relayed one stage) to the central
    // arbiter, which keeps a per-lane count, grants <= NLP heads a cycle (rotating priority; the collective's
    // flow-controlled word lanes take what is left) and sends the grants back over LGL relay stages; each granted lane
    // reads its head (macro output captured with no logic) and returns it over LDL relay stages; the drain mux selects
    // on the grant delayed by the same LGL + 2 + LDL cycles.
    localparam integer LSD = LGL + 2 + LDL;
    reg [NLL-1:0] av_r; reg [NLL-1:0] g_r [0:LGL-1];
    reg [NLL*512-1:0] dd_r [0:LDL-1]; reg [NLL*14-1:0] dr_r [0:LDL-1];
    genvar gll;
    generate for (gll = 0; gll < NLL; gll = gll + 1) begin : g_ll
        localparam integer ST = (gll < 2 * NSVC) ? 2 : (gll < 2 * NSVC + 4) ? 4 : (gll < 2 * NSVC + 6) ? 1 : 2;
        localparam integer OF = (gll < 2 * NSVC) ? gll % 2 : (gll < 2 * NSVC + 4) ? gll - 2 * NSVC : (gll < 2 * NSVC + 6) ? 0 : gll - (2 * NSVC + 6);
`ifdef OT_SPVM_MUT_LSMALL
        localparam integer DP = LD / 4;            // MUTANT: undersized landing FIFOs (must overflow at the burst bench)
`else
        localparam integer DP = LD;
`endif
        (* keep = 1 *) reg [1:0] rr_ll;
        always @(posedge clk) rr_ll <= {rr_ll[0], rn0};
        // room flag padded by the relay latency added in v3 (8 -> 16 rows)
        dsfd_vm_ll #(.DEPTH(DP), .MACRO(LMACRO), .STRIDE(ST), .OFF(OF), .AL(LAL), .RTH(16)) u_ll (.clk(clk), .rn(rr_ll[1]),
            .in_v(ll_iv[gll]), .in_d(ll_id[512*gll +: 512]), .arm_v(ll_arm[gll]), .arm_base(arg[13:0]),
            .o_av(ll_av[gll]), .g(g_r[LGL-1][gll]), .o_v(ll_ov_v[gll]), .o_row(ll_or[14*gll +: 14]), .o_d(ll_od[512*gll +: 512]),
            .room_ok(ll_ok[gll]), .ovf(ll_ov[gll]));
    end endgenerate
    reg [6:0] lc [0:NLL-1];             // rows written and not yet granted, per lane
    reg [$clog2(NLL)-1:0] ll_ptr; reg [NLP-1:0] lp_v; reg [NLP*14-1:0] lp_row; reg [NLP*512-1:0] lp_d;
    reg [NLP-1:0] lsel_v; reg [$clog2(NLL)-1:0] lsel [0:NLP-1];
    always @* begin : p_l562 integer li, lj, lk;
        ll_tk = {NLL{1'b0}}; lsel_v = {NLP{1'b0}};
        for (lk = 0; lk < NLP; lk = lk + 1) lsel[lk] = {$clog2(NLL){1'b0}};
        lk = 0;
        // lanes with no back-pressure first (rotating), the collective's flow-controlled word lanes take what is left
        for (li = 0; li < NLL; li = li + 1) begin
            lj = (ll_ptr + li) % NLL;
            if (lc[lj] != 7'd0 && lk < NLP && !(lj >= 2 * NSVC && lj < 2 * NSVC + 4)) begin
                ll_tk[lj] = 1'b1; lsel_v[lk] = 1'b1; lsel[lk] = lj; lk = lk + 1;
            end
        end
        for (li = 0; li < 4; li = li + 1) begin
            lj = 2 * NSVC + li;
            if (lc[lj] != 7'd0 && lk < NLP) begin ll_tk[lj] = 1'b1; lsel_v[lk] = 1'b1; lsel[lk] = lj; lk = lk + 1; end
        end
    end
    reg [NLL-1:0] sd_oh [0:NLP-1][0:LSD-1]; reg [NLP-1:0] sd_v [0:LSD-1];
    always @(posedge clk) begin : p_l578 integer lk, li, i; reg [511:0] dsel; reg [13:0] rsel;
        if (!rn) begin
            lp_v <= {NLP{1'b0}}; ll_ptr <= 0; av_r <= {NLL{1'b0}};
            for (li = 0; li < NLL; li = li + 1) lc[li] <= 7'd0;
            for (i = 0; i < LGL; i = i + 1) g_r[i] <= {NLL{1'b0}};
            for (i = 0; i < LSD; i = i + 1) sd_v[i] <= {NLP{1'b0}};
        end else begin
            ll_ptr <= (ll_ptr == NLL - 1) ? 0 : ll_ptr + 1'b1;
            av_r <= ll_av;
            for (li = 0; li < NLL; li = li + 1) lc[li] <= lc[li] + {6'd0, av_r[li]} - {6'd0, ll_tk[li]};
            g_r[0] <= ll_tk;
            for (i = 1; i < LGL; i = i + 1) g_r[i] <= g_r[i-1];
            sd_v[0] <= lsel_v;
            for (i = 1; i < LSD; i = i + 1) sd_v[i] <= sd_v[i-1];
            lp_v <= sd_v[LSD-1];
        end
        for (lk = 0; lk < NLP; lk = lk + 1) begin
            sd_oh[lk][0] <= lsel_v[lk] ? ({{(NLL-1){1'b0}}, 1'b1} << lsel[lk]) : {NLL{1'b0}};
            for (i = 1; i < LSD; i = i + 1) sd_oh[lk][i] <= sd_oh[lk][i-1];
            dsel = 512'd0; rsel = 14'd0;
            for (li = 0; li < NLL; li = li + 1) if (sd_oh[lk][LSD-1][li]) begin
                dsel = dsel | dd_r[LDL-1][512*li +: 512]; rsel = rsel | dr_r[LDL-1][14*li +: 14];
            end
            lp_row[14*lk +: 14] <= rsel; lp_d[512*lk +: 512] <= dsel;
        end
        dd_r[0] <= ll_od; dr_r[0] <= ll_or;
        for (i = 1; i < LDL; i = i + 1) begin dd_r[i] <= dd_r[i-1]; dr_r[i] <= dr_r[i-1]; end
    end
    // collective flow control: room for >= 16 rows (8 + the v3 relay latency) on every word lane, relayed one stage
    reg cts_ok;
    always @(posedge clk) if (!rn) cts_ok <= 1'b0; else cts_ok <= &ll_ok[2*NSVC +: 4];
    always @(posedge clk) if (!rn) t_cts <= 3'd0; else t_cts <= {1'b0, 1'b1, cts_ok};
    reg ll_ovr;
    always @(posedge clk) if (!rn) ll_ovr <= 1'b0; else ll_ovr <= |ll_ov;
    reg l_src_flt;
    always @(posedge clk) begin : p_l596 integer li;
        if (!rn) l_src_flt <= 1'b0;
        else begin
            for (li = 0; li < NSVC; li = li + 1) if (q_svc[1027*li + 1026]) l_src_flt <= 1'b1;
            if (q_coll[41] || q_sel[514] || q_col[514]) l_src_flt <= 1'b1;
        end
    end

    // ---------------------------------------------------------------- stage B: the order register (all ports)
    reg [NP-1:0] b_v, b_we; reg [NP*RA-1:0] b_row; reg [NP*16-1:0] b_m; reg [NP*512-1:0] b_d;

    always @(posedge clk) begin
        if (!rn) b_v <= {NP{1'b0}};
        else begin
            b_v[0] <= e_v && !e_row[14]; b_v[1] <= e1_v && !e1_row[14]; b_v[2] <= x_iss[2];
            b_v[3] <= ca_v; b_v[4] <= cb_v; b_v[5] <= r_iss; b_v[6] <= x_iss[0]; b_v[7] <= x_iss[1];
            b_v[8] <= x_iss[3]; b_v[9] <= x_iss[4]; b_v[11:10] <= lp_v;
            b_v[NP-1:CP] <= cl_v;
        end
        b_we[CP-1:0] <= {2'b11, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, cb_d[526], ca_d[526], 1'b0, 1'b0, e_we};
        b_we[NP-1:CP] <= 16'hffff;
        b_row[CP*RA-1:0] <= {lp_row, x_row4, x_row3, x_row1, x_row0, r_base + {7'd0, r_w}, cb_d[525:512], ca_d[525:512],
                             x_row2, e1_row[13:0], e_row[13:0]};
        b_row[NP*RA-1:CP*RA] <= cl_row;
        b_m[CP*16-1:0] <= {CP{16'hffff}};
        b_m[NP*16-1:CP*16] <= cl_m;
        b_d[CP*512-1:0] <= {lp_d, {508'd0, x_bus[4]}, {508'd0, x_bus[3]}, {508'd0, x_bus[1]}, {508'd0, x_bus[0]},
                            {420'd0, r_id, r_ex, r_sh, r_last, r_w}, cb_d[511:0], ca_d[511:0], {508'd0, x_bus[2]}, 512'd0, e_d};
        b_d[NP*512-1:CP*512] <= cl_d;
    end

    // ---------------------------------------------------------------- stage C: per-slice copies at the tile pins
`ifdef OT_SPVM_MUT_STALE
    // MUTANT: ctrl lane A (p3) ops reach the memory one cycle after their order-register position
    reg s_v6, s_we6; reg [RA-1:0] s_row6; reg [15:0] s_m6; reg [511:0] s_d6;
    always @(posedge clk) begin
        if (!rn) s_v6 <= 1'b0; else s_v6 <= b_v[3];
        s_we6 <= b_we[3]; s_row6 <= b_row[3*RA +: RA]; s_m6 <= b_m[3*16 +: 16]; s_d6 <= b_d[3*512 +: 512];
    end
    wire [NP-1:0] c_vv = {b_v[NP-1:4], s_v6, b_v[2:0]};
    wire [NP-1:0] c_we = {b_we[NP-1:4], s_we6, b_we[2:0]};
    wire [NP*RA-1:0] c_row = {b_row[NP*RA-1:4*RA], s_row6, b_row[3*RA-1:0]};
    wire [NP*16-1:0] c_m = {b_m[NP*16-1:4*16], s_m6, b_m[3*16-1:0]};
    wire [NP*512-1:0] c_dd = {b_d[NP*512-1:4*512], s_d6, b_d[3*512-1:0]};
`else
    wire [NP-1:0] c_vv = b_v, c_we = b_we;
    wire [NP*RA-1:0] c_row = b_row;
    wire [NP*16-1:0] c_m = b_m;
    wire [NP*512-1:0] c_dd = b_d;
`endif
    // stage C + FRL relay stages per slice (el1011-ds-vm/fe): each slice owns its copy of the port valid / we / row and
    // its own 128-b data / 4-b mask chunk of every port; FRL + 1 registers from the order register to the slice pins
    // (lane 0 -> slice 3 is ~1,405 um: <= ~350 um a hop); the valid chain is reset, the rest is reset-free
    integer s;
    genvar gsl, gp;
    generate for (gsl = 0; gsl < NS; gsl = gsl + 1) begin : g_sl
        wire [NP*4-1:0] cm_s; wire [NP*128-1:0] cd_s;
        for (gp = 0; gp < NP; gp = gp + 1) begin : g_p
            assign cm_s[4*gp +: 4] = c_m[gp*16 + 4*gsl +: 4];
            assign cd_s[128*gp +: 128] = c_dd[gp*512 + 128*gsl +: 128];
        end
        reg [NP-1:0] rv_ [0:FRL]; reg [NP-1:0] rwe [0:FRL]; reg [NP*RA-1:0] rrow [0:FRL];
        reg [NP*4-1:0] rm [0:FRL]; reg [NP*128-1:0] rd_ [0:FRL];
        always @(posedge clk) begin : p_rl integer i;
            if (!rn) for (i = 0; i <= FRL; i = i + 1) rv_[i] <= {NP{1'b0}};
            else begin rv_[0] <= c_vv; for (i = 1; i <= FRL; i = i + 1) rv_[i] <= rv_[i-1]; end
            rwe[0] <= c_we; rrow[0] <= c_row; rm[0] <= cm_s; rd_[0] <= cd_s;
            for (i = 1; i <= FRL; i = i + 1) begin rwe[i] <= rwe[i-1]; rrow[i] <= rrow[i-1]; rm[i] <= rm[i-1]; rd_[i] <= rd_[i-1]; end
        end
        assign m_v[gsl*NP +: NP] = rv_[FRL]; assign m_we[gsl*NP +: NP] = rwe[FRL]; assign m_row[gsl*NP*RA +: NP*RA] = rrow[FRL];
        assign m_mask[gsl*NP*4 +: NP*4] = rm[FRL]; assign m_d[gsl*NP*128 +: NP*128] = rd_[FRL];
    end endgenerate

    // ---------------------------------------------------------------- row-completion counter + early-read check
    // stage K (one cycle after B, the same order): per port and slot {in range, write elements | read}
    reg [NSLOT-1:0] sl_arm, sl_dp, sl_rp, sl_ntf;
    reg [13:0] sl_base [0:NSLOT-1]; reg [14:0] sl_n [0:NSLOT-1]; reg [18:0] sl_need [0:NSLOT-1], sl_cnt [0:NSLOT-1];
    reg [9:0] sl_user [0:NSLOT-1]; reg [7:0] sl_tag [0:NSLOT-1];
    reg [13:0] st_base [0:NSLOT-1]; reg [14:0] st_n [0:NSLOT-1]; reg [NSLOT-1:0] st_ntf;   // ARMB / ARMR staging
    reg [NSLOT*NP-1:0] k_w, k_r;        // registered in-range flags
    reg [NP*5-1:0] k_pc;                // registered popcount of each port's mask
    reg [NP-1:0] k_v, k_we;
    reg [NSLOT-1:0] k_ok;
    // KD relay stages (el1011-ds-vm/fe): the counter sees the order register (28 ports from the full 1,520-um width)
    // AND the ARM ops KD cycles later -- a uniform shift, so the old-range / new-range contract is unchanged
    reg [NP-1:0] kq_v [0:KD-1], kq_we [0:KD-1]; reg [NP*RA-1:0] kq_row [0:KD-1]; reg [NP*16-1:0] kq_m [0:KD-1];
    reg [KD-1:0] kq_armb, kq_armr, kq_arm; reg [23:0] kq_arg [0:KD-1]; reg [7:0] kq_tag [0:KD-1]; reg [9:0] kq_user [0:KD-1];
    always @(posedge clk) begin : p_kq integer i;
        if (!rn) begin
            for (i = 0; i < KD; i = i + 1) kq_v[i] <= {NP{1'b0}};
            kq_armb <= {KD{1'b0}}; kq_armr <= {KD{1'b0}}; kq_arm <= {KD{1'b0}};
        end else begin
            kq_v[0] <= b_v; for (i = 1; i < KD; i = i + 1) kq_v[i] <= kq_v[i-1];
            kq_armb <= {kq_armb, is_armb}; kq_armr <= {kq_armr, is_armr}; kq_arm <= {kq_arm, is_arm};
        end
        kq_we[0] <= b_we; kq_row[0] <= b_row; kq_m[0] <= b_m; kq_arg[0] <= arg; kq_tag[0] <= ctag; kq_user[0] <= ad_d[82:73];
        for (i = 1; i < KD; i = i + 1) begin
            kq_we[i] <= kq_we[i-1]; kq_row[i] <= kq_row[i-1]; kq_m[i] <= kq_m[i-1];
            kq_arg[i] <= kq_arg[i-1]; kq_tag[i] <= kq_tag[i-1]; kq_user[i] <= kq_user[i-1];
        end
    end
    wire [NP-1:0] kb_v = kq_v[KD-1], kb_we = kq_we[KD-1]; wire [NP*RA-1:0] kb_row = kq_row[KD-1]; wire [NP*16-1:0] kb_m = kq_m[KD-1];
    wire k_armb = kq_armb[KD-1], k_armr = kq_armr[KD-1], k_arm = kq_arm[KD-1];
    wire [23:0] k_arg = kq_arg[KD-1]; wire [7:0] k_tag = kq_tag[KD-1]; wire [9:0] k_user = kq_user[KD-1];
    wire [1:0] k_s = k_arg[20:19];
    integer kk, b;
    reg [4:0] pc;
    reg [15:0] wm;
    always @(posedge clk) begin : p_l672 integer kk, q, b;
        for (q = 0; q < NP; q = q + 1) begin
            wm = kb_m[q*16 +: 16];
            pc = 5'd0; for (b = 0; b < 16; b = b + 1) pc = pc + {4'd0, wm[b]};
            k_pc[5*q +: 5] <= pc;
            for (kk = 0; kk < NSLOT; kk = kk + 1) begin
                k_w[kk*NP + q] <= kb_v[q] && kb_we[q] && kb_row[q*RA +: RA] >= sl_base[kk] &&
                                  {1'b0, kb_row[q*RA +: RA]} < {1'b0, sl_base[kk]} + sl_n[kk];
                k_r[kk*NP + q] <= kb_v[q] && !kb_we[q] && kb_row[q*RA +: RA] >= sl_base[kk] &&
                                  {1'b0, kb_row[q*RA +: RA]} < {1'b0, sl_base[kk]} + sl_n[kk];
            end
        end
        if (!rn) k_v <= {NP{1'b0}}; else k_v <= kb_v;
        // the flags of a slot being ARMed this edge were compared with its OLD range: not counted, not checked
        // (contract: no op into a range in the cycle its ARMN lands)
        k_ok <= ~(k_arm ? ({{(NSLOT-1){1'b0}}, 1'b1} << k_s) : {NSLOT{1'b0}});
    end
    reg [9:0] inc [0:NSLOT-1];
    reg [NSLOT-1:0] hit_r, cmpl;
    always @* begin : p_l691 integer kk, q;
        for (kk = 0; kk < NSLOT; kk = kk + 1) begin
            inc[kk] = 10'd0; hit_r[kk] = 1'b0;
            for (q = 0; q < NP; q = q + 1) begin
                if (k_w[kk*NP + q] && k_ok[kk]) inc[kk] = inc[kk] + {5'd0, k_pc[5*q +: 5]};
                if (k_r[kk*NP + q] && k_ok[kk]) hit_r[kk] = 1'b1;
            end
`ifdef OT_SPVM_MUT_EARLY
            cmpl[kk] = sl_arm[kk] && sl_cnt[kk] + inc[kk] + 19'd1 >= sl_need[kk];   // MUTANT: one element early
`else
            cmpl[kk] = sl_arm[kk] && sl_cnt[kk] + inc[kk] >= sl_need[kk];
`endif
        end
    end
    // P2 done pending: tags of finished P2RD commands, in order (<= CQD + 1 outstanding)
    reg [7:0] pd_q [0:CQD]; reg [$clog2(CQD+2)-1:0] pd_h, pd_t, pd_n;
    reg early, ovf_cr, rearm, ovf_pd;
    reg [NSLOT-1:0] dsel, rsel;
    always @* begin : p_l709 integer kk;
        dsel = {NSLOT{1'b0}}; rsel = {NSLOT{1'b0}};
        for (kk = NSLOT - 1; kk >= 0; kk = kk - 1) begin
            if (sl_dp[kk]) dsel = {{(NSLOT-1){1'b0}}, 1'b1} << kk;
            if (sl_rp[kk]) rsel = {{(NSLOT-1){1'b0}}, 1'b1} << kk;
        end
    end
    wire d_slot = |sl_dp;                      // slot dones first, then P2 dones, then the immediate done
    wire d_p2 = !d_slot && pd_n != 0;
    wire d_x = !d_slot && !d_p2 && x_dp != 5'd0;
    reg [2:0] xsel; integer xq;
    always @* begin xsel = 3'd0; for (xq = 4; xq >= 0; xq = xq - 1) if (x_dp[xq]) xsel = xq[2:0]; end
    wire d_imm = !d_slot && !d_p2 && !d_x && imm_v;
    wire c_w_go = !c_wv[0] || c_wr[0];
    reg [7:0] dsel_tag; reg [9:0] rsel_user;
    always @* begin : p_l724 integer kk;
        dsel_tag = 8'd0; rsel_user = 10'd0;
        for (kk = 0; kk < NSLOT; kk = kk + 1) begin
            if (dsel[kk]) dsel_tag = dsel_tag | sl_tag[kk];
            if (rsel[kk]) rsel_user = rsel_user | sl_user[kk];
        end
    end
    always @(posedge clk) begin : p_l731 integer kk;
        if (!rn) begin
            sl_arm <= 0; sl_dp <= 0; sl_rp <= 0; sl_ntf <= 0; ed_v <= 1'b0; c_wv <= 1'b0; t_rdy <= 0; imm_v <= 1'b0; x_dp <= 5'd0;
            pd_h <= 0; pd_t <= 0; pd_n <= 0;
            early <= 1'b0; ovf_cr <= 1'b0; rearm <= 1'b0; ovf_pd <= 1'b0;
            for (kk = 0; kk < NSLOT; kk = kk + 1) begin sl_base[kk] <= 14'd0; sl_n[kk] <= 15'd0; end
        end else begin
            for (kk = 0; kk < NSLOT; kk = kk + 1) begin
                if (sl_arm[kk]) sl_cnt[kk] <= sl_cnt[kk] + {9'd0, inc[kk]};
                if (hit_r[kk] && sl_arm[kk] && !cmpl[kk]) early <= 1'b1;
                if (cmpl[kk]) begin sl_arm[kk] <= 1'b0; t_rdy[kk] <= 1'b1; end
            end
            if (k_armb) begin st_base[k_s] <= k_arg[13:0]; st_ntf[k_s] <= k_arg[18]; end
            if (k_armr) st_n[k_s] <= k_arg[14:0];
            if (k_arm) begin
                if (sl_arm[k_s] || sl_dp[k_s] || sl_rp[k_s]) rearm <= 1'b1;
                sl_arm[k_s] <= 1'b1; t_rdy[k_s] <= 1'b0; sl_ntf[k_s] <= st_ntf[k_s]; sl_user[k_s] <= k_user;
                sl_base[k_s] <= st_base[k_s]; sl_n[k_s] <= st_n[k_s];
                sl_need[k_s] <= k_arg[18:0]; sl_cnt[k_s] <= 19'd0; sl_tag[k_s] <= k_tag;
            end
            // engine done output (one a cycle)
            ed_v <= d_slot || d_p2 || d_x || d_imm;
            ed_t <= d_slot ? dsel_tag : d_p2 ? pd_q[pd_h] : d_x ? x_tag[xsel] : imm_t;
            x_dp <= (x_dp & ~(d_x ? (5'd1 << xsel) : 5'd0)) | x_last;
            sl_dp <= (sl_dp & ~(d_slot ? dsel : {NSLOT{1'b0}})) | cmpl;
            if (d_imm) imm_v <= 1'b0;
            if (acc && imm_op) begin imm_v <= 1'b1; imm_t <= ctag; end
            // P2 done queue
            if (r_last) begin pd_q[pd_t] <= r_tag; pd_t <= (pd_t == CQD) ? 0 : pd_t + 1'b1; end
            if (d_p2) pd_h <= (pd_h == CQD) ? 0 : pd_h + 1'b1;
            pd_n <= pd_n + r_last - d_p2;
            if (r_last && pd_n == CQD + 1) ovf_pd <= 1'b1;
            // rows-ready output (held until the ep takes it)
            if (c_w_go) begin
                c_wv <= |sl_rp; c_wd <= rsel_user;
                sl_rp <= (sl_rp & ~rsel) | (cmpl & sl_ntf);
            end else sl_rp <= sl_rp | (cmpl & sl_ntf);
            if (cr > P2D) ovf_cr <= 1'b1;
        end
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (rn) for (kk = 0; kk < NSLOT; kk = kk + 1)
        if (hit_r[kk] && sl_arm[kk] && !cmpl[kk])
            $error("SPVM EARLY_READ: read into slot %0d range [%0d, +%0d) at %0d of %0d elements (ports %b)", kk, sl_base[kk],
                   sl_n[kk], sl_cnt[kk], sl_need[kk], k_r[kk*NP +: NP]);
`endif

    // ---------------------------------------------------------------- FE status
    reg rbad; reg [3:0] clf;
    always @(posedge clk) if (!rn) rbad <= 1'b0; else if ((e_v && e_row[14]) || (e1_v && e1_row[14])) rbad <= 1'b1;
    always @* begin : p_l781 integer l; clf = 4'd0; for (l = 0; l < 16; l = l + 1) clf = clf | cl_f[4*l +: 4]; end
    always @(posedge clk) begin
        if (!rn) fe_flt <= 16'd0;
        else fe_flt <= fe_flt | {so_s[1], ll_ovr, ad_flt, cap_src_flt, clf, is_bad, ovf_pd, rearm, l_src_flt, ovf_cr, 1'b0,
                                 e_err | rbad, early};
    end
    always @(posedge clk) for (s = 0; s < NS; s = s + 1) m_rf[s*4 +: 4] <= {|fe_flt, 3'b000};
endmodule

// ================================================================================================ back end
module dsfd_vm_be #(
    parameter integer NS = 4,
    parameter integer P2D = 40,         // P2 flit FIFO depth (the FE reader's credits)
    parameter integer MD = 9            // tile-3 f_* (request exit) -> o_* (read data) skew (NSTG 2, QD 4)
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,
    input  wire [0:0]          cks,      // stream clock / reset (ctrl read return)
    input  wire [0:0]          rss,
    // tile-3 S faces, slice-major (NPR = 10 return lanes)
    input  wire [NS*10-1:0]    o_v,
    input  wire [NS*10*128-1:0] o_d,
    input  wire [NS*4-1:0]     o_f,
    input  wire [NS*3-1:0]     o_o,
    input  wire [0:0]          f_v5,     // slice 0 tile-3 f_v[5]
    input  wire [0:0]          f_we5,    // slice 0 tile-3 f_we[5]
    input  wire [91:0]         f_m5,     // slice 0 tile-3 f_d[5*128 +: 92]: P2 metadata
    input  wire [4:0]          f_vx,     // slice 0 tile-3 f_v / f_we / f_d[p*128 +: 4] of the X ports {p9, p8, p2, p7, p6}
    input  wire [4:0]          f_wex,
    input  wire [19:0]         f_mx,
    input  wire [15:0]         fe_flt,   // FE status (composition net)
    // WFC kit response (dsfd_vm_wfc_ep RD2 t_srq) and sticky status
    output reg  [1025:0]       t_srq,
    output reg  [0:0]          t_err,
    // dsfd_sp_ctrl VM read return (stream domain)
    output reg  [0:0]          vrv,
    output reg  [511:0]        vrq,
    // VM -> consumer die read-bus lanes (X streamers), each {v, row}: 0 / 1 su_s, 2 / 3 su_n, 4 / 5 hc, 6 gather,
    // 7 .. 10 pq, 11 .. 14 q svc 0 .. 3, 15 eng
    output reg  [16*513-1:0]   t_bl,
    // P2 lane 0 to dsfd_vm_p2_ep (core side c_l0*) + credit to the FE
    output wire [0:0]          c_l0v,
    output wire [603:0]        c_l0d,
    input  wire [0:0]          c_l0r,
    output reg  [0:0]          t_p2c,
    // status
    output reg  [0:0]          flt,
    output reg  [31:0]         fvec,
    output reg  [2:0]          max_occ
);
    localparam integer NP = 10;
    wire clk = ck[0];
    wire rn, rns;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));
    ot_dsrom_mtp_rstsync u_rss (.clk(cks[0]), .rst_n_async(rss[0]), .rst_n(rns));
    // pin flops
    reg [NS*10-1:0] q_v; reg [NS*10*128-1:0] q_d; reg [NS*4-1:0] q_f; reg [NS*3-1:0] q_o;
    reg q_fv; reg [91:0] q_fm; reg [15:0] q_fe; reg [4:0] q_xv; reg [19:0] q_xm;
    always @(posedge clk) begin
        if (!rn) begin q_v <= 0; q_f <= 0; q_fv <= 1'b0; q_fe <= 16'd0; q_xv <= 5'd0; end
        else begin q_v <= o_v; q_f <= o_f; q_fv <= f_v5[0] && !f_we5[0]; q_fe <= fe_flt; q_xv <= f_vx & ~f_wex; end
        q_d <= o_d; q_o <= o_o; q_fm <= f_m5; q_xm <= f_mx;
    end
    function automatic [511:0] row_of(input [NS*10*128-1:0] d, input integer p);
        integer ss; begin
            row_of = 512'd0;
            for (ss = 0; ss < NS; ss = ss + 1) row_of[128*ss +: 128] = d[(ss*NP + p)*128 +: 128];
        end
    endfunction
    wire [NP-1:0] v0 = q_v[NP-1:0];
    // ---------------------------------------------------------------- responses (one output register)
    always @(posedge clk) begin
        if (!rn) t_srq <= 0;
        else t_srq <= {v0[1], row_of(q_d, 1), v0[0], row_of(q_d, 0)};
    end
    // X returns -> bus lanes: the lane id rode down with the read (metadata delay line, MD cycles like P2)
    reg [MD-1:0] xd_v [0:4]; reg [3:0] xd_m [0:4][0:MD-1];
    integer xi2, xj2;
    always @(posedge clk) for (xi2 = 0; xi2 < 5; xi2 = xi2 + 1) begin
        if (!rn) xd_v[xi2] <= {MD{1'b0}}; else xd_v[xi2] <= {xd_v[xi2][MD-2:0], q_xv[xi2]};
        xd_m[xi2][0] <= q_xm[4*xi2 +: 4];
        for (xj2 = 1; xj2 < MD; xj2 = xj2 + 1) xd_m[xi2][xj2] <= xd_m[xi2][xj2-1];
    end
    // X port index -> tile port: {p9, p8, p2, p7, p6}
    function automatic integer xport(input integer x);
        begin xport = (x == 0) ? 6 : (x == 1) ? 7 : (x == 2) ? 2 : (x == 3) ? 8 : 9; end
    endfunction
    reg x_mis, x_col; reg [15:0] bl_v; integer bl;
    always @(posedge clk) begin : p_l869 integer xi2;
        if (!rn) begin x_mis <= 1'b0; x_col <= 1'b0; for (bl = 0; bl < 16; bl = bl + 1) t_bl[513*bl] <= 1'b0; end
        else begin
            bl_v = 16'd0;
            for (bl = 0; bl < 16; bl = bl + 1) t_bl[513*bl] <= 1'b0;
            for (xi2 = 0; xi2 < 5; xi2 = xi2 + 1) begin
                if (xd_v[xi2][MD-1] != v0[xport(xi2)]) x_mis <= 1'b1;
                if (xd_v[xi2][MD-1]) begin
                    if (bl_v[xd_m[xi2][MD-1]]) x_col <= 1'b1;
                    bl_v[xd_m[xi2][MD-1]] = 1'b1;
                    t_bl[513*xd_m[xi2][MD-1]] <= 1'b1;
                    t_bl[513*xd_m[xi2][MD-1] + 1 +: 512] <= row_of(q_d, xport(xi2));
                end
            end
        end
    end
    // ---------------------------------------------------------------- ctrl read return: p3 then p4 -> 2 CDC FIFOs
    reg w_nx; wire [1:0] rw_rdy, rr_v; wire [511:0] rr_d0, rr_d1; reg rr_nx; reg r_ovf;
    wire [1:0] pv = {v0[4], v0[3]};
    // the op order of a cycle: p3 (if valid) first, then p4; pushes alternate FIFOs starting at w_nx
    wire       pa = pv[0] | pv[1];                    // first return of the cycle
    wire       pb = pv[0] & pv[1];                    // second
    wire [511:0] da = pv[0] ? row_of(q_d, 3) : row_of(q_d, 4);
    wire [511:0] db = row_of(q_d, 4);
    wire [1:0] wv = {(pa && w_nx) || (pb && !w_nx), (pa && !w_nx) || (pb && w_nx)};
    wire [511:0] wd0 = (pa && !w_nx) ? da : db;
    wire [511:0] wd1 = (pa && w_nx) ? da : db;
    always @(posedge clk) begin
        if (!rn) begin w_nx <= 1'b0; r_ovf <= 1'b0; end
        else begin
            if (pa && !pb) w_nx <= ~w_nx;
            if ((wv[0] && !rw_rdy[0]) || (wv[1] && !rw_rdy[1])) r_ovf <= 1'b1;
        end
    end
    wire [1:0] rtk = {rr_v[1] && rr_nx, rr_v[0] && !rr_nx};
    ot_ratio_cdc_fifo #(.W(512), .DEPTH(8)) u_rc0 (.wclk(clk), .wrst_n(rn), .w_v(wv[0]), .w_rdy(rw_rdy[0]), .w_d(wd0),
        .rclk(cks[0]), .rrst_n(rns), .r_v(rr_v[0]), .r_rdy(rtk[0]), .r_d(rr_d0), .w_live(), .r_live());
    ot_ratio_cdc_fifo #(.W(512), .DEPTH(8)) u_rc1 (.wclk(clk), .wrst_n(rn), .w_v(wv[1]), .w_rdy(rw_rdy[1]), .w_d(wd1),
        .rclk(cks[0]), .rrst_n(rns), .r_v(rr_v[1]), .r_rdy(rtk[1]), .r_d(rr_d1), .w_live(), .r_live());
    always @(posedge cks[0]) begin
        if (!rns) begin rr_nx <= 1'b0; vrv <= 1'b0; end
        else begin
            vrv <= |rtk;
            if (|rtk) rr_nx <= ~rr_nx;
        end
        vrq <= rr_nx ? rr_d1 : rr_d0;
    end
    // ---------------------------------------------------------------- P2: metadata delay line + flit FIFO
    reg [MD-1:0] md_v; reg [91:0] md_m [0:MD-1];

    always @(posedge clk) begin : p_l919 integer i;
        if (!rn) md_v <= 0; else md_v <= {md_v[MD-2:0], q_fv};
        md_m[0] <= q_fm;
        for (i = 1; i < MD; i = i + 1) md_m[i] <= md_m[i-1];
    end
    wire mv = md_v[MD-1]; wire [91:0] mm = md_m[MD-1];
    wire [603:0] flit = {mm, row_of(q_d, 5)};
    localparam integer PB = $clog2(P2D);
    reg [603:0] pf [0:P2D-1];
    reg [PB-1:0] ph, pt; reg [PB:0] pn;
    reg ov; reg [603:0] od;
    wire take = ov && c_l0r[0];
    wire ld = (!ov || take) && (pn != 0 || mv);
    wire byp = pn == 0;
    wire push = mv && !(ld && byp);
    wire popq = ld && !byp;
    assign c_l0v = ov; assign c_l0d = od;
    reg p_ovf, p_mis;
    always @(posedge clk) begin
        if (!rn) begin ph <= 0; pt <= 0; pn <= 0; ov <= 1'b0; t_p2c <= 1'b0; p_ovf <= 1'b0; p_mis <= 1'b0; end
        else begin
            if (push) begin pf[pt] <= flit; pt <= (pt == P2D - 1) ? 0 : pt + 1'b1; end
            if (popq) ph <= (ph == P2D - 1) ? 0 : ph + 1'b1;
            pn <= pn + push - popq;
            if (ld) begin ov <= 1'b1; od <= byp ? flit : pf[ph]; end
            else if (take) ov <= 1'b0;
            t_p2c <= take;
            if (push && pn == P2D) p_ovf <= 1'b1;
            if (mv != v0[5]) p_mis <= 1'b1;
        end
    end
    // ---------------------------------------------------------------- status
    reg s_mis; reg [31:0] fv; integer ss;
    always @(posedge clk) begin
        if (!rn) begin s_mis <= 1'b0; flt <= 1'b0; fvec <= 32'd0; t_err <= 1'b0; max_occ <= 3'd0; end
        else begin
            for (ss = 1; ss < NS; ss = ss + 1) if (q_v[ss*NP +: NP] != q_v[NP-1:0] || q_f[ss*4 +: 4] != q_f[3:0]) s_mis <= 1'b1;
            // [3:0] memory {fault, und, mis, ovf | write-only read}; [19:4] FE vector; [20] P2 FIFO overflow;
            // [21] P2 metadata misalignment; [22] slice mismatch; [23] ctrl return overflow
            fv = {6'd0, x_col, x_mis, r_ovf, s_mis, p_mis, p_ovf, q_fe, q_f[3:0]};
            fvec <= fvec | fv;
            flt <= flt | (|fv);
            t_err <= t_err | (|fv);
            max_occ <= (q_o[2:0] > max_occ) ? q_o[2:0] : max_occ;
        end
    end
endmodule

// ================================================================================================ composition
// dsfd_sp_vm_m: the exact composition netlist (bench + composition record): FE, NS x 4 dsfd_vm_bgq (NSTG 2, NP 24,
// NPR 8), BE.  The die places the FE, the 16 tiles and the BE by abutment (physical/s81_ph_views/vm_master/).
module dsfd_sp_vm_m #(
    parameter integer NS = 4, parameter integer NSTG = 2, parameter integer QD = 4, parameter integer MACRO = 1,
    parameter integer VF = 13, parameter integer VR = 13, parameter integer NSLOT = 4, parameter integer P2D = 40,
    parameter integer CQD = 4, parameter integer LA = 12, parameter integer LTO = 16,
    parameter integer NSVC = 1, parameter integer LD = 64, parameter integer NLP = 2, parameter integer LMACRO = 1
) (
    input  wire [0:0]    ck, input wire [0:0] rst, input wire [0:0] cks, input wire [0:0] rss,
    input  wire [0:0]    f_swv, input wire [526:0] f_swd, output wire [0:0] t_swg,
    input  wire [0:0]    f_srv, input wire [30:0]  f_srd, output wire [0:0] t_srg,
    output wire [52:0]   t_ks,
    output wire [1025:0] t_srq, output wire [0:0] t_err,
    input  wire [13375:0] f_cap,
    input  wire [0:0]    vwe, input wire [13:0] vwa, input wire [511:0] vwd,
    input  wire [0:0]    vre, input wire [13:0] vra, output wire [0:0] vrv, output wire [511:0] vrq,
    input  wire [0:0]    cv, input wire [83:0] cd, output wire [0:0] dv, output wire [7:0] dt,
    input  wire [NSVC*1027-1:0] f_svc, input wire [2099:0] f_coll, output wire [2:0] t_cts,
    input  wire [514:0]  f_sel, input wire [514:0] f_col, input wire [1025:0] f_hc,
    output wire [16*513-1:0] t_bl,
    output wire [0:0]    c_wv, output wire [9:0] c_wd, input wire [0:0] c_wr,
    output wire [NSLOT-1:0] t_rdy,
    output wire [0:0]    c_l0v, output wire [603:0] c_l0d, input wire [0:0] c_l0r,
    output wire [0:0]    flt, output wire [31:0] fvec, output wire [2:0] max_occ
);
    localparam integer NP = 28, NPR = 10, NT = 4, RA = 14, OW = 3;
    // el1011-ds-vm/bgq28: the hard tile's enqueue pipeline (EP, = dsfd_vm_bgq28) adds ED = EP + 1 cycles to every op
`ifdef OT_VM28_EP1
    localparam integer EP = 1;
`else
    localparam integer EP = 2;
`endif
    localparam integer ED = (EP == 0) ? 0 : EP + 1;
    localparam integer FRL = 2;         // el1011-ds-vm/fe: FE order register -> slice pin relay stages
    localparam integer MD = 4 * NSTG + QD + 9 - 4 * (NSTG + 1) + ED + FRL;
    wire [NS*NP-1:0] mv, mwe; wire [NS*NP*RA-1:0] mrow; wire [NS*NP*4-1:0] mm; wire [NS*NP*128-1:0] md;
    wire [NS*4-1:0] mrf; wire [15:0] fe_flt;
    wire p2c;
    dsfd_vm_fe #(.NS(NS), .VF(VF), .VR(VR), .NSLOT(NSLOT), .P2D(P2D), .CQD(CQD), .LA(LA), .LTO(LTO), .NSVC(NSVC), .LD(LD),
                 .NLP(NLP), .LMACRO(LMACRO), .FRL(FRL)) u_fe (
        .ck(ck), .rst(rst), .cks(cks), .rss(rss), .f_swv(f_swv), .f_swd(f_swd), .t_swg(t_swg), .f_srv(f_srv), .f_srd(f_srd),
        .t_srg(t_srg), .t_ks(t_ks), .f_cap(f_cap), .vwe(vwe), .vwa(vwa), .vwd(vwd), .vre(vre), .vra(vra),
        .cv(cv), .cd(cd), .dv(dv), .dt(dt), .f_svc(f_svc), .f_coll(f_coll), .t_cts(t_cts), .f_sel(f_sel), .f_col(f_col), .f_hc(f_hc),
        .c_wv(c_wv), .c_wd(c_wd), .c_wr(c_wr), .t_rdy(t_rdy), .f_p2c(p2c),
        .m_v(mv), .m_we(mwe), .m_row(mrow), .m_mask(mm), .m_d(md), .m_rf(mrf), .fe_flt(fe_flt));
    wire [NS*NPR-1:0] ov; wire [NS*NPR*128-1:0] od; wire [NS*4-1:0] of; wire [NS*3-1:0] oo;
    wire [NP-1:0] f0v, f0we; wire [NP*128-1:0] f0d;
    genvar h, t;
    generate for (h = 0; h < NS; h = h + 1) begin : g_h
        wire [NP-1:0] cv_ [0:NT], cwe [0:NT];
        wire [NPR-1:0] cov [0:NT];
        wire [NP*RA-1:0] crow [0:NT]; wire [NP*4-1:0] cm [0:NT]; wire [NP*128-1:0] cd_ [0:NT];
        wire [NPR*128-1:0] cod [0:NT];
        wire [3:0] cof [0:NT]; wire [OW-1:0] coo [0:NT];
        assign cv_[0] = mv[h*NP +: NP]; assign cwe[0] = mwe[h*NP +: NP]; assign crow[0] = mrow[h*NP*RA +: NP*RA];
        assign cm[0] = mm[h*NP*4 +: NP*4]; assign cd_[0] = md[h*NP*128 +: NP*128];
        // chain head: no upstream tile (no read data, occupancy 0); the FE status enters on the fault lane
        assign cov[0] = {NPR{1'b0}}; assign cod[0] = {NPR*128{1'b0}}; assign cof[0] = mrf[h*4 +: 4];
        assign coo[0] = {OW{1'b0}};
        for (t = 0; t < NT; t = t + 1) begin : g_t
            wire [1:0] gid = t;
            // = dsfd_vm_bgq28 (the hard tile) at the default parameters
            dsfd_vm_bgq #(.NP(NP), .NPR(NPR), .NB(32), .NBL(8), .QD(QD), .RQ(8), .MACRO(MACRO), .DW(128), .NSTG(NSTG), .EP(EP)) u_bg (
                .ck(ck), .rs(rst), .grp(gid),
                .i_v(cv_[t]), .i_we(cwe[t]), .i_row(crow[t]), .i_mask(cm[t]), .i_d(cd_[t]),
                .f_v(cv_[t+1]), .f_we(cwe[t+1]), .f_row(crow[t+1]), .f_mask(cm[t+1]), .f_d(cd_[t+1]),
                .r_v(cov[t]), .r_d(cod[t]), .r_f(cof[t]), .r_o(coo[t]),
                .o_v(cov[t+1]), .o_d(cod[t+1]), .o_f(cof[t+1]), .o_o(coo[t+1]));
        end
        assign ov[h*NPR +: NPR] = cov[NT]; assign od[h*NPR*128 +: NPR*128] = cod[NT]; assign of[h*4 +: 4] = cof[NT];
        assign oo[h*3 +: 3] = coo[NT];
        if (h == 0) begin : g_f
            assign f0v = cv_[NT]; assign f0we = cwe[NT]; assign f0d = cd_[NT];
        end
    end endgenerate
    dsfd_vm_be #(.NS(NS), .P2D(P2D), .MD(MD)) u_be (
        .ck(ck), .rst(rst), .cks(cks), .rss(rss), .o_v(ov), .o_d(od), .o_f(of), .o_o(oo),
        .f_v5(f0v[5]), .f_we5(f0we[5]), .f_m5(f0d[5*128 +: 92]), .fe_flt(fe_flt),
        .f_vx({f0v[9], f0v[8], f0v[2], f0v[7], f0v[6]}), .f_wex({f0we[9], f0we[8], f0we[2], f0we[7], f0we[6]}),
        .f_mx({f0d[9*128 +: 4], f0d[8*128 +: 4], f0d[2*128 +: 4], f0d[7*128 +: 4], f0d[6*128 +: 4]}),
        .t_srq(t_srq), .t_err(t_err), .vrv(vrv), .vrq(vrq), .t_bl(t_bl),
        .c_l0v(c_l0v), .c_l0d(c_l0d), .c_l0r(c_l0r), .t_p2c(p2c), .flt(flt), .fvec(fvec), .max_occ(max_occ));
endmodule
