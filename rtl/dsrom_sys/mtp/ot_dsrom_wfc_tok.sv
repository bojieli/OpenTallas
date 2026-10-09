`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_wfc_tok: the WFC's cfg / prompt-port producer with the MTP draft-block store (stream mtp-rom,
// 2026-10-08; WFC integration binding 2 of 4, "cfg_* pr_*").
//
// The closed SOURCE WFC (ot_rom_pkg_ctrl_wfc, WAVE 1, CFG_Q 1) reads
//   cfg_users / cfg_prompt_len / cfg_gen_len   static while users are in flight, stable >= 1 edge before reset
//                                              release (CFG_Q registers them): driven here from flops;
//   pr_re / pr_user / pr_pos / pr_blk -> pr_q / pr_qk   a synchronous read: the response is taken on the edge
//                                              after the one that launched pr_re (fixed, not latency-insensitive),
//                                              so this block answers from flops through one registered level.
// pr_qk = 1 when the token at (user, pos) is KNOWN for draft block pr_blk:
//   * a prompt token: pos < plen (prompt memory, PU users x PMAX positions, written by the config port);
//   * a draft: user < MAXU, pr_blk == the user's stored epoch and base <= pos < base + n (the DRAFT flit of
//     ot_dsrom_mtp_seq, delivered by ot_dsrom_wfc_lnk on dw_*).  base + k is precomputed per entry at write
//     time, so the read is an equality compare + one-hot select (no adder on the read path).
// pr_qk = 0 otherwise: the WFC then lets the argmax decide (autoregressive), which is always exact.
// A DRAFT write is visible to a read launched >= 2 cycles after dw_v (dw pin flop + entry write); the link
// shim holds the next flit for that long, and the WFC needs >= 4 more cycles before it can read.
//
// Config port (static, before reset release): c_sel 0 users, 1 plen, 2 glen, 3 prompt token (c_user, c_pos).
// Mutant: OT_WFCTOK_MUT_NOEPOCH ignores the epoch compare (a stale block's draft would be reused).
// ---------------------------------------------------------------------------
module ot_dsrom_wfc_tok #(
    parameter integer FLIT   = 512,
    parameter integer NW     = 21,
    parameter integer USER_W = 10,
    parameter integer UCW    = 10,      // the WFC's cfg_users width
    parameter integer MAXU   = 8,       // users with a draft block
    parameter integer PU     = 8,       // users with prompt memory
    parameter integer PMAX   = 16,      // prompt positions per user
    parameter integer G      = 5
) (
    input  wire              clk,
    input  wire              rst_n,
    // static configuration
    input  wire              c_we,
    input  wire [1:0]        c_sel,
    input  wire [USER_W-1:0] c_user,
    input  wire [NW-1:0]     c_pos,
    input  wire [NW-1:0]     c_val,
    output reg  [UCW-1:0]    cfg_users,
    output reg  [NW-1:0]     cfg_prompt_len,
    output reg  [NW-1:0]     cfg_gen_len,
    // DRAFT flits (from ot_dsrom_wfc_lnk)
    input  wire              dw_v,
    input  wire [FLIT-1:0]   dw_d,
    // WFC prompt port
    input  wire              pr_re,
    input  wire [USER_W-1:0] pr_user,
    input  wire [NW-1:0]     pr_pos,
    input  wire [3:0]        pr_blk,
    output reg  [NW-1:0]     pr_q,
    output reg               pr_qk,
    output reg               fault
);
    localparam integer HDR_TYPE = 16, HDR_USER = 32, HDR_POS = 40, HDR_IDX = HDR_POS + NW, HDR_VAL = HDR_IDX + NW,
                       HDR_TOK = HDR_VAL + 32, HDR_ADDR = HDR_TOK + NW, HDR_USER_HI = HDR_ADDR + 16;
    localparam integer UHIW = (USER_W > 8) ? USER_W - 8 : 1;
    localparam integer DR_N = 248, DR_D = 256;
    localparam [3:0] MT_DRAFT = 4'd4;
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam integer PB = (PMAX > 1) ? $clog2(PMAX) : 1;

    // static configuration + prompt memory
    reg [NW-1:0] pm [0:PU*PMAX-1];
    always @(posedge clk) if (c_we) begin
        case (c_sel)
            2'd0: cfg_users <= c_val[UCW-1:0];
            2'd1: cfg_prompt_len <= c_val;
            2'd2: cfg_gen_len <= c_val;
            default: if (c_user < PU && c_pos < PMAX) pm[c_user * PMAX + c_pos] <= c_val;
        endcase
    end

    // DRAFT write: pin flop, then the entry (base + k precomputed)
    reg dv; reg [FLIT-1:0] dd;
    always @(posedge clk) begin dv <= dw_v && rst_n; dd <= dw_d; end
    wire [USER_W-1:0] d_u = USER_W'(dd[HDR_USER +: 8]) | (USER_W'(dd[HDR_USER_HI +: UHIW]) << 8);
    wire [NW-1:0]     d_b = dd[HDR_POS +: NW];
    reg [3:0]    e_ep [0:MAXU-1];
    reg [G-1:0]  e_vk [0:MAXU-1];                 // slot k valid (k < n)
    reg [NW-1:0] e_bk [0:MAXU*G-1];               // base + k
    reg [NW-1:0] e_tk [0:MAXU*G-1];
    integer i, k;
    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < MAXU; i = i + 1) begin e_vk[i] <= {G{1'b0}}; e_ep[i] <= 4'd0; end
            fault <= 1'b0;
        end else if (dv) begin
            if (dd[HDR_TYPE +: 4] != MT_DRAFT || d_u >= MAXU || dd[DR_N +: 3] > G) fault <= 1'b1;
            else begin
                e_ep[d_u[UB-1:0]] <= dd[HDR_ADDR +: 4];
                for (k = 0; k < G; k = k + 1) begin
                    e_vk[d_u[UB-1:0]][k] <= k < dd[DR_N +: 3];
                    e_bk[d_u[UB-1:0] * G + k] <= d_b + k;
                    e_tk[d_u[UB-1:0] * G + k] <= dd[DR_D + k * NW +: NW];
                end
            end
        end
    end

    // the read: one registered level from the WFC's flops
    reg          hit;
    reg [NW-1:0] tok;
    always @(*) begin
        hit = 1'b0; tok = {NW{1'b0}};
        if (pr_user < PU && pr_pos < cfg_prompt_len && pr_pos < PMAX) begin
            hit = 1'b1; tok = pm[pr_user * PMAX + pr_pos[PB-1:0]];
        end else if (pr_user < MAXU
`ifndef OT_WFCTOK_MUT_NOEPOCH
                     && e_ep[pr_user[UB-1:0]] == pr_blk
`endif
                     ) begin
            for (k = 0; k < G; k = k + 1)
                if (e_vk[pr_user[UB-1:0]][k] && e_bk[pr_user[UB-1:0] * G + k] == pr_pos) begin
                    hit = 1'b1; tok = e_tk[pr_user[UB-1:0] * G + k];
                end
        end
    end
    always @(posedge clk) if (pr_re) begin pr_qk <= hit; pr_q <= tok; end
endmodule
