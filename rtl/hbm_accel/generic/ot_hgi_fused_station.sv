`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 FUSED station in the quant block (hgi-1010/c2, 2026-10-10; AUDIT N5, lead / hbm-phys: FUSED is hosted in hb_quant
// on lane group lgE, slot 2).  The die form of the e2e bench's hgi_e2e_fused_slot + the quant unit behind it:
//   * ot_hgi_fused_record (UNIT 1, UWIDE): unit 4's record (the CP's FUSED field set, 1,216 b) -> ROW_NORM / HC_PRE_NORM /
//     HC_POST on its internal stream unit; QDQ_* forwarded on q_rec to
//   * ot_hgi_quant_unit (unchanged; its own VM packet client), whose {done, fault} return to the FUSED front;
//   * the FUSED unit's own ot_hgi_dma_mover (the gain LOAD HBM BF16 -> VM scratch) with
//       - its HBM side on a REMOTE kport read lane (ot_hgi_hbm_rdq_client here, ot_hgi_hbm_rdq_server on one loader kport (peers/ot_hgi_hbm_rdq.sv)
//         lane): xq {addr 37, v} / xr {data 256, v}, up to Q sectors in flight, credit = the client's in-flight count
//         against the server's Q-deep queue (no back-pressure crosses the die);
//       - its VM packet client (die client 'fmv');
//       - its VM wide-write lane wl carried on the FUSED station's lgE WRITE group (lane b = bank b = sector mod 32, the
//         same {v, sector 15, data 256, mask 8} word): the station takes the write group for the whole move before the
//         mover sees the move (so no other lgE client holds the lanes while wl runs unthrottled), per-lane credits LQ,
//         wl_done = the lane write dones (in the macro), serialised one a cycle; a 16-deep landing FIFO, fail-closed on
//         overflow (k_fault -> the move faults -> the FUSED record faults).  Contiguous destination sectors rotate over
//         the 32 lanes, so a lane sees one write every 32 sectors: its credits never run out at <= 1 sector a cycle;
//   * the FUSED body's own VM packet client (die client 'fused') and its wide lanes on lgE (read group: the body only;
//     write group: the body outside a move, the mover inside one -- FUSED issues them strictly in sequence).
// lgE tap packing (LSB first, ot_hgi_vm_lanestation local side, as the lgW taps of hfd_su / hfd_sfu):
//   rup {wrq 32 x 16, rg_req} 513 | rdn {wrr 32 x 257, wrq_cr 32, rg_gnt} 8,257 | wup {wwq 32 x 280, wg_req} 8,961 |
//   wdn {wwq_done 32, wwq_cr 32, wg_gnt} 65.
// Return {fault, done, ready} = the FUSED front's (the CP holds one credit for unit 4).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_fused_station #(
    parameter integer UN = 64, UM = 16, ULWB = 18,   // the measured wide FUSED body (UN64 UM16, local 2^18 words)
    parameter integer UWIDE = 1,
    parameter integer SCRATCH = 245760,       // the FUSED scratch: VM words [SCRATCH, SCRATCH + SCR_WORDS), a static compiler
    parameter integer SCR_WORDS = 16384,      //   reservation (no MD word carries it yet: open, lead / e); a record that needs more
                                              //   faults (F10 fail-closed: DS HC_PRE_NORM d 5,120 needs 10,242)
    parameter integer Q = 32,                 // remote kport lane: sectors in flight (= the server queue depth)
    parameter integer LQ = 32,                // lane-group credits a lane (the VM unit's lane queue depth)
    parameter integer QWIDE = 0,              // 1: the quant unit's WIDE body (ot_hgi_quant_wide, 2628ec01a) on the same lgE
                                              //    slot (FUSED forwards one QDQ and waits: the three sources never overlap)
    parameter integer HCE = 0,                // 2 (the die): d = 5120 HC_POST / HC_PRE_NORM go to hfd_hc_eng over ne_o / ne_i
    parameter integer HLL = 0,                //   (ot_hgi_fused_record HCE 2; the lane-local engine's compiler rules apply)
    parameter integer MUT = 0                 // bench mutants: 1 the wl lane index from sector bits [5:1] (wrong bank)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1215:0] rec,                 // {n_O, n_B, n_A, O, C, B, A, header, valid}
    output wire [2:0]    ret,                 // {fault, done, ready}
    output wire [337:0]  q_vmq,               // the quant unit's VM packet client
    input  wire [273:0]  q_vmr,
    output wire [337:0]  f_vmq,               // the FUSED body's VM packet client
    input  wire [273:0]  f_vmr,
    output wire [337:0]  m_vmq,               // the FUSED mover's VM packet client
    input  wire [273:0]  m_vmr,
    output wire [512:0]  lg_rup,
    input  wire [8256:0] lg_rdn,
    output wire [8960:0] lg_wup,
    input  wire [64:0]   lg_wdn,
    output wire [37:0]   xq,                  // remote kport read lane
    input  wire [256:0]  xr,
    output wire [150:0]  ne_o,                // die net fused_ne:   {g_rdy, job_v, job 149} to hfd_hc_eng
    input  wire [2:0]    ne_i                 // die net fused_ne_r: {job_rdy, fault, done}
);
    // ---- FUSED front
    wire f_rdy, f_done, f_fault, mv_v, mv_rdy, mv_done, mv_fault; wire [226:0] mv;
    wire [682:0] q_rec; wire [2:0] q_ret; reg qph; reg mph; wire qsel = (QWIDE != 0) && qph;
    wire [32*16-1:0] f_wrq; wire [32*280-1:0] f_wwq; wire f_rg_req, f_wg_req, f_wg_gnt;
    // the body sees lane-group credits / responses / dones only while it owns slot 2: the mover phase (mph) and a forwarded
    // QDQ (qsel) use the same slot, and their returns must not reach the body's per-lane counters (a gain LOAD's 16 dones
    // a lane wrapped the body's pending-write count and hung its drain)
    wire f_rown = !qsel, f_wown = !mph && !qsel;
    wire [31:0] f_rcr = f_rown ? lg_rdn[32:1] : 32'd0;
    wire [32*257-1:0] f_rr = f_rown ? lg_rdn[8256:33] : '0;
    wire [31:0] f_wcr = f_wown ? lg_wdn[32:1] : 32'd0;
    wire [31:0] f_wdone = f_wown ? lg_wdn[64:33] : 32'd0;
    ot_hgi_fused_record #(.UNIT(1), .UN(UN), .UM(UM), .UWIDE(UWIDE), .ULWB(ULWB), .SCR_WORDS(SCR_WORDS), .HCE(HCE), .HLL(HLL)) u_f (.clk(clk), .rst_n(rst_n),
        .cfg_scratch(18'(SCRATCH)), .rec_v(rec[0]), .rec_rdy(f_rdy), .rec_hdr(rec[128:1]), .rec_a(rec[384:129]),
        .rec_b(rec[640:385]), .rec_c(rec[896:641]), .rec_o(rec[1152:897]), .rec_n_a(rec[1173:1153]),
        .rec_n_b(rec[1194:1174]), .rec_n_o(rec[1215:1195]), .rec_done(f_done), .rec_fault(f_fault), .halted(),
        .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done), .mv_fault(mv_fault),
        .op_v(), .op_rdy(1'b0), .op_w(), .su_idle(1'b1), .su_fault(1'b0), .vmq(f_vmq), .vmr(f_vmr),
        .wrq(f_wrq), .wrq_cr(f_rcr), .wrr(f_rr), .wwq(f_wwq), .wwq_cr(f_wcr),
        .wwq_done(f_wdone), .rg_req(f_rg_req), .rg_gnt(lg_rdn[0] && !qsel), .wg_req(f_wg_req), .wg_gnt(f_wg_gnt),
        .ne_v(ne_o[149]), .ne_rdy(ne_i[2]), .ne_job(ne_o[148:0]), .ne_g(ne_o[150]), .ne_done(ne_i[0]), .ne_fault(ne_i[1]), .q_rec(q_rec), .q_done(q_ret[1]),
        .q_fault(q_ret[2]));
    assign ret = {f_fault, f_done, f_rdy};
    assign lg_rup = qsel ? {q_wrq, q_rg_req} : {f_wrq, f_rg_req};
    // ---- quant unit (QDQ behind the FUSED front)
    wire [32*16-1:0] q_wrq; wire [32*280-1:0] q_wwq; wire q_rg_req, q_wg_req;
    ot_hgi_quant_unit #(.WIDE(QWIDE), .WLQ(LQ)) u_q (.clk(clk), .rst_n(rst_n), .rec(q_rec), .ret(q_ret), .vmq(q_vmq),
        .vmr(q_vmr), .wrq(q_wrq), .wrq_cr(QWIDE ? lg_rdn[32:1] : 32'd0), .wrr(QWIDE ? lg_rdn[8256:33] : {32*257{1'b0}}),
        .wwq(q_wwq), .wwq_cr(QWIDE ? lg_wdn[32:1] : 32'd0), .wwq_done(QWIDE ? lg_wdn[64:33] : 32'd0), .rg_req(q_rg_req),
        .rg_gnt(QWIDE ? (lg_rdn[0] && qph) : 1'b1), .wg_req(q_wg_req), .wg_gnt(QWIDE ? (lg_wdn[0] && qph) : 1'b1));
    always @(posedge clk or negedge rst_n)        // a forwarded QDQ owns the lanes until its done / fault
        if (!rst_n) qph <= 1'b0; else if (q_ret[1] || q_ret[2]) qph <= 1'b0; else if (q_rec[0]) qph <= 1'b1;
    // ---- the move phase: the write group is held from the move's request to its done / fault
    // mph                                    // a move is pending or running: the write group belongs to the mover
    wire own = mph && lg_wdn[0];
    wire m_v = mv_v && own;
    wire m_rdy;
    assign mv_rdy = m_rdy && own;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) mph <= 1'b0;
        else if (mv_done || mv_fault) mph <= 1'b0;
        else if (mv_v) mph <= 1'b1;
    assign f_wg_gnt = lg_wdn[0] && !mph && !qsel;
    // ---- mover + remote lane client
    wire k_req_v, k_req_rdy, k_req_we, k_rsp_v; wire [36:0] k_addr; wire [255:0] k_wd, k_rd; wire [31:0] k_ws;
    wire [15:0] k_tag; wire [279:0] wl; reg wl_done; wire k_flt; reg ov;
    // the mover's HBM loads: main's mover bursts on four per-stack lanes (r_*) and single sectors on k_*; the station has one
    // remote kport read lane, so ot_hgi_rlane_rdq serves both onto it in order (hbmdie-1011/bind)
    wire [3:0] r_v, r_rdy, r_we, r_rv, r_rrdy, r_rl; wire [4*37-1:0] r_a; wire [15:0] r_len; wire [63:0] r_tg, r_rtg;
    wire [4*256-1:0] r_wd, r_rd; wire [127:0] r_ws; wire c_v, c_rdy, c_we, c_rv, a_flt; wire [36:0] c_a; wire [255:0] c_rd;
    ot_hgi_dma_mover u_mv (.clk(clk), .rst_n(rst_n), .mv_v(m_v), .mv_rdy(m_rdy), .mv(mv), .mv_done(mv_done),
        .mv_fault(mv_fault), .mv_src(), .fence_v(1'b0), .fence_rdy(), .fence_done(),
        .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_addr), .k_req_wdata(k_wd),
        .k_req_wstrb(k_ws), .k_req_tag(k_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(), .k_rsp_we(1'b0), .k_rsp_data(k_rd),
        .k_fault(k_flt | ov | a_flt),
        .r_req_v(r_v), .r_req_rdy(r_rdy), .r_req_addr(r_a), .r_req_len(r_len), .r_req_tag(r_tg), .r_req_we(r_we),
        .r_req_wdata(r_wd), .r_req_wstrb(r_ws), .r_rsp_v(r_rv), .r_rsp_we(4'd0), .r_rsp_rdy(r_rrdy), .r_rsp_tag(r_rtg),
        .r_rsp_last(r_rl), .r_rsp_data(r_rd), .vr2q(), .vr2r(8257'd0),
        .vmq(m_vmq), .vmr(m_vmr), .wl(wl), .wl_done(wl_done));
    ot_hgi_rlane_rdq #(.D(Q)) u_rl (.clk(clk), .rst_n(rst_n), .r_req_v(r_v), .r_req_rdy(r_rdy), .r_req_addr(r_a),
        .r_req_len(r_len), .r_req_tag(r_tg), .r_req_we(r_we), .r_rsp_v(r_rv), .r_rsp_rdy(r_rrdy), .r_rsp_tag(r_rtg),
        .r_rsp_last(r_rl), .r_rsp_data(r_rd), .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we),
        .k_req_addr(k_addr), .k_rsp_v(k_rsp_v), .k_rsp_data(k_rd), .c_req_v(c_v), .c_req_rdy(c_rdy), .c_req_we(c_we),
        .c_req_addr(c_a), .c_rsp_v(c_rv), .c_rsp_data(c_rd), .fault(a_flt));
    ot_hgi_hbm_rdq_client #(.Q(Q)) u_cl (.clk(clk), .rst_n(rst_n), .req_v(c_v), .req_rdy(c_rdy), .req_we(c_we),
        .req_addr(c_a), .rsp_v(c_rv), .rsp_data(c_rd), .fault(k_flt), .xq(xq), .xr(xr));
    // ---- wl -> the lgE write group (landing FIFO, per-lane credits)
    localparam integer FD = 16;
    reg [279:0] fq [0:FD-1]; reg [4:0] fn; reg [3:0] fh, ft;
    reg [5:0] cr [0:31];                        // credits a lane
    reg [32*280-1:0] wq; reg wreq;
    reg [10:0] dpend;                           // lane dones not yet passed to the mover
    wire [279:0] hd = fq[fh];
    wire [4:0] hl = (MUT == 1) ? hd[269:265] : hd[268:264];   // sector bits [4:0] = the bank = the lane
    wire pop = mph && own && fn != 5'd0 && cr[hl] != 6'd0;
    integer b; reg [5:0] nd;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fn <= 5'd0; fh <= 4'd0; ft <= 4'd0; wq <= '0; wreq <= 1'b0; dpend <= 11'd0; wl_done <= 1'b0; ov <= 1'b0;
            for (b = 0; b < 32; b = b + 1) cr[b] <= 6'(LQ);
        end else begin
            wreq <= mph;
            wq <= '0;
            if (wl[279]) begin
                fq[ft] <= wl; ft <= ft + 4'd1;
                if (fn == 5'(FD) && !pop) ov <= 1'b1;        // fail closed: the move faults
            end
            fn <= fn + (wl[279] ? 5'd1 : 5'd0) - (pop ? 5'd1 : 5'd0);
            if (pop) begin
                fh <= fh + 4'd1;
                wq[hl*280 +: 280] <= hd;
            end
            for (b = 0; b < 32; b = b + 1)
                cr[b] <= cr[b] + (mph && lg_wdn[1 + b] ? 6'd1 : 6'd0) - ((pop && hl == b[4:0]) ? 6'd1 : 6'd0);
            nd = 6'd0;
            for (b = 0; b < 32; b = b + 1) nd = nd + (mph && lg_wdn[33 + b] ? 6'd1 : 6'd0);
            dpend <= dpend + 11'(nd) - ((dpend != 11'd0) ? 11'd1 : 11'd0);
            wl_done <= dpend != 11'd0;
            if (!mph) ov <= 1'b0;
        end
    end
    assign lg_wup = mph ? {wq, wreq} : qsel ? {q_wwq, q_wg_req} : {f_wwq, f_wg_req};
endmodule

`default_nettype wire
