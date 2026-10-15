`ifdef OT_VMFE_FLD_PARALLEL_ARB
`include "dsfd_vm_fld_pick2.svh"
`endif
`ifdef OT_SPVM_RESET_ACK
`include "dsfd_vm_reset_ack.svh"
`include "dsfd_vm_fe_h_if.svh"
`endif
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
//   OT_SPVM_MUT_RLAT     the BE P2 output honours c_l0r one cycle early (ready latency 3, not 4): beats the consumer never granted
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
    parameter integer LA = 12,          // row entries
    parameter integer LTO = 16,         // partial-row timeout (cycles since last element)
    parameter integer WQ = 2,           // write queue depth
    parameter integer RT = 1            // 1 (the hard view): match / touch terms formed from registers (see "RT" below); 0: the v3
                                        // expressions.  BIT-EXACT and cycle-exact to each other (bench tb_dsfd_vm_cl_rt)
) (
    input  wire          clk, rn,       // rn: this lane's relayed reset (control only)
    input  wire [3:0]    gid,           // lane index (static strap, registered by dsfd_vm_clt): one hard view serves all 16 lanes
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
`ifdef OT_SPVM_SLOC
            // VM FE (a) capture-slice locality: lane gid in quadrant gid[3:2] owns words 4 gid[3:2] .. + 3 of rows
            // {key, gid[1:0], i[2:1]}: address bits {row[3:0], word[3:1]} = {gid[1:0], i[2:1], gid[3:2], i[0]}
            else if (ea[19*k + 1 +: 7] != {gid[1:0], k[3:2], gid[3:2], k[1]}) d_fal = 1'b1;
