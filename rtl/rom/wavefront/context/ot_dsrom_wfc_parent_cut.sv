`timescale 1ns/1ps
// Minimum physical cut of the retained native parent controller boundary.
// Native port0 controller, port1 UCIE, port2 boardlink; same NP3/BUF4 router,
// reset release, and actual C8 mutable-state visibility gate. No new caller,
// completion/coverage authority, VM, prompt storage, or S81 wiring is created.
// core_done/data are the external source-held wf_stage_done/result bundle;
// configuration and VM/prompt producers remain external, as in the parent.
// This cut cannot qualify their launch/capture clocks without real binding.
// DECODED_READ stays default-off. No parent instantiates this candidate yet.
module ot_dsrom_wfc_parent_cut #(
    parameter integer DECODED_READ = 0,
    parameter integer LOCAL_CONTROL = 0, // opt-in same-edge control locality
    parameter integer PKG_ID       = 0,
    parameter integer FLIT         = 512,    // bits; one vector-memory word
    parameter integer NW           = 21,     // token / position bits
    parameter integer AW           = 30,     // KV address bits
    parameter integer VWA          = 15,      // vector-memory word address bits
    parameter integer MAXU         = 866,     // user contexts
    parameter integer USER_W       = 10,      // 10 for the full-shape 866-user namespace
    parameter integer KVW          = 32768,   // KV words per user
    parameter integer XWORDS       = 46,      // payload flits of a HIDDEN message
    parameter integer RXB          = 0,      // vector-memory word of received payload flit 0
    parameter integer TXB          = 0,      // vector-memory word of sent payload flit 0
    parameter integer SOURCE       = 0,      // 1: issues steps (embedding package), reduces RESULTs
    parameter integer RESULT_PARTS = 1,      // RESULTs per step reduced at the SOURCE
    parameter integer SEND_HIDDEN  = 1,
    parameter integer HID_DEST     = 1,
    parameter integer SEND_RESULT  = 0,
    parameter integer RES_DEST     = 0,
    parameter integer COMBINE_IN   = 0,      // fold the header's running argmax into ours
    parameter integer ROW0         = 0,      // vocabulary row of our lm_head part's row 0
    parameter integer TXQ          = 4,      // outbound queue, flits
    parameter integer RXWORDS      = 41,      // payload flits of a received HIDDEN message (0: XWORDS)
    parameter integer FWD_TOKEN    = 1,      // HIDDEN headers carry the token to the next core
    parameter integer SEND_SIDE    = 0,      // after HIDDEN, send a SIDE message
    parameter integer SIDE_DEST    = 0,
    parameter integer SIDE_WORDS   = 1,      // its payload flits, read from words SIDE_TXB..
    parameter integer SIDE_TXB     = 0,
    parameter integer SIDE_RXB     = 0,      // word address the receivers write it at (in the header)
    parameter integer SIDE_IN      = 0,      // SIDE messages each step waits for
    parameter integer SIDE_USH     = 10,     // per-user staging stride, log2 words
    parameter integer WAVE         = 1,      // 1: wavefront issue of known-token positions (SOURCE), rewind (all)
    parameter integer WIN          = 6       // WAVE: positions of one user in flight
,
    parameter integer DESTS = 64,
    parameter [DESTS*3-1:0] ROUTE_INIT = {DESTS*3{1'b0}}
) (
    input  wire               clk,
    input  wire               rst_n,
    // run configuration (SOURCE)
    input  wire [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] cfg_users,
    input  wire [NW-1:0]      cfg_prompt_len,
    input  wire [NW-1:0]      cfg_gen_len,
    // inbound link
    input  wire               in_valid,
    output reg                in_ready,
    input  wire [FLIT-1:0]    in_data,
    input  wire               in_last,
    // outbound link
    output wire               out_valid,
    input  wire               out_ready,
    output wire [FLIT-1:0]    out_data,
    output wire               out_last,
    // decode core
    output reg                core_start,
    output reg  [NW-1:0]      core_token,
    output reg  [NW-1:0]      core_pos,
    output wire [USER_W-1:0]  core_user,
    input  wire               core_done,
    input  wire [NW-1:0]      core_next_token,
    input  wire [31:0]        core_next_val,
    output reg  [AW-1:0]      kv_base,
    // vector memory, one word per access, synchronous read
    output reg                vm_we,
    output reg  [VWA-1:0]     vm_waddr,
    output wire [FLIT-1:0]    vm_wdata,
    output reg                vm_re,
    output reg  [VWA-1:0]     vm_raddr,
    input  wire [FLIT-1:0]    vm_rq,
    // prompt tokens (SOURCE), synchronous read
    output reg                pr_re,
    output reg  [USER_W-1:0]  pr_user,
    output reg  [NW-1:0]      pr_pos,
    input  wire [NW-1:0]      pr_q,
    output reg  [3:0]         pr_blk,         // WAVE: draft block of the read
    input  wire               pr_qk,          // WAVE: the read position's token is known
    // observation
    output wire               core_busy,
    output reg                tok_valid,      // SOURCE: a step's reduced token
    output reg  [USER_W-1:0]  tok_user,
    output reg  [NW-1:0]      tok_pos,
    output reg  [NW-1:0]      tok_id,
    output reg  [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] users_done,
    output reg                proto_fault,
    output reg                wf_issue,       // WAVE observation: a known-token issue this cycle
    output reg                wf_reject,      // a verified token was rejected
    output reg                wf_squash       // a squashed result was discarded
,
    input wire c8_write_quiet, c8_write_quarantine, c8_write_fault, coll_busy,
    input wire bl_rx_valid, bl_rx_last,
    input wire [FLIT-1:0] bl_rx_data,
    output wire bl_rx_ready,
    output wire bl_tx_valid, bl_tx_last,
    output wire [FLIT-1:0] bl_tx_data,
    input wire bl_tx_ready,
    input wire rcfg_we,
    input wire [7:0] rcfg_dest,
    input wire [2:0] rcfg_mask,
    output wire [31:0] rtr_drops,
    output wire rtr_overflow
);

    reg [1:0] rst_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rst_s <= 2'b00; else rst_s <= {rst_s[0],1'b1};
    wire rn = rst_s[1];
    wire wf_result_visible = c8_write_quiet && !c8_write_quarantine &&
                             !c8_write_fault && !coll_busy;
    wire pc_in_valid, pc_in_ready, pc_in_last;
    wire pc_out_valid, pc_out_ready, pc_out_last;
    wire [FLIT-1:0] pc_in_data, pc_out_data;
    wire [2:0] r_in_valid, r_in_ready, r_in_last;
    wire [2:0] r_out_valid, r_out_ready, r_out_last;
    wire [3*FLIT-1:0] r_in_data, r_out_data;
    assign r_in_valid = {bl_rx_valid, in_valid, pc_out_valid};
    assign r_in_data = {bl_rx_data, in_data, pc_out_data};
    assign r_in_last = {bl_rx_last, in_last, pc_out_last};
    assign pc_out_ready = r_in_ready[0];
    assign in_ready = r_in_ready[1];
    assign bl_rx_ready = r_in_ready[2];
    assign pc_in_valid = r_out_valid[0];
    assign pc_in_data = r_out_data[0 +: FLIT];
    assign pc_in_last = r_out_last[0];
    assign out_valid = r_out_valid[1];
    assign out_data = r_out_data[FLIT +: FLIT];
    assign out_last = r_out_last[1];
    assign bl_tx_valid = r_out_valid[2];
    assign bl_tx_data = r_out_data[2*FLIT +: FLIT];
    assign bl_tx_last = r_out_last[2];
    assign r_out_ready = {bl_tx_ready, out_ready, pc_in_ready};
    ot_rom_fabric_router #(.NP(3),.FW(FLIT),.BUF(4),.DESTS(DESTS),
        .INPUT_READY_VALID(1),.ROUTE_INIT(ROUTE_INIT)) u_rtr (
        .clk(clk),.rst_n(rn),
        .in_valid(r_in_valid),.in_ready(r_in_ready),.in_credit(),
        .in_data(r_in_data),.in_last(r_in_last),
        .out_valid(r_out_valid),.out_ready(r_out_ready),
        .out_data(r_out_data),.out_last(r_out_last),
        .cfg_we(rcfg_we),.cfg_dest(rcfg_dest),.cfg_mask(rcfg_mask),
        .drops(rtr_drops),.overflow(rtr_overflow));
    ot_rom_pkg_ctrl_wfc #(
        .DECODED_READ(DECODED_READ),
        .LOCAL_CONTROL(LOCAL_CONTROL),
        .PKG_ID(PKG_ID),
        .FLIT(FLIT),
        .NW(NW),
        .AW(AW),
        .VWA(VWA),
        .MAXU(MAXU),
        .USER_W(USER_W),
        .KVW(KVW),
        .XWORDS(XWORDS),
        .RXB(RXB),
        .TXB(TXB),
        .SOURCE(SOURCE),
        .RESULT_PARTS(RESULT_PARTS),
        .SEND_HIDDEN(SEND_HIDDEN),
        .HID_DEST(HID_DEST),
        .SEND_RESULT(SEND_RESULT),
        .RES_DEST(RES_DEST),
        .COMBINE_IN(COMBINE_IN),
        .ROW0(ROW0),
        .TXQ(TXQ),
        .RXWORDS(RXWORDS),
        .FWD_TOKEN(FWD_TOKEN),
        .SEND_SIDE(SEND_SIDE),
        .SIDE_DEST(SIDE_DEST),
        .SIDE_WORDS(SIDE_WORDS),
        .SIDE_TXB(SIDE_TXB),
        .SIDE_RXB(SIDE_RXB),
        .SIDE_IN(SIDE_IN),
        .SIDE_USH(SIDE_USH),
        .WAVE(WAVE),
        .WIN(WIN)) u_ctrl (
        .clk(clk),
        .rst_n(rn),
        .cfg_users(cfg_users),
        .cfg_prompt_len(cfg_prompt_len),
        .cfg_gen_len(cfg_gen_len),
        .in_valid(pc_in_valid),
        .in_ready(pc_in_ready),
        .in_data(pc_in_data),
        .in_last(pc_in_last),
        .out_valid(pc_out_valid),
        .out_ready(pc_out_ready),
        .out_data(pc_out_data),
        .out_last(pc_out_last),
        .core_start(core_start),
        .core_token(core_token),
        .core_pos(core_pos),
        .core_user(core_user),
        .core_done(core_done && wf_result_visible),
        .core_next_token(core_next_token),
        .core_next_val(core_next_val),
        .kv_base(kv_base),
        .vm_we(vm_we),
        .vm_waddr(vm_waddr),
        .vm_wdata(vm_wdata),
        .vm_re(vm_re),
        .vm_raddr(vm_raddr),
        .vm_rq(vm_rq),
        .pr_re(pr_re),
        .pr_user(pr_user),
        .pr_pos(pr_pos),
        .pr_q(pr_q),
        .pr_blk(pr_blk),
        .pr_qk(pr_qk),
        .core_busy(core_busy),
        .tok_valid(tok_valid),
        .tok_user(tok_user),
        .tok_pos(tok_pos),
        .tok_id(tok_id),
        .users_done(users_done),
        .proto_fault(proto_fault),
        .wf_issue(wf_issue),
        .wf_reject(wf_reject));
endmodule
