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
module ot_dsrom_wfc_tok_r3 #(
    parameter integer FLIT   = 512,
    parameter integer NW     = 21,
    parameter integer USER_W = 10,
    parameter integer UCW    = 10,      // the WFC's cfg_users width
    parameter integer MAXU   = 8,       // users with a draft block
    parameter integer PU     = 8,       // users with prompt memory
    parameter integer PMAX   = 16,      // prompt positions per user
    parameter integer G      = 5,
    parameter integer HARD_READ = 0 // off by default; separate four-edge master
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
    generate if (HARD_READ == 0) begin : legacy_read
    // DR5: selected entry + identity captured together; tag compare/output one cycle later.
    reg [TW-1:0] e;
    reg e_v, read_v, u_ok;
    reg [NW-PB-1:0] read_hi;
    reg [3:0] read_ep;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) read_v<=0; else read_v<=pr_re;
    always @(posedge clk) if(pr_re) begin
        e<=tb[pr_user[UB-1:0]*PMAX+pr_pos[PB-1:0]];
        e_v<=tv[pr_user[UB-1:0]*PMAX+pr_pos[PB-1:0]];
        u_ok<=(pr_user>>UB)==0;read_hi<=pr_pos[NW-1:PB];read_ep<=pr_blk;
    end
    wire hit=u_ok && e_v && e[NW+:NW-PB]==read_hi
`ifndef OT_WFCTOK_MUT_NOEPOCH
              && (e[TW-1] || e[TW-2-:4]==read_ep)
`endif
              ;
    always @(posedge clk) if(read_v) begin pr_qk<=hit;pr_q<=e[NW-1:0];end    end else begin : hard_read
        // E1: request lands directly at pin registers. E2: each user reads
        // one of 16 slots. E3: select one of eight users. E4: tag/output.
        // Read/write collision semantics are the E2 table snapshot; callers
        // fence DRAFT visibility before issuing a dependent prompt request.
        reg [PB-1:0] pos_q;
        reg [UB-1:0] user_q, user_b;
        reg ok_q, ok_b, ok_e;
        reg [NW-PB-1:0] hi_q, hi_b, hi_e;
        reg [3:0] ep_q, ep_b, ep_e;
        reg [2:0] valid_pipe;
        reg [TW:0] bank [0:MAXU-1];
        reg [TW:0] entry_q;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) valid_pipe <= 0;
            else valid_pipe <= {valid_pipe[1:0],pr_re};
        always @(posedge clk) begin
            pos_q <= pr_pos[PB-1:0]; user_q <= pr_user[UB-1:0];
            ok_q <= pr_user < MAXU; hi_q <= pr_pos[NW-1:PB]; ep_q <= pr_blk;
            user_b <= user_q; ok_b <= ok_q; hi_b <= hi_q; ep_b <= ep_q;
            entry_q <= bank[user_b]; ok_e <= ok_b; hi_e <= hi_b; ep_e <= ep_b;
        end
        for (genvar u = 0; u < MAXU; u = u + 1) begin : bank_read
            always @(posedge clk) bank[u] <= {tv[u*PMAX+pos_q],tb[u*PMAX+pos_q]};
        end
        wire hard_hit = ok_e && entry_q[TW] && entry_q[NW+:NW-PB] == hi_e
`ifndef OT_WFCTOK_MUT_NOEPOCH
            && (entry_q[TW-1] || entry_q[TW-2-:4] == ep_e)
`endif
            ;
        always @(posedge clk) if (valid_pipe[2]) begin
            pr_qk <= hard_hit; pr_q <= entry_q[NW-1:0];
        end
    end endgenerate

endmodule

module dsfd_wfc_tok_r3 #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10, parameter integer UCW = 10,
    parameter integer MAXU = 8, parameter integer PU = 8, parameter integer PMAX = 16, parameter integer G = 5
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rst,
    input  wire [2+USER_W+2*NW:0] f_c,       // {we, sel[1:0], user, pos, val} static configuration
    output wire [UCW+2*NW-1:0] t_cfg,        // {users, plen, glen} to the WFC cfg_* (flops)
    input  wire [FLIT:0]     f_dw,           // {v, DRAFT flit} from dsfd_wfc_lnk
    input  wire [USER_W+NW+4:0] f_pr,        // {re, user, pos, blk} from the WFC (fixed one-edge read)
    output wire [NW:0]       t_pr,           // {qk, q} (flops)
    output wire [0:0]        t_ft
);
    wire clk = ck[0];
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));
    reg [2+USER_W+2*NW:0] c_q; always @(posedge clk) c_q <= f_c;
    wire [UCW-1:0] cu; wire [NW-1:0] cp, cg, q; wire qk, fl;
    ot_dsrom_wfc_tok_r3 #(.FLIT(FLIT), .NW(NW), .USER_W(USER_W), .UCW(UCW), .MAXU(MAXU), .PU(PU), .PMAX(PMAX), .G(G)) u_tok (
        .clk(clk), .rst_n(rn), .c_we(c_q[2+USER_W+2*NW]), .c_sel(c_q[USER_W+2*NW +: 2]), .c_user(c_q[2*NW +: USER_W]),
        .c_pos(c_q[NW +: NW]), .c_val(c_q[NW-1:0]), .cfg_users(cu), .cfg_prompt_len(cp), .cfg_gen_len(cg),
        .dw_v(f_dw[FLIT]), .dw_d(f_dw[FLIT-1:0]),
        .pr_re(f_pr[USER_W+NW+4]), .pr_user(f_pr[NW+4 +: USER_W]), .pr_pos(f_pr[4 +: NW]), .pr_blk(f_pr[3:0]),
        .pr_q(q), .pr_qk(qk), .fault(fl));
    assign t_cfg = {cu, cp, cg};
    assign t_pr = {qk, q};
    assign t_ft = fl;
endmodule

// Separate opt-in physical master; original and r3 defaults remain unchanged.
module dsfd_wfc_tok_hard (
    input wire [0:0] ck, rst,
    input wire [54:0] f_c, output wire [51:0] t_cfg,
    input wire [512:0] f_dw, input wire [35:0] f_pr,
    output wire [21:0] t_pr, output wire [0:0] t_ft
);
    wire rn;
    ot_dsrom_mtp_rstsync rs (.clk(ck[0]),.rst_n_async(rst[0]),.rst_n(rn));
    reg [54:0] c_q; always @(posedge ck[0]) c_q <= f_c;
    wire [9:0] cu; wire [20:0] cp,cg,q; wire qk,ft;
    ot_dsrom_wfc_tok_r3 #(.HARD_READ(1)) tok (
        .clk(ck[0]),.rst_n(rn),.c_we(c_q[54]),.c_sel(c_q[52+:2]),
        .c_user(c_q[42+:10]),.c_pos(c_q[21+:21]),.c_val(c_q[20:0]),
        .cfg_users(cu),.cfg_prompt_len(cp),.cfg_gen_len(cg),
        .dw_v(f_dw[512]),.dw_d(f_dw[511:0]),.pr_re(f_pr[35]),
        .pr_user(f_pr[25+:10]),.pr_pos(f_pr[4+:21]),.pr_blk(f_pr[3:0]),
        .pr_q(q),.pr_qk(qk),.fault(ft));
    assign t_cfg={cu,cp,cg}; assign t_pr={qk,q}; assign t_ft=ft;
endmodule