`else
            else if (ea[19*k + 1 +: 7] != {gid, k[3:1]}) d_fal = 1'b1;
`endif
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
    // RT (el1013-s81-vmfe/B6, S3: the M5 route of dsfd_vm_clt missed setup by 113 ps on KEY -> compare -> touchA -> cand ->
    // vic -> allocate -> AGE / KEY / s3_ev, 24-26 levels).  The tag compare of the batch in A and both touch vectors are
    // formed ONE CYCLE AHEAD from the pin-registered keys and re-based on the only state that can change in between:
    //   KEY[e] at t = b_al[e] at t-1 ? the key of the leader that allocated e (s2_k[j], b_ent[j][e]) : KEY[e] at t-1
    //   p_eqS[k][e] = KEY[e] == key k     p_eqB[k][j] = s2_k[j] == key k     (C1 cycle, registered)
    //   a_hS[k][e]  = s1_ld[k] & V[e] & (alP[e] ? |(p_eqB[k] & ent_p[.][e]) : p_eqS[k][e])            (= the v3 compare)
    //   touchA[e]   = V[e] & (alP[e] ? |(p_xB & ent_p[.][e]) : p_tS[e])       p_tS / p_xB = OR over the accepted elements
    //                 (every accepted element carries its leader's key, so the OR over elements = the OR over leaders)
    //   touchB[e]   = p_tAS[e] | |(p_yB & ent_p[.][e])       p_tAS = OR of the state hits of leaders with no B hit, p_yB =
    //                 OR of a_hB, both registered in A
    // An allocated entry has exactly one leader in ent_p (free entries are not valid and a victim is untouched by B).
    // No latency, no behaviour change: cand -> vic now starts 6-7 levels after registers.
    reg [LA-1:0] alP, p_tS, p_tAS; reg [15:0] p_xB, p_yB;
    reg [LA-1:0] p_eqS [0:15]; reg [15:0] p_eqB [0:15];
    reg [LA-1:0] ent_p [0:15];          // entry of each leader of the previous B batch
    reg [15:0] entc [0:LA-1];           // ent_p by entry
    reg [LA-1:0] b_al;
    always @* begin : p_ec integer e, j;
        for (e = 0; e < LA; e = e + 1) for (j = 0; j < 16; j = j + 1) entc[e][j] = ent_p[j][e];
    end
    always @(posedge clk) begin : p_pre integer k, e, j; reg [LA-1:0] t; reg [15:0] x; reg [9:0] kk;
        t = {LA{1'b0}}; x = 16'd0;
        for (k = 0; k < 16; k = k + 1) begin
            kk = ea[19*k + 8 +: 10];
            for (e = 0; e < LA; e = e + 1) begin
                p_eqS[k][e] <= KEY[e] == kk;
                if (rn && d_ok[k] && KEY[e] == kk) t[e] = 1'b1;
            end
            for (j = 0; j < 16; j = j + 1) begin
                p_eqB[k][j] <= s2_k[j] == kk;
                if (rn && d_ok[k] && s2_k[j] == kk) x[j] = 1'b1;
            end
        end
        p_tS <= t; p_xB <= x; alP <= b_al;
    end
`ifndef SYNTHESIS
    integer cov_fw = 0, cov_ev = 0;      // bench cover: forwarded touch of a just-allocated entry; evictions
`endif
    always @* begin : p_a integer k, e, j; reg [OB-1:0] c;
        touchA = {LA{1'b0}}; c = {OB{1'b0}};
        for (k = 0; k < 16; k = k + 1) begin
            for (e = 0; e < LA; e = e + 1)
                if (RT != 0) a_hS[k][e] = s1_ld[k] && V[e] && (alP[e] ? |(p_eqB[k] & entc[e]) : p_eqS[k][e]);
                else a_hS[k][e] = s1_ld[k] && V[e] && KEY[e] == s1_k[k];
            for (j = 0; j < 16; j = j + 1) a_hB[k][j] = s1_ld[k] && s2_ld[j] && s2_k[j] == s1_k[k];
            a_ms[k] = s1_ld[k] && a_hS[k] == {LA{1'b0}} && a_hB[k] == 16'd0;
            a_mo[k] = c; c = c + {{(OB-1){1'b0}}, a_ms[k]};
            touchA = touchA | a_hS[k];
        end
        if (RT != 0) for (e = 0; e < LA; e = e + 1)
`ifdef OT_SPVM_MUT_CLRT
            touchA[e] = V[e] && p_tS[e];     // MUTANT: the touch of a just-allocated entry is not forwarded
`else
            touchA[e] = V[e] && (alP[e] ? |(p_xB & entc[e]) : p_tS[e]);
`endif
    end
    always @(posedge clk) begin : p_pb integer k; reg [LA-1:0] t; reg [15:0] y;
        t = {LA{1'b0}}; y = 16'd0;
        for (k = 0; k < 16; k = k + 1) begin
            if (a_hB[k] == 16'd0) t = t | a_hS[k];
            y = y | a_hB[k];
        end
        if (!rn) begin p_tAS <= {LA{1'b0}}; p_yB <= 16'd0; end else begin p_tAS <= t; p_yB <= y; end
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
    reg [LA-1:0] b_ent [0:15];          // entry of each leader of this batch (0: dropped)
    reg [LA-1:0] touchB, b_ev, vic, cand, fr;
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
        if (RT != 0) for (e = 0; e < LA; e = e + 1) touchB[e] = p_tAS[e] || |(p_yB & entc[e]);
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
`ifndef SYNTHESIS
        if (rn && b_ev != {LA{1'b0}}) cov_ev = cov_ev + 1;
        for (e = 0; e < LA; e = e + 1) if (rn && V[e] && alP[e] && |(p_xB & entc[e])) cov_fw = cov_fw + 1;
`endif
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
        if (q_pop) begin w_row <= {q_t[qh], gid}; w_m <= q_m[qh]; w_d <= q_d[qh]; end
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

// ================================================================================================ capture lane tile
// dsfd_vm_clt (el1011-ds-vm/fe): the hardened capture-lane tile (own clock tree, registered seams): pin flops on the
// 832-b f_cap slice (8 roots x {row1 {data32, addr19}, v1, row0 {data32, addr19}, v0}), registered reset and port slot,
// dsfd_vm_cl (outputs registered).  Pin plan physical/s81_ph_views/ports/contract_vm28/dsfd_vm_clt.
module dsfd_vm_clt #(
    parameter integer LA = 12,
    parameter integer LTO = 16
) (
    input  wire [0:0]   ck,
    input  wire [0:0]   rn,
    input  wire [0:0]   sok,
    input  wire [3:0]   gid,            // v3: lane index as a static strap pin (was parameter G: a hard view has no parameters)
    input  wire [831:0] f_c,
    output wire [0:0]   w_v,
    output wire [13:0]  w_row,
    output wire [15:0]  w_m,
    output wire [511:0] w_d,
    output wire [3:0]   flt
`ifdef OT_SPVM_RESET_ACK
    , input wire reset_epoch_n, output wire rst_ack
`endif
);
    wire clk = ck[0];
    reg [831:0] cp; reg rn_r, sok_r; reg [3:0] gid_r;
    always @(posedge clk) begin cp <= f_c; rn_r <= rn[0]; sok_r <= sok[0]; gid_r <= gid; end
    wire [15:0] lv; wire [16*19-1:0] la; wire [16*32-1:0] ld;
    genvar gk;
    generate for (gk = 0; gk < 8; gk = gk + 1) begin : g_r
        assign lv[2*gk]     = cp[104*gk];
        assign la[19*(2*gk) +: 19] = cp[104*gk + 1 +: 19];
        assign ld[32*(2*gk) +: 32] = cp[104*gk + 20 +: 32];
        assign lv[2*gk + 1] = cp[104*gk + 52];
        assign la[19*(2*gk+1) +: 19] = cp[104*gk + 53 +: 19];
        assign ld[32*(2*gk+1) +: 32] = cp[104*gk + 72 +: 32];
    end endgenerate
`ifdef OT_SPVM_MUT_DROPW
    // MUTANT: lane 0 drops every 61st accepted element (posted write vanishes)
    reg [5:0] dc;
    always @(posedge clk) if (!rn_r) dc <= 6'd0; else if (gid_r == 4'd0 && lv[0]) dc <= (dc == 6'd60) ? 6'd0 : dc + 6'd1;
    wire [15:0] lvx = (gid_r == 4'd0 && dc == 6'd60) ? (lv & 16'hfffe) : lv;
`else
    wire [15:0] lvx = lv;
`endif
    dsfd_vm_cl #(.LA(LA), .LTO(LTO)) u_c (.clk(clk), .rn(rn_r), .gid(gid_r), .ev(lvx), .ea(la), .ed(ld), .slot_ok(sok_r),
        .w_v(w_v[0]), .w_row(w_row), .w_m(w_m), .w_d(w_d), .flt(flt));
`ifdef OT_SPVM_RESET_ACK
    dsfd_vm_reset_ack u_reset_ack (.clk(clk), .request_n(reset_epoch_n), .local_release(rn_r), .consumer_live(1'b1), .ack(rst_ack));
`endif
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
    parameter integer WCOMMIT = 0,
    parameter integer BANK_XOR = 0,
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
    parameter integer FRL = 2,          // relay stages order register -> slice pins (BE MD unchanged)
    parameter integer KD = 1,           // relay stages order register -> completion counter (ARM ops delayed alike)
    parameter integer LAL = 2,          // landing input / LARM relay stages
    parameter integer LGL = 2,          // landing grant relay stages (arbiter -> lane)
    parameter integer LDL = 2,          // landing data relay stages (lane -> drain mux)
    parameter integer DVR = 0,          // 1: engine done dv / dt leave a pin register (stream domain, +1 stream cycle on every done)
    parameter integer LVX = 0,          // extra relay stages lane -> drain on the written-row flag o_av and on room_ok (ok)
    parameter integer XRT = 0,          // 1: engine adapter with one reset synchroniser a domain + registered reset tree (no cross-domain reset arc)
    parameter integer CCA = 0           // 1: the ctrl VM crossing is a REAL two-clock CDC (Gray pointers through 2-flop synchronisers,
                                        // ot_async_fifo DEPTH 16) instead of the related-clock ot_ratio_cdc_fifo: +2 serial cycles an op
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
    output wire         vready,
    input wire [15:0] vwm, input wire [7:0] vwt, output wire [15:0] m_wtag,
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
    output wire [NS*4-1:0]      m_rf,   // tile-0 status input: bit 3 = FE fault (every slice; registered in dsfd_vm_fsr)
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
    // the 16 capture lanes are hardened tiles dsfd_vm_clt (own pin flops, registered reset / slot, registered outputs),
    // each under its 832-b f_cap slice; only the 64 status bits are registered here
    reg [63:0] cq_p;
    always @(posedge clk) cq_p <= f_cap[13312 +: 64];
    wire [15:0] cl_v; wire [16*14-1:0] cl_row; wire [16*16-1:0] cl_m; wire [16*512-1:0] cl_d; wire [63:0] cl_f;
    reg np16_ph;                        // MUT_NP16: the lane pair's shared port slot alternates
    always @(posedge clk) if (!rn) np16_ph <= 1'b0; else np16_ph <= ~np16_ph;
    genvar gl;
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_cl
`ifdef OT_SPVM_MUT_NP16
        wire sok = np16_ph == gl[0];
`else
        wire sok = 1'b1;
`endif
        (* keep = 1 *) reg rr_l;
        always @(posedge clk) rr_l <= rn0;
        // hard child: NO parameter overrides (the hard view is LA 12 / LTO 16); the lane index is the gid strap
        if (LA != 12 || LTO != 16) begin : g_cfg
            dsfd_vm_clt_hard_cfg_mismatch u_err ();   // elaboration error: the hardened dsfd_vm_clt is LA 12 / LTO 16
        end
        dsfd_vm_clt u_l (.ck(ck), .rn(rr_l), .sok(sok), .gid(gl[3:0]), .f_c(f_cap[832*gl +: 832]),
            .w_v(cl_v[gl]), .w_row(cl_row[14*gl +: 14]), .w_m(cl_m[16*gl +: 16]), .w_d(cl_d[512*gl +: 512]),
            .flt(cl_f[4*gl +: 4]));
    end endgenerate
    wire cap_src_flt = cq_p[3];

    // ---------------------------------------------------------------- ctrl VM port: stream pins -> 2 ratio CDC FIFOs
    reg [15:0] s_wm; reg [7:0] s_wt;
    reg s_we, s_re, s_tg; reg [13:0] s_wa, s_ra; reg [511:0] s_wd;
    always @(posedge cks[0]) begin
        if (!rns) begin s_we <= 1'b0; s_re <= 1'b0; end else begin s_we <= vwe[0]; s_re <= vre[0]; end
        s_wm <= WCOMMIT ? vwm : 16'hffff; s_wt <= WCOMMIT ? vwt : 8'd0;
        s_wa <= vwa; s_ra <= vra; s_wd <= vwd;
    end
    // up to two ops a stream cycle (a write and a read: the write is ordered first).  Ops alternate between the two
    // FIFOs (s_tg = the FIFO of the next op); the serial side drains <= 2 a cycle, so the controller's VM op rate must
    // stay <= 1.5 a stream cycle on average (8-entry FIFOs); beyond -> sticky overflow fault (fail closed).
    wire [550:0] s_wo = {s_wt,s_wm,1'b1, s_wa, s_wd}, s_ro = {24'd0,1'b0, s_ra, 512'd0};   // {we, row, data}
    wire s_f = s_we | s_re;                       // first op of the cycle
    wire s_s = s_we & s_re;                       // second op (the read)
    wire [550:0] s_fd = s_we ? s_wo : s_ro;
    wire [1:0] sw_v = {(s_f && s_tg) || (s_s && !s_tg), (s_f && !s_tg) || (s_s && s_tg)};
    wire [550:0] sw_d0 = (s_f && !s_tg) ? s_fd : s_ro;
    wire [550:0] sw_d1 = (s_f && s_tg) ? s_fd : s_ro;
    always @(posedge cks[0]) if (!rns) s_tg <= 1'b0; else if (s_f && !s_s) s_tg <= ~s_tg;
    wire [1:0] cw_rdy, cr_v, cw_live; wire [550:0] cr_d0, cr_d1; reg [1:0] cr_take; reg s_ovf;
    generate if (CCA != 0) begin : g_cca
        // el1013-s81-vmfe/B8 (coordinator decision 10-13 (b)): with ot_ratio_cdc_fifo every storage bit crossed EVERY read
        // cycle (mem[i] (cks tree) -> sh[i] (ck tree), 2 x 8 x 527 flop -> flop arcs) and had to meet the 277.8-ps window AND
        // the coincident-edge hold between two independently built clock trees: -140.7 ps setup, 2,039 stalled hold arcs.
        // Here the storage is written and held in the stream domain only (its write register s_wd / s_wa is same-domain),
        // the pointers cross Gray-coded through 2-flop synchronisers, and an entry is read (mem -> read mux -> the serial
        // order register) only after the synchronised pointer has published it, >= 2 serial cycles after it was written:
        // the only cross-clock arcs are pointer / online -> first synchroniser flop and stable storage -> order register
        // (max-delay, datapath only).  Reset: one synchroniser a domain on the pin-level AND of both asynchronous resets
        // (an assertion of either flushes both sides), then one registered stage; no cross-domain reset arc.
        wire x_arn = rst[0] & rss[0];
        wire xw0, xr0; wire [1:0] xr_v;
        ot_reset_sync u_xw (.clk(cks[0]), .async_rst_n(x_arn), .sync_rst_n(xw0));
        ot_reset_sync u_xr (.clk(clk), .async_rst_n(x_arn), .sync_rst_n(xr0));
        (* keep = 1 *) reg [1:0] xw_t; (* keep = 1 *) reg [1:0] xr_t;
        always @(posedge cks[0] or negedge xw0) if (!xw0) xw_t <= 2'b00; else xw_t <= 2'b11;
        always @(posedge clk or negedge xr0) if (!xr0) xr_t <= 2'b00; else xr_t <= 2'b11;
        ot_async_fifo #(.WIDTH(551), .DEPTH(16), .EXT_RST(1)
`ifdef OT_VMFE_FCC_PIPE
            , .FIFO_PIPE(1)
`endif
            ) u_cc0 (.wr_clk(cks[0]), .wr_rst_n(xw_t[0]), .wr_valid(sw_v[0]),
            .wr_ready(cw_rdy[0]), .wr_data(sw_d0), .wr_overflow(), .rd_clk(clk), .rd_rst_n(xr_t[0]), .rd_valid(xr_v[0]),
            .rd_ready(cr_take[0]), .rd_data(cr_d0), .rd_underflow());
        ot_async_fifo #(.WIDTH(551), .DEPTH(16), .EXT_RST(1)
`ifdef OT_VMFE_FCC_PIPE
            , .FIFO_PIPE(1)
`endif
            ) u_cc1 (.wr_clk(cks[0]), .wr_rst_n(xw_t[1]), .wr_valid(sw_v[1]),
            .wr_ready(cw_rdy[1]), .wr_data(sw_d1), .wr_overflow(), .rd_clk(clk), .rd_rst_n(xr_t[1]), .rd_valid(xr_v[1]),
            .rd_ready(cr_take[1]), .rd_data(cr_d1), .rd_underflow());
        assign cr_v = rn ? xr_v : 2'b00;        // nothing is popped while the serial order registers are in reset
        assign cw_live = 2'b11;
    end else begin : g_ncca
        ot_ratio_cdc_fifo #(.W(551), .DEPTH(8)) u_cc0 (.wclk(cks[0]), .wrst_n(rns), .w_v(sw_v[0]), .w_rdy(cw_rdy[0]), .w_d(sw_d0),
            .rclk(clk), .rrst_n(rn), .r_v(cr_v[0]), .r_rdy(cr_take[0]), .r_d(cr_d0), .w_live(cw_live[0]), .r_live());
        ot_ratio_cdc_fifo #(.W(551), .DEPTH(8)) u_cc1 (.wclk(cks[0]), .wrst_n(rns), .w_v(sw_v[1]), .w_rdy(cw_rdy[1]), .w_d(sw_d1),
            .rclk(clk), .rrst_n(rn), .r_v(cr_v[1]), .r_rdy(cr_take[1]), .r_d(cr_d1), .w_live(cw_live[1]), .r_live());
    end endgenerate
    // One request can enter only with both pin stages empty. No intervening
    // writer can consume the selected FIFO slot before this request reaches it.
    assign vready = rns && !vwe[0] && !vre[0] && !s_we && !s_re && cw_rdy[s_tg];
    always @(posedge cks[0]) if (!rns) s_ovf <= 1'b0;
        else if ((sw_v[0] && !cw_rdy[0]) || (sw_v[1] && !cw_rdy[1])) s_ovf <= 1'b1;   // incl. ops before the crossing is up
    // serial side: pop in alternation order, <= 2 a cycle: first -> lane A (p3), second -> lane B (p4)
    reg c_nx;                           // FIFO holding the next op
    reg ca_v, cb_v; reg [550:0] ca_d, cb_d;
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
    wire ad_v, ad_r; wire [83:0] ad_d; wire ad_flt_c, ad_on; wire ad_flt;
    // XRT 1 (B8): the adapter's fault is a STREAM-domain level (cf || ef_c2) read by the serial fault register: it crosses
    // through a stream register and a 2-flop synchroniser (sticky, so +3 cycles on a fault that is already fatal)
    generate if (XRT != 0) begin : g_afs
        reg ad_flt_q; (* async_reg = "true" *) reg [1:0] ad_flt_s;
        always @(posedge cks[0]) ad_flt_q <= ad_flt_c;
        always @(posedge clk) ad_flt_s <= {ad_flt_s[0], ad_flt_q};
        assign ad_flt = ad_flt_s[1];
    end else begin : g_nafs
        assign ad_flt = ad_flt_c;
    end endgenerate
    reg ed_v; reg [7:0] ed_t;
    // engine command pin flops (el1011-ds-vm/fe6): cv / cd enter a register at the pin (stream domain, +1 stream cycle on
    // every command alike) so the adapter's tag lookup (cd -> cpending[tag] -> admit -> u_cmd, 14 levels) starts at a flop
    reg cv_p; reg [83:0] cd_p;
    always @(posedge cks[0]) begin if (!rns) cv_p <= 1'b0; else cv_p <= cv[0]; cd_p <= cd; end
    // engine done pin flops (el1013-s81-vmfe/B6, DVR 1 = the hard leaf dsfd_vm_fcn): the adapter's done register sits in its
    // tag logic (enable, asynchronous clear, 280-load reset), not at the face; dv / dt leave their own stream-domain register
    wire ad_dv; wire [7:0] ad_dt;
    generate if (DVR != 0) begin : g_dvr
        reg dv_q; reg [7:0] dt_q;
        always @(posedge cks[0]) begin if (!rns) dv_q <= 1'b0; else dv_q <= ad_dv; dt_q <= ad_dt; end
        assign dv[0] = dv_q; assign dt = dt_q;
    end else begin : g_ndvr
        assign dv[0] = ad_dv; assign dt = ad_dt;
    end endgenerate
    ot_s81_engine_adapter #(.QD(8), .XRT(XRT)) u_ad (
        .c_clk(cks[0]), .c_rst_n(rss[0]), .c_cmd_v(cv_p), .c_cmd_d(cd_p), .c_done_v(ad_dv), .c_done_tag(ad_dt),
        .fault(ad_flt_c), .online(ad_on),
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
`ifdef OT_SPVM_XGOS
    // XGOS (claude s81-grpA r3, default-off VM-read variant): XGO arg[16] = wait, arg[15:14] = producer slot.  The
    // streamer is loaded at once but starts only when the slot COMPLETES (or at once if the slot completed and was not
    // re-armed since): the controller no longer waits for the producer's ARMN done to issue the consumer's XGO.
    reg [4:0] x_wt, x_rel;              // waiting on a slot / release pulse (row-completion counter section)
    wire x_hold_new = vop == 3'd7 && x_go && xp_c < 3'd5 && (x_wt[xp_c] || x_rel[xp_c]);
`else
    wire x_hold_new = 1'b0;
`endif
    wire imm_op = vop == 3'd1 || vop == 3'd2 || vop == 3'd4 || vop == 3'd6 || (vop == 3'd7 && !x_go);
    assign ad_r = !(imm_op && imm_v) && !(vop == 3'd5 && cq_n == CQD) && !(vop == 3'd7 && x_go && xp_c < 3'd5 && x_act[xp_c]) && !x_hold_new;
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
`ifdef OT_SPVM_XGOS
            if (is_xgo && xp_c == xi[2:0]) begin x_act[xi] <= !arg[16]; x_b[xi] <= arg[13:0]; x_c[xi] <= 13'd0; x_tag[xi] <= ctag; end
            else if (x_rel[xi]) x_act[xi] <= 1'b1;
`else
            if (is_xgo && xp_c == xi[2:0]) begin x_act[xi] <= 1'b1; x_b[xi] <= arg[13:0]; x_c[xi] <= 13'd0; x_tag[xi] <= ctag; end
`endif
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
        // room flag padded by the relay latency added in v3 (8 -> 16 rows at LAL 2; +1 row per further input stage:
        // a row in the LAL relay is in flight and not yet counted when room_ok is formed)
        dsfd_vm_ll #(.DEPTH(DP), .MACRO(LMACRO), .STRIDE(ST), .OFF(OF), .AL(LAL), .RTH(14 + LAL + LVX)) u_ll (.clk(clk), .rn(rr_ll[1]),
            .in_v(ll_iv[gll]), .in_d(ll_id[512*gll +: 512]), .arm_v(ll_arm[gll]), .arm_base(arg[13:0]),
            .o_av(ll_av[gll]), .g(g_r[LGL-1][gll]), .o_v(ll_ov_v[gll]), .o_row(ll_or[14*gll +: 14]), .o_d(ll_od[512*gll +: 512]),
            .room_ok(ll_ok[gll]), .ovf(ll_ov[gll]));
    end endgenerate
    // LVX (el1013-s81-vmfe/B6): the written-row flags and the collective room flags cross LVX more stages on their way to
    // the drain (hierarchy: one mid-hop relay tile dsfd_vm_frv a lane); the room threshold grows by one row a stage
    reg [NLL-1:0] av_x [0:((LVX > 0) ? LVX : 1)-1]; reg [3:0] ok_x [0:((LVX > 0) ? LVX : 1)-1];
    always @(posedge clk) begin : p_lvx integer i;
        if (!rn) for (i = 0; i < ((LVX > 0) ? LVX : 1); i = i + 1) begin av_x[i] <= {NLL{1'b0}}; ok_x[i] <= 4'd0; end
        else begin
            av_x[0] <= ll_av; ok_x[0] <= ll_ok[2*NSVC +: 4];
            for (i = 1; i < LVX; i = i + 1) begin av_x[i] <= av_x[i-1]; ok_x[i] <= ok_x[i-1]; end
        end
    end
    wire [NLL-1:0] ll_avd = (LVX == 0) ? ll_av : av_x[((LVX > 0) ? LVX : 1)-1];
    wire [3:0] ll_okd = (LVX == 0) ? ll_ok[2*NSVC +: 4] : ok_x[((LVX > 0) ? LVX : 1)-1];
    reg [6:0] lc [0:NLL-1];             // rows written and not yet granted, per lane
    reg [$clog2(NLL)-1:0] ll_ptr; reg [NLP-1:0] lp_v; reg [NLP*14-1:0] lp_row; reg [NLP*512-1:0] lp_d;
    reg [NLP-1:0] lsel_v; reg [$clog2(NLL)-1:0] lsel [0:NLP-1];
`ifdef OT_VMFE_FLD_PARALLEL_ARB
`include "dsfd_vm_fld_parallel_arb.svh"
`else
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
`endif
    reg [NLL-1:0] sd_oh [0:NLP-1][0:LSD-1]; reg [NLP-1:0] sd_v [0:LSD-1];
    always @(posedge clk) begin : p_l578 integer lk, li, i; reg [511:0] dsel; reg [13:0] rsel;
        if (!rn) begin
            lp_v <= {NLP{1'b0}}; ll_ptr <= 0; av_r <= {NLL{1'b0}};
            for (li = 0; li < NLL; li = li + 1) lc[li] <= 7'd0;
            for (i = 0; i < LGL; i = i + 1) g_r[i] <= {NLL{1'b0}};
            for (i = 0; i < LSD; i = i + 1) sd_v[i] <= {NLP{1'b0}};
        end else begin
            ll_ptr <= (ll_ptr == NLL - 1) ? 0 : ll_ptr + 1'b1;
            av_r <= ll_avd;
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
    always @(posedge clk) if (!rn) cts_ok <= 1'b0; else cts_ok <= &ll_okd;
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
    reg [15:0] b_tag;
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
        b_m[3*16+:16] <= WCOMMIT ? ca_d[542:527] : 16'hffff;
        b_m[4*16+:16] <= WCOMMIT ? cb_d[542:527] : 16'hffff;
        b_tag<={cb_d[550:543],ca_d[550:543]};
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
    // stage C + FRL relay stages per slice (el1011-ds-vm/fe6, FE v6): stage 0 of each slice is an ID-distinct kept register
    // (dsfd_vm_be_kreg: the 4 slices' valid / we / row copies are identical in value and must NOT be merged into one flop
    // driving all 4 slice faces -- the feh5 424 x > 500-um wire-reach class); relay stages 1 .. FRL are the hard tile
    // dsfd_vm_fsr (pin flop + output flop, FRL 2 fixed) sitting directly above bgq column s at the S face.  The valid copy
    // folds the synchronous reset into its D (rn ? c_vv : 0, as before); the tile's valid reset is its pin-flopped rn, fed
    // from a kept per-slice copy of rn0 so the tile sees rr_c[1] exactly.  m_rf is registered inside the tile (was here).
`ifdef OT_SPVM_REF_FRL
    // LOCKSTEP REFERENCE of the hierarchy dsfd_vm_fe_h (el1013-s81-vmfe): FRL - 2 behavioural relay stages between the
    // stage-0 register and the hard dsfd_vm_fsr (= the R dsfd_vm_fxr tiles, 2 flops each); m_rf sees |fe_flt FRL - 1
    // cycles later (fcn out flop + the same relay chain).  Simulation reference only, never a physical view.
    localparam integer FRX = FRL - 2;
    if (FRL < 2) begin : g_frl
        dsfd_vm_fsr_hard_frl_mismatch u_err ();
    end
`else
    localparam integer FRX = 0;
    if (FRL != 2) begin : g_frl
        dsfd_vm_fsr_hard_frl_mismatch u_err ();    // elaboration error: the hardened dsfd_vm_fsr is FRL 2 (two stages)
    end
`endif
    reg [15:0] tag_pipe[0:FRL]; integer ti;
    always @(posedge clk) begin
        tag_pipe[0]<=b_tag;
        for(ti=1;ti<=FRL;ti=ti+1) tag_pipe[ti]<=tag_pipe[ti-1];
    end
    assign m_wtag=tag_pipe[FRL];
    integer s;
    genvar gsl, gp;
    generate for (gsl = 0; gsl < NS; gsl = gsl + 1) begin : g_sl
        wire [NP*4-1:0] cm_s; wire [NP*128-1:0] cd_s;
        wire [NP-1:0] cv_s, cw_s; wire [NP*RA-1:0] cr_s;
        for (gp = 0; gp < NP; gp = gp + 1) begin : g_p
`ifdef OT_SPVM_SLOC
            // VM FE (a) capture-slice locality (claude s81-grpA r5): slice gsl's capture port CP + 4 l + m takes segment m
            // (virtual words 4m .. 4m+3 = its OWN slice's words) of lane g = 4 gsl + l, row {key, l, m}: the lanes of
            // quadrant gsl feed only slice gsl (no 4 x 4 crossbar); every other port as before
            if (gp >= CP && gp < CP + 16) begin : g_c
                localparam integer LL = (gp - CP) / 4, SG = (gp - CP) % 4, LG = CP + 4 * gsl + LL;
                localparam [1:0] S2 = SG;
                assign cv_s[gp] = c_vv[LG]; assign cw_s[gp] = c_we[LG];
                wire [RA-1:0] capture_row = {c_row[LG*RA + 4 +: RA - 4], c_row[LG*RA +: 2], S2};
                assign cr_s[gp*RA +: RA] = {capture_row[13:5],capture_row[4:0] ^ (BANK_XOR ? {capture_row[7:5],2'b00} : 5'd0)};   // c_row[1:0] = gid[1:0] = L2 when valid
                assign cm_s[4*gp +: 4] = c_m[LG*16 + 4*SG +: 4];
                assign cd_s[128*gp +: 128] = c_dd[LG*512 + 128*SG +: 128];
            end else begin : g_n
`endif
            assign cv_s[gp] = c_vv[gp]; assign cw_s[gp] = c_we[gp]; wire [RA-1:0] logical_row = c_row[gp*RA +: RA];
`ifdef OT_VM_BANK_XOR_MUT_WRITE_ONLY
            wire do_hash = BANK_XOR && c_we[gp];
`else
            wire do_hash = BANK_XOR;
`endif
            assign cr_s[gp*RA +: RA] = {logical_row[13:5],logical_row[4:0] ^ (do_hash ? {logical_row[7:5],2'b00} : 5'd0)};
            assign cm_s[4*gp +: 4] = c_m[gp*16 + 4*gsl +: 4];
            assign cd_s[128*gp +: 128] = c_dd[gp*512 + 128*gsl +: 128];
`ifdef OT_SPVM_SLOC
            end
`endif
        end
        localparam integer W0 = NP * (2 + RA + 4 + 128);
        wire [W0-1:0] s0;
        dsfd_vm_be_kreg #(.W(W0), .ID(600 + gsl)) u_s0 (.clk(clk), .d({rn ? cv_s : {NP{1'b0}}, cw_s, cr_s, cm_s, cd_s}), .q(s0));
        (* keep = 1 *) reg rr_f;
        always @(posedge clk) rr_f <= rn0;
        reg [3:0] rf_d;
        wire [W0-1:0] s0x;
        if (FRX == 0) begin : g_nx
            always @* rf_d = {|fe_flt, 3'b000};
            assign s0x = s0;
        end else begin : g_x                // reference relay (OT_SPVM_REF_FRL only)
            reg [W0-1:0] xq [0:FRX-1]; reg [FRX:0] xrf; reg rr_x; integer xi;
            always @(posedge clk) begin
                rr_x <= rr_f;
                xq[0] <= s0; for (xi = 1; xi < FRX; xi = xi + 1) xq[xi] <= xq[xi-1];
                if (!rr_x) for (xi = 0; xi < FRX; xi = xi + 1) xq[xi][W0-1 -: NP] <= {NP{1'b0}};
                xrf <= {xrf[FRX-1:0], |fe_flt};
            end
            always @* rf_d = {xrf[FRX], 3'b000};
            assign s0x = xq[FRX-1];
        end
        // hard child: NO parameter overrides (one view for all 4 slices)
        dsfd_vm_fsr u_fr (.ck(clk), .rn(rr_f),
            .i_v(s0x[W0-1 -: NP]), .i_we(s0x[W0-NP-1 -: NP]), .i_row(s0x[W0-2*NP-1 -: NP*RA]), .i_mask(s0x[NP*128 +: NP*4]),
            .i_d(s0x[0 +: NP*128]), .i_rf(rf_d),
            .o_v(m_v[gsl*NP +: NP]), .o_we(m_we[gsl*NP +: NP]), .o_row(m_row[gsl*NP*RA +: NP*RA]),
            .o_mask(m_mask[gsl*NP*4 +: NP*4]), .o_d(m_d[gsl*NP*128 +: NP*128]), .o_rf(m_rf[gsl*4 +: 4]));
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
    // stage K2 (el1011-ds-vm/fe6: the k_pc -> 28-port sum -> compare -> early path was ~1,525 ps in one cycle): per slot
    // 4 group sums of 7 ports (masked by k_ok) and the read-hit OR are registered; the counter adds the 4 group sums.
    // The counter half of every ARM (sl_arm / sl_cnt / sl_need / tag / user / ntf / t_rdy / rearm) moves one cycle later
    // with them (k2_*), so ARM and op counts keep their order; the range half (sl_base / sl_n, read by stage K's compares)
    // still lands at k_arm.  Effect: slot completion / done / rows-ready one serial cycle later, same order of events.
    reg [7:0] k2_g [0:NSLOT*4-1]; reg [NSLOT-1:0] k2_hr;
    reg k2_arm; reg [1:0] k2_s; reg [18:0] k2_need; reg [7:0] k2_tag; reg [9:0] k2_user; reg k2_ntf;
    always @(posedge clk) begin : p_k2 integer kk, g, q; reg [7:0] a; reg h;
        for (kk = 0; kk < NSLOT; kk = kk + 1) begin
            h = 1'b0;
            for (g = 0; g < 4; g = g + 1) begin
                a = 8'd0;
                for (q = 7 * g; q < 7 * g + 7; q = q + 1) if (k_w[kk*NP + q]) a = a + {3'd0, k_pc[5*q +: 5]};
                k2_g[kk*4 + g] <= k_ok[kk] ? a : 8'd0;
            end
            for (q = 0; q < NP; q = q + 1) if (k_r[kk*NP + q]) h = 1'b1;
            k2_hr[kk] <= h && k_ok[kk];
        end
        if (!rn) k2_arm <= 1'b0; else k2_arm <= k_arm;
        k2_s <= k_s; k2_need <= k_arg[18:0]; k2_tag <= k_tag; k2_user <= k_user; k2_ntf <= st_ntf[k_s];
    end
`ifdef OT_VMFE_FCN_SUM_PIPE
    // Stage K3: reduce the four K2 groups before the wide count/compare.
    // ARM metadata and read hits advance with the same accepted operation.
    reg [9:0] k3_inc [0:NSLOT-1]; reg [NSLOT-1:0] k3_hr;
    reg k3_arm; reg [1:0] k3_s; reg [18:0] k3_need; reg [7:0] k3_tag;
    reg [9:0] k3_user; reg k3_ntf;
    always @(posedge clk) begin : p_k3 integer kk;
        for (kk = 0; kk < NSLOT; kk = kk + 1)
            k3_inc[kk] <= ({2'd0, k2_g[kk*4]} + {2'd0, k2_g[kk*4+1]})
                         + ({2'd0, k2_g[kk*4+2]} + {2'd0, k2_g[kk*4+3]});
        k3_hr <= k2_hr;
        if (!rn) k3_arm <= 1'b0; else k3_arm <= k2_arm;
        k3_s <= k2_s; k3_need <= k2_need; k3_tag <= k2_tag;
        k3_user <= k2_user; k3_ntf <= k2_ntf;
    end
`endif
    reg [9:0] inc [0:NSLOT-1];
    reg [NSLOT-1:0] hit_r, cmpl;
    always @* begin : p_l691 integer kk;
        for (kk = 0; kk < NSLOT; kk = kk + 1) begin
`ifdef OT_VMFE_FCN_SUM_PIPE
`ifdef OT_VMFE_FCN_SUM_PIPE_MUT
            inc[kk] = k3_inc[kk] ^ 10'd1;
`else
            inc[kk] = k3_inc[kk];
`endif
            hit_r[kk] = k3_hr[kk];
`else
            inc[kk] = ({2'd0, k2_g[kk*4]} + {2'd0, k2_g[kk*4 + 1]}) + ({2'd0, k2_g[kk*4 + 2]} + {2'd0, k2_g[kk*4 + 3]});
            hit_r[kk] = k2_hr[kk];
`endif
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
            if (k_arm) begin sl_base[k_s] <= st_base[k_s]; sl_n[k_s] <= st_n[k_s]; end   // range half: stage K compares
`ifdef OT_VMFE_FCN_SUM_PIPE
            if (k3_arm) begin                                                            // counter half: with the K2 sums
                if (sl_arm[k3_s] || sl_dp[k3_s] || sl_rp[k3_s]) rearm <= 1'b1;
                sl_arm[k3_s] <= 1'b1; t_rdy[k3_s] <= 1'b0; sl_ntf[k3_s] <= k3_ntf; sl_user[k3_s] <= k3_user;
                sl_need[k3_s] <= k3_need; sl_cnt[k3_s] <= 19'd0; sl_tag[k3_s] <= k3_tag;
            end
`else
            if (k2_arm) begin                                                            // counter half: with the K2 sums
                if (sl_arm[k2_s] || sl_dp[k2_s] || sl_rp[k2_s]) rearm <= 1'b1;
                sl_arm[k2_s] <= 1'b1; t_rdy[k2_s] <= 1'b0; sl_ntf[k2_s] <= k2_ntf; sl_user[k2_s] <= k2_user;
                sl_need[k2_s] <= k2_need; sl_cnt[k2_s] <= 19'd0; sl_tag[k2_s] <= k2_tag;
            end
`endif
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

`ifdef OT_SPVM_XGOS
    // XGOS release: x_fr[s] = slot s completed and not re-armed since (set by its completion, cleared when an ARMN of s is
    // accepted, in command order with the XGOS).  A waiting streamer is released by its slot's completion pulse; an XGOS
    // that arrives after the completion is released at once.  One registered cycle (x_rel) before the streamer starts.
    reg [NSLOT-1:0] x_fr; reg [1:0] x_ws [0:4];
    always @(posedge clk) begin : p_xgos integer xi, kk;
        if (!rn) begin x_wt <= 5'd0; x_rel <= 5'd0; x_fr <= {NSLOT{1'b0}}; end
        else begin
            for (kk = 0; kk < NSLOT; kk = kk + 1) begin
                if (cmpl[kk]) x_fr[kk] <= 1'b1;
                if (is_arm && arm_s == kk[1:0]) x_fr[kk] <= 1'b0;
            end
            for (xi = 0; xi < 5; xi = xi + 1) begin
                x_rel[xi] <= 1'b0;
                if (is_xgo && arg[16] && xp_c == xi[2:0]) begin
`ifdef OT_SPVM_MUT_XGOS_EARLY
                    x_rel[xi] <= 1'b1;                                              // MUTANT: starts without its slot
`else
                    if (x_fr[arg[15:14]] || cmpl[arg[15:14]]) x_rel[xi] <= 1'b1;
                    else begin x_wt[xi] <= 1'b1; x_ws[xi] <= arg[15:14]; end
`endif
                end else if (x_wt[xi] && cmpl[x_ws[xi]]) begin x_wt[xi] <= 1'b0; x_rel[xi] <= 1'b1; end
            end
        end
    end
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
endmodule

// ================================================================================================ FE slice relay tile
// dsfd_vm_fsr (el1011-ds-vm/fe6, FE v6): the FE's per-slice request relay stages 1 .. 2 as ONE hard tile (harden once, 4
// instances), 345.6 um wide directly above bgq column s at the FE S face.  N face: the slice's request bus from the FE's
// stage-0 register + ck / rn; S face: the same bus at the exact x of the FE m_* S pins (= the bgq tile-0 N pins), so every
// bit is a vertical feed-through.  Inside: pin flop + output flop on every bit (FRL 2), valid bits reset by the
// pin-flopped rn, datapath reset-free; o_rf = the slice's tile-0 status input, registered once (one flop, as before).
(* keep_hierarchy = "yes" *)
module dsfd_vm_fsr (
    input  wire          ck,
    input  wire          rn,
    input  wire [27:0]   i_v,  input wire [27:0]  i_we, input wire [391:0] i_row, input wire [111:0] i_mask,
    input  wire [3583:0] i_d,  input wire [3:0]   i_rf,
    output reg  [27:0]   o_v,  output reg [27:0]  o_we, output reg [391:0] o_row, output reg [111:0] o_mask,
    output reg  [3583:0] o_d,  output reg [3:0]   o_rf
`ifdef OT_SPVM_RESET_ACK
    , input wire reset_epoch_n, output wire rst_ack
`endif
);
    reg rn_q;
    reg [27:0] v1, we1; reg [391:0] row1; reg [111:0] m1; reg [3583:0] d1;
    always @(posedge ck) begin
        rn_q <= rn;
        if (!rn_q) begin v1 <= 28'd0; o_v <= 28'd0; end else begin v1 <= i_v; o_v <= v1; end
        we1 <= i_we; row1 <= i_row; m1 <= i_mask; d1 <= i_d;
        o_we <= we1; o_row <= row1; o_mask <= m1; o_d <= d1;
        o_rf <= i_rf;
    end
`ifdef OT_SPVM_RESET_ACK
    dsfd_vm_reset_ack u_reset_ack (.clk(ck), .request_n(reset_epoch_n), .local_release(rn_q), .consumer_live(1'b1), .ack(rst_ack));
`endif
endmodule

// New real pin-registered leaf variant; CLOSED dsfd_vm_fsr remains unchanged.
module dsfd_vm_fsr_xor (
    input  wire          ck,
    input  wire          rn,
    input  wire [27:0]   i_v,  input wire [27:0]  i_we, input wire [391:0] i_row, input wire [111:0] i_mask,
    input  wire [3583:0] i_d,  input wire [3:0]   i_rf,
    output reg  [27:0]   o_v,  output reg [27:0]  o_we, output reg [391:0] o_row, output reg [111:0] o_mask,
    output reg  [3583:0] o_d,  output reg [3:0]   o_rf
`ifdef OT_SPVM_RESET_ACK
    , input wire reset_epoch_n, output wire rst_ack
`endif
);
    reg rn_q;
    reg [27:0] v1, we1; reg [391:0] row1; reg [111:0] m1; reg [3583:0] d1;
    always @(posedge ck) begin
        rn_q <= rn;
        if (!rn_q) begin v1 <= 28'd0; o_v <= 28'd0; end else begin v1 <= i_v; o_v <= v1; end
        we1 <= i_we; row1 <= i_row; m1 <= i_mask; d1 <= i_d;
        o_we <= we1; o_mask <= m1; o_d <= d1;
        for(integer p=0;p<28;p=p+1)begin
`ifdef OT_VM_BANK_XOR_MUT_WRITE_ONLY
            o_row[14*p+:14]<={row1[14*p+5+:9],row1[14*p+:5] ^ (we1[p] ? {row1[14*p+5+:3],2'b00} : 5'd0)};
`else
            o_row[14*p+:14]<={row1[14*p+5+:9],row1[14*p+:5] ^ {row1[14*p+5+:3],2'b00}};
`endif
        end
        o_rf <= i_rf;
    end
`ifdef OT_SPVM_RESET_ACK
    dsfd_vm_reset_ack u_reset_ack (.clk(ck), .request_n(reset_epoch_n), .local_release(rn_q), .consumer_live(1'b1), .ack(rst_ack));
`endif
endmodule

// ================================================================================================ back end
// dsfd_vm_be v3 (el1011-ds-vm/be 2026-10-11, BIT-SLICED; ds-1010 decision): the back end is 4 identical hardened slice tiles
// dsfd_vm_be_sl (302.4 x 99.36 um, one under each bgq column) + a thin parent.  Tile s takes its own column's tile-3
// S-face read data (o_v / o_d / o_f / o_o of slice s) and emits ITS OWN 128-b slice of every response (t_srq rows 0 / 1,
// vrq, the 16 bus lanes, the P2 flit data + 23 of its 92 metadata bits) from its own S-face x range (BE S-FACE CONTRACT
// v3): no row is ever gathered across the slab.  Control is replicated per slice in lockstep: the X lane ids, the P2
// metadata, both synchronous resets and the status reach each tile through the parent's registered relay chains, equal
// length for every tile (R = MD - XT stages, <= ~400 um a stage); every tile has its own ck / cks roots.  The only
// unregistered slab-wide net: none.  The P2 consumer port is READY-LATENCY 4 (c_l0r pin flop, relay, tile register; a
// beat leaves on c_l0v only if c_l0r was high 4 cycles earlier and every c_l0v beat is a transfer).
// Inside a tile: pin flops (1 load each), datapath registers without reset (kept regional reset copies for control),
// kept one-hot selects / X-row copies per lane group, the ctrl return through a mesochronous ratio FIFO (LAG 1: an entry
// is stable for a full serial cycle before its pointer is published) with a registered read port, and the P2 FIFO in 2
// column chunks with kept pointer copies.  Latency vs v1: t_srq +0, bus lanes +1, P2 +1, ctrl return +2 serial +1 stream.
// ID: a distinct value per copy makes every copy its own module (no pass can merge two copies)
(* keep_hierarchy = "yes" *)
module dsfd_vm_be_kreg #(parameter integer W = 1, parameter integer ID = 0) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge clk) q <= d;
endmodule

// dsfd_vm_be_rcdc: the ot_ratio_cdc_fifo protocol (HOLD handshake, LAG 1 publication, identical pointer / state behaviour)
// with per-chunk storage written through kept one-hot copies of the next wp, and a registered read port: o_v = the take
// one stream cycle later, o_d = the taken entry (sh registered through kept one-hot copies of the next rp), o_vc = kept
// copies of o_v.
module dsfd_vm_be_rcdc #(
    parameter integer W = 128, parameter integer DEPTH = 8, parameter integer HOLD = 2, parameter integer NC = 2,
    parameter integer IDB = 0
) (
    input  wire          wclk, wrst_n, w_v,
    output wire          w_rdy,
    input  wire [W-1:0]  w_d,
    input  wire          rclk, rrst_n,
    output wire          r_v,
    input  wire          r_rdy,
    output reg           o_v,
    output wire [W-1:0]  o_d,
    output wire [NC-1:0] o_vc
`ifdef OT_SPVM_RESET_ACK
    , output wire w_online, r_online
`endif
);
    localparam integer AW = $clog2(DEPTH);
    localparam integer CW = $clog2(HOLD + 1);
    localparam integer CB = W / NC;
    localparam [1:0] S_DOWN = 2'b00, S_WAIT = 2'b01, S_RUN = 2'b10;
    localparam [AW:0] DP = DEPTH;
    localparam [CW-1:0] HL = HOLD;
    reg [AW:0]   wp, wp_pub, rp_w, rp, wp_r;
    reg [1:0]    w_st, r_st_w, r_st, w_st_r;
    reg [CW-1:0] w_cnt, r_cnt;
    reg          w_ok, r_ok;
    always @(posedge wclk) begin rp_w <= rp; r_st_w <= r_st; end
    wire w_live = (w_st == S_RUN) && (r_st_w != S_DOWN);
    assign w_rdy = wrst_n && w_live && ((wp - rp_w) != DP);
`ifdef OT_SPVM_RESET_ACK
    // Export actual rendezvous state, independent of FIFO occupancy or traffic.
    assign w_online = wrst_n && w_live;
    assign r_online = rrst_n && r_live;
`endif
    wire w_fire = w_v && w_rdy;
    reg [AW:0] wp_nx;
    always @* begin
        wp_nx = wp;
        if (!wrst_n) wp_nx = {(AW+1){1'b0}};
        else case (w_st)
            S_DOWN, S_WAIT: wp_nx = {(AW+1){1'b0}};
            default: if (r_st_w == S_DOWN) wp_nx = {(AW+1){1'b0}}; else if (w_fire) wp_nx = wp + 1'b1;
        endcase
    end
    always @(posedge wclk) begin
        wp <= wp_nx;
        wp_pub <= wp;                       // LAG 1
        if (!wrst_n) begin
            w_st <= S_DOWN; w_cnt <= HL; w_ok <= 1'b0;
        end else begin
            case (w_st)
                S_DOWN: begin
                    if (r_st_w != S_RUN) w_ok <= 1'b1;
                    if (w_cnt != {CW{1'b0}}) w_cnt <= w_cnt - 1'b1;
                    else if (w_ok || r_st_w != S_RUN) w_st <= S_WAIT;
                end
                S_WAIT: if (r_st_w != S_DOWN) w_st <= S_RUN;
                default: if (r_st_w == S_DOWN) begin w_st <= S_DOWN; w_cnt <= HL; w_ok <= 1'b1; end
            endcase
        end
    end
    always @(posedge rclk) begin wp_r <= wp_pub; w_st_r <= w_st; end
    wire r_live = (r_st == S_RUN) && (w_st_r != S_DOWN);
    assign r_v = rrst_n && r_live && (wp_r != rp);
    wire r_take = r_v && r_rdy;
    reg [AW:0] rp_nx;
    always @* begin
        rp_nx = rp;
        if (!rrst_n) rp_nx = {(AW+1){1'b0}};
        else case (r_st)
            S_DOWN, S_WAIT: rp_nx = {(AW+1){1'b0}};
            default: if (w_st_r == S_DOWN) rp_nx = {(AW+1){1'b0}}; else if (r_take) rp_nx = rp + 1'b1;
        endcase
    end
    always @(posedge rclk) begin
        rp <= rp_nx;
        o_v <= r_take;
        if (!rrst_n) begin
            r_st <= S_DOWN; r_cnt <= HL; r_ok <= 1'b0;
        end else begin
            case (r_st)
                S_DOWN: begin
                    if (w_st_r != S_RUN) r_ok <= 1'b1;
                    if (r_cnt != {CW{1'b0}}) r_cnt <= r_cnt - 1'b1;
                    else if (r_ok || w_st_r != S_RUN) r_st <= S_WAIT;
                end
                S_WAIT: if (w_st_r != S_DOWN) r_st <= S_RUN;
                default: if (w_st_r == S_DOWN) begin r_st <= S_DOWN; r_cnt <= HL; r_ok <= 1'b1; end
            endcase
        end
    end
    wire [DEPTH-1:0] oh_nx = {{(DEPTH-1){1'b0}}, 1'b1} << rp_nx[AW-1:0];
    wire [DEPTH-1:0] woh_nx = {{(DEPTH-1){1'b0}}, 1'b1} << wp_nx[AW-1:0];
    genvar c;
    generate for (c = 0; c < NC; c = c + 1) begin : g_c
        wire [DEPTH-1:0] oh, woh;
        dsfd_vm_be_kreg #(.W(DEPTH), .ID(IDB + c)) u_oh (.clk(rclk), .d(oh_nx), .q(oh));
        dsfd_vm_be_kreg #(.W(1), .ID(IDB + NC + c)) u_vc (.clk(rclk), .d(r_take), .q(o_vc[c]));
        dsfd_vm_be_kreg #(.W(DEPTH), .ID(IDB + 2*NC + c)) u_woh (.clk(wclk), .d(woh_nx), .q(woh));
        reg [CB-1:0] mem [0:DEPTH-1]; reg [CB-1:0] sh [0:DEPTH-1];
        always @(posedge wclk) begin : p_w integer i;
            for (i = 0; i < DEPTH; i = i + 1) if (w_fire && woh[i]) mem[i] <= w_d[c*CB +: CB];
        end
        always @(posedge rclk) begin : p_sh integer i;
            for (i = 0; i < DEPTH; i = i + 1) sh[i] <= mem[i];
        end
        reg [CB-1:0] od;
        always @(posedge rclk) begin : p_od integer i; reg [CB-1:0] a;
            a = {CB{1'b0}};
            for (i = 0; i < DEPTH; i = i + 1) a = a | (sh[i] & {CB{oh[i]}});
            od <= a;
        end
        assign o_d[c*CB +: CB] = od;
    end endgenerate
endmodule

// ------------------------------------------------------------------------------------------------ slice tile
// dsfd_vm_be_sl: one 128-b bit slice of the back end (hardened; 4 identical instances).  Control inputs xc / pm arrive
// MD - XT serial cycles after the parent's pin flops of f_vx / f_mx / f_v5 / f_m5; the tile's XT-stage line aligns them
// with its own o_* pin flops (stage 0).  rn_in / rns_in: synchronous resets from the parent's equal-length relays.
module dsfd_vm_be_sl #(
    parameter integer P2D = 40,
    parameter integer XT = 2
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        cks,
    input  wire [0:0]        rn_in,
    input  wire [0:0]        rns_in,
    input  wire [9:0]        o_v,
    input  wire [1279:0]     o_d,
    input  wire [3:0]        o_f,
    input  wire [2:0]        o_o,
    // v4 (GLUE PLACEMENT rule): the die-facing control arrives on this tile's own pins (die-top relays: exactly DIE_D = 3
    // stages on every control seam, equal for all 4 slices); pin flops + the alignment line live in the tile
    input  wire [4:0]        f_vx,       // X lane valids (port order {p9, p8, p2, p7, p6}), f_wex write flags
    input  wire [4:0]        f_wex,
    input  wire [19:0]       f_mx,       // X lane ids (4 b each)
    input  wire [0:0]        f_v5,
    input  wire [0:0]        f_we5,
    input  wire [22:0]       f_m5s,      // this slice's 23 bits of the P2 metadata (f_m5[23 s +: 23])
    input  wire [0:0]        c_l0r,      // consumer ready (die relays: exactly 1 stage) -> pin flop: READY-LATENCY 3 + die relays
    input  wire [15:0]       fe_flt,     // FE fault vector (the die drives it on one slice, 0 on the others)
    input  wire [39:0]       st_i,       // status chain from the W neighbour (slice 0: tied 0) {fe 16, sst 17, mis, sf 5, v}
    output reg  [39:0]       st_o,       // status chain to the E neighbour (registered; abutting seam, no die relay)
    output reg  [255:0]      srq_d,      // {row 1, row 0} slices
    output reg  [1:0]        srq_v,
    output reg  [0:0]        vrv,
    output reg  [127:0]      vrq,
    output reg  [16*128-1:0] bl_d,
    output reg  [15:0]       bl_v,
    output wire [0:0]        c_l0v,
    output wire [150:0]      c_l0d,      // {23 metadata bits, 128 data bits}
    output reg  [0:0]        t_p2c,
    output reg  [0:0]        t_err,      // sticky status of the chain up to this slice (the die uses slice 3's)
    output reg  [0:0]        flt,
    output reg  [31:0]       fvec,
    output reg  [2:0]        max_occ
`ifdef OT_SPVM_RESET_ACK
    , input wire reset_epoch_n, reset_epoch_s_n
    , output reg rst_ack, rst_ack_s
`endif
);
    localparam integer KX = 4;          // in-tile alignment relays after the control pin flops (DIE_D + 1 + KX + XT = MD + 1)
    reg [4:0] sflt;                     // this cycle {x_col, x_mis, r_ovf, p_mis, p_ovf}
    reg [16:0] sst;                     // {o_o, o_f, o_v} pin flops (slice compare / status)
    localparam integer NP = 10;
    localparam integer NC = 2;          // ctrl-return 64-b chunks
    localparam integer NG = 4;          // bus-lane groups
    wire clk = ck[0], sclk = cks[0];
    wire rn_i, rn_x, rn_c, rn_p, rn_w, rns;
    dsfd_vm_be_kreg #(.W(1), .ID(1)) u_rn_i (.clk(clk), .d(rn_in[0]), .q(rn_i));
    dsfd_vm_be_kreg #(.W(1), .ID(2)) u_rn_x (.clk(clk), .d(rn_in[0]), .q(rn_x));
    dsfd_vm_be_kreg #(.W(1), .ID(3)) u_rn_c (.clk(clk), .d(rn_in[0]), .q(rn_c));
    dsfd_vm_be_kreg #(.W(1), .ID(4)) u_rn_p (.clk(clk), .d(rn_in[0]), .q(rn_p));
    dsfd_vm_be_kreg #(.W(1), .ID(5)) u_rn_w (.clk(clk), .d(rn_in[0]), .q(rn_w));
    dsfd_vm_be_kreg #(.W(1), .ID(6)) u_rns (.clk(sclk), .d(rns_in[0]), .q(rns));
`ifdef OT_SPVM_RESET_ACK
    wire [1:0] cdc_w_online, cdc_r_online;
    reg ack_reset_seen, ack_reset_seen_s;
`ifdef OT_SPVM_MUT_ACK_EPOCH_FORWARD
    wire ack_epoch_n = rn_in[0], ack_epoch_s_n = rns_in[0];
`else
    wire ack_epoch_n = reset_epoch_n, ack_epoch_s_n = reset_epoch_s_n;
`endif
    wire all_local_rn = rn_i && rn_x && rn_c && rn_p && rn_w;
    wire no_local_rn = !(rn_i || rn_x || rn_c || rn_p || rn_w);
`ifdef OT_SPVM_MUT_ACK_MIRROR
    always @* begin rst_ack = rn_in[0]; rst_ack_s = rns_in[0]; end
`else
    // Witness reset at the real consumer clock; a stopped clock cannot acknowledge
    // a reset pulse it never sampled. ACK state adds no datapath admission logic.
    always @(posedge clk or negedge ack_epoch_n) begin
        if (!ack_epoch_n) begin ack_reset_seen <= 1'b0; rst_ack <= 1'b0; end
        else begin
            if (no_local_rn) ack_reset_seen <= 1'b1;
            rst_ack <= ack_reset_seen && all_local_rn && (&cdc_w_online);
        end
    end
    always @(posedge sclk or negedge ack_epoch_s_n) begin
        if (!ack_epoch_s_n) begin ack_reset_seen_s <= 1'b0; rst_ack_s <= 1'b0; end
        else begin
            if (!rns) ack_reset_seen_s <= 1'b1;
            rst_ack_s <= ack_reset_seen_s && rns && (&cdc_r_online);
        end
    end
`endif
`endif
    // ---------------------------------------------------------------- pin flops (stage 0)
    reg [NP-1:0] q_v; reg [NP*128-1:0] q_d; reg [3:0] q_f; reg [2:0] q_o;
    always @(posedge clk) begin
        if (!rn_i) begin q_v <= {NP{1'b0}}; q_f <= 4'd0; end else begin q_v <= o_v; q_f <= o_f; end
        q_d <= o_d; q_o <= o_o;
    end
    always @(posedge clk) sst <= {q_o, q_f, q_v};
    // control pin flops (v3: in the parent) + KX alignment relays -> xc / pm exactly as the v3 parent delivered them
    reg c_fv, c_rdy; reg [19:0] c_xm; reg [22:0] c_fm; reg [15:0] c_fe;
    // the control pin flops + KX line are a pure delay line WITHOUT reset (as v3's relays): the die's rn reaches the
    // tile DR stages after the die synchroniser, so a reset here would drop requests issued in that window whose read
    // data arrives after rn_i (v3 reset its pin flops on the earlier parent rn0); the reset hold (>= MD + 1 cycles of
    // running clock, inputs idle) flushes the line
    always @(posedge clk) begin
        if (!rn_i) c_fe <= 16'd0; else c_fe <= fe_flt;
        c_fv <= f_v5[0] && !f_we5[0]; c_xm <= f_mx; c_fm <= f_m5s;
    end
    reg [4:0] c_xv5;
    always @(posedge clk) c_xv5 <= f_vx & ~f_wex;
    reg [24:0] xl [0:KX-1]; reg [23:0] pl_ [0:KX-1];
    always @(posedge clk) begin : p_kx integer i;
        xl[0] <= {c_xm, c_xv5}; pl_[0] <= {c_fm, c_fv};
        for (i = 1; i < KX; i = i + 1) begin xl[i] <= xl[i-1]; pl_[i] <= pl_[i-1]; end
    end
    wire [24:0] xc = xl[KX-1]; wire [23:0] pm = pl_[KX-1];
    always @(posedge clk) c_rdy <= c_l0r[0];   // ready pin flop
    // ---------------------------------------------------------------- t_srq slice (no data reset)
    always @(posedge clk) begin
        if (!rn_w) srq_v <= 2'b00; else srq_v <= q_v[1:0];
        srq_d <= q_d[255:0];
    end
    // ---------------------------------------------------------------- control lines (XT stages, aligned with stage 0)
    reg [XT-1:0] xd_v [0:4]; reg [3:0] xd_m [0:4][0:XT-1];
    reg [XT-1:0] pd_v; reg [22:0] pd_m [0:XT-1];
    always @(posedge clk) begin : p_xd integer xi, xj;
        for (xi = 0; xi < 5; xi = xi + 1) begin
            if (!rn_x) xd_v[xi] <= {XT{1'b0}}; else xd_v[xi] <= {xd_v[xi][XT-2:0], xc[xi]};
            xd_m[xi][0] <= xc[5 + 4*xi +: 4];
            for (xj = 1; xj < XT; xj = xj + 1) xd_m[xi][xj] <= xd_m[xi][xj-1];
        end
        if (!rn_p) pd_v <= {XT{1'b0}}; else pd_v <= {pd_v[XT-2:0], pm[0]};
        pd_m[0] <= pm[23:1];
        for (xj = 1; xj < XT; xj = xj + 1) pd_m[xj] <= pd_m[xj-1];
    end
    // ---------------------------------------------------------------- X returns -> bus lanes
    function automatic integer xport(input integer x);
        begin xport = (x == 0) ? 6 : (x == 1) ? 7 : (x == 2) ? 2 : (x == 3) ? 8 : 9; end
    endfunction
    reg [4:0] xsel [0:15]; reg xmis_n, xcol_n;
    always @* begin : p_xsel integer l, x; reg [15:0] seen;
        seen = 16'd0; xmis_n = 1'b0; xcol_n = 1'b0;
        for (l = 0; l < 16; l = l + 1) xsel[l] = 5'd0;
        for (x = 0; x < 5; x = x + 1) begin
            if (xd_v[x][XT-1] != q_v[xport(x)]) xmis_n = 1'b1;
            if (xd_v[x][XT-1]) begin
                if (seen[xd_m[x][XT-1]]) xcol_n = 1'b1;
                seen[xd_m[x][XT-1]] = 1'b1;
            end
        end
        for (l = 0; l < 16; l = l + 1)
            for (x = 0; x < 5; x = x + 1) if (xd_v[x][XT-1] && xd_m[x][XT-1] == l[3:0]) xsel[l] = 5'd1 << x;
    end
    reg [15:0] tv;
    always @(posedge clk) begin : p_tv integer l;
        if (!rn_x) tv <= 16'd0; else for (l = 0; l < 16; l = l + 1) tv[l] <= |xsel[l];
    end
    wire [5*128-1:0] xrow = {q_d[9*128 +: 128], q_d[8*128 +: 128], q_d[2*128 +: 128], q_d[7*128 +: 128], q_d[6*128 +: 128]};
    wire [5*128-1:0] xb [0:NG-1];
    genvar gg, gl;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_xb
        dsfd_vm_be_kreg #(.W(5*128), .ID(16 + gg)) u_xb (.clk(clk), .d(xrow), .q(xb[gg]));
    end endgenerate
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_bl
        wire [4:0] s;
        dsfd_vm_be_kreg #(.W(5), .ID(32 + gl)) u_s (.clk(clk), .d(xsel[gl]), .q(s));
        always @(posedge clk) begin : p_o integer x; reg [127:0] a;
            if (!rn_x) bl_v[gl] <= 1'b0; else bl_v[gl] <= tv[gl];
            a = 128'd0;
            for (x = 0; x < 5; x = x + 1) a = a | (xb[gl/4][128*x +: 128] & {128{s[x]}});
            bl_d[128*gl +: 128] <= a;
        end
    end endgenerate
    // ---------------------------------------------------------------- ctrl read return: p3 then p4 -> 2 CDC FIFOs
    reg [NC-1:0] w_nx; reg [1:0] wq_v; reg [127:0] wq_d0, wq_d1; reg r_ovf_n;
    wire [NC-1:0] cv3, cv4;
    generate for (gg = 0; gg < NC; gg = gg + 1) begin : g_cv
        dsfd_vm_be_kreg #(.W(2), .ID(48 + gg)) u_cv (.clk(clk), .d(rn_i ? o_v[4:3] : 2'b00), .q({cv4[gg], cv3[gg]}));
    end endgenerate
    wire [1:0] rw_rdy, rr_v, o_vr; wire [127:0] o_d0, o_d1; wire [NC-1:0] o_vc0, o_vc1; reg rr_nx;
    always @(posedge clk) begin : p_cw integer c; reg p0, p1, pa_, pb_, nx;
        for (c = 0; c < NC; c = c + 1) begin
            p0 = cv3[c]; p1 = cv4[c]; pa_ = p0 | p1; pb_ = p0 & p1; nx = w_nx[c];
            wq_d0[64*c +: 64] <= (pa_ && !nx && p0) ? q_d[3*128 + 64*c +: 64] : q_d[4*128 + 64*c +: 64];
            wq_d1[64*c +: 64] <= (pa_ && nx && p0) ? q_d[3*128 + 64*c +: 64] : q_d[4*128 + 64*c +: 64];
            if (!rn_c) w_nx[c] <= 1'b0; else if (pa_ && !pb_) w_nx[c] <= ~nx;
        end
        p0 = q_v[3]; p1 = q_v[4]; pa_ = p0 | p1; pb_ = p0 & p1; nx = w_nx[0];
        if (!rn_c) begin wq_v <= 2'b00; r_ovf_n <= 1'b0; end
        else begin
            wq_v <= {(pa_ && nx) || (pb_ && !nx), (pa_ && !nx) || (pb_ && nx)};
            r_ovf_n <= (wq_v[0] && !rw_rdy[0]) || (wq_v[1] && !rw_rdy[1]);
        end
    end
    wire [1:0] rtk = {rr_v[1] && rr_nx, rr_v[0] && !rr_nx};
    dsfd_vm_be_rcdc #(.W(128), .DEPTH(8), .HOLD(2), .NC(NC), .IDB(100)) u_rc0 (.wclk(clk), .wrst_n(rn_c), .w_v(wq_v[0]),
        .w_rdy(rw_rdy[0]), .w_d(wq_d0), .rclk(sclk), .rrst_n(rns), .r_v(rr_v[0]), .r_rdy(rtk[0]),
        .o_v(o_vr[0]), .o_d(o_d0), .o_vc(o_vc0)
`ifdef OT_SPVM_RESET_ACK
        , .w_online(cdc_w_online[0]), .r_online(cdc_r_online[0])
`endif
        );
    dsfd_vm_be_rcdc #(.W(128), .DEPTH(8), .HOLD(2), .NC(NC), .IDB(200)) u_rc1 (.wclk(clk), .wrst_n(rn_c), .w_v(wq_v[1]),
        .w_rdy(rw_rdy[1]), .w_d(wq_d1), .rclk(sclk), .rrst_n(rns), .r_v(rr_v[1]), .r_rdy(rtk[1]),
        .o_v(o_vr[1]), .o_d(o_d1), .o_vc(o_vc1)
`ifdef OT_SPVM_RESET_ACK
        , .w_online(cdc_w_online[1]), .r_online(cdc_r_online[1])
`endif
        );
    always @(posedge sclk) begin : p_vr integer c;
        if (!rns) begin rr_nx <= 1'b0; vrv <= 1'b0; end
        else begin
            vrv <= |o_vr;
            if (|rtk) rr_nx <= ~rr_nx;
        end
        for (c = 0; c < NC; c = c + 1) vrq[64*c +: 64] <= o_vc1[c] ? o_d1[64*c +: 64] : o_d0[64*c +: 64];
    end
    // ---------------------------------------------------------------- P2 flit FIFO (this slice: 23 metadata + 128 data bits)
    // every flit is written (no bypass: no ready / reset in the write enables); 2 column chunks, each with kept copies of
    // the next write / read one-hot, push and non-empty flag.  READY-LATENCY output (BE S-FACE CONTRACT v3): the ready is
    // registered here (rq) after the parent's pin flop + relay, a beat is loaded when rq and the FIFO is non-empty and
    // leaves on c_l0v the next cycle; every c_l0v beat is a transfer (c_l0v(t) only if c_l0r(t - 4) at the BE pin).
    localparam integer PB = $clog2(P2D);
    localparam integer FW = 151, PC = 2, PCB = 76;
    wire mv = q_v[5];
    wire mv_nx = rn_i && o_v[5];
    wire [FW-1:0] flit = {pd_m[XT-1], q_d[5*128 +: 128]};
    reg [PB-1:0] ph, pt; reg [PB:0] pn; reg ov; reg p_ovf_n, p_mis_n; reg rq;
    always @(posedge clk) if (!rn_p) rq <= 1'b0; else rq <= c_rdy;
`ifdef OT_SPVM_MUT_RLAT
    wire rdy = c_rdy;                   // mutant: honours the ready one cycle early (beats the consumer did not grant)
`else
    wire rdy = rq;
`endif
    wire ld = rdy && (pn != 0);
    assign c_l0v = ov;
    wire [PB-1:0] pt_nx = !rn_p ? {PB{1'b0}} : mv ? ((pt == P2D - 1) ? {PB{1'b0}} : pt + 1'b1) : pt;
    wire [PB-1:0] ph_nx = !rn_p ? {PB{1'b0}} : ld ? ((ph == P2D - 1) ? {PB{1'b0}} : ph + 1'b1) : ph;
    wire [PB:0]   pn_nx = !rn_p ? {(PB+1){1'b0}} : pn + mv - ld;
    wire          ov_nx = rn_p && ld;
    wire [P2D-1:0] pw_oh = {{(P2D-1){1'b0}}, 1'b1} << pt_nx;
    wire [P2D-1:0] pr_oh = {{(P2D-1){1'b0}}, 1'b1} << ph_nx;
    genvar gp;
    generate for (gp = 0; gp < PC; gp = gp + 1) begin : g_pf
        localparam integer O = PCB * gp;
        localparam integer CWD = (gp == PC - 1) ? FW - PCB * (PC - 1) : PCB;
        wire [P2D-1:0] wo, ro; wire mvc, rqc, pec;
        dsfd_vm_be_kreg #(.W(2*P2D + 3), .ID(64 + gp)) u_pc (.clk(clk), .d({pw_oh, pr_oh, mv_nx, rn_p && c_rdy, pn_nx != 0}),
            .q({wo, ro, mvc, rqc, pec}));
`ifdef OT_SPVM_MUT_RLAT
        wire ldc = c_rdy && pec;
`else
        wire ldc = rqc && pec;                             // = ld
`endif
        reg [CWD-1:0] pf [0:P2D-1]; reg [CWD-1:0] q;
        always @(posedge clk) begin : p_w integer i;
            for (i = 0; i < P2D; i = i + 1) if (mvc && wo[i]) pf[i] <= flit[O +: CWD];
        end
        always @(posedge clk) begin : p_r integer i; reg [CWD-1:0] a;
            a = {CWD{1'b0}};
            for (i = 0; i < P2D; i = i + 1) a = a | (pf[i] & {CWD{ro[i]}});
            if (ldc) q <= a;
        end
        assign c_l0d[O +: CWD] = q;
    end endgenerate
    always @(posedge clk) begin
        if (!rn_p) begin ph <= 0; pt <= 0; pn <= 0; ov <= 1'b0; t_p2c <= 1'b0; p_ovf_n <= 1'b0; p_mis_n <= 1'b0; end
        else begin
            pt <= pt_nx; ph <= ph_nx; pn <= pn_nx; ov <= ov_nx;
            t_p2c <= ov;                    // every c_l0v beat is a transfer
            p_ovf_n <= mv && pn == P2D;
            p_mis_n <= pd_v[XT-1] != mv;
        end
    end
    reg x_mis_r, x_col_r;
    always @(posedge clk) begin
        if (!rn_w) begin x_mis_r <= 1'b0; x_col_r <= 1'b0; sflt <= 5'd0; end
        else begin
            x_mis_r <= xmis_n; x_col_r <= xcol_n;
            sflt <= {x_col_r, x_mis_r, r_ovf_n, p_mis_n, p_ovf_n};
        end
    end
    // ---------------------------------------------------------------- status chain (v4: replaces the parent's combine)
    // st_i pin flop; the neighbour's sst arrives 2 cycles old (its st_o register + this pin flop) and is compared with
    // this slice's sst delayed 2 (lockstep slices: equal every cycle); OR-accumulate faults; sticky status per slice.
    reg [39:0] st_r; reg [16:0] sst_d1, sst_d2;
    always @(posedge clk) begin st_r <= st_i; sst_d1 <= sst; sst_d2 <= sst_d1; end
    wire [4:0] c_sf = st_r[5:1] | sflt;
    wire c_mis = st_r[6] | (st_r[0] && st_r[20:7] != sst_d2[13:0]);
    wire [15:0] c_fe2 = st_r[39:24] | c_fe;
    always @(posedge clk) begin
        if (!rn_w) st_o <= 40'd0;
        else st_o <= {c_fe2, sst, c_mis, c_sf, 1'b1};
    end
    reg [31:0] fv;
    always @(posedge clk) begin
        if (!rn_w) begin flt <= 1'b0; fvec <= 32'd0; t_err <= 1'b0; max_occ <= 3'd0; end
        else begin
            // [3:0] memory {fault, und, mis, ovf | write-only read}; [19:4] FE vector; [20] P2 FIFO overflow;
            // [21] P2 metadata misalignment; [22] slice mismatch; [23] ctrl return overflow; [24] X misalignment; [25] X collision
            fv = {6'd0, c_sf[4], c_sf[3], c_sf[2], c_mis, c_sf[1], c_sf[0], c_fe2, sst_d2[13:10]};
            fvec <= fvec | fv;
            flt <= flt | (|fv);
            t_err <= t_err | (|fv);
            max_occ <= (sst_d2[16:14] > max_occ) ? sst_d2[16:14] : max_occ;
        end
    end
endmodule

// ------------------------------------------------------------------------------------------------ back end (composition)
// dsfd_vm_be v4 (GLUE PLACEMENT rule, el1011-ds-vm/be-sl4): NO parent element.  The 4 hardened slices dsfd_vm_be_sl are
// placed by the die; this module is the RTL composition the bench runs: 4 slices + the die-top glue modelled
// behaviourally (die reset synchronisers + DR equal-length reset relays, DIE_D = 3 control relay stages per slice,
// 1 c_l0r relay stage per slice, abutting W->E status chain, slice 3's sticky status = the BE status outputs).
// Latency vs v3: responses +0, P2 ready latency 4 (1 die relay + 3 in the slice), status +2..+5 cycles (chain).
module dsfd_vm_be #(
    parameter integer NS = 4,
    parameter integer P2D = 40,         // P2 flit FIFO depth (the FE reader's credits)
    parameter integer MD = 9,           // tile-3 f_* (request exit) -> o_* (read data) skew
    parameter integer XT = 2,           // control stages inside a slice tile
    parameter integer DR = 3,           // reset / status relay stages (each tile alike)
    parameter integer HARD_RELAYS = 0    // opt-in fixed hard masters, exact same stages
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,
    input  wire [0:0]          cks,      // stream clock / reset (ctrl read return)
    input  wire [0:0]          rss,
    input  wire [NS*10-1:0]    o_v,
    input  wire [NS*10*128-1:0] o_d,
    input  wire [NS*4-1:0]     o_f,
    input  wire [NS*3-1:0]     o_o,
    input  wire [0:0]          f_v5,
    input  wire [0:0]          f_we5,
    input  wire [91:0]         f_m5,
    input  wire [4:0]          f_vx,
    input  wire [4:0]          f_wex,
    input  wire [19:0]         f_mx,
    input  wire [15:0]         fe_flt,
    output wire [1025:0]       t_srq,
    output reg  [0:0]          t_err,
    output wire [0:0]          vrv,
    output wire [511:0]        vrq,
    output wire [16*513-1:0]   t_bl,
    output wire [0:0]          c_l0v,
    output wire [603:0]        c_l0d,
    input  wire [0:0]          c_l0r,
    output wire [0:0]          t_p2c,
    output reg  [0:0]          flt,
    output reg  [31:0]         fvec,
    output reg  [2:0]          max_occ
`ifdef OT_SPVM_RESET_ACK
    , output wire [NS-1:0] rst_ack, rst_ack_s
`endif
);
    localparam integer KX = 4;          // dsfd_vm_be_sl in-tile alignment relays
    localparam integer DIE_D = MD - KX - XT;   // die control relay stages (DIE_D + 1 + KX + XT = MD + 1, as v3's 1 + R + XT)
    initial if (NS != 4 || DIE_D < 1 || XT != 2 || P2D != 40) $error("dsfd_vm_be: NS 4, XT 2, P2D 40 (the hardened slice tile), MD >= 7");
    wire clk = ck[0];
    wire rn0, rns0;
    // die glue: reset synchronisers (one each, at the die), equal-length relays to every slice
    generate if (HARD_RELAYS != 0) begin : g_hrst
        dsfd_die_rstsync u_rs (.ck(clk), .rst(rst[0]), .rn(rn0));
        dsfd_die_rstsync u_rss (.ck(cks[0]), .rst(rss[0]), .rn(rns0));
    end else begin : g_rst
        ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn0));
        ot_dsrom_mtp_rstsync u_rss (.clk(cks[0]), .rst_n_async(rss[0]), .rst_n(rns0));
    end endgenerate
    wire [255:0] srq_d [0:NS-1]; wire [1:0] srq_v [0:NS-1]; wire [NS-1:0] vrv_s, c_l0v_s, t_p2c_s;
    wire [127:0] vrq_s [0:NS-1]; wire [16*128-1:0] bl_d [0:NS-1]; wire [15:0] bl_v [0:NS-1];
    wire [150:0] p2_s [0:NS-1]; wire [39:0] st [0:NS];
    wire [NS-1:0] terr_s, flt_s; wire [31:0] fvec_s [0:NS-1]; wire [2:0] mocc_s [0:NS-1];
    assign st[0] = 40'd0;               // chain head
    genvar gs, gl;
    generate for (gs = 0; gs < NS; gs = gs + 1) begin : g_s
        // die-top relays (behavioural): DR reset stages, DIE_D control stages, 1 c_l0r stage, all equal per slice
        wire [DR-1:0] rnc, rns_;
        wire [4:0] dvx [0:DIE_D-1]; wire [4:0] dwx [0:DIE_D-1]; wire [19:0] dmx [0:DIE_D-1];
        wire dv5 [0:DIE_D-1]; wire dw5 [0:DIE_D-1]; wire [22:0] dm5 [0:DIE_D-1]; wire rr;
        if (HARD_RELAYS != 0) begin : g_hard
            wire [54:0] ctl [0:DIE_D];
            assign ctl[0] = {f_vx, f_wex, f_mx, f_v5[0], f_we5[0], f_m5[23*gs +: 23]};
            for (genvar ri=0; ri<DIE_D; ri=ri+1) begin : g_ctl
                dsfd_be_r55 u_r (.ck(clk), .i(ctl[ri]), .o(ctl[ri+1]));
                assign {dvx[ri],dwx[ri],dmx[ri],dv5[ri],dw5[ri],dm5[ri]}=ctl[ri+1];
            end
            for (genvar ri=0; ri<DR; ri=ri+1) begin : g_rst
                dsfd_die_r1 u_c (.ck(clk), .i(ri==0 ? rn0 : rnc[ri==0 ? 0 : ri-1]), .o(rnc[ri]));
                dsfd_die_r1 u_s (.ck(cks[0]), .i(ri==0 ? rns0 : rns_[ri==0 ? 0 : ri-1]), .o(rns_[ri]));
            end
            dsfd_die_r1 u_ready (.ck(clk), .i(c_l0r[0]), .o(rr));
        end else begin : g_flat
        reg [DR-1:0] rnc_q, rns_q;
        reg [4:0] dvx_q [0:DIE_D-1]; reg [4:0] dwx_q [0:DIE_D-1]; reg [19:0] dmx_q [0:DIE_D-1];
        reg dv5_q [0:DIE_D-1]; reg dw5_q [0:DIE_D-1]; reg [22:0] dm5_q [0:DIE_D-1]; reg rr_q;
        always @(posedge clk) begin : p_rl integer i;
            rnc_q <= {rnc_q[DR-2:0], rn0};
            rr_q <= c_l0r[0];
            dvx_q[0] <= f_vx; dwx_q[0] <= f_wex; dmx_q[0] <= f_mx; dv5_q[0] <= f_v5[0]; dw5_q[0] <= f_we5[0]; dm5_q[0] <= f_m5[23*gs +: 23];
            for (i = 1; i < DIE_D; i = i + 1) begin
                dvx_q[i] <= dvx_q[i-1]; dwx_q[i] <= dwx_q[i-1]; dmx_q[i] <= dmx_q[i-1]; dv5_q[i] <= dv5_q[i-1]; dw5_q[i] <= dw5_q[i-1]; dm5_q[i] <= dm5_q[i-1];
            end
        end
        always @(posedge cks[0]) rns_q <= {rns_q[DR-2:0], rns0};
            assign rnc=rnc_q; assign rns_=rns_q; assign rr=rr_q;
            for (genvar ri=0; ri<DIE_D; ri=ri+1) begin : g_o
                assign dvx[ri]=dvx_q[ri]; assign dwx[ri]=dwx_q[ri]; assign dmx[ri]=dmx_q[ri];
                assign dv5[ri]=dv5_q[ri]; assign dw5[ri]=dw5_q[ri]; assign dm5[ri]=dm5_q[ri];
            end
        end
        dsfd_vm_be_sl u_sl (                // hard macro at its defaults (P2D 40, XT 2): no parameter overrides
            .ck(ck), .cks(cks), .rn_in(rnc[DR-1]), .rns_in(rns_[DR-1]),
            .o_v(o_v[10*gs +: 10]), .o_d(o_d[1280*gs +: 1280]), .o_f(o_f[4*gs +: 4]), .o_o(o_o[3*gs +: 3]),
            .f_vx(dvx[DIE_D-1]), .f_wex(dwx[DIE_D-1]), .f_mx(dmx[DIE_D-1]), .f_v5(dv5[DIE_D-1]), .f_we5(dw5[DIE_D-1]),
            .f_m5s(dm5[DIE_D-1]), .c_l0r(rr), .fe_flt(gs == 0 ? fe_flt : 16'd0), .st_i(st[gs]), .st_o(st[gs+1]),
            .srq_d(srq_d[gs]), .srq_v(srq_v[gs]), .vrv(vrv_s[gs]), .vrq(vrq_s[gs]), .bl_d(bl_d[gs]), .bl_v(bl_v[gs]),
            .c_l0v(c_l0v_s[gs]), .c_l0d(p2_s[gs]), .t_p2c(t_p2c_s[gs]),
            .t_err(terr_s[gs]), .flt(flt_s[gs]), .fvec(fvec_s[gs]), .max_occ(mocc_s[gs])
`ifdef OT_SPVM_RESET_ACK
            , .reset_epoch_n(rst[0]), .reset_epoch_s_n(rss[0])
            , .rst_ack(rst_ack[gs]), .rst_ack_s(rst_ack_s[gs])
`endif
            );
        // this slice's bits of every response (S-FACE CONTRACT v3/v4: at this tile's x range)
        assign t_srq[128*gs +: 128] = srq_d[gs][127:0];
        assign t_srq[513 + 128*gs +: 128] = srq_d[gs][255:128];
        assign vrq[128*gs +: 128] = vrq_s[gs];
        assign c_l0d[128*gs +: 128] = p2_s[gs][127:0];
        assign c_l0d[512 + 23*gs +: 23] = p2_s[gs][150:128];
        for (gl = 0; gl < 16; gl = gl + 1) begin : g_l
            assign t_bl[513*gl + 1 + 128*gs +: 128] = bl_d[gs][128*gl +: 128];
        end
    end endgenerate
    // lockstep control outputs from one slice next to their pins
    assign t_srq[512] = srq_v[0][0]; assign t_srq[1025] = srq_v[0][1];
    assign vrv = vrv_s[0];
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_bv
        assign t_bl[513*gl] = bl_v[0][gl];
    end endgenerate
    assign c_l0v = c_l0v_s[1];
    assign t_p2c = t_p2c_s[NS-1];
    // status = the chain tail (slice NS-1)
    always @* begin t_err = terr_s[NS-1]; flt = flt_s[NS-1]; fvec = fvec_s[NS-1]; max_occ = mocc_s[NS-1]; end
endmodule

// ================================================================================================ composition
// dsfd_sp_vm_m: the exact composition netlist (bench + composition record): FE, NS x 4 dsfd_vm_bgq (NSTG 2, NP 24,
// NPR 8), BE.  The die places the FE, the 16 tiles and the BE by abutment (physical/s81_ph_views/vm_master/).
module dsfd_sp_vm_m #(
    parameter integer WCOMMIT = 0,
    parameter integer BANK_XOR = 0,
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
    output wire         vready,
    input wire [15:0] vwm, input wire [7:0] vwt,
    output wire vwv, output wire [7:0] vack_tag, output wire [15:0] vack_mask,
    input  wire [0:0]    cv, input wire [83:0] cd, output wire [0:0] dv, output wire [7:0] dt,
    input  wire [NSVC*1027-1:0] f_svc, input wire [2099:0] f_coll, output wire [2:0] t_cts,
    input  wire [514:0]  f_sel, input wire [514:0] f_col, input wire [1025:0] f_hc,
    output wire [16*513-1:0] t_bl,
    output wire [0:0]    c_wv, output wire [9:0] c_wd, input wire [0:0] c_wr,
    output wire [NSLOT-1:0] t_rdy,
    output wire [0:0]    c_l0v, output wire [603:0] c_l0d, input wire [0:0] c_l0r,
    output wire [0:0]    flt, output wire [31:0] fvec, output wire [2:0] max_occ
`ifdef OT_SPVM_RESET_ACK
    , output wire [40+24*`VMFE_R:0] fe_rst_ack
    , output wire [3:0] fe_rst_ack_s
    , output wire [NS-1:0] be_rst_ack, be_rst_ack_s
    , output wire [NS*4-1:0] bank_rst_ack
`endif
);
`ifdef OT_SPVM_RESET_ACK
`ifndef OT_SPVM_FE_H_SUBST
    initial $error("VM reset ACK candidate requires actual selected FE_H_SUBST consumers");
    assign fe_rst_ack = '0; assign fe_rst_ack_s = '0;
`endif
`endif
    localparam integer NP = 28, NPR = 10, NT = 4, RA = 14, OW = 3;
    // el1011-ds-vm/bgq28: the hard tile's enqueue pipeline (EP, = dsfd_vm_bgq28) adds ED = EP + 1 cycles to every op
`ifdef OT_VM28_EP1
    localparam integer EP = 1;
`else
    localparam integer EP = 2;
`endif
    localparam integer ED = (EP == 0) ? 0 : EP + 1;
`ifdef OT_SPVM_REF_FRL
    `include "dsfd_vm_fe_h_if.svh"
    // the hierarchy's stage counts (lockstep reference)
    localparam integer FRL = `VMFE_FRL, FKD = `VMFE_KD, FLDL = `VMFE_LDL, FLGL = `VMFE_LGL, FLAL = `VMFE_LAL, FDVR = `VMFE_DVR, FLVX = `VMFE_LVX, FXRT = `VMFE_XRT, FCCA = `VMFE_CCA;
`else
    localparam integer FRL = 2, FKD = 1, FLDL = 2, FLGL = 2, FLAL = 2, FDVR = 0, FLVX = 0, FXRT = 0, FCCA = 0;
`endif
                                        // el1011-ds-vm/fe: FE order register -> slice pin relay stages (shifts f_* and o_*
                                        // alike: MD, the tile-3 f_* -> o_* skew, is unchanged)
    localparam integer MD = 4 * NSTG + QD + 9 - 4 * (NSTG + 1) + ED;
    wire [15:0] mtag; wire [NS*NT*8*28-1:0] commits;
    wire [NS*NP-1:0] mv, mwe; wire [NS*NP*RA-1:0] mrow; wire [NS*NP*4-1:0] mm; wire [NS*NP*128-1:0] md;
    wire [NS*4-1:0] mrf; wire [15:0] fe_flt;
    wire p2c;
    wire [NS*NP-1:0] fmv, fmwe; wire [NS*NP*RA-1:0] fmrow; wire [NS*NP*4-1:0] fmm; wire [NS*NP*128-1:0] fmd;
    wire [NS*4-1:0] fmrf; wire [15:0] f_flt;
    wire [0:0] f_swg, f_srg, f_dv, f_cwv; wire [52:0] f_ks; wire [7:0] f_dt; wire [2:0] f_cts; wire [9:0] f_cwd; wire [NSLOT-1:0] f_rdy;
    dsfd_vm_fe #(.BANK_XOR(BANK_XOR), .WCOMMIT(WCOMMIT), .NS(NS), .VF(VF), .VR(VR), .NSLOT(NSLOT), .P2D(P2D), .CQD(CQD), .LA(LA), .LTO(LTO), .NSVC(NSVC), .LD(LD),
                 .NLP(NLP), .LMACRO(LMACRO), .FRL(FRL), .KD(FKD), .LAL(FLAL), .LGL(FLGL), .LDL(FLDL), .DVR(FDVR), .LVX(FLVX), .XRT(FXRT), .CCA(WCOMMIT ? 1 : FCCA)) u_fe (
        .ck(ck), .rst(rst), .cks(cks), .rss(rss), .f_swv(f_swv), .f_swd(f_swd), .t_swg(f_swg), .f_srv(f_srv), .f_srd(f_srd),
        .t_srg(f_srg), .t_ks(f_ks), .f_cap(f_cap), .vwe(vwe), .vwa(vwa), .vwd(vwd), .vre(vre), .vra(vra), .vready(vready), .vwm(vwm), .vwt(vwt), .m_wtag(mtag),
        .cv(cv), .cd(cd), .dv(f_dv), .dt(f_dt), .f_svc(f_svc), .f_coll(f_coll), .t_cts(f_cts), .f_sel(f_sel), .f_col(f_col), .f_hc(f_hc),
        .c_wv(f_cwv), .c_wd(f_cwd), .c_wr(c_wr), .t_rdy(f_rdy), .f_p2c(p2c),
        .m_v(fmv), .m_we(fmwe), .m_row(fmrow), .m_mask(fmm), .m_d(fmd), .m_rf(fmrf), .fe_flt(f_flt));
`ifdef OT_SPVM_FE_H
    // The hierarchy dsfd_vm_fe_h on the SAME FE inputs.  OT_SPVM_FE_H alone: shadow (the flat reference drives the system);
    // with OT_SPVM_FE_H_SUBST: SUBSTITUTED (the hierarchy drives every FE output; the flat instance stays as the bench's order-register probe
    // and lockstep reference).  Needs OT_SPVM_REF_FRL (same stage counts).
    wire [NS*NP-1:0] hmv, hmwe; wire [NS*NP*RA-1:0] hmrow; wire [NS*NP*4-1:0] hmm; wire [NS*NP*128-1:0] hmd;
    wire [NS*4-1:0] hmrf; wire [15:0] h_flt;
    wire [0:0] h_swg, h_srg, h_dv, h_cwv; wire [52:0] h_ks; wire [7:0] h_dt; wire [2:0] h_cts; wire [9:0] h_cwd; wire [3:0] h_rdy;
    dsfd_vm_fe_h #(.BANK_XOR(BANK_XOR)) u_feh (
        .ck(ck), .rst(rst), .cks(cks), .rss(rss), .f_swv(f_swv), .f_swd(f_swd), .t_swg(h_swg), .f_srv(f_srv), .f_srd(f_srd),
        .t_srg(h_srg), .t_ks(h_ks), .f_cap(f_cap), .vwe(vwe), .vwa(vwa), .vwd(vwd), .vre(vre), .vra(vra),
        .cv(cv), .cd(cd), .dv(h_dv), .dt(h_dt), .f_svc(f_svc), .f_coll(f_coll), .t_cts(h_cts), .f_sel(f_sel), .f_col(f_col), .f_hc(f_hc),
        .c_wv(h_cwv), .c_wd(h_cwd), .c_wr(c_wr), .t_rdy(h_rdy), .f_p2c(p2c),
        .m_v(hmv), .m_we(hmwe), .m_row(hmrow), .m_mask(hmm), .m_d(hmd), .m_rf(hmrf), .fe_flt(h_flt)
`ifdef OT_SPVM_RESET_ACK
        , .rst_ack(fe_rst_ack), .rst_ack_s(fe_rst_ack_s)
`endif
        );
`endif
`ifdef OT_SPVM_FE_H_SUBST
    initial if(WCOMMIT)$error("native FE true commit/tag hierarchy still requires its explicit leaf variant");
    assign mv = hmv; assign mwe = hmwe; assign mrow = hmrow; assign mm = hmm; assign md = hmd; assign mrf = hmrf;
    assign fe_flt = h_flt; assign t_swg = h_swg; assign t_srg = h_srg; assign t_ks = h_ks; assign dv = h_dv; assign dt = h_dt;
    assign t_cts = h_cts; assign c_wv = h_cwv; assign c_wd = h_cwd; assign t_rdy = h_rdy;
`else
    assign mv = fmv; assign mwe = fmwe; assign mrow = fmrow; assign mm = fmm; assign md = fmd; assign mrf = fmrf;
    assign fe_flt = f_flt; assign t_swg = f_swg; assign t_srg = f_srg; assign t_ks = f_ks; assign dv = f_dv; assign dt = f_dt;
    assign t_cts = f_cts; assign c_wv = f_cwv; assign c_wd = f_cwd; assign t_rdy = f_rdy;
`endif
    wire [NS*NPR-1:0] ov; wire [NS*NPR*128-1:0] od; wire [NS*4-1:0] of; wire [NS*3-1:0] oo;
    wire [NP-1:0] f0v, f0we; wire [NP*128-1:0] f0d;
    genvar h, t;
    generate for (h = 0; h < NS; h = h + 1) begin : g_h
        wire [NP-1:0] cv_ [0:NT], cwe [0:NT];
        wire [NPR-1:0] cov [0:NT];
        wire [NP*RA-1:0] crow [0:NT]; wire [NP*4-1:0] cm [0:NT]; wire [NP*128-1:0] cd_ [0:NT];
        wire [NPR*128-1:0] cod [0:NT];
        wire [15:0] tags[0:NT];
        assign tags[0]=mtag;
        wire [3:0] cof [0:NT]; wire [OW-1:0] coo [0:NT];
        assign cv_[0] = mv[h*NP +: NP]; assign cwe[0] = mwe[h*NP +: NP]; assign crow[0] = mrow[h*NP*RA +: NP*RA];
        assign cm[0] = mm[h*NP*4 +: NP*4]; assign cd_[0] = md[h*NP*128 +: NP*128];
        // chain head: no upstream tile (no read data, occupancy 0); the FE status enters on the fault lane
        assign cov[0] = {NPR{1'b0}}; assign cod[0] = {NPR*128{1'b0}}; assign cof[0] = mrf[h*4 +: 4];
        assign coo[0] = {OW{1'b0}};
        for (t = 0; t < NT; t = t + 1) begin : g_t
            wire [1:0] gid = t;
`ifdef OT_SPVM_BGL
            // el1013-s81-bgq28: 8 one-bank leaves dsfd_vm_bgl28 under the wires-only dsfd_vm_bgq28h (hop 16, same
            // o_* -> f_* skew HL + 1, so MD and the BE are unchanged).  Fixed parameters: QD 4, EP 2.
            initial if (QD != 4 || EP != 2) $error("dsfd_sp_vm_m: dsfd_vm_bgq28h is QD 4 / EP 2");
            dsfd_vm_bgq28h u_bg (
                .ck(ck), .rs(rst), .grp(gid),
                .i_v(cv_[t]), .i_we(cwe[t]), .i_row(crow[t]), .i_mask(cm[t]), .i_d(cd_[t]),
                .f_v(cv_[t+1]), .f_we(cwe[t+1]), .f_row(crow[t+1]), .f_mask(cm[t+1]), .f_d(cd_[t+1]),
                .r_v(cov[t]), .r_d(cod[t]), .r_f(cof[t]), .r_o(coo[t]),
                .o_v(cov[t+1]), .o_d(cod[t+1]), .o_f(cof[t+1]), .o_o(coo[t+1]));
`else
            // = dsfd_vm_bgq28 (the hard tile) at the default parameters
            // v4 (el1011-ds-vm/bgq28 2026-10-12): dsfd_vm_bgr, 4 bank-pair stages + 2-stage control lead (hop 6); its
            // o_* -> f_* skew is HL + 1 = QD + 5 + ED, the MD below (NSTG-independent), so the BE is unchanged
            dsfd_vm_bgr #(.WCOMMIT(WCOMMIT), .NP(NP), .NPR(NPR), .NB(32), .NBL(8), .QD(QD), .RQ(8), .MACRO(MACRO), .DW(128), .NSTG(4), .EP(EP)) u_bg (
                .ck(ck), .rs(WCOMMIT ? (rst & rss) : rst), .grp(gid),
                .i_wtag(tags[t]), .f_wtag(tags[t+1]), .write_commit(commits[28*8*(h*NT+t)+:28*8]),
                .i_v(cv_[t]), .i_we(cwe[t]), .i_row(crow[t]), .i_mask(cm[t]), .i_d(cd_[t]),
                .f_v(cv_[t+1]), .f_we(cwe[t+1]), .f_row(crow[t+1]), .f_mask(cm[t+1]), .f_d(cd_[t+1]),
                .r_v(cov[t]), .r_d(cod[t]), .r_f(cof[t]), .r_o(coo[t]),
                .o_v(cov[t+1]), .o_d(cod[t+1]), .o_f(cof[t+1]), .o_o(coo[t+1])
`ifdef OT_SPVM_RESET_ACK
                , .reset_ack(bank_rst_ack[4*h+t])
`endif
                );
`endif
`ifdef OT_SPVM_BGTRACE
            // simulation only: the production request trace at the head of slice 0 (replayed by tb_dsfd_vm_bgl_lockstep)
            if (h == 0 && t == 0) begin : g_tr
                integer fd, cy;
                initial begin fd = $fopen("bg_trace.txt", "w"); cy = 0; end
                always @(posedge ck[0]) begin
                    cy <= cy + 1;
                    if (|cv_[0]) $fwrite(fd, "%0d %h %h %h %h %h\n", cy, cv_[0], cwe[0], crow[0], cm[0], cd_[0]);
                end
            end
`endif
        end
        assign ov[h*NPR +: NPR] = cov[NT]; assign od[h*NPR*128 +: NPR*128] = cod[NT]; assign of[h*4 +: 4] = cof[NT];
        assign oo[h*3 +: 3] = coo[NT];
        if (h == 0) begin : g_f
            assign f0v = cv_[NT]; assign f0we = cwe[NT]; assign f0d = cd_[NT];
        end
    end endgenerate
`ifdef OT_SPVM_BE_HARD_RELAYS
    localparam integer BEHR=1;
`else
    localparam integer BEHR=0;
`endif
    dsfd_vm_be #(.NS(NS), .P2D(P2D), .MD(MD), .HARD_RELAYS(BEHR)) u_be (
        .ck(ck), .rst(rst), .cks(cks), .rss(rss), .o_v(ov), .o_d(od), .o_f(of), .o_o(oo),
        .f_v5(f0v[5]), .f_we5(f0we[5]), .f_m5(f0d[5*128 +: 92]), .fe_flt(fe_flt),
        .f_vx({f0v[9], f0v[8], f0v[2], f0v[7], f0v[6]}), .f_wex({f0we[9], f0we[8], f0we[2], f0we[7], f0we[6]}),
        .f_mx({f0d[9*128 +: 4], f0d[8*128 +: 4], f0d[2*128 +: 4], f0d[7*128 +: 4], f0d[6*128 +: 4]}),
        .t_srq(t_srq), .t_err(t_err), .vrv(vrv), .vrq(vrq), .t_bl(t_bl),
        .c_l0v(c_l0v), .c_l0d(c_l0d), .c_l0r(c_l0r), .t_p2c(p2c), .flt(flt), .fvec(fvec), .max_occ(max_occ)
`ifdef OT_SPVM_RESET_ACK
        , .rst_ack(be_rst_ack), .rst_ack_s(be_rst_ack_s)
`endif
        );
    generate if(WCOMMIT) begin:g_commit
        dsfd_vm_write_ack #(.NS(NS),.NT(NT)) u_ack(.ck(ck[0]),.rst_n(rst[0]),.cks(cks[0]),.rss_n(rss[0]),
          .records(commits),.ack_v(vwv),.ack_tag(vack_tag),.ack_mask(vack_mask));
    end else begin:g_no_commit
        assign vwv=1'b0; assign vack_tag=0; assign vack_mask=0;
    end endgenerate

endmodule

module dsfd_vm_fsr_bank #(parameter integer BANK_XOR=0) (
    input  wire          ck,
    input  wire          rn,
    input  wire [27:0]   i_v,  input wire [27:0]  i_we, input wire [391:0] i_row, input wire [111:0] i_mask,
    input  wire [3583:0] i_d,  input wire [3:0]   i_rf,
    output wire  [27:0]   o_v,  output wire [27:0]  o_we, output wire [391:0] o_row, output wire [111:0] o_mask,
    output wire  [3583:0] o_d,  output wire [3:0]   o_rf
`ifdef OT_SPVM_RESET_ACK
    , input wire reset_epoch_n, output wire rst_ack
`endif
);
 generate if(BANK_XOR)begin:g_x dsfd_vm_fsr_xor u_native(.ck(ck), .rn(rn), .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_mask), .i_d(i_d), .i_rf(i_rf), .o_v(o_v), .o_we(o_we), .o_row(o_row), .o_mask(o_mask), .o_d(o_d), .o_rf(o_rf)
`ifdef OT_SPVM_RESET_ACK
, .reset_epoch_n(reset_epoch_n),.rst_ack(rst_ack)
`endif
);end else begin:g_n dsfd_vm_fsr u_native(.ck(ck), .rn(rn), .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_mask), .i_d(i_d), .i_rf(i_rf), .o_v(o_v), .o_we(o_we), .o_row(o_row), .o_mask(o_mask), .o_d(o_d), .o_rf(o_rf)
`ifdef OT_SPVM_RESET_ACK
, .reset_epoch_n(reset_epoch_n),.rst_ack(rst_ack)
`endif
);end endgenerate
endmodule
