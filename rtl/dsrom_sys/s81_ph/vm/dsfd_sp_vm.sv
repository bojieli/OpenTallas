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
// dsfd_vm_cl: one capture lane (8 roots = 16 element inputs a cycle).  LA fully associative row entries (key = round
// addr[17:8]; the lane fixes addr[7:4] = G): an element merges into the entry of its row, or allocates a free entry
// (several new rows a cycle are allocated in element order); with no free entry the oldest entry not touched this
// cycle is EVICTED (written as a partial row).  A row leaves its entry when full, when evicted, or LTO cycles after its
// last element; it goes to the lane's write queue (WQ entries, one move a cycle), which the lane's port drains one row a
// cycle.  Every element is written exactly once (a later element of a row that already left starts a new partial row).
// Faults (sticky): [0] alignment, [1] range, [2] allocation (a second eviction needed in one cycle), [3] write queue
// full at a needed eviction.
module dsfd_vm_cl #(
    parameter integer G = 0,            // lane index (static)
    parameter integer LA = 12,          // row entries
    parameter integer LTO = 16,         // partial-row timeout (cycles since last element)
    parameter integer WQ = 4            // write queue depth (power of 2)
) (
    input  wire          clk, rn,
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
    localparam integer LB = (LA > 1) ? $clog2(LA) : 1;
    localparam integer QB = (WQ > 1) ? $clog2(WQ) : 1;
    localparam integer AW = $clog2(LTO + 1);
    reg          e_v [0:LA-1];
    reg [9:0]    e_t [0:LA-1];
    reg [15:0]   e_m [0:LA-1];
    reg [511:0]  e_d [0:LA-1];
    reg [AW-1:0] e_a [0:LA-1];
    reg [9:0]    q_t [0:WQ-1];
    reg [15:0]   q_m [0:WQ-1];
    reg [511:0]  q_d [0:WQ-1];
    reg [QB-1:0] qh, qt; reg [QB:0] qn;
    // every procedural block below owns its loop indices and temporaries (no variable is written by two processes)
    // ---- element qualification
    reg [15:0] ok; reg f_al, f_rg;
    always @* begin : p_qual integer k;
        ok = 16'd0; f_al = 1'b0; f_rg = 1'b0;
        for (k = 0; k < 16; k = k + 1) if (ev[k]) begin
            if (ea[19*k + 18]) f_rg = 1'b1;
`ifndef OT_SPVM_MUT_NOALIGN
            else if (ea[19*k + 4 +: 4] != G[3:0]) f_al = 1'b1;
`endif
            else ok[k] = 1'b1;
        end
    end
    // ---- match / allocate (element order) / evict
    reg [LB-1:0] ix [0:15];             // entry of element k
    reg [15:0]   gk;                    // element k placed
    reg [LA-1:0] hitd;                  // entries touched by a matched element
    reg [LA-1:0] al;                    // entries (re)allocated this cycle
    reg [9:0]    at [0:LA-1];
    reg          evn, f_al2;            // an eviction is needed this cycle / a second one was needed
    reg [LB-1:0] evi;
    // (found / fi / best: locals of p_match)

    always @* begin : p_match integer k, e; reg found; reg [LB-1:0] fi; reg [AW-1:0] best;
        hitd = {LA{1'b0}}; al = {LA{1'b0}}; gk = 16'd0; evn = 1'b0; f_al2 = 1'b0; evi = {LB{1'b0}};
        for (e = 0; e < LA; e = e + 1) at[e] = 10'd0;
        for (k = 0; k < 16; k = k + 1) begin
            ix[k] = {LB{1'b0}};
            if (ok[k]) begin
                found = 1'b0; fi = {LB{1'b0}};
                for (e = LA - 1; e >= 0; e = e - 1)
                    if ((e_v[e] && !al[e] && e_t[e] == ea[19*k + 8 +: 10]) || (al[e] && at[e] == ea[19*k + 8 +: 10])) begin
                        found = 1'b1; fi = e[LB-1:0];
                    end
                if (found) begin
                    ix[k] = fi; gk[k] = 1'b1; if (!al[fi]) hitd[fi] = 1'b1;
                end else begin
                    for (e = LA - 1; e >= 0; e = e - 1) if (!e_v[e] && !al[e]) begin found = 1'b1; fi = e[LB-1:0]; end
                    if (!found && !evn) begin
                        // evict the oldest entry not touched this cycle
                        best = {AW{1'b0}};
                        for (e = 0; e < LA; e = e + 1)
                            if (e_v[e] && !hitd[e] && !al[e] && (!found || e_a[e] > best)) begin found = 1'b1; fi = e[LB-1:0]; best = e_a[e]; end
                        if (found) begin evn = 1'b1; evi = fi; end
                    end
                    if (found) begin al[fi] = 1'b1; at[fi] = ea[19*k + 8 +: 10]; ix[k] = fi; gk[k] = 1'b1; end
                    else f_al2 = 1'b1;
                end
            end
        end
    end
    // ---- merged content of every entry
    reg [15:0]  hm [0:LA-1];
    reg [511:0] hd [0:LA-1];

    always @* begin : p_merge integer k, e; reg [3:0] sl;
        for (e = 0; e < LA; e = e + 1) begin hm[e] = 16'd0; hd[e] = 512'd0; end
        for (k = 0; k < 16; k = k + 1) if (gk[k]) begin
            sl = ea[19*k +: 4];
            hm[ix[k]][sl] = 1'b1;
            hd[ix[k]][32*sl +: 32] = ed[32*k +: 32];
        end
    end
    // ---- move selection: eviction, else the lowest full entry, else the lowest timed-out entry
    wire q_pop = (qn != 0) && slot_ok;
    wire q_room = (qn - q_pop) < WQ;
    reg          mv; reg [LB-1:0] mi; reg mv_ev;
    reg [15:0]   nm_ [0:LA-1];

    always @* begin : p_move integer e;
        for (e = 0; e < LA; e = e + 1) begin
            nm_[e] = al[e] ? hm[e] : (e_m[e] | hm[e]);
        end
        mv = 1'b0; mi = {LB{1'b0}}; mv_ev = 1'b0;
        if (evn) begin mv = 1'b1; mi = evi; mv_ev = 1'b1; end
        else begin
            for (e = LA - 1; e >= 0; e = e - 1)
                if ((e_v[e] || al[e]) && nm_[e] == 16'hffff) begin mv = 1'b1; mi = e[LB-1:0]; end
            if (!mv)
                for (e = LA - 1; e >= 0; e = e - 1)
                    if (e_v[e] && !al[e] && hm[e] == 16'd0 && e_a[e] == LTO[AW-1:0]) begin mv = 1'b1; mi = e[LB-1:0]; end
        end
    end
    // ---- state update

    always @(posedge clk) begin : p_state integer e, j; reg [511:0] bm, md_;
        if (!rn) begin
            for (e = 0; e < LA; e = e + 1) e_v[e] <= 1'b0;
            qh <= 0; qt <= 0; qn <= 0; w_v <= 1'b0; flt <= 4'd0;
        end else begin
            // port: pop the queue head
            w_v <= q_pop;
            if (q_pop) begin w_row <= {q_t[qh], G[3:0]}; w_m <= q_m[qh]; w_d <= q_d[qh]; qh <= qh + 1'b1; end
            // the moved row -> queue tail
            if (mv && q_room) begin
                if (mv_ev) begin q_t[qt] <= e_t[mi]; q_m[qt] <= e_m[mi]; q_d[qt] <= e_d[mi]; end
                else begin
                    for (j = 0; j < 16; j = j + 1) bm[32*j +: 32] = {32{hm[mi][j]}};
                    md_ = al[mi] ? (hd[mi] & bm) : ((e_d[mi] & ~bm) | (hd[mi] & bm));
                    q_t[qt] <= al[mi] ? at[mi] : e_t[mi]; q_m[qt] <= nm_[mi]; q_d[qt] <= md_;
                end
                qt <= qt + 1'b1;
            end
            qn <= qn + (mv && q_room) - q_pop;
            if (mv && mv_ev && !q_room) flt[3] <= 1'b1;
            // entries
            for (e = 0; e < LA; e = e + 1) begin
                for (j = 0; j < 16; j = j + 1) bm[32*j +: 32] = {32{hm[e][j]}};
                if (mv && q_room && !mv_ev && mi == e[LB-1:0]) e_v[e] <= 1'b0;             // full / timed out: left
                else if (al[e]) begin
                    e_v[e] <= 1'b1; e_t[e] <= at[e]; e_m[e] <= hm[e]; e_d[e] <= hd[e] & bm; e_a[e] <= {AW{1'b0}};
                end else if (hm[e] != 16'd0) begin
                    e_m[e] <= e_m[e] | hm[e]; e_d[e] <= (e_d[e] & ~bm) | (hd[e] & bm); e_a[e] <= {AW{1'b0}};
                end else if (e_v[e] && e_a[e] != LTO[AW-1:0]) e_a[e] <= e_a[e] + 1'b1;
            end
            if (f_al2) flt[2] <= 1'b1;
            if (f_rg) flt[1] <= 1'b1;
            if (f_al) flt[0] <= 1'b1;
        end
    end
endmodule

// ================================================================================================ landing lane
// dsfd_vm_ll: one row lane of a landing producer (a die bus with no back-pressure into the VM, or with the room level
// t_cts).  Rows queue in a DEPTH-row FIFO (an ot_sram_1r1w_64x512 macro at DEPTH 64, flops below), each with the row
// address assigned at arrival from the lane's write pointer (LARM sets it to base + OFF, every row adds STRIDE).  The
// drain arbiter takes the head (o_rq / o_take, one row a cycle at most) onto a shared landing port.  A row arriving at a
// full FIFO -> sticky ovf (fail closed: the row is dropped); room = free rows (the collective's flow control).
module dsfd_vm_ll #(
    parameter integer DEPTH = 64,       // rows (power of 2)
    parameter integer MACRO = 1,
    parameter integer STRIDE = 1,
    parameter integer OFF = 0
) (
    input  wire         clk, rn,
    input  wire         in_v,
    input  wire [511:0] in_d,
    input  wire         arm_v,
    input  wire [13:0]  arm_base,
    output wire         o_rq,
    input  wire         o_take,
    output wire [13:0]  o_row,
    output wire [511:0] o_d,
    output wire [$clog2(DEPTH):0] room,
    output reg          ovf
);
    localparam integer AB = $clog2(DEPTH);
    reg [13:0] wp_row;                       // next arriving row's address
    reg [13:0] ra [0:DEPTH-1];               // row address per entry
    reg [AB-1:0] wp, rp; reg [AB:0] n;       // FIFO entries not yet read out of the array
    reg rf; reg [AB-1:0] rf_i;               // a read in flight (data next cycle)
    reg [1:0] oq_n; reg [511:0] oq_d [0:1]; reg [13:0] oq_r [0:1];
    wire [511:0] rd;
    wire wr = in_v && (n != DEPTH);
    wire take = o_take && oq_n != 0;
    wire iss = (n != 0) && ({1'b0, oq_n} + rf - take) < 2;
    generate if (MACRO && DEPTH == 64) begin : g_m
        (* keep = 1 *) ot_sram_1r1w_64x512_m1_r2c2 u_m (.clk(clk), .r_ce_in(iss), .r_addr_in(rp), .rd_out(rd),
            .w_ce_in(wr), .w_addr_in(wp), .wd_in(in_d), .w_mask_in({512{1'b1}}), .rr_en(2'd0), .rr_addr(12'd0),
            .cr_en(2'd0), .cr_sel(18'd0));
    end else begin : g_f
        reg [511:0] mem [0:DEPTH-1]; reg [511:0] q;
        always @(posedge clk) begin if (wr) mem[wp] <= in_d; if (iss) q <= mem[rp]; end
        assign rd = q;
    end endgenerate
    assign o_rq = oq_n != 0;
    assign o_d = oq_d[0]; assign o_row = oq_r[0];
    assign room = DEPTH - n;
    always @(posedge clk) begin
        if (!rn) begin wp <= 0; rp <= 0; n <= 0; rf <= 1'b0; oq_n <= 2'd0; ovf <= 1'b0; wp_row <= OFF; end
        else begin
            if (arm_v) wp_row <= arm_base + OFF + (wr ? STRIDE : 0);
            else if (wr) wp_row <= wp_row + STRIDE;
            if (wr) begin ra[wp] <= arm_v ? arm_base + OFF : wp_row; wp <= wp + 1'b1; end
            if (in_v && n == DEPTH) ovf <= 1'b1;
            if (iss) begin rp <= rp + 1'b1; rf_i <= rp; end
            n <= n + wr - iss;
            rf <= iss;
            // output queue: pop the head on take, push the read data
            if (take) begin oq_d[0] <= oq_d[1]; oq_r[0] <= oq_r[1]; end
            if (rf) begin
                if (oq_n - take == 0) begin oq_d[0] <= rd; oq_r[0] <= ra[rf_i]; end
                else begin oq_d[1] <= rd; oq_r[1] <= ra[rf_i]; end
            end
            oq_n <= oq_n - take + rf;
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
    parameter integer LMACRO = 1
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
    output reg  [NS*28-1:0]     m_v,
    output reg  [NS*28-1:0]     m_we,
    output reg  [NS*28*14-1:0]  m_row,
    output reg  [NS*28*4-1:0]   m_mask,
    output reg  [NS*28*128-1:0] m_d,
    output reg  [NS*4-1:0]      m_rf,   // tile-0 status input: bit 3 = FE fault (every slice)
    output reg  [15:0]          fe_flt  // FE sticky fault vector (composition net to the BE)
);
    localparam integer NP = 28, RA = 14, CP = 12;   // capture lanes on ports CP .. CP + 15
    wire clk = ck[0];
    wire rn, rns;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));
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
        dsfd_vm_cl #(.G(gl), .LA(LA), .LTO(LTO)) u_l (.clk(clk), .rn(rn), .ev(lvx), .ea(la), .ed(ld), .slot_ok(sok),
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
    wire [NLL-1:0] ll_iv, ll_rq, ll_ov, ll_arm; wire [NLL*512-1:0] ll_id, ll_od; wire [NLL*14-1:0] ll_or;
    wire [NLL*($clog2(LD)+1)-1:0] ll_room;
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
    genvar gll;
    generate for (gll = 0; gll < NLL; gll = gll + 1) begin : g_ll
        localparam integer ST = (gll < 2 * NSVC) ? 2 : (gll < 2 * NSVC + 4) ? 4 : (gll < 2 * NSVC + 6) ? 1 : 2;
        localparam integer OF = (gll < 2 * NSVC) ? gll % 2 : (gll < 2 * NSVC + 4) ? gll - 2 * NSVC : (gll < 2 * NSVC + 6) ? 0 : gll - (2 * NSVC + 6);
`ifdef OT_SPVM_MUT_LSMALL
        localparam integer DP = LD / 4;            // MUTANT: undersized landing FIFOs (must overflow at the burst bench)
`else
        localparam integer DP = LD;
`endif
        dsfd_vm_ll #(.DEPTH(DP), .MACRO(LMACRO), .STRIDE(ST), .OFF(OF)) u_ll (.clk(clk), .rn(rn),
            .in_v(ll_iv[gll]), .in_d(ll_id[512*gll +: 512]), .arm_v(ll_arm[gll]), .arm_base(arg[13:0]),
            .o_rq(ll_rq[gll]), .o_take(ll_tk[gll]), .o_row(ll_or[14*gll +: 14]), .o_d(ll_od[512*gll +: 512]),
            .room(ll_room[($clog2(LD)+1)*gll +: $clog2(LD)+1]), .ovf(ll_ov[gll]));
    end endgenerate
    // drain: up to NLP heads a cycle, rotating priority
    reg [$clog2(NLL)-1:0] ll_ptr; reg [NLP-1:0] lp_v; reg [NLP*14-1:0] lp_row; reg [NLP*512-1:0] lp_d;
    reg [NLP-1:0] lsel_v; reg [$clog2(NLL)-1:0] lsel [0:NLP-1];
    always @* begin : p_l562 integer li, lj, lk;
        ll_tk = {NLL{1'b0}}; lsel_v = {NLP{1'b0}};
        for (lk = 0; lk < NLP; lk = lk + 1) lsel[lk] = {$clog2(NLL){1'b0}};
        lk = 0;
        // lanes with no back-pressure first (rotating), the collective's flow-controlled word lanes take what is left
        for (li = 0; li < NLL; li = li + 1) begin
            lj = (ll_ptr + li) % NLL;
            if (ll_rq[lj] && lk < NLP && !(lj >= 2 * NSVC && lj < 2 * NSVC + 4)) begin
                ll_tk[lj] = 1'b1; lsel_v[lk] = 1'b1; lsel[lk] = lj; lk = lk + 1;
            end
        end
        for (li = 0; li < 4; li = li + 1) begin
            lj = 2 * NSVC + li;
            if (ll_rq[lj] && lk < NLP) begin ll_tk[lj] = 1'b1; lsel_v[lk] = 1'b1; lsel[lk] = lj; lk = lk + 1; end
        end
    end
    always @(posedge clk) begin : p_l578 integer lk;
        if (!rn) begin lp_v <= {NLP{1'b0}}; ll_ptr <= 0; end
        else begin
            lp_v <= lsel_v;
            ll_ptr <= (ll_ptr == NLL - 1) ? 0 : ll_ptr + 1'b1;
        end
        for (lk = 0; lk < NLP; lk = lk + 1) begin
            lp_row[14*lk +: 14] <= ll_or[14*lsel[lk] +: 14]; lp_d[512*lk +: 512] <= ll_od[512*lsel[lk] +: 512];
        end
    end
    // collective flow control: room for >= 8 words on every word lane
    reg cts_ok; integer lc;
    always @* begin
        cts_ok = 1'b1;
        for (lc = 0; lc < 4; lc = lc + 1) if (ll_room[($clog2(LD)+1)*(2*NSVC+lc) +: $clog2(LD)+1] < 8) cts_ok = 1'b0;
    end
    always @(posedge clk) if (!rn) t_cts <= 3'd0; else t_cts <= {1'b0, 1'b1, cts_ok};
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
    integer s;
    always @(posedge clk) begin : p_l647 integer s, p;
        for (s = 0; s < NS; s = s + 1) begin
            if (!rn) m_v[s*NP +: NP] <= {NP{1'b0}}; else m_v[s*NP +: NP] <= c_vv;
            m_we[s*NP +: NP] <= c_we;
            m_row[s*NP*RA +: NP*RA] <= c_row;
            for (p = 0; p < NP; p = p + 1) begin
                m_mask[(s*NP + p)*4 +: 4] <= c_m[p*16 + 4*s +: 4];
                m_d[(s*NP + p)*128 +: 128] <= c_dd[p*512 + 128*s +: 128];
            end
        end
    end

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
    integer kk, b;
    reg [4:0] pc;
    reg [15:0] wm;
    always @(posedge clk) begin : p_l672 integer kk, q, b;
        for (q = 0; q < NP; q = q + 1) begin
            wm = b_m[q*16 +: 16];
            pc = 5'd0; for (b = 0; b < 16; b = b + 1) pc = pc + {4'd0, wm[b]};
            k_pc[5*q +: 5] <= pc;
            for (kk = 0; kk < NSLOT; kk = kk + 1) begin
                k_w[kk*NP + q] <= b_v[q] && b_we[q] && b_row[q*RA +: RA] >= sl_base[kk] &&
                                  {1'b0, b_row[q*RA +: RA]} < {1'b0, sl_base[kk]} + sl_n[kk];
                k_r[kk*NP + q] <= b_v[q] && !b_we[q] && b_row[q*RA +: RA] >= sl_base[kk] &&
                                  {1'b0, b_row[q*RA +: RA]} < {1'b0, sl_base[kk]} + sl_n[kk];
            end
        end
        if (!rn) k_v <= {NP{1'b0}}; else k_v <= b_v;
        // the flags of a slot being ARMed this edge were compared with its OLD range: not counted, not checked
        // (contract: no op into a range in the cycle its ARMN lands)
        k_ok <= ~(is_arm ? ({{(NSLOT-1){1'b0}}, 1'b1} << arm_s) : {NSLOT{1'b0}});
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
            if (is_armb) begin st_base[arm_s] <= arg[13:0]; st_ntf[arm_s] <= arg[18]; end
            if (is_armr) st_n[arm_s] <= arg[14:0];
            if (is_arm) begin
                if (sl_arm[arm_s] || sl_dp[arm_s] || sl_rp[arm_s]) rearm <= 1'b1;
                sl_arm[arm_s] <= 1'b1; t_rdy[arm_s] <= 1'b0; sl_ntf[arm_s] <= st_ntf[arm_s]; sl_user[arm_s] <= ad_d[82:73];
                sl_base[arm_s] <= st_base[arm_s]; sl_n[arm_s] <= st_n[arm_s];
                sl_need[arm_s] <= arg[18:0]; sl_cnt[arm_s] <= 19'd0; sl_tag[arm_s] <= ctag;
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
        else fe_flt <= fe_flt | {so_s[1], |ll_ov, ad_flt, cap_src_flt, clf, is_bad, ovf_pd, rearm, l_src_flt, ovf_cr, 1'b0,
                                 e_err | rbad, early};
    end
    always @(posedge clk) for (s = 0; s < NS; s = s + 1) m_rf[s*4 +: 4] <= {|fe_flt, 3'b000};
endmodule

// ================================================================================================ back end
// dsfd_vm_be v2 (el1011-ds-vm/be 2026-10-11): structural redesign after s81vm-be-e66305b64-tc-rd-v5050 PREROUTE_MARGIN
// (reg2reg -1071.7 ps, 47,602 / 49,290 endpoints < 0 on the 1520 x 108 um strip).  Measured causes (3_4_place_resized):
//   (1) the one reset-synchronizer output gated every data register (P2 FIFO 24,160 + CDC 5,871 + bus lanes + c_l0d +
//       t_srq enables: ~33k loads across 1,520 um, -551 ps);
//   (2) the bus-lane select xd_m (4-b lane id, compared per lane) drove 16 x 512 enables per X port (-749 ps, 7,713 eps);
//   (3) the ctrl-return read: rp -> 8:1 x 512 shadow mux -> rr_nx 2:1 -> vrq in one stream cycle (-1,088 ps), with rp
//       also feeding the core-side sampler (-770 ps);
//   (4) a 512-b row is 4 x 128 b from slices 1,200 um apart (o_d pins x 91 .. 1,315, outputs x 2 .. 1,000) assembled
//       with no stage between the slice pin flops and the output registers.
// Structure now: data registers carry no reset (only valids / control state, from 6 kept regional reset copies); the
// slice pin flops feed RL relay stages (every lane, every slice, aligned) before the response stage; the bus-lane
// selects are priority-resolved one-hot, registered and kept per lane x 128-b quarter, and the 5 X rows are broadcast
// through 4 kept per-lane-group copies (t_bl = AND-OR of registered operands); the ctrl return writes the CDC from
// registered pushes (per-slice replicated pointer) and reads it through a registered output with kept one-hot read
// selects per 64-b chunk (dsfd_vm_be_rcdc); the P2 FIFO always writes (no bypass: its enables never see c_l0r).
// Added latency (fixed, every lane alike; metadata lines are MD + RL long): t_srq / P2 RL + 1 (P2 +1 no bypass),
// bus lanes RL + 2, ctrl return RL + 1 serial + 1 stream cycle.  Pins and contract unchanged.
// ID: a distinct value per copy makes every copy its own module (no pass can merge two copies)
(* keep_hierarchy = "yes" *)
module dsfd_vm_be_kreg #(parameter integer W = 1, parameter integer ID = 0) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge clk) q <= d;
endmodule

// dsfd_vm_be_rcdc: the ot_ratio_cdc_fifo protocol (HOLD handshake, LAG 0, identical pointer / state behaviour) with a
// registered read port: o_v = the take one stream cycle later, o_d = the taken entry (sh[rp] registered every cycle
// through NC kept one-hot copies of the next rp, one per W/NC-bit chunk), o_vc = NC kept copies of o_v.
module dsfd_vm_be_rcdc #(
    parameter integer W = 512, parameter integer DEPTH = 8, parameter integer HOLD = 2, parameter integer NC = 8,
    parameter integer IDB = 0          // kept-copy ID base
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
);
    localparam integer AW = $clog2(DEPTH);
    localparam integer CW = $clog2(HOLD + 1);
    localparam integer CB = W / NC;
    localparam [1:0] S_DOWN = 2'b00, S_WAIT = 2'b01, S_RUN = 2'b10;
    localparam [AW:0] DP = DEPTH;
    localparam [CW-1:0] HL = HOLD;
    reg [W-1:0]  mem [0:DEPTH-1];
    reg [AW:0]   wp, rp_w, rp, wp_r;
    reg [1:0]    w_st, r_st_w, r_st, w_st_r;
    reg [CW-1:0] w_cnt, r_cnt;
    reg          w_ok, r_ok;
    always @(posedge wclk) begin rp_w <= rp; r_st_w <= r_st; end
    wire w_live = (w_st == S_RUN) && (r_st_w != S_DOWN);
    assign w_rdy = wrst_n && w_live && ((wp - rp_w) != DP);
    wire w_fire = w_v && w_rdy;
    always @(posedge wclk) begin
        if (!wrst_n) begin
            w_st <= S_DOWN; w_cnt <= HL; w_ok <= 1'b0; wp <= {(AW+1){1'b0}};
        end else begin
            case (w_st)
                S_DOWN: begin
                    wp <= {(AW+1){1'b0}};
                    if (r_st_w != S_RUN) w_ok <= 1'b1;
                    if (w_cnt != {CW{1'b0}}) w_cnt <= w_cnt - 1'b1;
                    else if (w_ok || r_st_w != S_RUN) w_st <= S_WAIT;
                end
                S_WAIT: begin
                    wp <= {(AW+1){1'b0}};
                    if (r_st_w != S_DOWN) w_st <= S_RUN;
                end
                default: begin
                    if (r_st_w == S_DOWN) begin
                        w_st <= S_DOWN; w_cnt <= HL; w_ok <= 1'b1; wp <= {(AW+1){1'b0}};
                    end else if (w_fire) wp <= wp + 1'b1;
                end
            endcase
        end
    end
    always @(posedge wclk) if (w_fire) mem[wp[AW-1:0]] <= w_d;
    reg [W-1:0] sh [0:DEPTH-1];
    always @(posedge rclk) begin : p_sh integer i;
        wp_r <= wp; w_st_r <= w_st;
        for (i = 0; i < DEPTH; i = i + 1) sh[i] <= mem[i];
    end
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
    genvar c;
    generate for (c = 0; c < NC; c = c + 1) begin : g_c
        wire [DEPTH-1:0] oh;
        dsfd_vm_be_kreg #(.W(DEPTH), .ID(IDB + c)) u_oh (.clk(rclk), .d(oh_nx), .q(oh));
        dsfd_vm_be_kreg #(.W(1), .ID(IDB + NC + c)) u_vc (.clk(rclk), .d(r_take), .q(o_vc[c]));
        reg [CB-1:0] od;
        always @(posedge rclk) begin : p_od integer i; reg [CB-1:0] a;
            a = {CB{1'b0}};
            for (i = 0; i < DEPTH; i = i + 1) a = a | (sh[i][c*CB +: CB] & {CB{oh[i]}});
            od <= a;
        end
        assign o_d[c*CB +: CB] = od;
    end endgenerate
endmodule

module dsfd_vm_be #(
    parameter integer NS = 4,
    parameter integer P2D = 40,         // P2 flit FIFO depth (the FE reader's credits)
    parameter integer MD = 9,           // tile-3 f_* (request exit) -> o_* (read data) skew (NSTG 2, QD 4)
    parameter integer RL = 2            // relay stages between the slice pin flops and the response stage
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
    localparam integer XL = MD + RL;    // f_* pin flop -> relayed o_* stage
    localparam integer NG = 4;          // bus-lane groups (4 lanes each), one X-row copy per group
    localparam integer NC = 8;          // ctrl-return 64-b chunks
    wire clk = ck[0];
    wire rn0, rns;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn0));
    ot_dsrom_mtp_rstsync u_rss (.clk(cks[0]), .rst_n_async(rss[0]), .rst_n(rns));
    // regional reset copies (control state only; no data register carries a reset)
    wire rn_i, rn_x, rn_c, rn_p, rn_s, rn_w;
    dsfd_vm_be_kreg #(.W(1), .ID(1)) u_rn_i (.clk(clk), .d(rn0), .q(rn_i));
    dsfd_vm_be_kreg #(.W(1), .ID(2)) u_rn_x (.clk(clk), .d(rn0), .q(rn_x));
    dsfd_vm_be_kreg #(.W(1), .ID(3)) u_rn_c (.clk(clk), .d(rn0), .q(rn_c));
    dsfd_vm_be_kreg #(.W(1), .ID(4)) u_rn_p (.clk(clk), .d(rn0), .q(rn_p));
    dsfd_vm_be_kreg #(.W(1), .ID(5)) u_rn_s (.clk(clk), .d(rn0), .q(rn_s));
    dsfd_vm_be_kreg #(.W(1), .ID(6)) u_rn_w (.clk(clk), .d(rn0), .q(rn_w));
    // ---------------------------------------------------------------- pin flops (stage 0) + RL relay stages
    reg [NS*NP-1:0] q_v; reg [NS*NP*128-1:0] q_d; reg [NS*4-1:0] q_f; reg [NS*3-1:0] q_o;
    reg q_fv; reg [91:0] q_fm; reg [15:0] q_fe; reg [4:0] q_xv; reg [19:0] q_xm;
    always @(posedge clk) begin
        if (!rn_i) begin q_v <= 0; q_f <= 0; q_fv <= 1'b0; q_fe <= 16'd0; q_xv <= 5'd0; end
        else begin q_v <= o_v; q_f <= o_f; q_fv <= f_v5[0] && !f_we5[0]; q_fe <= fe_flt; q_xv <= f_vx & ~f_wex; end
        q_d <= o_d; q_o <= o_o; q_fm <= f_m5; q_xm <= f_mx;
    end
    wire [NS*NP-1:0] rv [0:RL]; wire [NS*NP*128-1:0] rd [0:RL]; wire [NS*4-1:0] rf [0:RL];
    assign rv[0] = q_v; assign rd[0] = q_d; assign rf[0] = q_f;
    genvar gr, gl, gq, gg;
    generate for (gr = 0; gr < RL; gr = gr + 1) begin : g_rl
        reg [NS*NP-1:0] v; reg [NS*NP*128-1:0] d; reg [NS*4-1:0] f;
        always @(posedge clk) begin
            if (!rn_i) begin v <= {NS*NP{1'b0}}; f <= {NS*4{1'b0}}; end
            else begin v <= rv[gr]; f <= rf[gr]; end
            d <= rd[gr];
        end
        assign rv[gr+1] = v; assign rd[gr+1] = d; assign rf[gr+1] = f;
    end endgenerate
    wire [NS*NP-1:0] a_v = rv[RL]; wire [NS*NP*128-1:0] a_d = rd[RL]; wire [NS*4-1:0] a_f = rf[RL];
    function automatic [511:0] row_of(input [NS*NP*128-1:0] d, input integer p);
        integer ss; begin
            row_of = 512'd0;
            for (ss = 0; ss < NS; ss = ss + 1) row_of[128*ss +: 128] = d[(ss*NP + p)*128 +: 128];
        end
    endfunction
    wire [NP-1:0] v0 = a_v[NP-1:0];
    // ---------------------------------------------------------------- responses (one output register, no data reset)
    always @(posedge clk) begin
        if (!rn_w) begin t_srq[512] <= 1'b0; t_srq[1025] <= 1'b0; end
        else begin t_srq[512] <= v0[0]; t_srq[1025] <= v0[1]; end
        t_srq[511:0] <= row_of(a_d, 0); t_srq[1024:513] <= row_of(a_d, 1);
    end
    // ---------------------------------------------------------------- X returns -> bus lanes
    // the lane id rode down with the read (metadata delay line, XL = MD + RL cycles like P2)
    reg [XL-1:0] xd_v [0:4]; reg [3:0] xd_m [0:4][0:XL-1];
    always @(posedge clk) begin : p_xd integer xi, xj;
        for (xi = 0; xi < 5; xi = xi + 1) begin
            if (!rn_x) xd_v[xi] <= {XL{1'b0}}; else xd_v[xi] <= {xd_v[xi][XL-2:0], q_xv[xi]};
            xd_m[xi][0] <= q_xm[4*xi +: 4];
            for (xj = 1; xj < XL; xj = xj + 1) xd_m[xi][xj] <= xd_m[xi][xj-1];
        end
    end
    // X port index -> tile port: {p9, p8, p2, p7, p6}
    function automatic integer xport(input integer x);
        begin xport = (x == 0) ? 6 : (x == 1) ? 7 : (x == 2) ? 2 : (x == 3) ? 8 : 9; end
    endfunction
    // stage RL: per lane, the one-hot select of the X port that targets it (the last one wins, as the serial loop did)
    reg [4:0] xsel [0:15]; reg xmis_n, xcol_n;
    always @* begin : p_xsel integer l, x; reg [15:0] seen;
        seen = 16'd0; xmis_n = 1'b0; xcol_n = 1'b0;
        for (l = 0; l < 16; l = l + 1) xsel[l] = 5'd0;
        for (x = 0; x < 5; x = x + 1) begin
            if (xd_v[x][XL-1] != v0[xport(x)]) xmis_n = 1'b1;
            if (xd_v[x][XL-1]) begin
                if (seen[xd_m[x][XL-1]]) xcol_n = 1'b1;
                seen[xd_m[x][XL-1]] = 1'b1;
            end
        end
        for (l = 0; l < 16; l = l + 1)
            for (x = 0; x < 5; x = x + 1) if (xd_v[x][XL-1] && xd_m[x][XL-1] == l[3:0]) xsel[l] = 5'd1 << x;
    end
    reg x_mis, x_col; reg [15:0] tv;
    wire [5*512-1:0] xrow = {row_of(a_d, 9), row_of(a_d, 8), row_of(a_d, 2), row_of(a_d, 7), row_of(a_d, 6)};
    always @(posedge clk) begin : p_xv integer l;
        if (!rn_x) begin x_mis <= 1'b0; x_col <= 1'b0; tv <= 16'd0; end
        else begin
            if (xmis_n) x_mis <= 1'b1;
            if (xcol_n) x_col <= 1'b1;
            for (l = 0; l < 16; l = l + 1) tv[l] <= |xsel[l];
        end
    end
    // stage RL + 1: kept X-row copies per lane group, kept one-hot selects per lane x 128-b quarter
    wire [5*512-1:0] xb [0:NG-1];
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_xb
        dsfd_vm_be_kreg #(.W(5*512), .ID(16 + gg)) u_xb (.clk(clk), .d(xrow), .q(xb[gg]));
    end endgenerate
    // stage RL + 2: t_bl = AND-OR of registered operands
    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_bl
        always @(posedge clk) if (!rn_x) t_bl[513*gl] <= 1'b0; else t_bl[513*gl] <= tv[gl];
        for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
            wire [4:0] s;
            dsfd_vm_be_kreg #(.W(5), .ID(32 + 4*gl + gq)) u_s (.clk(clk), .d(xsel[gl]), .q(s));
            always @(posedge clk) begin : p_o integer x; reg [127:0] a;
                a = 128'd0;
                for (x = 0; x < 5; x = x + 1) a = a | (xb[gl/4][512*x + 128*gq +: 128] & {128{s[x]}});
                t_bl[513*gl + 1 + 128*gq +: 128] <= a;
            end
        end
    end endgenerate
    // ---------------------------------------------------------------- ctrl read return: p3 then p4 -> 2 CDC FIFOs
    // the op order of a cycle: p3 (if valid) first, then p4; pushes alternate FIFOs starting at w_nx.  The pushes are
    // registered (wq_*) and every slice muxes its own 128 b with its own valid copy and its own w_nx replica.
    reg [NS-1:0] w_nx; reg [1:0] wq_v; reg [511:0] wq_d0, wq_d1; reg r_ovf;
    wire [1:0] rw_rdy, rr_v, o_vr; wire [511:0] o_d0, o_d1; wire [NC-1:0] o_vc0, o_vc1; reg rr_nx;
    always @(posedge clk) begin : p_cw integer ss; reg p0, p1, pa_, pb_, nx;
        for (ss = 0; ss < NS; ss = ss + 1) begin
            p0 = a_v[ss*NP + 3]; p1 = a_v[ss*NP + 4]; pa_ = p0 | p1; pb_ = p0 & p1; nx = w_nx[ss];
            wq_d0[128*ss +: 128] <= (pa_ && !nx && p0) ? a_d[(ss*NP + 3)*128 +: 128] : a_d[(ss*NP + 4)*128 +: 128];
            wq_d1[128*ss +: 128] <= (pa_ && nx && p0) ? a_d[(ss*NP + 3)*128 +: 128] : a_d[(ss*NP + 4)*128 +: 128];
            if (!rn_c) w_nx[ss] <= 1'b0; else if (pa_ && !pb_) w_nx[ss] <= ~nx;
        end
        p0 = v0[3]; p1 = v0[4]; pa_ = p0 | p1; pb_ = p0 & p1; nx = w_nx[0];
        if (!rn_c) begin wq_v <= 2'b00; r_ovf <= 1'b0; end
        else begin
            wq_v <= {(pa_ && nx) || (pb_ && !nx), (pa_ && !nx) || (pb_ && nx)};
            if ((wq_v[0] && !rw_rdy[0]) || (wq_v[1] && !rw_rdy[1])) r_ovf <= 1'b1;
        end
    end
    wire [1:0] rtk = {rr_v[1] && rr_nx, rr_v[0] && !rr_nx};
    dsfd_vm_be_rcdc #(.W(512), .DEPTH(8), .HOLD(2), .NC(NC), .IDB(100)) u_rc0 (.wclk(clk), .wrst_n(rn_c), .w_v(wq_v[0]),
        .w_rdy(rw_rdy[0]), .w_d(wq_d0), .rclk(cks[0]), .rrst_n(rns), .r_v(rr_v[0]), .r_rdy(rtk[0]),
        .o_v(o_vr[0]), .o_d(o_d0), .o_vc(o_vc0));
    dsfd_vm_be_rcdc #(.W(512), .DEPTH(8), .HOLD(2), .NC(NC), .IDB(200)) u_rc1 (.wclk(clk), .wrst_n(rn_c), .w_v(wq_v[1]),
        .w_rdy(rw_rdy[1]), .w_d(wq_d1), .rclk(cks[0]), .rrst_n(rns), .r_v(rr_v[1]), .r_rdy(rtk[1]),
        .o_v(o_vr[1]), .o_d(o_d1), .o_vc(o_vc1));
    always @(posedge cks[0]) begin : p_vr integer c;
        if (!rns) begin rr_nx <= 1'b0; vrv <= 1'b0; end
        else begin
            vrv <= |o_vr;
            if (|rtk) rr_nx <= ~rr_nx;
        end
        for (c = 0; c < NC; c = c + 1) vrq[64*c +: 64] <= o_vc1[c] ? o_d1[64*c +: 64] : o_d0[64*c +: 64];
    end
    // ---------------------------------------------------------------- P2: metadata delay line + flit FIFO
    reg [XL-1:0] md_v; reg [91:0] md_m [0:XL-1];
    always @(posedge clk) begin : p_md integer i;
        if (!rn_p) md_v <= {XL{1'b0}}; else md_v <= {md_v[XL-2:0], q_fv};
        md_m[0] <= q_fm;
        for (i = 1; i < XL; i = i + 1) md_m[i] <= md_m[i-1];
    end
    wire mv = md_v[XL-1]; wire [91:0] mm = md_m[XL-1];
    wire [603:0] flit = {mm, row_of(a_d, 5)};
    localparam integer PB = $clog2(P2D);
    reg [603:0] pf [0:P2D-1];
    reg [PB-1:0] ph, pt; reg [PB:0] pn;
    reg ov; reg [603:0] od;
    wire take = ov && c_l0r[0];
    wire ld = (!ov || take) && (pn != 0);
    assign c_l0v = ov; assign c_l0d = od;
    always @(posedge clk) if (mv) pf[pt] <= flit;          // every flit is written (no bypass, no reset in the enable)
    always @(posedge clk) if (ld) od <= pf[ph];
    reg p_ovf, p_mis;
    always @(posedge clk) begin
        if (!rn_p) begin ph <= 0; pt <= 0; pn <= 0; ov <= 1'b0; t_p2c <= 1'b0; p_ovf <= 1'b0; p_mis <= 1'b0; end
        else begin
            if (mv) pt <= (pt == P2D - 1) ? 0 : pt + 1'b1;
            if (ld) ph <= (ph == P2D - 1) ? 0 : ph + 1'b1;
            pn <= pn + mv - ld;
            if (ld) ov <= 1'b1; else if (take) ov <= 1'b0;
            t_p2c <= take;
            if (mv && pn == P2D) p_ovf <= 1'b1;
            if (mv != v0[5]) p_mis <= 1'b1;
        end
    end
    // ---------------------------------------------------------------- status
    reg s_mis; reg [31:0] fv;
    always @(posedge clk) begin : p_st integer ss;
        if (!rn_s) begin s_mis <= 1'b0; flt <= 1'b0; fvec <= 32'd0; t_err <= 1'b0; max_occ <= 3'd0; end
        else begin
            for (ss = 1; ss < NS; ss = ss + 1) if (a_v[ss*NP +: NP] != a_v[NP-1:0] || a_f[ss*4 +: 4] != a_f[3:0]) s_mis <= 1'b1;
            // [3:0] memory {fault, und, mis, ovf | write-only read}; [19:4] FE vector; [20] P2 FIFO overflow;
            // [21] P2 metadata misalignment; [22] slice mismatch; [23] ctrl return overflow
            fv = {6'd0, x_col, x_mis, r_ovf, s_mis, p_mis, p_ovf, q_fe, a_f[3:0]};
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
    localparam integer MD = 4 * NSTG + QD + 9 - 4 * (NSTG + 1);
    wire [NS*NP-1:0] mv, mwe; wire [NS*NP*RA-1:0] mrow; wire [NS*NP*4-1:0] mm; wire [NS*NP*128-1:0] md;
    wire [NS*4-1:0] mrf; wire [15:0] fe_flt;
    wire p2c;
    dsfd_vm_fe #(.NS(NS), .VF(VF), .VR(VR), .NSLOT(NSLOT), .P2D(P2D), .CQD(CQD), .LA(LA), .LTO(LTO), .NSVC(NSVC), .LD(LD),
                 .NLP(NLP), .LMACRO(LMACRO)) u_fe (
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
            dsfd_vm_bgq #(.NP(NP), .NPR(NPR), .NB(32), .NBL(8), .QD(QD), .RQ(8), .MACRO(MACRO), .DW(128), .NSTG(NSTG)) u_bg (
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
