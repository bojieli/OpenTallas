`timescale 1ns/1ps
`default_nettype none
// hbm-forks 2026-10-09: the HGI-1 COMMAND PROCESSOR of the generic HBM die (docs/HBM_GENERIC_INTERFACE.md 2.2, 5.5):
// the configuration path (ot_hgi_cfg_master: CFG window on the host write port, CFG_COMMIT busy / range check, config
// bus, settle hold-off, CFG_STATUS; ot_hgi_cfg_rx: cp_vocab / cp_ctx_max active words) + the record sequencer
// (ot_hgi_seq, v1.0 normative, with indexed descriptors, CTL.TOKX and the 18-bit token).  This replaces the LAUNCH-list
// TOKEN18 core (ot_hgi_cmdproc) on the die: DS runs native unit records too (no kernel engine on r25).
// Registered boundary: the host write port and units_busy land in pin flops here; the sequencer registers its own.
//   host write: cmd_addr[5] = CFG window; cmd_addr[4:0] = descriptor word pair (2a, 2a+1); window + 5'h1F = CFG_COMMIT.
module ot_hgi_cp #(
    parameter integer SETTLE = 64,
    parameter integer RW = 512,
    parameter integer USE_MACRO = 1,
    parameter integer FETCH_PIN_FIFO = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // host write port (CFG window)
    input  wire          cmd_we,
    input  wire [5:0]    cmd_addr,
    input  wire [63:0]   cmd_wdata,
    input  wire          units_busy,     // any unit queue non-empty outside this block (E_BUSY)
    output wire [39:0]   cfg_bus,        // to the first config-bus station
    output wire          cfg_loaded,
    output wire [2:0]    cfg_err,
    output wire [63:0]   cfg_cp_act,     // active words 40-41 (CF-0 read-back)
    input  wire [7:0]    rank,
    // doorbell
    input  wire          db_v,
    output wire          db_rdy,
    input  wire [17:0]   db_token,
    input  wire [19:0]   db_pos,
    input  wire [31:0]   db_job,
    input  wire [3:0]    db_gen,
    input  wire [1:0]    db_entry,
    input  wire [3:0]    db_ncol,
    input  wire [3:0]    db_kernel,     // G23 KERNEL entry index (entry 3)
    // record fetch, VM read, dispatch, retire (ot_hgi_seq)
    output wire          f_req_v,
    input  wire          f_req_rdy,
    output wire [39:0]   f_req_addr,
    input  wire          f_rsp_v,
    input  wire [255:0]  f_rsp_data,
    output wire          vr_v,
    input  wire          vr_rdy,
    output wire [17:0]   vr_addr,
    input  wire          vr_rsp_v,
    input  wire [31:0]   vr_rsp_data,
    output wire [15:0]   u_v,
    input  wire [15:0]   u_rdy,
    output wire [127:0]  d_hdr,
    output wire [255:0]  d_sut,
    output wire [1791:0] d_desc,
    output wire [146:0]  d_n,
    output wire [20:0]   d_pos1,
    output wire [20:0]   d_pslot1,
    output wire [15:0]   d_L,
    output wire [15:0]   d_L1,
    input  wire [15:0]   u_done,
    input  wire [15:0]   u_fault,
    input  wire          wr_quiet,
    // completion
    output wire          cpl_v,
    input  wire          cpl_rdy,
    output wire [17:0]   cpl_token,
    output wire [19:0]   cpl_pos,
    output wire [31:0]   cpl_job,
    output wire [3:0]    cpl_gen,
    output wire [3:0]    cpl_status,
    output wire [31:0]   cpl_cycles,
    output wire          cpl_tokx
);
`include "ot_hgi_cfg_consts.svh"
    reg        we_q; reg [5:0] a_q; reg [63:0] wd_q; reg ub_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin we_q <= 1'b0; ub_q <= 1'b0; end
        else begin we_q <= cmd_we; ub_q <= units_busy; end
    always @(posedge clk) begin a_q <= cmd_addr; wd_q <= cmd_wdata; end
    wire win = a_q[5];
    wire c_commit = we_q && win && (a_q[4:0] == 5'h1F);
    wire c_wr = we_q && win;           // F1 (hgi_e2e 2026-10-09): the commit write stages MD words 62 / 63 too
    wire hold, seq_busy;
    wire [5*32-1:0] md_d; wire [11*32-1:0] md_k;
    ot_hgi_cfg_master #(.SETTLE(SETTLE)) u_cfg (.clk(clk), .rst_n(rst_n), .w_en(c_wr), .w_pair(a_q[4:0]),
        .w_data(wd_q), .commit(c_commit), .busy(ub_q || seq_busy), .bus(cfg_bus),
        .st_loaded(cfg_loaded), .st_err(cfg_err), .st_hold(hold), .md_d(md_d), .md_k(md_k));
    wire [2*32-1:0] cp_act;
    ot_hgi_cfg_rx #(.W0(40), .NW(2), .RST({HGI_RST_W41, HGI_RST_W40})) u_rx (.clk(clk), .rst_n(rst_n), .bus(cfg_bus),
        .act(cp_act));
    assign cfg_cp_act = cp_act;
    // The sequencer's rqf[rqh] is a mux, so it cannot be the die pin stage.
    // Two elastic slots put both address and valid on a register at the pin.
    // Ready reserves the back slot; downstream stalls never lose a request.
    wire sf_v, sf_rdy; wire [39:0] sf_addr;
    generate if (FETCH_PIN_FIFO) begin : g_fetch_pin
        (* keep = 1 *) reg [39:0] front_addr, back_addr;
        (* keep = 1 *) reg front_v, back_v;
        wire take_in = sf_v && sf_rdy;
        wire take_out = front_v && f_req_rdy;
        assign sf_rdy = !back_v;
        assign f_req_v = front_v;
        assign f_req_addr = front_addr;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin front_v <= 0; back_v <= 0; end
            else begin
                if (take_out) begin
                    front_v <= back_v || take_in;
                    back_v <= 0;
                end else if (take_in) begin
                    if (!front_v) front_v <= 1;
                    else back_v <= 1;
                end
            end
        always @(posedge clk) begin
            if (take_out && back_v) front_addr <= back_addr;
            else if (take_in && (!front_v || take_out)) front_addr <= sf_addr;
            if (take_in && front_v && !take_out) back_addr <= sf_addr;
        end
    end else begin : g_fetch_legacy
        assign f_req_v = sf_v;
        assign f_req_addr = sf_addr;
        assign sf_rdy = f_req_rdy;
    end endgenerate
    ot_hgi_seq #(.RW(RW), .USE_MACRO(USE_MACRO)) u_seq (.clk(clk), .rst_n(rst_n), .md_d(md_d),
        .cfg_vocab(cp_act[HGI_CP_VOCAB_L +: HGI_CP_VOCAB_N]), .cfg_ctx_max(cp_act[32 + HGI_CP_CTX_MAX_L +: HGI_CP_CTX_MAX_N]),
        .rank(rank), .hold(hold), .busy(seq_busy),
        .db_v(db_v), .db_rdy(db_rdy), .db_token(db_token), .db_pos(db_pos), .db_job(db_job), .db_gen(db_gen),
        .db_entry(db_entry), .db_ncol(db_ncol), .db_kernel(db_kernel), .md_k(md_k), .f_req_v(sf_v), .f_req_rdy(sf_rdy), .f_req_addr(sf_addr), .f_rsp_v(f_rsp_v),
        .f_rsp_data(f_rsp_data), .vr_v(vr_v), .vr_rdy(vr_rdy), .vr_addr(vr_addr), .vr_rsp_v(vr_rsp_v),
        .vr_rsp_data(vr_rsp_data), .u_v(u_v), .u_rdy(u_rdy), .d_hdr(d_hdr), .d_sut(d_sut), .d_desc(d_desc), .d_n(d_n),
        .d_pos1(d_pos1), .d_pslot1(d_pslot1), .d_L(d_L), .d_L1(d_L1), .u_done(u_done), .u_fault(u_fault),
        .wr_quiet(wr_quiet), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy), .cpl_token(cpl_token), .cpl_pos(cpl_pos),
        .cpl_job(cpl_job), .cpl_gen(cpl_gen), .cpl_status(cpl_status), .cpl_cycles(cpl_cycles), .cpl_tokx(cpl_tokx));
endmodule
`default_nettype wire
