`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// QE weight streaming engine of the DeepSeek-V4.1 hardwired decode core: the
// quantised (FP8 / FP4 block-scaled) weights in HBM.
//
// The quantised engine (ot_hdc_v41_qe) reads its weights as if from a ROM: in
// the row phase of a LINQ op it presents one word address a cycle on qr_addr
// (base, base + 1, ... -- the base plus an expert id times a stride for a routed
// expert) and takes the word one cycle later, with no valid and no stall.
// This engine keeps that contract with the words in HBM
// (ot_hdc_core_v41x W_HBM = 1).
//
// LAYOUT.  The HBM holds the quantised ROM in ROM order (routed experts at a
// fixed stride, as in the ROM): an FP8 word as its 17 32-byte sectors, an FP4
// word packed into 9 (per lane 32 E2M1 nibbles and the exponent; the ROM's
// word gives each 4-bit code an 8-bit slot), so the FP4 experts cost the HBM
// half the bytes of an FP8 word.  The fetch LIST (tools/hdc_program_v41.py
// qe_fetch_list, an external ROM of 128-bit entries) names every LINQ op of a
// token in consumption order: HBM sector base, ROM word base, words, FP4,
// predicate (the core's: pos odd / pos > 0), and for a routed expert the
// vector-memory element holding its id, the stride, and its release group.
//
// FETCH.  From each token start the walker takes the list in order, skips an
// entry whose predicate fails, and requests the entry's words one word (17 or
// 9 sectors, over up to 5 pseudo-channels) per request, out of order within a
// look-ahead of LA words: the lowest word whose pseudo-channels all have
// queue room (pc_room) goes next, so a pseudo-channel held by a refresh
// delays only the words that touch it.  Word n goes into slot n mod 2^LWIN of
// a window of 2^LWIN words
// (17 sector banks, sector j of slot s in bank (j + s) mod 17, a valid bit
// per sector; an FP4 word's 8 unused sectors are marked at request) whenever
// the window has room.  An expert-indexed entry waits until the program's
// release instruction of its group has issued (wrel_v: that instruction
// waited for the SELECT that wrote the ids), reads the id from the vector
// memory (vi_*), and adds id * stride.  The completion pointer walks the
// window in order and passes a word once all its sectors have arrived.
//
// NO STALL.  When the sequencer reaches a LINQ op it announces its shape
// (qd_*); its n = tiles * nb * IL words are the next n of the stream, and q_ok
// rises once the completion pointer is T = min(n, lead + n - floor(n * rate /
// 256)) words into it (see ot_hdc_wstream).  Every word the QE reads is
// checked (fail closed, sticky fault): it must have arrived, and its ROM
// address must be the list entry's next.
// ---------------------------------------------------------------------------
module ot_hdc_qstream #(
    parameter integer FULL_SHAPE = 0,
    parameter integer LIST_BITS = FULL_SHAPE ? 160 : 128,
    parameter integer BL     = 16,
    parameter integer QLB    = 272,      // bits per lane of a QE word (32 codes, 16-bit exponent)
    parameter integer SB     = 256,
    parameter integer AW     = FULL_SHAPE ? 30 : 24,
    parameter integer HAW    = FULL_SHAPE ? 30 : 24,
    parameter integer NW     = FULL_SHAPE ? 21 : 16,
    parameter integer IL     = 8,
    parameter integer LWIN   = 10,
    parameter integer NPC    = 8,
    parameter integer LENW   = 6,
    parameter integer BEATW  = 5,
    parameter integer LAW    = 12,       // fetch-list address bits
    parameter integer LA     = 8         // request look-ahead, words
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [HAW-1:0]    cfg_base,       // HBM sector of the quantised region
    input  wire [LAW-1:0]    cfg_lbase,      // first fetch-list entry of the program the token runs
    input  wire [NW-1:0]     cfg_lead,
    input  wire [15:0]       cfg_rate,       // words per cycle x 256
    input  wire              tok_start,
    input  wire [NW-1:0]     pos,
    // fetch list (synchronous-read ROM)
    output reg               l_re,
    output reg  [LAW-1:0]    l_addr,
    input  wire [LIST_BITS-1:0] l_q,
    // vector-memory read of an expert id
    output reg               vi_re,
    output reg  [AW-1:0]     vi_addr,
    input  wire [31:0]       vi_q,
    input  wire              wrel_v,
    // shape of the LINQ op the sequencer waits on, and its issue permission
    input  wire              qd_v,
    input  wire [7:0]        qd_nb,
    input  wire [NW-1:0]     qd_tiles,
    output reg               q_ok,
    // the QE's weight read port (fixed latency 1, no stall)
    input  wire              qr_re,
    input  wire [AW-1:0]     qr_addr,
    output reg  [BL*QLB-1:0] qr_q,
    // window SRAM: SPW banks of 2^LWIN sectors
    output reg  [BL*QLB/SB-1:0] win_we,
    output reg  [(BL*QLB/SB)*LWIN-1:0] win_waddr,
    output reg  [BL*QLB-1:0] win_wdata,
    output wire              win_re,
    output wire [LWIN-1:0]   win_raddr,
    input  wire [BL*QLB-1:0] win_q,
    // HBM read requests
    output reg               hq_v,
    input  wire              hq_rdy,
    output reg  [HAW-1:0]    hq_addr,
    output reg  [LENW-1:0]   hq_len,
    output reg  [LWIN-1:0]   hq_tag,
    input  wire [NPC-1:0]    hq_room,        // pseudo-channels with queue room
    input  wire [NPC-1:0]    hr_v,
    output reg  [NPC-1:0]    hr_rdy,
    input  wire [NPC*LWIN-1:0] hr_tag,
    input  wire [NPC*BEATW-1:0] hr_beat,
    input  wire [NPC*SB-1:0] hr_data,
    output reg               fault,
    output reg  [3:0]        fault_why,      // {uncoverable, overrun, address, underflow}
    output wire [31:0]       st_fetched,
    output wire [31:0]       st_consumed
);
    localparam integer WB   = BL * QLB;
    localparam integer SPW  = WB / SB;              // 17: an FP8 word
    localparam integer SPW4 = (BL * 144) / SB;      // 9: an FP4 word, packed
    localparam integer WIN  = 1 << LWIN;
    localparam integer LS   = $clog2(SPW);

    localparam integer DA=FULL_SHAPE ? 30 : 24;
    localparam integer DN=FULL_SHAPE ? 21 : 16;
    localparam integer O_ROM=DA, O_N=2*DA, O_FP4=2*DA+DN;
    localparam integer O_PRED=O_FP4+1, O_IND=O_FP4+3;
    localparam integer O_IBASE=O_FP4+4, O_STRIDE=O_IBASE+DA;
    localparam integer O_GRP=O_STRIDE+DA, USED=O_GRP+8;
    wire [63:0] desc_hbm_sum = 64'(cfg_base) + 64'(l_q[0 +: DA]);
    wire [95:0] indirect_words = 96'(FULL_SHAPE ? vi_q : 32'(vi_q[AW-1:0])) * 96'(e_istride);
    wire [95:0] indirect_rom = 96'(e_rom) + indirect_words;
    wire [95:0] indirect_hbm = 96'(e_hbm) + indirect_words * (e_fp4 ? SPW4 : SPW);
    reg descriptor_bad;
    initial begin
        if (FULL_SHAPE && (AW<DA || HAW<DA || NW<DN || LIST_BITS!=160))
            $fatal(1,"full qstream profile requires AW/HAW>=30 NW>=21 LIST_BITS160");
    end
    reg  [31:0] fp, cp, cons;
    reg  [WIN*SPW-1:0] vbits;
    reg  [WIN-1:0] sfp4;                            // the slot's word is FP4 (packed)

    // ---- list walker ------------------------------------------------------------------------------
    localparam [3:0] W_IDLE = 0, W_LOAD = 1, W_LWAIT = 2, W_DEC = 3, W_REL = 4, W_IW1 = 5, W_IW2 = 6,
                     W_PUSH = 7, W_REQ = 8;
    reg  [3:0]    w_st;
    reg  [LAW-1:0] l_idx;
    reg  [7:0]    rel_cnt;
    reg  [HAW-1:0] e_hbm, a_hbm;
    reg  [AW-1:0] e_rom;
    reg  [DN-1:0] e_n, e_i;
    reg           e_fp4, e_ind;
    reg  [1:0]    e_pred;
    reg  [AW-1:0] e_ibase, e_istride;
    reg  [7:0]    e_grp;
    wire          e_pred_ok = (e_pred == 2'd0) || (e_pred == 2'd1 && pos[0]) || (e_pred == 2'd2 && pos != 0);
    wire          hq_free = !hq_v || hq_rdy;
    wire [LENW-1:0] e_spw = e_fp4 ? SPW4 : SPW;
    reg  [31:0]   e_g0;                             // stream index of the entry's word 0
    reg  [LA-1:0] la_iss;                           // look-ahead words already requested
    localparam integer LPC = (NPC > 1) ? $clog2(NPC) : 0;
    localparam integer LLA = (LA > 1) ? $clog2(LA) : 1;
    function automatic [LPC:0] pc_of_chunk(input [HAW-1:0] c);
        pc_of_chunk = (c ^ (c >> LPC) ^ (c >> (2 * LPC))) & (NPC - 1);
    endfunction
    // candidate words of the look-ahead: request-able when unrequested, in the
    // entry, in a free window slot and every pseudo-channel they touch has room
    reg  [LA-1:0]  la_ok;
    reg  [HAW-1:0] la_addr [0:LA-1];
    reg  [31:0]    la_g [0:LA-1];
    reg  [HAW-1:0] la_c0, la_c1;
    reg            la_room;
    integer lj, lc;
    always @(*) begin
        for (lj = 0; lj < LA; lj = lj + 1) begin
            la_addr[lj] = e_hbm + (e_i + lj) * e_spw;
            la_g[lj] = e_g0 + e_i + lj;
            la_c0 = la_addr[lj] >> 2;
            la_c1 = (la_addr[lj] + e_spw - 1) >> 2;
            la_room = 1'b1;
            for (lc = 0; lc < 6; lc = lc + 1)
                if (la_c0 + lc <= la_c1 && !hq_room[pc_of_chunk(la_c0 + lc)]) la_room = 1'b0;
            la_ok[lj] = (e_i + lj < e_n) && !la_iss[lj] && (la_g[lj] - cons < WIN) && la_room;
        end
    end
    reg            la_any;
    reg  [LLA-1:0] la_pick;
    reg  [LA-1:0]  la_nxt;
    reg  [LLA:0]   la_shift;
    integer lk;
    always @(*) begin
        la_any = 1'b0; la_pick = 0;
        for (lk = LA - 1; lk >= 0; lk = lk - 1) if (la_ok[lk]) begin la_any = 1'b1; la_pick = lk; end
        la_nxt = la_iss | (la_any ? ({{(LA-1){1'b0}}, 1'b1} << la_pick) : {LA{1'b0}});
        la_shift = 0;
        for (lk = 0; lk < LA; lk = lk + 1) if (la_shift == lk && la_nxt[lk]) la_shift = lk + 1;
    end
    wire [31:0]   occ = fp - cons;
    // op FIFO: the entries the walker has started, for the consumer's address check
    reg  [AW-1:0] of_rom [0:31];
    reg  [DN-1:0] of_n [0:31];
    reg  [4:0]    of_wp, of_rp;
    reg  [5:0]    of_cnt;
    wire          of_pop;
    wire          of_push = (w_st == W_PUSH);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            descriptor_bad <= 1'b0; w_st <= W_IDLE; l_re <= 1'b0; vi_re <= 1'b0; hq_v <= 1'b0; fp <= 0; rel_cnt <= 0; l_idx <= 0;
        end else begin
            l_re <= 1'b0; vi_re <= 1'b0;
            if (tok_start) rel_cnt <= 0;
            else if (wrel_v) rel_cnt <= rel_cnt + 1'b1;
            if (hq_free) hq_v <= 1'b0;
            case (w_st)
                W_IDLE: if (tok_start) begin l_idx <= cfg_lbase; w_st <= W_LOAD; end
                W_LOAD: begin l_re <= 1'b1; l_addr <= l_idx; w_st <= W_LWAIT; end
                W_LWAIT: w_st <= W_DEC;
                W_DEC: begin
                    e_hbm <= desc_hbm_sum[HAW-1:0]; e_rom <= l_q[O_ROM +: DA];
                    e_n <= l_q[O_N +: DN]; e_fp4 <= l_q[O_FP4];
                    e_pred <= l_q[O_PRED +: 2]; e_ind <= l_q[O_IND];
                    e_ibase <= l_q[O_IBASE +: DA]; e_istride <= l_q[O_STRIDE +: DA];
                    e_grp <= l_q[O_GRP +: 8];
                    if (FULL_SHAPE && ((|l_q[LIST_BITS-1:USED]) ||
                        (desc_hbm_sum >> HAW)!=0 ||
                        (64'(l_q[O_ROM +: DA])+64'(l_q[O_N +: DN]) > (64'd1<<AW)) ||
                        (desc_hbm_sum+64'(l_q[O_N +: DN])*(l_q[O_FP4] ? SPW4 : SPW) > (64'd1<<HAW)))) begin
                        descriptor_bad <= 1'b1; w_st <= W_IDLE;
                    end else w_st <= (l_q[O_N +: DN] == 0) ? W_IDLE : W_REL;
                end
                W_REL: begin
                    if (!e_pred_ok) begin l_idx <= l_idx + 1'b1; w_st <= W_LOAD; end
                    else if (!e_ind) w_st <= W_PUSH;
                    else if (rel_cnt >= e_grp) begin vi_re <= 1'b1; vi_addr <= e_ibase; w_st <= W_IW1; end
                end
                W_IW1: w_st <= W_IW2;
                W_IW2: begin
                    if (FULL_SHAPE &&
                        (indirect_rom+64'(e_n) > (64'd1<<AW) ||
                         indirect_hbm+64'(e_n)*(e_fp4 ? SPW4 : SPW) > (64'd1<<HAW))) begin
                        descriptor_bad <= 1'b1; w_st <= W_IDLE;
                    end else begin
                        e_rom <= indirect_rom[AW-1:0];
                        e_hbm <= indirect_hbm[HAW-1:0]; w_st <= W_PUSH;
                    end
                end
                W_PUSH: begin e_i <= 0; e_g0 <= fp; la_iss <= 0; w_st <= W_REQ; end
                W_REQ: if (hq_free && la_any) begin
                    hq_v <= 1'b1; hq_addr <= la_addr[la_pick]; hq_len <= e_spw; hq_tag <= la_g[la_pick][LWIN-1:0];
                    //: the issued prefix of the look-ahead retires
                    e_i <= e_i + la_shift;
                    la_iss <= la_nxt >> la_shift;
                    if (e_i + la_shift == e_n) begin
                        fp <= e_g0 + e_n; l_idx <= l_idx + 1'b1; w_st <= W_LOAD;
                    end
                end
                default: w_st <= W_IDLE;
            endcase
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin of_wp <= 0; of_rp <= 0; of_cnt <= 0; end
        else begin
            if (of_push) begin of_wp <= of_wp + 1'b1; end
            if (of_pop) of_rp <= of_rp + 1'b1;
            of_cnt <= of_cnt + (of_push ? 6'd1 : 6'd0) - (of_pop ? 6'd1 : 6'd0);
        end
    end
    always @(posedge clk) if (of_push) begin of_rom[of_wp] <= e_rom; of_n[of_wp] <= e_n; end

    // ---- responses -> window banks ------------------------------------------------------------------
    reg  [$clog2(NPC+1)-1:0] rr;
    wire [NPC*LS-1:0] rsp_bank;
    genvar gp;
    generate
        for (gp = 0; gp < NPC; gp = gp + 1) begin : g_rsp
            wire [LWIN-1:0]  t = hr_tag[gp*LWIN +: LWIN];
            wire [BEATW-1:0] b = hr_beat[gp*BEATW +: BEATW];
            assign rsp_bank[gp*LS +: LS] = (b + (t % SPW)) % SPW;
        end
    endgenerate
    reg  [SPW-1:0] bank_used;
    integer pi, pp;
    always @(*) begin
        hr_rdy = 0; bank_used = 0;
        for (pi = 0; pi < NPC; pi = pi + 1) begin
            pp = (rr + pi) % NPC;
            if (hr_v[pp] && !bank_used[rsp_bank[pp*LS +: LS]]) begin
                hr_rdy[pp] = 1'b1; bank_used[rsp_bank[pp*LS +: LS]] = 1'b1;
            end
        end
    end
    reg  [SPW-1:0]      st_we;
    reg  [SPW*LWIN-1:0] st_slot;
    reg  [WB-1:0]       st_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rr <= 0; st_we <= 0; win_we <= 0; end
        else begin
            rr <= (rr == NPC - 1) ? 0 : rr + 1'b1;
            st_we <= 0;
            for (pi = 0; pi < NPC; pi = pi + 1)
                if (hr_v[pi] && hr_rdy[pi]) st_we[rsp_bank[pi*LS +: LS]] <= 1'b1;
            win_we <= st_we;
        end
    end
    always @(posedge clk) begin
        for (pi = 0; pi < NPC; pi = pi + 1)
            if (hr_v[pi] && hr_rdy[pi]) begin
                st_slot[rsp_bank[pi*LS +: LS]*LWIN +: LWIN] <= hr_tag[pi*LWIN +: LWIN];
                st_data[rsp_bank[pi*LS +: LS]*SB +: SB] <= hr_data[pi*SB +: SB];
            end
        win_waddr <= st_slot; win_wdata <= st_data;
    end

    // ---- completion pointer, consumer ------------------------------------------------------------------
    wire [LWIN-1:0] cp_slot = cp[LWIN-1:0];
    wire [LWIN-1:0] c_slot = cons[LWIN-1:0];
    wire [LWIN-1:0] f_slot = la_g[la_pick][LWIN-1:0];
    wire [31:0]     cp_ahead = cp - cons;
    wire            cp_step = (cp_ahead < WIN) && (&vbits[cp_slot*SPW +: SPW]);
    wire            f_take = (w_st == W_REQ) && hq_free && la_any;
    integer vb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vbits <= 0; cp <= 0; cons <= 0; end
        else begin
            if (cp_step) cp <= cp + 1'b1;
            if (qr_re) begin
                cons <= cons + 1'b1;
                vbits[c_slot*SPW +: SPW] <= {SPW{1'b0}};
            end
            //: an FP4 word's unused sectors count as arrived from its request on
            //: (its bank rotation puts them in banks (j + s) mod 17, j >= 9)
            if (f_take && e_fp4)
                for (vb = SPW4; vb < SPW; vb = vb + 1) vbits[f_slot*SPW + (vb + f_slot % SPW) % SPW] <= 1'b1;
            for (vb = 0; vb < SPW; vb = vb + 1)
                if (win_we[vb]) vbits[win_waddr[vb*LWIN +: LWIN]*SPW + vb] <= 1'b1;
        end
    end
    always @(posedge clk) if (f_take) sfp4[f_slot] <= e_fp4;
    assign win_re = qr_re;
    assign win_raddr = c_slot;
    reg          q_fp4;
    reg [LS-1:0] q_rot;
    always @(posedge clk) begin
        q_fp4 <= sfp4[c_slot];
        q_rot <= c_slot % SPW;
    end
    // sector j of the word is bank (j + rot) mod SPW; an FP4 word is unpacked:
    // lane l's 32 nibbles and exponent from bits l*144 of the packed word
    reg [WB-1:0] w_raw;
    integer rj, ln, cn;
    always @(*) begin
        for (rj = 0; rj < SPW; rj = rj + 1) w_raw[rj*SB +: SB] = win_q[((rj + q_rot) % SPW)*SB +: SB];
        if (!q_fp4) qr_q = w_raw;
        else begin
            qr_q = {WB{1'b0}};
            for (ln = 0; ln < BL; ln = ln + 1) begin
                for (cn = 0; cn < 32; cn = cn + 1) qr_q[ln*QLB + 8*cn +: 4] = w_raw[ln*144 + 4*cn +: 4];
                qr_q[ln*QLB + 256 +: 16] = w_raw[ln*144 + 128 +: 16];
            end
        end
    end

    // ---- announced ops: threshold and issue permission ------------------------------------------------
    reg  [2:0]    tp;
    reg  [7:0]    a_nb;
    reg  [NW-1:0] a_tiles;
    reg  [31:0]   a_n, a_T, ann_end, op_start;
    reg [(FULL_SHAPE ? 48 : 32)-1:0] a_nr;
    reg           t_rdy, uncoverable;
    wire [31:0]   a_fast = a_nr >> 8;
    wire [31:0]   a_short = (a_fast >= a_n) ? 32'd0 : a_n - a_fast;
    wire [31:0]   a_Tl = cfg_lead + a_short;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tp <= 0; t_rdy <= 1'b0; q_ok <= 1'b0; uncoverable <= 1'b0; ann_end <= 0; op_start <= 0;
        end else begin
            uncoverable <= 1'b0;
            tp <= {tp[1:0], qd_v};
            if (qd_v) begin a_nb <= qd_nb; a_tiles <= qd_tiles; t_rdy <= 1'b0; end
            if (tp[0]) a_n <= a_tiles * a_nb * IL;
            if (tp[1]) begin a_nr <= a_n * cfg_rate; op_start <= ann_end; ann_end <= ann_end + a_n; end
            if (tp[2]) begin
                a_T <= (a_Tl < a_n) ? a_Tl : a_n;
                uncoverable <= ((a_Tl < a_n) ? a_Tl : a_n) > WIN;
                t_rdy <= 1'b1;
            end
            q_ok <= t_rdy && !qd_v && (tp == 0) && (cp - op_start >= a_T);
        end
    end
    // consumer check against the op FIFO
    reg  [DN-1:0] c_i;
    reg         addr_bad, underflow, overrun;
    assign of_pop = qr_re && (of_cnt != 0) && (c_i + 1'b1 == of_n[of_rp]);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c_i <= 0; addr_bad <= 1'b0; underflow <= 1'b0; overrun <= 1'b0; end
        else begin
            addr_bad <= 1'b0; underflow <= 1'b0;
            overrun <= of_push && of_cnt == 32;
            if (qr_re) begin
                if ($signed(cp - cons) <= 0) underflow <= 1'b1;
                if (of_cnt == 0 || qr_addr != of_rom[of_rp] + c_i) addr_bad <= 1'b1;
                c_i <= of_pop ? DN'(0) : c_i + 1'b1;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fault <= 1'b0; fault_why <= 0; end
        else if (underflow || addr_bad || overrun || uncoverable || descriptor_bad) begin
            fault <= 1'b1;
            fault_why <= fault_why | {uncoverable | descriptor_bad, overrun, addr_bad, underflow};
        end
    end
    reg  [31:0] n_req;
    always @(posedge clk or negedge rst_n) if (!rst_n) n_req <= 0; else if (f_take) n_req <= n_req + 1'b1;
    assign st_fetched = n_req;
    assign st_consumed = cons;
endmodule
