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
// pr_qk = 1 when the token at (user, pos) is KNOWN for draft block pr_blk (direct-mapped table, below):
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

    // static configuration
    always @(posedge clk) if (c_we) begin
        case (c_sel)
            2'd0: cfg_users <= c_val[UCW-1:0];
            2'd1: cfg_prompt_len <= c_val;
            2'd2: cfg_gen_len <= c_val;
            default: ;
        endcase
    end

    // DIRECT-MAPPED token table (route r1 missed -817 ps on the one-edge read through prompt mux + draft compares):
    // one entry per (user, pos[PB-1:0]) = {valid, prompt, epoch, pos high bits, token}; a prompt token or a draft
    // lands in the slot of its position.  Read = one PU*PMAX:1 select of the entry + a tag compare (pos high bits;
    // epoch unless the entry is a prompt token).  A stale entry can only match a read with the same FULL position
    // and the same epoch: a rejected block's epoch is dead (the WFC reads with the new one), an accepted block's
    // positions were all issued and are never read again; prompt slots are read only during the prefill, before the
    // first DRAFT write.  (The previous one-block-per-user form answered the same for every read the WFC makes.)
    localparam integer TW = 1 + 4 + (NW - PB) + NW;        // {prompt, epoch, pos high, token}; valid in tv
    localparam integer NE = MAXU * PMAX;
    reg [TW-1:0] tb [0:NE-1];
    reg [NE-1:0] tv;
    reg dv; reg [FLIT-1:0] dd;
    always @(posedge clk) begin dv <= dw_v && rst_n; dd <= dw_d; end       // pin flops
    wire [USER_W-1:0] d_u = USER_W'(dd[HDR_USER +: 8]) | (USER_W'(dd[HDR_USER_HI +: UHIW]) << 8);
    wire [NW-1:0]     d_b = dd[HDR_POS +: NW];
    integer i, k;
    function automatic [PB-1:0] dpk(input [NW-1:0] b, input integer kk); reg [NW-1:0] t; begin t = b + kk; dpk = t[PB-1:0]; end endfunction
    function automatic [NW-PB-1:0] dph(input [NW-1:0] b, input integer kk); reg [NW-1:0] t; begin t = b + kk; dph = t[NW-1:PB]; end endfunction
    always @(posedge clk) begin
        if (!rst_n) begin
            fault <= 1'b0;
        end
        if (c_we && c_sel == 2'd3 && c_user < MAXU && c_user < PU && c_pos < PMAX)
            tb[c_user * PMAX + c_pos[PB-1:0]] <= {1'b1, 4'd0, c_pos[NW-1:PB], c_val};
        if (rst_n && dv) begin
            if (dd[HDR_TYPE +: 4] != MT_DRAFT || d_u >= MAXU || dd[DR_N +: 3] > G) fault <= 1'b1;
            else for (k = 0; k < G; k = k + 1) if (k < dd[DR_N +: 3])
                tb[d_u[UB-1:0] * PMAX + dpk(d_b, k)] <= {1'b0, dd[HDR_ADDR +: 4], dph(d_b, k), dd[DR_D + k * NW +: NW]};
        end
    end
    // valid bits: the config port validates prompt slots (static, before reset release); a DRAFT validates its slots
    always @(posedge clk) begin
        if (c_we && c_sel == 2'd3 && c_user < MAXU && c_user < PU && c_pos < PMAX) tv[c_user * PMAX + c_pos[PB-1:0]] <= 1'b1;
        else if (c_we && c_sel == 2'd0) tv <= {NE{1'b0}};                  // cfg_users written first: clear
        if (rst_n && dv && dd[HDR_TYPE +: 4] == MT_DRAFT && d_u < MAXU && dd[DR_N +: 3] <= G)
            for (k = 0; k < G; k = k + 1) if (k < dd[DR_N +: 3]) tv[d_u[UB-1:0] * PMAX + dpk(d_b, k)] <= 1'b1;
    end
    // the read: one registered level from the WFC's flops
    wire [TW-1:0] e = tb[pr_user[UB-1:0] * PMAX + pr_pos[PB-1:0]];
    wire e_v = tv[pr_user[UB-1:0] * PMAX + pr_pos[PB-1:0]], e_p = e[TW-1];
    wire [3:0] e_ep = e[TW-2 -: 4];
    wire [NW-PB-1:0] e_hi = e[NW +: NW - PB];
    wire u_ok = (pr_user >> UB) == 0;
    wire hit = u_ok && e_v && e_hi == pr_pos[NW-1:PB]
`ifndef OT_WFCTOK_MUT_NOEPOCH
               && (e_p || e_ep == pr_blk)
`endif
               ;
    always @(posedge clk) if (pr_re) begin pr_qk <= hit; pr_q <= e[NW-1:0]; end
endmodule
