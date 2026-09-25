`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Host interface of the decode chip (docs/HOST_INTERFACE_AND_RUNTIME.md).
//
// The host sees a PCIe-BAR-style register file on an AXI4-Lite slave and the
// chip reaches host memory through an AXI4 master (single-beat, 64-bit: the
// DMA a PCIe endpoint's bridge would present).  Work is exchanged through two
// rings in host memory, NVMe-style:
//
//   submission queue (SQ): 32-byte descriptors written by the host; the host
//     rings the SQ_TAIL doorbell, the chip fetches each descriptor and the
//     prompt it points to, and advances SQ_HEAD.
//   completion queue (CQ): 16-byte entries written by the chip, one per
//     generated token (the token stream), the last one of a request flagged
//     with its stop status.  A phase bit flips on every wrap, so the host
//     finds new entries without reading a register; it returns entries by
//     writing the CQ_HEAD doorbell, and the chip never overwrites an entry the
//     host has not returned.
//
// Every CQ entry raises IRQ_STATUS bit 0; `irq` is the level (INTx) view of
// IRQ_STATUS & IRQ_MASK, and with MSI enabled the chip also posts MSI_DATA
// to MSI_ADDR through the DMA write channel, the way a PCIe function signals
// a message-signalled interrupt.
//
// Descriptor (four little-endian 64-bit words):
//   w0 [7:0] opcode (1 = GENERATE)  [15:8] flags (bit 0 greedy -- required,
//      bit 1 stop at EOS)  [31:16] tag  [47:32] prompt length
//      [63:48] max new tokens
//   w1 host address of the prompt: 16-bit token ids, packed four per word
//   w2 [7:0] user context (slot)
//   w3 [15:0] EOS id 0  [31:16] EOS id 1
// Completion entry (two 64-bit words; w1 is written before w0):
//   w0 [0] phase  [2:1] kind (1 token, 2 last token, 3 error)  [7:4] status
//      [15:8] slot  [31:16] tag  [47:32] position  [63:48] token
//   w1 [31:0] cycles of this step  [47:32] tokens generated so far
//
// User contexts.  NSLOT slots, one per user, as the package controller keeps
// them (ot_rom_pkg_ctrl MAXU).  A slot holds the request, its next position,
// the fed-back token and its counts; the prompt is DMA'd once into the prompt
// buffer, an external 1R1W SRAM addressed {slot, position}, like every memory
// of the decode cores.
//
// Engines (MODE):
//   0 step: the chip schedules every decode step of every running slot onto
//     one decode core through its start/done handshake (ot_hdc_core,
//     ot_hdc_core_v41), round robin over slots; `kv_base` is the running
//     slot's KV slice (slot * KVW), added to the core's KV addresses by the
//     memory wrapper.  With ENG_CTX == 1 the core holds one user's state
//     (the V4.1 core's persistent vector memory and Engram history, or a KV
//     tail SRAM): a slot then runs to completion and the engine's state is
//     cleared (eng_clr_req / eng_clr_ack) before the next slot starts.
//   1 batch: the chip fronts the SOURCE package of a ROM array
//     (ot_rom_pkg_ctrl SOURCE = 1).  The package controller schedules its
//     users itself with one prompt and generation length; the chip serves
//     its prompt reads from the prompt buffer and takes its token stream.
//     The host starts slots 0..n-1 together by writing n to BATCH_GO; the
//     chip checks that they are loaded with one common length, resets the
//     array, and runs it until every user is done.
//
// Registers (byte offsets, 32-bit):
//   000 ID "OTHI"         004 CAPS {version, ENG_CTX, MODE, NSLOT}
//   008 CTRL [0] enable   00C STATUS [0] engine busy [1] engine fault
//                                    [2] DMA error [3] batch running [4] event overflow
//   010/014 SQ_BASE lo/hi  018 SQ_LOG2  01C SQ_TAIL (doorbell)  020 SQ_HEAD
//   024/028 CQ_BASE lo/hi  02C CQ_LOG2  030 CQ_HEAD (doorbell)  034 CQ_TAIL
//   038 IRQ_STATUS (write 1 to clear)  03C IRQ_MASK
//   040/044 MSI_ADDR lo/hi  048 MSI_DATA  04C MSI_CTRL [0] enable
//   050 BATCH_GO (write n) / batch status
//   060/064 cycles  068/06C engine busy cycles  070 tokens  074 steps
//   078 requests completed  07C MSIs  080 DMA read beats  084 DMA write beats
//   088 CQ-full stall cycles
//   100 + 8*s  slot s {pos, 00, inflight, state}   104 + 8*s {tag, generated}
// ---------------------------------------------------------------------------
module ot_host_if #(
    parameter integer NSLOT   = 16,     // user contexts
    parameter integer MODE    = 0,      // 0 step (one core), 1 batch (ROM array SOURCE package)
    parameter integer ENG_CTX = 16,     // contexts the engine holds at once (1: clear between users)
    parameter integer NW      = 16,     // token / position bits
    parameter integer PLB     = 8,      // log2 prompt-buffer entries per slot
    parameter integer CTX_MAX = 64,     // KV positions per user (prompt + generated - 1 <= CTX_MAX)
    parameter integer AW      = 24,     // KV address bits
    parameter integer KVW     = 1024,   // KV words per user
    parameter integer EVQ     = 4       // log2 completion-event queue depth
) (
    input  wire               clk,
    input  wire               rst_n,
    // AXI4-Lite slave: the register BAR
    input  wire               s_awvalid,
    output wire               s_awready,
    input  wire [11:0]        s_awaddr,
    input  wire               s_wvalid,
    output wire               s_wready,
    input  wire [31:0]        s_wdata,
    input  wire [3:0]         s_wstrb,
    output reg                s_bvalid,
    input  wire               s_bready,
    output wire [1:0]         s_bresp,
    input  wire               s_arvalid,
    output wire               s_arready,
    input  wire [11:0]        s_araddr,
    output reg                s_rvalid,
    input  wire               s_rready,
    output reg  [31:0]        s_rdata,
    output wire [1:0]         s_rresp,
    // AXI4 master: DMA to host memory, single 64-bit beats
    output reg                m_arvalid,
    input  wire               m_arready,
    output reg  [63:0]        m_araddr,
    output wire [7:0]         m_arlen,
    output wire [2:0]         m_arsize,
    input  wire               m_rvalid,
    output wire               m_rready,
    input  wire [63:0]        m_rdata,
    input  wire [1:0]         m_rresp,
    input  wire               m_rlast,
    output reg                m_awvalid,
    input  wire               m_awready,
    output reg  [63:0]        m_awaddr,
    output wire [7:0]         m_awlen,
    output wire [2:0]         m_awsize,
    output reg                m_wvalid,
    input  wire               m_wready,
    output reg  [63:0]        m_wdata,
    output reg  [7:0]         m_wstrb,
    output wire               m_wlast,
    input  wire               m_bvalid,
    output wire               m_bready,
    input  wire [1:0]         m_bresp,
    // interrupt, level (INTx model)
    output wire               irq,
    // prompt buffer: external 1R1W SRAM, synchronous read, address {slot, position}
    output reg                pb_we,
    output reg  [SB+PLB-1:0]  pb_waddr,
    output reg  [NW-1:0]      pb_wdata,
    output reg                pb_re,
    output reg  [SB+PLB-1:0]  pb_raddr,
    input  wire [NW-1:0]      pb_q,
    // MODE 0: one decode core
    output reg                eng_start,
    output reg  [NW-1:0]      eng_token,
    output reg  [NW-1:0]      eng_pos,
    output reg  [SB-1:0]      eng_slot,
    output reg  [AW-1:0]      kv_base,
    input  wire               eng_done,
    input  wire [NW-1:0]      eng_next_token,
    input  wire [31:0]        eng_cycles,
    input  wire               eng_fault,
    output reg                eng_clr_req,     // clear the engine's user state (ENG_CTX == 1)
    input  wire               eng_clr_ack,
    // MODE 1: SOURCE package of a ROM array (ot_rom_pkg_ctrl)
    output reg                arr_rst_n,
    output reg  [7:0]         cfg_users,
    output reg  [NW-1:0]      cfg_prompt_len,
    output reg  [NW-1:0]      cfg_gen_len,
    input  wire               pr_re,
    input  wire [7:0]         pr_user,
    input  wire [NW-1:0]      pr_pos,
    input  wire               tok_valid,
    input  wire [7:0]         tok_user,
    input  wire [NW-1:0]      tok_pos,
    input  wire [NW-1:0]      tok_id,
    input  wire [7:0]         users_done,
    input  wire               arr_fault
);
    localparam integer SB = (NSLOT > 1) ? $clog2(NSLOT) : 1;
    localparam integer EQD = 1 << EVQ;
    localparam [31:0] ID = 32'h4F54_4849;               // "OTHI"
    localparam [7:0]  VERSION = 8'd1;
    localparam [1:0]  SL_FREE = 2'd0, SL_RUN = 2'd1, SL_DRAIN = 2'd2;
    localparam [1:0]  EV_TOKEN = 2'd1, EV_LAST = 2'd2, EV_ERROR = 2'd3;
    localparam [3:0]  ST_OK = 4'd0, ST_EOS = 4'd1, ST_LENGTH = 4'd2, ST_BAD_OP = 4'd3, ST_SAMPLING = 4'd4,
                      ST_SLOT = 4'd5, ST_BAD_LEN = 4'd6, ST_FAULT = 4'd7, ST_DMA = 4'd8;

    assign s_bresp = 2'b00;
    assign s_rresp = 2'b00;
    assign m_arlen = 8'd0;  assign m_arsize = 3'd3;
    assign m_awlen = 8'd0;  assign m_awsize = 3'd3;
    assign m_wlast = 1'b1;
    assign m_rready = 1'b1;
    assign m_bready = 1'b1;

    // -- registers ---------------------------------------------------------------------
    reg          enable;
    reg [63:0]   sq_base, cq_base, msi_addr;
    reg [3:0]    sq_log, cq_log;
    reg [15:0]   sq_tail, sq_head, cq_head, cq_tail;
    reg          cq_phase;
    reg [1:0]    irq_status, irq_mask;
    reg [31:0]   msi_data;
    reg          msi_en;
    reg          sticky_fault, sticky_dma;
    reg [63:0]   c_cycles, c_busy;
    reg [31:0]   c_tokens, c_steps, c_reqs, c_msis, c_rd, c_wr, c_cqfull;
    reg          ev_ovf;
    // MODE 0 issue state and MODE 1 batch state (declared before the register mux)
    localparam [2:0] I_IDLE = 0, I_CLR = 1, I_RD = 2, I_WAIT = 3, I_GO = 4, I_RUN = 5;
    reg [2:0]    i_st;
    reg          inflight;
    localparam [1:0] B_IDLE = 0, B_RST = 1, B_RUN = 2;
    reg [1:0]    b_st;
    reg [1:0]    b_err;
    reg [2:0]    b_cnt;
    wire [15:0]  sq_mask = (16'd1 << sq_log) - 16'd1;
    wire [15:0]  cq_mask = (16'd1 << cq_log) - 16'd1;
    assign irq = |(irq_status & irq_mask);

    // -- user contexts -------------------------------------------------------------------
    reg [1:0]    sl_st   [0:NSLOT-1];
    reg [15:0]   sl_tag  [0:NSLOT-1];
    reg [NW-1:0] sl_plen [0:NSLOT-1];
    reg [NW-1:0] sl_max  [0:NSLOT-1];
    reg [NW-1:0] sl_pos  [0:NSLOT-1];      // next position to issue (MODE 0)
    reg [NW-1:0] sl_ngen [0:NSLOT-1];
    reg [NW-1:0] sl_tok  [0:NSLOT-1];      // fed-back token
    reg          sl_eos  [0:NSLOT-1];
    reg [NW-1:0] sl_eos0 [0:NSLOT-1];
    reg [NW-1:0] sl_eos1 [0:NSLOT-1];
    reg [31:0]   sl_t    [0:NSLOT-1];      // MODE 1: cycle of the slot's previous token

    // -- completion-event queue ----------------------------------------------------------
    // {kind, status, slot, tag, pos, token, cycles, generated}
    localparam integer EVW = 2 + 4 + 8 + 16 + NW + NW + 32 + NW;
    reg [EVW-1:0] evq [0:EQD-1];
    reg [EVQ-1:0] ev_w, ev_r;
    reg [EVQ:0]   ev_n;
    wire          ev_full = ev_n == EQD;
    // engine-side push (priority) and DMA-side push (errors)
    reg           ep_v;  reg [EVW-1:0] ep_d;
    reg           dp_v;  reg [EVW-1:0] dp_d;
    wire          dp_ok = !ep_v && !ev_full;
    wire          ev_pop;
    wire [EVW-1:0] ev_head = evq[ev_r];
    function automatic [EVW-1:0] ev(input [1:0] kind, input [3:0] status, input [7:0] slot, input [15:0] tag,
                                    input [NW-1:0] pos, input [NW-1:0] tok, input [31:0] cyc,
                                    input [NW-1:0] ngen);
        ev = {kind, status, slot, tag, pos, tok, cyc, ngen};
    endfunction
    wire [1:0]    eh_kind = ev_head[EVW-1 -: 2];
    wire [3:0]    eh_st   = ev_head[EVW-3 -: 4];
    wire [7:0]    eh_slot8 = ev_head[EVW-7 -: 8];
    wire [SB-1:0] eh_slot = eh_slot8[SB-1:0];
    wire [15:0]   eh_tag  = ev_head[EVW-15 -: 16];
    wire [NW-1:0] eh_pos  = ev_head[32 + 3*NW - 1 -: NW];
    wire [NW-1:0] eh_tok  = ev_head[32 + 2*NW - 1 -: NW];
    wire [31:0]   eh_cyc  = ev_head[32 + NW - 1 -: 32];
    wire [NW-1:0] eh_ngen = ev_head[NW-1:0];

    // -- AXI4-Lite slave -----------------------------------------------------------------
    wire wr_go = s_awvalid && s_wvalid && !s_bvalid;
    assign s_awready = wr_go;
    assign s_wready  = wr_go;
    wire rd_go = s_arvalid && !s_rvalid;
    assign s_arready = rd_go;
    reg  batch_go;  reg [7:0] batch_n;     // BATCH_GO write, taken by the batch FSM

    reg [31:0] rmux;
    integer si;
    always @(*) begin
        rmux = 32'd0;
        case (s_araddr[11:2])
            10'h000: rmux = ID;
            10'h001: rmux = {VERSION, ENG_CTX[7:0], MODE[7:0], NSLOT[7:0]};
            10'h002: rmux = {31'd0, enable};
            10'h003: rmux = {27'd0, ev_ovf, b_st != B_IDLE, sticky_dma, sticky_fault, inflight};
            10'h004: rmux = sq_base[31:0];
            10'h005: rmux = sq_base[63:32];
            10'h006: rmux = {28'd0, sq_log};
            10'h007: rmux = {16'd0, sq_tail};
            10'h008: rmux = {16'd0, sq_head};
            10'h009: rmux = cq_base[31:0];
            10'h00A: rmux = cq_base[63:32];
            10'h00B: rmux = {28'd0, cq_log};
            10'h00C: rmux = {16'd0, cq_head};
            10'h00D: rmux = {15'd0, cq_phase, cq_tail};
            10'h00E: rmux = {30'd0, irq_status};
            10'h00F: rmux = {30'd0, irq_mask};
            10'h010: rmux = msi_addr[31:0];
            10'h011: rmux = msi_addr[63:32];
            10'h012: rmux = msi_data;
            10'h013: rmux = {31'd0, msi_en};
            10'h014: rmux = {20'd0, b_err, b_st, cfg_users};
            10'h018: rmux = c_cycles[31:0];
            10'h019: rmux = c_cycles[63:32];
            10'h01A: rmux = c_busy[31:0];
            10'h01B: rmux = c_busy[63:32];
            10'h01C: rmux = c_tokens;
            10'h01D: rmux = c_steps;
            10'h01E: rmux = c_reqs;
            10'h01F: rmux = c_msis;
            10'h020: rmux = c_rd;
            10'h021: rmux = c_wr;
            10'h022: rmux = c_cqfull;
            default: ;
        endcase
        for (si = 0; si < NSLOT; si = si + 1) begin
            if (s_araddr[11:2] == 10'h040 + 2 * si)
                rmux = {sl_pos[si], 13'd0, inflight && (eng_slot == si), sl_st[si]};
            if (s_araddr[11:2] == 10'h041 + 2 * si)
                rmux = {sl_tag[si], sl_ngen[si]};
        end
    end

    // -- MODE 0: step scheduler ------------------------------------------------------------
    // Round robin over running slots, one step in flight.  Issue: read the
    // prompt token (or use the fed-back one), then pulse eng_start.
    reg [SB-1:0] rr;                     // slot after the last issued one
    reg          own_v;                  // ENG_CTX == 1: the slot whose state the engine holds
    reg [SB-1:0] own;
    reg          pick_v;
    reg [SB-1:0] pick;
    integer k;
    reg [SB-1:0] cand;
    always @(*) begin
        pick_v = 1'b0; pick = {SB{1'b0}};
        for (k = NSLOT - 1; k >= 0; k = k - 1) begin
            cand = rr + k[SB-1:0];
            if (sl_st[cand] == SL_RUN) begin pick_v = 1'b1; pick = cand; end
        end
        if (ENG_CTX == 1 && own_v && sl_st[own] == SL_RUN) begin pick_v = 1'b1; pick = own; end
    end
    wire          step_done = (MODE == 0) && inflight && eng_done && !eng_start;
    wire [NW-1:0] d_pos  = eng_pos;
    wire [SB-1:0] d_slot = eng_slot;
    wire          d_gen  = d_pos + 1'b1 >= sl_plen[d_slot];                  // output is a generated token
    wire [NW-1:0] d_ngen = sl_ngen[d_slot] + 1'b1;
    wire          d_eos  = sl_eos[d_slot] && (eng_next_token == sl_eos0[d_slot] || eng_next_token == sl_eos1[d_slot]);
    wire          d_last = eng_fault || (d_gen && (d_eos || d_ngen == sl_max[d_slot]));
    wire [3:0]    d_stat = eng_fault ? ST_FAULT : d_eos ? ST_EOS : ST_LENGTH;

    // -- MODE 1: batch control ----------------------------------------------------------------
    wire [SB-1:0] t_slot = tok_user[SB-1:0];
    wire          t_ok   = (MODE == 1) && b_st == B_RUN && tok_valid && sl_st[t_slot] == SL_RUN;
    wire          t_gen  = tok_pos + 1'b1 >= sl_plen[t_slot];
    wire [NW-1:0] t_ngen = sl_ngen[t_slot] + 1'b1;
    wire          t_eos  = sl_eos[t_slot] && (tok_id == sl_eos0[t_slot] || tok_id == sl_eos1[t_slot]);
    wire          t_last = arr_fault || (t_gen && (t_eos || t_ngen == sl_max[t_slot]));
    wire [3:0]    t_stat = arr_fault ? ST_FAULT : t_eos ? ST_EOS : ST_LENGTH;
    // check of slots 0..batch_n-1 for BATCH_GO
    reg          b_ok;
    integer bj;
    always @(*) begin
        b_ok = (batch_n != 0) && (batch_n <= NSLOT);
        for (bj = 0; bj < NSLOT; bj = bj + 1)
            if (bj < batch_n)
                if (sl_st[bj] != SL_RUN || sl_plen[bj] != sl_plen[0] || sl_max[bj] != sl_max[0]) b_ok = 1'b0;
    end

    // -- DMA: descriptor fetch, prompt load, completion post, MSI --------------------------
    localparam [3:0] D_IDLE = 0, D_SQ_AR = 1, D_SQ_R = 2, D_CHECK = 3, D_PR_AR = 4, D_PR_R = 5, D_PR_W = 6,
                     D_ERR = 7, D_CQ1 = 8, D_CQ1_B = 9, D_CQ0 = 10, D_CQ0_B = 11, D_MSI = 12, D_MSI_B = 13;
    reg [3:0]    d_st;
    reg [1:0]    dw;                     // descriptor word / prompt token in word
    reg [63:0]   dsc0, dsc1, dsc2, dsc3;
    reg [NW-1:0] pr_i;                   // prompt tokens loaded
    reg [63:0]   pr_word;
    reg [3:0]    err_st;
    wire [7:0]    q_op   = dsc0[7:0];
    wire [7:0]    q_fl   = dsc0[15:8];
    wire [15:0]   q_tag  = dsc0[31:16];
    wire [NW-1:0] q_plen = dsc0[32 +: NW];
    wire [NW-1:0] q_max  = dsc0[48 +: NW];
    wire [7:0]    q_slot = dsc2[7:0];
    wire [SB-1:0] q_s    = q_slot[SB-1:0];
    wire [NW+1:0] q_span = q_plen + q_max;
    wire [63:0]   cq_entry = {cq_base + {44'd0, cq_tail, 4'd0}};
    wire          cq_room  = ((cq_tail + 16'd1) & cq_mask) != cq_head;
    assign ev_pop = (d_st == D_CQ0_B) && m_bvalid;

    // CQ entry words of the head event
    wire [63:0] cq_w0 = {eh_tok, eh_pos, eh_tag, eh_slot8, eh_st, 1'b0, eh_kind, cq_phase};
    wire [63:0] cq_w1 = {{(32-NW){1'b0}}, eh_ngen, eh_cyc};

    integer j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            enable <= 1'b0; sq_base <= 0; cq_base <= 0; msi_addr <= 0; sq_log <= 0; cq_log <= 0;
            sq_tail <= 0; sq_head <= 0; cq_head <= 0; cq_tail <= 0; cq_phase <= 1'b1;
            irq_status <= 0; irq_mask <= 0; msi_data <= 0; msi_en <= 1'b0;
            sticky_fault <= 1'b0; sticky_dma <= 1'b0;
            c_cycles <= 0; c_busy <= 0; c_tokens <= 0; c_steps <= 0; c_reqs <= 0; c_msis <= 0;
            c_rd <= 0; c_wr <= 0; c_cqfull <= 0;
            s_bvalid <= 1'b0; s_rvalid <= 1'b0; s_rdata <= 0;
            batch_go <= 1'b0; batch_n <= 0;
            m_arvalid <= 1'b0; m_araddr <= 0; m_awvalid <= 1'b0; m_awaddr <= 0;
            m_wvalid <= 1'b0; m_wdata <= 0; m_wstrb <= 0;
            pb_we <= 1'b0; pb_waddr <= 0; pb_wdata <= 0;
            d_st <= D_IDLE; dw <= 0; dsc0 <= 0; dsc1 <= 0; dsc2 <= 0; dsc3 <= 0; ev_ovf <= 1'b0; pr_i <= 0; pr_word <= 0; err_st <= 0;
            ev_w <= 0; ev_r <= 0; ev_n <= 0;
            i_st <= I_IDLE; inflight <= 1'b0; rr <= 0; own_v <= 1'b0; own <= 0;
            eng_start <= 1'b0; eng_token <= 0; eng_pos <= 0; eng_slot <= 0; kv_base <= 0; eng_clr_req <= 1'b0;
            b_st <= B_IDLE; b_err <= 0; b_cnt <= 0;
            arr_rst_n <= 1'b0; cfg_users <= 0; cfg_prompt_len <= 0; cfg_gen_len <= 0;
            for (j = 0; j < NSLOT; j = j + 1) begin
                sl_st[j] <= SL_FREE; sl_tag[j] <= 0; sl_plen[j] <= 0; sl_max[j] <= 0; sl_pos[j] <= 0;
                sl_ngen[j] <= 0; sl_tok[j] <= 0; sl_eos[j] <= 1'b0; sl_eos0[j] <= 0; sl_eos1[j] <= 0;
                sl_t[j] <= 0;
            end
        end else begin
            // ---- counters
            if (enable) c_cycles <= c_cycles + 1'b1;
            if (inflight || b_st == B_RUN) c_busy <= c_busy + 1'b1;
            if (ev_n != 0 && !cq_room) c_cqfull <= c_cqfull + 1'b1;

            // ---- AXI4-Lite
            if (s_bvalid && s_bready) s_bvalid <= 1'b0;
            if (s_rvalid && s_rready) s_rvalid <= 1'b0;
            if (rd_go) begin s_rvalid <= 1'b1; s_rdata <= rmux; end
            batch_go <= 1'b0;
            if (wr_go) begin
                s_bvalid <= 1'b1;
                case (s_awaddr[11:2])
                    10'h002: enable <= s_wdata[0];
                    10'h004: sq_base[31:0] <= s_wdata;
                    10'h005: sq_base[63:32] <= s_wdata;
                    10'h006: sq_log <= s_wdata[3:0];
                    10'h007: sq_tail <= s_wdata[15:0] & sq_mask;
                    10'h009: cq_base[31:0] <= s_wdata;
                    10'h00A: cq_base[63:32] <= s_wdata;
                    10'h00B: cq_log <= s_wdata[3:0];
                    10'h00C: cq_head <= s_wdata[15:0] & cq_mask;
                    10'h00E: ;                          // W1C, below
                    10'h00F: irq_mask <= s_wdata[1:0];
                    10'h010: msi_addr[31:0] <= s_wdata;
                    10'h011: msi_addr[63:32] <= s_wdata;
                    10'h012: msi_data <= s_wdata;
                    10'h013: msi_en <= s_wdata[0];
                    10'h014: begin batch_go <= 1'b1; batch_n <= s_wdata[7:0]; end
                    default: ;
                endcase
            end

            // ---- event queue
            if (ep_v || (dp_v && dp_ok)) begin
                evq[ev_w] <= ep_v ? ep_d : dp_d;
                ev_w <= ev_w + 1'b1;
            end
            if (ev_pop) ev_r <= ev_r + 1'b1;
            if (ep_v && ev_full && !ev_pop) ev_ovf <= 1'b1;
            ev_n <= ev_n + ((ep_v || (dp_v && dp_ok)) ? 1'b1 : 1'b0) - (ev_pop ? 1'b1 : 1'b0);

            // ---- DMA
            pb_we <= 1'b0;
            if (m_rvalid) c_rd <= c_rd + 1'b1;
            if (m_bvalid) c_wr <= c_wr + 1'b1;
            if ((m_rvalid && m_rresp[1]) || (m_bvalid && m_bresp[1])) sticky_dma <= 1'b1;
            case (d_st)
                D_IDLE:
                    if (ev_n != 0 && cq_room) begin
                        // post the head event: w1 first, then w0 with the phase bit
                        m_awvalid <= 1'b1; m_awaddr <= cq_entry + 64'd8;
                        m_wvalid <= 1'b1; m_wdata <= cq_w1; m_wstrb <= 8'hFF;
                        d_st <= D_CQ1;
                    end else if (enable && sq_head != sq_tail && ev_n < EQD - 1) begin
                        m_arvalid <= 1'b1; m_araddr <= sq_base + {43'd0, sq_head, 5'd0};
                        dw <= 0; d_st <= D_SQ_AR;
                    end
                D_SQ_AR: if (m_arready) begin m_arvalid <= 1'b0; d_st <= D_SQ_R; end
                D_SQ_R: if (m_rvalid) begin
                    case (dw)
                        2'd0: dsc0 <= m_rdata;
                        2'd1: dsc1 <= m_rdata;
                        2'd2: dsc2 <= m_rdata;
                        default: dsc3 <= m_rdata;
                    endcase
                    if (dw == 2'd3) d_st <= D_CHECK;
                    else begin
                        dw <= dw + 1'b1;
                        m_arvalid <= 1'b1; m_araddr <= sq_base + {43'd0, sq_head, 5'd0} + {59'd0, dw + 2'd1, 3'd0};
                        d_st <= D_SQ_AR;
                    end
                end
                D_CHECK: begin
                    sq_head <= (sq_head + 16'd1) & sq_mask;
                    err_st <= ST_OK;
                    if (q_op != 8'd1) err_st <= ST_BAD_OP;
                    else if (!q_fl[0] || q_fl[7:2] != 0) err_st <= ST_SAMPLING;
                    else if (q_slot >= NSLOT || sl_st[q_s] != SL_FREE || (MODE == 1 && b_st != B_IDLE))
                        err_st <= ST_SLOT;
                    else if (q_plen == 0 || q_max == 0 || q_plen > (1 << PLB) || q_span > CTX_MAX + 1)
                        err_st <= ST_BAD_LEN;
                    d_st <= D_ERR;
                end
                D_ERR:
                    if (err_st != ST_OK) begin
                        if (dp_ok) d_st <= D_IDLE;                       // the error event is pushed below
                    end else begin
                        sl_tag[q_s] <= q_tag; sl_plen[q_s] <= q_plen; sl_max[q_s] <= q_max;
                        sl_pos[q_s] <= 0; sl_ngen[q_s] <= 0; sl_eos[q_s] <= q_fl[1];
                        sl_eos0[q_s] <= dsc3[NW-1:0]; sl_eos1[q_s] <= dsc3[16 +: NW];
                        sl_t[q_s] <= c_cycles[31:0];
                        pr_i <= 0;
                        m_arvalid <= 1'b1; m_araddr <= dsc1;
                        d_st <= D_PR_AR;
                    end
                D_PR_AR: if (m_arready) begin m_arvalid <= 1'b0; d_st <= D_PR_R; end
                D_PR_R: if (m_rvalid) begin pr_word <= m_rdata; dw <= 0; d_st <= D_PR_W; end
                D_PR_W: begin
                    pb_we <= 1'b1;
                    pb_waddr <= {q_s, pr_i[PLB-1:0]};
                    pb_wdata <= pr_word[16*dw +: NW];
                    pr_i <= pr_i + 1'b1;
                    dw <= dw + 1'b1;
                    if (pr_i + 1'b1 == q_plen) begin
                        sl_st[q_s] <= SL_RUN;
                        d_st <= D_IDLE;
                    end else if (dw == 2'd3) begin
                        m_arvalid <= 1'b1; m_araddr <= dsc1 + {47'd0, pr_i + 1'b1, 1'b0};
                        d_st <= D_PR_AR;
                    end
                end
                D_CQ1: begin
                    if (m_awready) m_awvalid <= 1'b0;
                    if (m_wready) m_wvalid <= 1'b0;
                    if ((m_awready || !m_awvalid) && (m_wready || !m_wvalid)) d_st <= D_CQ1_B;
                end
                D_CQ1_B: if (m_bvalid) begin
                    m_awvalid <= 1'b1; m_awaddr <= cq_entry;
                    m_wvalid <= 1'b1; m_wdata <= cq_w0; m_wstrb <= 8'hFF;
                    d_st <= D_CQ0;
                end
                D_CQ0: begin
                    if (m_awready) m_awvalid <= 1'b0;
                    if (m_wready) m_wvalid <= 1'b0;
                    if ((m_awready || !m_awvalid) && (m_wready || !m_wvalid)) d_st <= D_CQ0_B;
                end
                D_CQ0_B: if (m_bvalid) begin
                    // entry visible: advance the tail, raise the interrupt
                    cq_tail <= (cq_tail + 16'd1) & cq_mask;
                    if (((cq_tail + 16'd1) & cq_mask) == 16'd0) cq_phase <= !cq_phase;
                    if (eh_kind != EV_TOKEN) begin
                        c_reqs <= c_reqs + 1'b1;
                        if (sl_st[eh_slot] == SL_DRAIN && MODE == 0) sl_st[eh_slot] <= SL_FREE;
                    end
                    if (eh_kind != EV_ERROR) c_tokens <= c_tokens + 1'b1;
                    if (msi_en && irq_mask[0]) begin
                        m_awvalid <= 1'b1; m_awaddr <= {msi_addr[63:3], 3'b000};
                        m_wvalid <= 1'b1; m_wdata <= msi_addr[2] ? {msi_data, 32'd0} : {32'd0, msi_data};
                        m_wstrb <= msi_addr[2] ? 8'hF0 : 8'h0F;
                        d_st <= D_MSI;
                    end else
                        d_st <= D_IDLE;
                end
                D_MSI: begin
                    if (m_awready) m_awvalid <= 1'b0;
                    if (m_wready) m_wvalid <= 1'b0;
                    if ((m_awready || !m_awvalid) && (m_wready || !m_wvalid)) d_st <= D_MSI_B;
                end
                D_MSI_B: if (m_bvalid) begin c_msis <= c_msis + 1'b1; d_st <= D_IDLE; end
                default: d_st <= D_IDLE;
            endcase

            // ---- interrupts: a posted entry sets bit 0, a fault bit 1; write 1 to clear
            if (wr_go && s_awaddr[11:2] == 10'h00E) irq_status <= irq_status & ~s_wdata[1:0];
            if (d_st == D_CQ0_B && m_bvalid) irq_status[0] <= 1'b1;
            if ((step_done && eng_fault) || (MODE == 1 && arr_fault)) begin
                irq_status[1] <= 1'b1; sticky_fault <= 1'b1;
            end

            // ---- MODE 0: issue and retire steps
            eng_start <= 1'b0;
            if (MODE == 0) begin
                case (i_st)
                    I_IDLE:
                        if (pick_v && enable && ev_n < EQD - 2) begin
                            eng_slot <= pick;
                            kv_base <= (ENG_CTX == 1) ? {AW{1'b0}} : pick * KVW;
                            if (ENG_CTX == 1 && (!own_v || own != pick)) begin
                                own_v <= 1'b1; own <= pick; eng_clr_req <= 1'b1; i_st <= I_CLR;
                            end else
                                i_st <= I_RD;
                        end
                    I_CLR: if (eng_clr_ack) begin eng_clr_req <= 1'b0; i_st <= I_RD; end
                    I_RD: i_st <= I_WAIT;                    // prompt-buffer read (below)
                    I_WAIT: begin
                        eng_pos <= sl_pos[eng_slot];
                        eng_token <= (sl_pos[eng_slot] < sl_plen[eng_slot]) ? pb_q : sl_tok[eng_slot];
                        i_st <= I_GO;
                    end
                    I_GO: begin
                        eng_start <= 1'b1; inflight <= 1'b1; c_steps <= c_steps + 1'b1;
                        rr <= eng_slot + 1'b1;
                        i_st <= I_RUN;
                    end
                    I_RUN:
                        if (step_done) begin
                            inflight <= 1'b0;
                            sl_pos[eng_slot] <= eng_pos + 1'b1;
                            sl_tok[eng_slot] <= eng_next_token;
                            if (d_gen) sl_ngen[eng_slot] <= d_ngen;
                            if (d_last) begin
                                sl_st[eng_slot] <= SL_DRAIN;
                                if (ENG_CTX == 1) own_v <= 1'b0;
                            end
                            i_st <= I_IDLE;
                        end
                    default: i_st <= I_IDLE;
                endcase
            end

            // ---- MODE 1: batches on the ROM array
            if (MODE == 1) begin
                case (b_st)
                    B_IDLE: if (batch_go) begin
                        if (b_ok) begin
                            b_err <= 0;
                            cfg_users <= batch_n; cfg_prompt_len <= sl_plen[0]; cfg_gen_len <= sl_max[0];
                            arr_rst_n <= 1'b0; b_cnt <= 0; b_st <= B_RST;
                            for (j = 0; j < NSLOT; j = j + 1) sl_t[j] <= c_cycles[31:0];
                        end else
                            b_err <= 2'd1;
                    end
                    B_RST: begin
                        b_cnt <= b_cnt + 1'b1;
                        if (b_cnt == 3'd7) begin arr_rst_n <= 1'b1; b_st <= B_RUN; end
                    end
                    B_RUN:
                        // the last user's token arrives with users_done: wait for its event to post
                        if (arr_rst_n && users_done == cfg_users && !tok_valid && ev_n == 0 && d_st == D_IDLE) begin
                            b_st <= B_IDLE;
                            for (j = 0; j < NSLOT; j = j + 1)
                                if (j < cfg_users) sl_st[j] <= SL_FREE;
                        end
                    default: b_st <= B_IDLE;
                endcase
                if (t_ok) c_steps <= c_steps + 1'b1;
                if (t_ok) begin
                    if (t_gen) begin
                        sl_ngen[t_slot] <= t_ngen;
                        sl_t[t_slot] <= c_cycles[31:0];
                    end
                    if (t_gen && t_last) sl_st[t_slot] <= SL_DRAIN;
                end
            end
        end
    end

    // -- event pushes ---------------------------------------------------------------------
    always @(*) begin
        ep_v = 1'b0; ep_d = {EVW{1'b0}};
        if (MODE == 0 && i_st == I_RUN && step_done && (d_gen || eng_fault)) begin
            ep_v = 1'b1;
            ep_d = ev(d_last ? EV_LAST : EV_TOKEN, d_last ? d_stat : ST_OK, {{(8-SB){1'b0}}, d_slot},
                      sl_tag[d_slot], d_pos, eng_next_token,
                      eng_cycles, d_gen ? d_ngen : sl_ngen[d_slot]);
        end
        if (MODE == 1 && t_ok && t_gen) begin
            ep_v = 1'b1;
            ep_d = ev(t_last ? EV_LAST : EV_TOKEN, t_last ? t_stat : ST_OK, {{(8-SB){1'b0}}, t_slot},
                      sl_tag[t_slot], tok_pos, tok_id,
                      c_cycles[31:0] - sl_t[t_slot], t_ngen);
        end
        dp_v = (d_st == D_ERR) && (err_st != ST_OK);
        dp_d = ev(EV_ERROR, err_st, q_slot, q_tag, {NW{1'b0}}, {NW{1'b0}}, 32'd0, {NW{1'b0}});
    end

    // -- prompt buffer read port: the step issue (MODE 0) or the package controller (MODE 1)
    always @(*) begin
        if (MODE == 1) begin
            pb_re = pr_re;
            pb_raddr = {pr_user[SB-1:0], pr_pos[PLB-1:0]};
        end else begin
            pb_re = (i_st == I_RD);
            pb_raddr = {eng_slot, sl_pos[eng_slot][PLB-1:0]};
        end
    end
endmodule
