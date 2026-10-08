// CLAUDE S81-PH su (2026-10-06): REMOTE-READ copy of rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv (module renamed ot_s81ph_*). RX = 0, GX = 0 is the original
// cycle for cycle.  RX: extra cycles between a lane's operand read (MR) and the memory's answer (the read request and
// the word cross the die bus: SU slab lanes, VM in the hub slab); GX: the same for the gather-index read (vi).  The lane
// delays its read tags (m -> x) by RX and its gather G1 stage by GX; the controller's fetch insertion line and its
// depth model (c_dF) grow by RX (+ GX with a gather), so every later stage, credit and checkpoint moves with it.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SU ADAPTER of the re-specified V4.1 decode core (ot_hdc_core_v41x): keeps the
// as-built stream unit's contract toward the sequencer (ot_hdc_v41_stream: go /
// ready / idle, every SU field with its DYN value added, su_chase, mx_m /
// mx_xps / mx_ops) and runs the op on the re-specified vector unit
// ot_hdc_v41x_vec (N light lanes, M SFU lanes, R-ARITH reductions).
//
// Fields.  The unit implements Machine.su's element semantics field for field;
// su_vec is not an input (the unit lays ops onto lanes itself).
//
// Batched ops (MTP, mx_m = m > 1).  The as-built core ran copy p of a batched op
// on stream copy p; the vector unit has one set of lanes, so the adapter issues
// the m copies BACK TO BACK as m ops (tools/hdc_program_v41.su_shift): copy p's
// VM-sourced A..D bases + p*mx_xps, the element write base (dst VM) and the
// reducer base + p*mx_ops (elements).  The copies write disjoint slots and are
// independent.
//
// Order between stream ops.  The vector unit overlaps ops with no drain and
// keeps every variable-depth stage in emit order, so reads, element writes and
// reducer results of consecutive ops stay in issue order -- the property the
// program's wait masks assume of the stream unit (hdc_program_v41.schedule: on
// its own unit only a read of in-flight writes conflicts).  A read of in-flight
// writes is either drained by the wait mask (the sequencer waits for idle) or
// CHASED (su_chase > 0): the adapter makes such an op (every copy) wait until
// the previous op accepted by the unit has written all its element results --
// vector-credit chaining SELF on that op with an unreachable lead, i.e. its
// completion (cr_dseq).  That is conservative (the as-built unit let the chaser
// run D vectors behind) and never reads early: the unit completes ops in order,
// so every older op is complete as well.
// CLS_DRAIN = 1 (the MTP programs, schedule(chain=True)): the as-built unit also
// drained on a change of CLASS (hdc_program_v41.su_class), and those programs
// rely on it; the adapter reproduces it the same way (the first op of a new
// class waits for the previous op's completion).
// ---------------------------------------------------------------------------
module ot_s81ph_su_adapt #(
    parameter integer RX = 0,
    parameter integer GX = 0,
    parameter integer N  = 16,          // vector-unit light lanes
    parameter integer M  = 8,           // SFU lanes
    parameter integer LV = 7,           // reducer time levels (a reduced segment spans <= 2^LV vectors), 1..7
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer CLS_DRAIN = 0,
    parameter integer KVT_SH = 9,
    parameter integer BCAST_STAGES = 0, // ot_hdc_v41x_vec: controller -> lane broadcast tree stages
    parameter integer RET_STAGES = 0,   // ot_hdc_v41x_vec: lane / reducer -> vector-memory write stages
    parameter integer MLAT = 3,         // ot_hdc_v41x_vec: multiplier latency (3, 4 or 5: W11 serial domain)
    parameter integer ALAT = 3          // ot_hdc_v41x_vec: FP add latency (3, or 4)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout, i_nin, i_chase,
    input  wire [1:0]        i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi, i_aibase,
    input  wire [1:0]        i_aind,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_bhalf,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire              i_cpair,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire              i_arnd, i_arelu, i_amin, i_cclip,
    input  wire [2:0]        i_m1,
    input  wire [1:0]        i_m2,
    input  wire [2:0]        i_qm, i_ad, i_sfu, i_e1,
    input  wire [1:0]        i_e2,
    input  wire              i_rnd,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_obase, i_oso, i_osi, i_orow,
    input  wire [1:0]        i_red,
    input  wire              i_redsq, i_redwhole, i_redtree, i_redrnd,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2, i_imm3,
    input  wire [2:0]        i_m,
    input  wire [AW-1:0]     i_xps, i_ops,
    // the vector unit's memory ports
    output wire [N-1:0]      vi_re,
    output wire [N*AW-1:0]   vi_addr,
    input  wire [N*32-1:0]   vi_q,
    output wire [4*N*AW-1:0] rd_addr,
    output wire [4*N-1:0]    rd_re,
    output wire [8*N-1:0]    rd_src,
    input  wire [4*N*32-1:0] rd_q,
    output wire [N-1:0]      vm_we,
    output wire [N*AW-1:0]   vm_waddr,
    output wire [N*32-1:0]   vm_wdata,
    output wire [N-1:0]      kv_we,
    output wire [N*AW-1:0]   kv_waddr,
    output wire [N*32-1:0]   kv_wdata,
    output wire [N/8-1:0]    res_we,
    output wire [N/8*AW-1:0] res_addr,
    output wire [N/8*32-1:0] res_data,
    output reg               fault,
    output reg [31:0]        dbg_ops, dbg_elems
);
    localparam [1:0] SRC_VM = 2'd0, DST_VM = 2'd1, CH_NONE = 2'd0, CH_SELF = 2'd1;
    localparam [2:0] M1_BYP = 3'd0, M1_DIVB = 3'd4, M1_DIVIMM = 3'd5, M1_MAXB = 3'd6;

    // ---- the latched op (one at a time; its copies go to the unit back to back)
    reg              pend;                 // copies left to hand to the unit
    reg  [2:0]       cp, m_r;              // copy being offered, copies of the op
    reg  [NW-1:0]    nout, nin;
    reg              chase;
    reg  [1:0]       asrc, bsrc, csrc, dsrc, aind, dst, red, m2, e2;
    reg  [AW-1:0]    abase, aso, asi, aibase, bbase, bso, bsi, cbase, cso, csi, dbase, dso, dsi;
    reg  [AW-1:0]    obase, oso, osi, orow, rbase, rso, xps, ops;
    reg              bhalf, cpair, arnd, arelu, amin, cclip, rnd, redsq, redwhole, redtree, redrnd;
    reg  [2:0]       m1, qm, ad, sfu, e1;
    reg  [31:0]      imm1, imm2, imm3;
    // the as-built class (hdc_program_v41.su_class): divide?, sfu, and the stages used
    wire [8:0] cls_in = {i_m1 == M1_DIVB || i_m1 == M1_DIVIMM, i_sfu,
                         !(i_m1 == M1_BYP || i_m1 == M1_MAXB), i_m2 != 2'd0 || i_qm != 3'd0, i_ad != 3'd0,
                         i_e1 != 3'd0, i_e2 != 2'd0};
    reg  [8:0]       cls_last;
    reg              any_op;               // an op was accepted since reset
    reg              wait_prev;            // the latched op waits for the previous op's completion
    reg  [7:0]       seq;                  // the unit's sequence number of the next op it accepts
    reg  [7:0]       prev_seq;             // seq of the last op accepted before the latched one

    wire             v_ready, v_idle, v_fault, v_ofault;
    wire             v_go = pend;
    wire             v_acc = v_go && v_ready;
    assign ready = !pend;
    assign idle = !pend && v_idle;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pend <= 1'b0; cp <= 3'd0; seq <= 8'd0; any_op <= 1'b0; cls_last <= 9'd0;
            dbg_ops <= 0;
        end else begin
            if (go && !pend) begin
                pend <= 1'b1; cp <= 3'd0; m_r <= (i_m == 3'd0) ? 3'd1 : i_m;
                cls_last <= cls_in; any_op <= 1'b1;
                prev_seq <= seq - 8'd1;
                wait_prev <= any_op && ((i_chase != 0) || (CLS_DRAIN != 0 && cls_in != cls_last));
            end else if (v_acc) begin
                dbg_ops <= dbg_ops + 1'b1;
                seq <= seq + 8'd1;
                cp <= cp + 3'd1;
                if (cp + 3'd1 == m_r) pend <= 1'b0;
            end
        end
    end
    always @(posedge clk) if (go && !pend) begin
        nout <= i_nout; nin <= i_nin;
        asrc <= i_asrc; bsrc <= i_bsrc; csrc <= i_csrc; dsrc <= i_dsrc; aind <= i_aind; dst <= i_dst;
        red <= i_red; m2 <= i_m2; e2 <= i_e2;
        abase <= i_abase; aso <= i_aso; asi <= i_asi; aibase <= i_aibase;
        bbase <= i_bbase; bso <= i_bso; bsi <= i_bsi; cbase <= i_cbase; cso <= i_cso; csi <= i_csi;
        dbase <= i_dbase; dso <= i_dso; dsi <= i_dsi; obase <= i_obase; oso <= i_oso; osi <= i_osi;
        orow <= i_orow; rbase <= i_rbase; rso <= i_rso; xps <= i_xps; ops <= i_ops;
        bhalf <= i_bhalf; cpair <= i_cpair; arnd <= i_arnd; arelu <= i_arelu; amin <= i_amin; cclip <= i_cclip;
        rnd <= i_rnd; redsq <= i_redsq; redwhole <= i_redwhole; redtree <= i_redtree; redrnd <= i_redrnd;
        m1 <= i_m1; qm <= i_qm; ad <= i_ad; sfu <= i_sfu; e1 <= i_e1;
        imm1 <= i_imm1; imm2 <= i_imm2; imm3 <= i_imm3;
    end
    // copy cp's stream offsets
    wire [AW-1:0] xo = cp * xps;
    wire [AW-1:0] oo = cp * ops;

    wire [7:0]  cr_seq, cr_dseq, cr_rseq;
    wire [15:0] cr_cnt, emitted;
    wire        retire_o, dbg_emit, dbg_ret, dbg_res;
    wire [7:0]  dbg_eseq, dbg_rseq, dbg_sseq;
    ot_s81ph_vec #(.RX(RX), .GX(GX), .N(N), .M(M), .LV(LV), .AW(AW), .NW(NW), .KVT_SH(KVT_SH), .BCAST_STAGES(BCAST_STAGES),
                     .RET_STAGES(RET_STAGES), .MLAT(MLAT), .ALAT(ALAT)) u_vec (
        .clk(clk), .rst_n(rst_n), .go(v_go), .ready(v_ready), .idle(v_idle),
        .i_nout(nout), .i_nin(nin),
        .i_asrc(asrc), .i_bsrc(bsrc), .i_csrc(csrc), .i_dsrc(dsrc),
        .i_abase(abase + ((asrc == SRC_VM) ? xo : {AW{1'b0}})), .i_aso(aso), .i_asi(asi), .i_aibase(aibase),
        .i_aind(aind),
        .i_bbase(bbase + ((bsrc == SRC_VM) ? xo : {AW{1'b0}})), .i_bso(bso), .i_bsi(bsi), .i_bhalf(bhalf),
        .i_cbase(cbase + ((csrc == SRC_VM) ? xo : {AW{1'b0}})), .i_cso(cso), .i_csi(csi), .i_cpair(cpair),
        .i_dbase(dbase + ((dsrc == SRC_VM) ? xo : {AW{1'b0}})), .i_dso(dso), .i_dsi(dsi),
        .i_arnd(arnd), .i_arelu(arelu), .i_amin(amin), .i_cclip(cclip),
        .i_m1(m1), .i_m2(m2), .i_qm(qm), .i_ad(ad), .i_sfu(sfu), .i_e1(e1), .i_e2(e2), .i_rnd(rnd),
        .i_dst(dst), .i_obase(obase + ((dst == DST_VM) ? oo : {AW{1'b0}})), .i_oso(oso), .i_osi(osi),
        .i_orow(orow),
        .i_red(red), .i_redsq(redsq), .i_redwhole(redwhole), .i_redtree(redtree), .i_redrnd(redrnd),
        .i_rbase(rbase + ((red != 2'd0) ? oo : {AW{1'b0}})), .i_rso(rso),
        .i_imm1(imm1), .i_imm2(imm2), .i_imm3(imm3),
        //: a chasing op (every copy) waits for the completion of the op accepted before it
        .i_ch_src(wait_prev ? CH_SELF : CH_NONE), .i_ch_seq(prev_seq), .i_ch_lead(16'hFFFF), .i_ch_mul(16'd0),
        .x_seq(8'd0), .x_dseq(8'hFF), .x_cnt(16'd0),
        .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq), .cr_cnt(cr_cnt),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q),
        .rd_addr(rd_addr), .rd_re(rd_re), .rd_src(rd_src), .rd_q(rd_q),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .res_we(res_we), .res_addr(res_addr), .res_data(res_data),
        .fault(v_fault), .order_fault(v_ofault), .emitted(emitted), .retire_o(retire_o),
        .dbg_emit(dbg_emit), .dbg_eseq(dbg_eseq), .dbg_ret(dbg_ret), .dbg_rseq(dbg_rseq),
        .dbg_res(dbg_res), .dbg_sseq(dbg_sseq));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else fault <= v_fault || v_ofault;
    end
    // Activation counters: accepted ops and elements written by the vector unit.
    integer ci;
    reg [31:0] written;
    always @(*) begin
        written = 0;
        for (ci = 0; ci < N; ci = ci + 1) written = written + vm_we[ci] + kv_we[ci];
        for (ci = 0; ci < N / 8; ci = ci + 1) written = written + res_we[ci];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin dbg_ops <= 0; dbg_elems <= 0; end
        else begin
            if (v_acc) dbg_ops <= dbg_ops + 1;
            dbg_elems <= dbg_elems + written;
        end
    end
endmodule
