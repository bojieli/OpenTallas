`timescale 1ns/1ps
// Separate hardened successor of closed src controller; no extra boundary registers.
module ot_dsrom_wfc_tokpipe_src #(
    parameter integer ENGRAM_REWIND = 0,
    parameter integer PROMPT_EXTRA = 0, // token HARD +2edges, off by default
    parameter integer DECODED_READ = 0,
    parameter integer HEADER_LOCAL = 0, // local RX release +1 reset admission edge
    parameter integer PREFIX_INC = 0, // explicit balanced position carry
    parameter integer QUEUE_SHIFT = 0, // priced same-edge constant-head TXQ
    parameter integer CONTROL_PIPE = 1, // priced completion/start capture, default off
    parameter integer LOCAL_CONTROL = 0, // opt-in same-edge control locality
    parameter integer REC_SRAM = 1,   // SOURCE engine: per-user record + issued-token ring in 1R1W SRAM macros (0 cycles)
    parameter integer UPOS_LWR = 1,   // upos groups: registered local write strobe / data copies (0 cycles)
    // CFG_Q: the run configuration (static while users are in flight; stable >= 1 edge before rst_n
    // releases) is registered at the boundary, and the SOURCE engine's steps / steps - 1 are a
    // 2-edge log-depth pipeline from it (0 cycles: every one of those registers settles during reset)
    parameter integer CFG_Q = 1,
    // PRECOMP: compares / increments of values that are stable for >= 1 cycle before use are taken
    // from registers loaded one edge earlier, and the remaining counters use log-depth increments (0 cycles)
    parameter integer PRECOMP = 1,
    // IN_DEC: in_ready / rx_* as a final AND-OR of the decoded inbound type over state-only readiness
    // terms (kept nets), so the link's type bits pass two gate levels to in_ready (0 cycles)
    parameter integer IN_DEC = 1,
    // TXQ_SLICE (needs CONTROL_PIPE): the outbound queue in 16 slices, each with its own copies of the
    // registered completion, read-in-flight, write and read pointers (one-hot), so no control net fans
    // out to all 512 x TXQ queue bits (0 cycles)
    parameter integer TXQ_SLICE = 1,
    // RDY_LT: the payload word-free compare (rx word < txh) that gates in_ready / vm_we as a log-depth
    // compare (0 cycles)
    parameter integer RDY_LT = 1,
    // FANOUT_COPY: kept register copies for the two long nets the routes left over the slew limit --
    // the header user's low bits into the 28 upos groups (one copy per 4 groups), and the SOURCE
    // record row / address into each SRAM bank (0 cycles)
    parameter integer FANOUT_COPY = 1,
    // MARGIN (owner margin-first rule; needs CONTROL_PIPE; priced in cycles by the bench):
    //  - core_done / core_next_token / core_next_val captured in flops at the pins (+1 cycle per completion;
    //    the completion is held off one more edge after a start so the pre-start done level is never taken);
    //  - the upos groups' read strobe from their own registered copies (as LOCAL_CONTROL);
    //  - the payload word-free compare (rx word < txh) from registers: (rxw < txh) and (rxw + 1 < txh)
    //    of the previous edge, used only when txh did not reset there and rxw did not reload there
    //    (conservative: never claims a word free that the exact compare would not; may stall a flit)
    parameter integer MARGIN = 1,
    // LINK_REG (owner die-integration rule: every block boundary register-to-register; priced in cycles):
    //  the link ports become a REGISTERED LINK (ready latency 2): in_valid / in_data / in_last are captured
    //  in pin flops (nothing between pin and D) and drain through a LINK_DEPTH-slot skid FIFO; in_ready is a
    //  flop -- a grant: in_ready high in cycle c admits one flit on the link in cycle c + 2 (the sender
    //  captures it in its own pin flop and launches from a flop), so the grant counts the flits still in
    //  flight; out_valid / out_data / out_last are launched from flops, out_ready is captured in a pin flop
    //  and a flit is sent only on a grant (a flit is transferred on every cycle out_valid is high).  Both
    //  ends: ot_rom_pkg_ctrl_wfc_tokpipe_lrx / _ltx (the routers / die stations use the same pair).  +1 cycle
    //  inbound, +1 outbound per hop.  LINK_DEPTH 4 = the grant round trip: full rate with zero stalls.
    parameter integer LINK_REG = 1,
    parameter integer LINK_DEPTH = 4,
    // LINK_SEL (LINK_REG): the receive skid's count / grant / pointer next-state computed from registers for
    // both values of the core side's ready, which then only selects (Shannon split; same function, 0 cycles).
    // r10 src: core ready (job_done copy -> lk_in_ready) + the count adder chain -> rdy was the worst path, +21.6
    parameter integer LINK_SEL = 1,
    // VM_REG: the vector-memory ports launched from flops (the VM is its own hardened element): a write
    // and a read reach the memory one edge later; the read data is taken one edge later (+1 cycle per
    // payload read; a second read in flight counts against the queue space)
    parameter integer VM_REG = 1,
    // RD_PIPE (SOURCE with REC_SRAM): a second register stage on the SRAM read (rd_out -> a capture
    // register that only feeds the second one, so it sits at the macro pins): +1 cycle per record event
    parameter integer RD_PIPE = 1,
    // SLEW_COPY: kept register copies for the nets the margin routes left over the slew limit: the header
    // user's group bits (upos group select, one copy per 4 groups), the registered hdr_pos + 1 into the upos
    // groups (one copy per 4 groups), and the SRAM write row / address per (bank, column) macro (0 cycles)
    parameter integer SLEW_COPY = 1,
    parameter integer PKG_ID       = 0,
    parameter integer FLIT         = 512,    // bits; one vector-memory word
    parameter integer NW           = 21,     // token / position bits
    parameter integer AW           = 30,     // KV address bits
    parameter integer VWA          = 15,      // vector-memory word address bits
    parameter integer MAXU         = 866,     // user contexts
    parameter integer USER_W       = 10,      // 10 for the full-shape 866-user namespace
    parameter integer KVW          = 32768,   // KV words per user
    parameter integer XWORDS       = 41,      // payload flits of a HIDDEN message
    parameter integer RXB          = 0,      // vector-memory word of received payload flit 0
    parameter integer TXB          = 0,      // vector-memory word of sent payload flit 0
    parameter integer SOURCE       = 1,      // 1: issues steps (embedding package), reduces RESULTs
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
    parameter integer WIN          = 6
) (
    input  wire               clk,
    input  wire               rst_n,
    // run configuration (SOURCE)
    input  wire [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] cfg_users,
    input  wire [NW-1:0]      cfg_prompt_len,
    input  wire [NW-1:0]      cfg_gen_len,
    // inbound link
    input  wire               in_valid,
    output wire               in_ready,
    input  wire [FLIT-1:0]    in_data,
    input  wire               in_last,
    // outbound link
    output wire               out_valid,
    input  wire               out_ready,
    output wire [FLIT-1:0]    out_data,
    output wire               out_last,
    // decode core
    output wire                core_start,
    output wire  [NW-1:0]      core_token,
    output wire  [NW-1:0]      core_pos,
    output wire [USER_W-1:0]  core_user,
    input  wire               core_done,
    input  wire [NW-1:0]      core_next_token,
    input  wire [31:0]        core_next_val,
    output wire  [AW-1:0]      kv_base,
    // vector memory, one word per access, synchronous read
    output wire               vm_we,
    output wire [VWA-1:0]     vm_waddr,
    output wire [FLIT-1:0]    vm_wdata,
    output wire               vm_re,
    output wire [VWA-1:0]     vm_raddr,
    input  wire [FLIT-1:0]    vm_rq,
    // prompt tokens (SOURCE), synchronous read
    output wire                pr_re,
    output wire  [USER_W-1:0]  pr_user,
    output wire  [NW-1:0]      pr_pos,
    input  wire [NW-1:0]      pr_q,
    output wire  [3:0]         pr_blk,         // WAVE: draft block of the read
    input  wire               pr_qk,          // WAVE: the read position's token is known
    // Actual SOURCE issue/rewind face; token request36/response22/config52 unchanged.
    input wire eng_window_ready,eng_rb_ready,
    output wire eng_issue_v,eng_rb_v,
    output wire [USER_W-1:0] eng_issue_user,eng_rb_user,
    output wire [NW-1:0] eng_issue_pos,eng_issue_tok,
    output wire [2:0] eng_rb_n,
    // observation
    output wire               core_busy,
    output wire                tok_valid,      // SOURCE: a step's reduced token
    output wire  [USER_W-1:0]  tok_user,
    output wire  [NW-1:0]      tok_pos,
    output wire  [NW-1:0]      tok_id,
    output wire  [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] users_done,
    output wire                proto_fault,
    output wire                wf_issue,       // WAVE observation: a known-token issue this cycle
    output wire                wf_reject,      // a verified token was rejected
    output wire                wf_squash       // a squashed result was discarded
);

    ot_rom_pkg_ctrl_wfc_tokpipe #(
        .ENGRAM_REWIND(ENGRAM_REWIND),
        .PROMPT_EXTRA(PROMPT_EXTRA),
        .DECODED_READ(DECODED_READ),
        .HEADER_LOCAL(HEADER_LOCAL),
        .PREFIX_INC(PREFIX_INC),
        .QUEUE_SHIFT(QUEUE_SHIFT),
        .CONTROL_PIPE(CONTROL_PIPE),
        .LOCAL_CONTROL(LOCAL_CONTROL),
        .REC_SRAM(REC_SRAM),
        .UPOS_LWR(UPOS_LWR),
        .CFG_Q(CFG_Q),
        .PRECOMP(PRECOMP),
        .IN_DEC(IN_DEC),
        .TXQ_SLICE(TXQ_SLICE),
        .RDY_LT(RDY_LT),
        .FANOUT_COPY(FANOUT_COPY),
        .MARGIN(MARGIN),
        .LINK_REG(LINK_REG),
        .LINK_DEPTH(LINK_DEPTH),
        .LINK_SEL(LINK_SEL),
        .VM_REG(VM_REG),
        .RD_PIPE(RD_PIPE),
        .SLEW_COPY(SLEW_COPY),
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
        .WIN(WIN)
    ) u_wfc (.*);
endmodule
