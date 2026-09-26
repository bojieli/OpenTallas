`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hardwired decode core (HDC): decodes one token of a fixed model.
//
// A static program (tools/hdc_program.py, format tools/hdc_isa.py) of
// macro-operations drives two units, the matrix-vector engine (ot_hdc_matvec)
// and the stream unit (ot_hdc_stream).  The sequencer fetches an instruction,
// adds the per-token DYN offsets (token row, RoPE row, KV write slot, context
// length) and issues it when the unit is ready; an instruction marked `barrier`
// first waits for both units to drain.  There is no descriptor queue, no
// admission and no interpretation: the program is the schedule.
//
// ISSUE PIPELINE.  Fetch runs ahead of issue: program words stream from the
// program ROM (a read every cycle while fewer than NFQ words are held or in
// flight) into a small word FIFO; the head is decoded (DYN offsets added) into
// the NEXT register set whenever it is empty or being issued.  An instruction
// issues from NEXT in the cycle its conditions hold: `me_go` / `su_go` are
// combinational and the unit latches NEXT's fields on that edge, the same edge
// that decodes the following instruction into NEXT -- so independent
// instructions issue on consecutive cycles (the issue gap is 1, was 5).
//
// Memories sit outside the core behind synchronous-read ports: program ROM,
// weight ROM (W x BF16 per word), constant ROM (FP32 pairs), KV SRAM (W x FP32
// per word, element write) and the vector memory (FP32 elements).
// ---------------------------------------------------------------------------
module ot_hdc_core #(
    parameter integer INSTR_BITS = 1024,   // must equal ISA_INSTR_BITS (tools/hdc_isa.py)
    parameter integer W    = 16,
    parameter integer G    = 4,
    parameter integer IL   = 8,
    parameter integer AW   = 24,
    parameter integer NW   = 16,
    parameter integer PAW  = 12,      // program address bits
    // model constants for the DYN offsets
    parameter integer HID  = 128,
    parameter integer HALF = 8,
    parameter integer HD   = 16,
    // KV_HBM = 1: the KV cache lives in HBM behind ot_hdc_kv_stream.  A
    // KV-sourced matrix op then announces its descriptor (kvd_*) when the
    // sequencer reaches it and issues only once the streamer raises kv_ok
    // (its prefetch window covers the op; the engine never stalls).  With
    // KV_HBM = 0 the kvd_* outputs are unused and kv_ok is ignored.
    parameter integer KV_HBM = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [NW-1:0]     token,
    input  wire [NW-1:0]     pos,
    output reg               done,
    output reg  [NW-1:0]     next_token,
    output reg  [31:0]       next_val,        // its logit (for an argmax combined across packages)
    output reg  [31:0]       cycles,
    output reg               fault,
    // program ROM
    output reg               prog_re,
    output reg  [PAW-1:0]    prog_addr,
    input  wire [INSTR_BITS-1:0] prog_q,
    // weight ROM
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    input  wire [G*W*16-1:0] wrom_q,
    // constant ROM
    output wire              crom_re,
    output wire [AW-1:0]     crom_addr,
    input  wire [63:0]       crom_q,
    // KV SRAM
    output wire              kv_re,
    output wire [G*AW-1:0]   kv_raddr,        // one read port per lane group
    input  wire [G*W*32-1:0] kv_q,
    output wire              kv_we,
    output wire [AW-1:0]     kv_waddr,
    output wire [31:0]       kv_wdata,
    // vector memory: G + 3 element read ports, G + 2 write ports
    output wire [G-1:0]      vx_re,
    output wire [G*AW-1:0]   vx_addr,
    input  wire [G*32-1:0]   vx_q,
    output wire              va_re,
    output wire [AW-1:0]     va_addr,
    input  wire [31:0]       va_q,
    output wire              vb_re,
    output wire [AW-1:0]     vb_addr,
    input  wire [31:0]       vb_q,
    output wire              vc_re,
    output wire [AW-1:0]     vc_addr,
    input  wire [31:0]       vc_q,
    output wire [G-1:0]      vw_me_we,
    output wire [G*AW-1:0]   vw_me_addr,       // words
    output wire [G*W-1:0]    vw_me_mask,
    output wire [G*W*32-1:0] vw_me_data,
    output wire              vw_su_we,
    output wire [AW-1:0]     vw_su_addr,
    output wire [31:0]       vw_su_data,
    output wire              vw_rd_we,
    output wire [AW-1:0]     vw_rd_addr,
    output wire [31:0]       vw_rd_data,
    // observation: every matrix-vector result word
    output wire              me_ov,
    output wire [G*AW-1:0]   me_oaddr,
    output wire [G*W-1:0]    me_omask,
    output wire [G*W*32-1:0] me_odata,
    // KV-streaming handshake (KV_HBM = 1 only)
    output reg               kvd_v,           // descriptor of the KV op now waiting to issue
    output wire [AW-1:0]     kvd_wbase, kvd_ts, kvd_ks, kvd_js,
    output wire [2:0]        kvd_jsh,
    output wire [NW-1:0]     kvd_tiles, kvd_k, kvd_nout,
    output wire              kvd_kindk,       // positions tile the lanes (scores); else positions are k (weighted sum)
    output wire [NW-1:0]     kvd_pos,
    input  wire              kv_ok
);
    `include "ot_hdc_isa.svh"
    localparam integer LW = $clog2(W);
    localparam integer LT = $clog2(W * IL);
    localparam integer LT0 = $clog2(W * G);

    // -- sequencer ----------------------------------------------------------------
    localparam [1:0] S_IDLE = 0, S_DYN = 1, S_RUN = 2;
    localparam integer NFQ = 4;           // program words held or in flight
    reg [1:0]  st;
    reg [PAW-1:0] pc;                     // index of the instruction in NEXT
    reg [PAW-1:0] fpc;                    // next word to fetch
    reg [NW-1:0] tok_r, pos_r;
    reg [AW-1:0] dyn [0:7];
    reg [INSTR_BITS-1:0] fq [0:NFQ-1];
    reg [1:0]  fq_rd, fq_wr;
    reg [2:0]  fq_n;
    reg        pend1;                     // a program read whose word arrives this cycle
    wire [INSTR_BITS-1:0] ir = fq[fq_rd]; // FIFO head: the word decode reads
    reg        nx_v;                      // NEXT holds a decoded instruction
    wire       me_go, su_go;
    wire       me_ready, me_idle, su_ready, su_idle;
    wire       me_fault, su_fault;
    wire [NW-1:0] am_idx;
    wire [31:0] am_val;
    wire       am_any;

    `define F(name) ir[O_``name +: W_``name]

    // decoded, DYN-adjusted fields
    reg [1:0]    d_unit;
    reg          d_barrier;
    reg [NW-1:0] me_nout, me_tiles, me_k;
    reg          me_wsrc, me_round, me_oen, me_amax, me_mmode, d_chase;
    reg [15:0]   d_chase_n;
    reg [AW-1:0] me_wbase, me_ts, me_ks, me_js, me_xbase, me_obase, me_xks, me_xjs, me_ots, me_ojs;
    reg [2:0]    me_jsh;
    reg [3:0]    me_split;
    reg [AW-1:0] me_xcs, me_wcs;
    reg [NW-1:0] su_nout, su_nin;
    reg          a_src, b_src, c_src, mc;
    reg [AW-1:0] a_base, a_so, a_si, b_base, b_so, b_si, c_base, c_so, c_si;
    reg [AW-1:0] d_base, d_so, d_si, r_base, r_so;
    reg [1:0]    ma, mb, dst, red;
    reg [2:0]    sfu;
    reg          redsq, md;
    reg [2:0]    ad;
    reg [31:0]   imm1, imm2;

    wire [15:0] su_progress, me_progress;
    reg          me_kindk;
    wire unit_ready = (d_unit == 2'd1) ? me_ready : su_ready;
    //: KV_HBM: a KV op waits for the streamer; never on the cycle its
    //: descriptor is announced, when kv_ok may still describe the previous op.
    wire kv_gate = (KV_HBM == 0) || !(d_unit == 2'd1 && me_wsrc) || (kv_ok && !kvd_v);
    //: the units' idle and progress are registered and cleared on the edge
    //: that accepts an op, so a go needs no guard term here
    wire drained = me_idle && su_idle;
    //: A chasing op waits only until the OTHER unit's latest op has made
    //: chase_n progress.
    wire chased = ((d_unit == 2'd1) ? su_progress : me_progress) >= d_chase_n;
    //: issue NEXT this cycle; the unit latches its fields on this edge
    wire issue = (st == S_RUN) && nx_v && (d_unit != 2'd0) &&
                 (d_barrier ? drained : (!d_chase || chased)) && unit_ready && kv_gate;
    assign me_go = issue && (d_unit == 2'd1);
    assign su_go = issue && (d_unit == 2'd2);
    wire fin = (st == S_RUN) && nx_v && (d_unit == 2'd0) && drained;
    //: decode the FIFO head into NEXT when NEXT is empty or issuing
    wire load = (st == S_RUN) && (fq_n != 0) && (!nx_v || issue);
    wire push = (st == S_RUN) && pend1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; pc <= 0; fpc <= 0; done <= 1'b0; prog_re <= 1'b0; pend1 <= 1'b0;
            fq_rd <= 0; fq_wr <= 0; fq_n <= 0; nx_v <= 1'b0;
            cycles <= 0; next_token <= 0;
        end else begin
            if (st != S_IDLE) cycles <= cycles + 1;
            pend1 <= prog_re && (st != S_IDLE);
            prog_re <= 1'b0;
            case (st)
                S_IDLE: if (start) begin
                    tok_r <= token; pos_r <= pos; pc <= 0; fpc <= 0; done <= 1'b0; cycles <= 0;
                    fq_rd <= 0; fq_wr <= 0; fq_n <= 0; nx_v <= 1'b0; pend1 <= 1'b0;
                    st <= S_DYN;
                end
                S_DYN: st <= S_RUN;
                S_RUN: begin
                    // fetch: one word a cycle while fewer than NFQ are held or in flight
                    if ({1'b0, fq_n} + prog_re + pend1 < NFQ) begin
                        prog_re <= 1'b1; prog_addr <= fpc; fpc <= fpc + 1'b1;
                    end
                    if (push) begin fq[fq_wr] <= prog_q; fq_wr <= fq_wr + 1'b1; end
                    if (load) fq_rd <= fq_rd + 1'b1;
                    fq_n <= fq_n + (push ? 3'd1 : 3'd0) - (load ? 3'd1 : 3'd0);
                    if (issue) pc <= pc + 1'b1;
                    if (load) nx_v <= 1'b1;
                    else if (issue) nx_v <= 1'b0;
                    if (fin) begin
                        done <= 1'b1; next_token <= am_idx; next_val <= am_val; st <= S_IDLE; nx_v <= 1'b0;
                        prog_re <= 1'b0;
                    end
                end
                default: st <= S_IDLE;
            endcase
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) kvd_v <= 1'b0;
        else kvd_v <= load && ir[O_UNIT +: W_UNIT] == 2'd1 && ir[O_ME_WSRC];
    end
    assign kvd_wbase = me_wbase; assign kvd_ts = me_ts; assign kvd_ks = me_ks; assign kvd_js = me_js;
    assign kvd_jsh = me_jsh; assign kvd_tiles = me_tiles; assign kvd_k = me_k; assign kvd_nout = me_nout;
    assign kvd_kindk = me_kindk; assign kvd_pos = pos_r;

    // DYN offsets derived once per token.
    always @(posedge clk) if (st == S_DYN) begin
        dyn[0] <= 0;
        dyn[1] <= tok_r * HID;
        dyn[2] <= pos_r * HALF;
        dyn[3] <= (pos_r >> LW) * (HD * W) + (pos_r & (W - 1));
        dyn[4] <= pos_r * HD;
        dyn[5] <= pos_r + 1;
        dyn[6] <= (pos_r >> LT0) + 1;            // rounds of G position tiles (split 0; see S_DEC)
        dyn[7] <= 0;
    end

    // Decode: every base and count may add one DYN value.
    always @(posedge clk) if (load) begin
        d_unit <= `F(UNIT); d_barrier <= `F(BARRIER);
        me_nout <= `F(ME_NOUT) + dyn[`F(ME_D_NOUT)];
        //: DYN_TTILES counts rounds of G/S position tiles (S = 2^split)
        me_tiles <= `F(ME_TILES) + ((`F(ME_D_TILES) == 3'd6) ? ((pos_r >> (LT0 - `F(ME_SPLIT))) + 1'b1)
                                                               : dyn[`F(ME_D_TILES)]);
        me_k <= `F(ME_K) + dyn[`F(ME_D_K)];
        me_kindk <= (`F(ME_D_TILES) == 3'd6);        // DYN_TTILES: rounds of position tiles
        me_wsrc <= `F(ME_WSRC); me_round <= `F(ME_ROUND); me_oen <= `F(ME_OEN); me_amax <= `F(ME_AMAX);
        me_wbase <= `F(ME_WBASE) + dyn[`F(ME_D_WBASE)];
        me_ts <= `F(ME_TS); me_ks <= `F(ME_KS); me_js <= `F(ME_JS);
        me_xbase <= `F(ME_XBASE) + dyn[`F(ME_D_XBASE)];
        me_obase <= `F(ME_OBASE) + dyn[`F(ME_D_OBASE)];
        me_xks <= `F(ME_XKS); me_xjs <= `F(ME_XJS); me_jsh <= `F(ME_JSH);
        me_ots <= `F(ME_OTS); me_ojs <= `F(ME_OJS); me_mmode <= `F(ME_MMODE);
        d_chase <= `F(CHASE); d_chase_n <= `F(CHASE_N);
        me_split <= `F(ME_SPLIT); me_xcs <= `F(ME_XCS); me_wcs <= `F(ME_WCS);
        su_nout <= `F(SU_NOUT);
        su_nin <= `F(SU_NIN) + dyn[`F(SU_D_NIN)];
        a_src <= `F(A_SRC); a_base <= `F(A_BASE) + dyn[`F(A_D)]; a_so <= `F(A_SO); a_si <= `F(A_SI);
        b_src <= `F(B_SRC); b_base <= `F(B_BASE) + dyn[`F(B_D)]; b_so <= `F(B_SO); b_si <= `F(B_SI);
        c_src <= `F(C_SRC); c_base <= `F(C_BASE) + dyn[`F(C_D)]; c_so <= `F(C_SO); c_si <= `F(C_SI);
        ma <= `F(MA); mb <= `F(MB); ad <= `F(AD); sfu <= `F(SFU); mc <= `F(MC); md <= `F(MD);
        dst <= `F(DST); d_base <= `F(D_BASE) + dyn[`F(D_D)]; d_so <= `F(D_SO); d_si <= `F(D_SI);
        red <= `F(RED); redsq <= `F(RED_SQ); r_base <= `F(R_BASE); r_so <= `F(R_SO);
        imm1 <= `F(IMM1); imm2 <= `F(IMM2);
    end
    `undef F

    // -- units ----------------------------------------------------------------------
    wire me_wrom_re, su_wrom_re;
    wire [AW-1:0] me_wrom_addr, su_wrom_addr;
    ot_hdc_matvec #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW)) u_me (
        .clk(clk), .rst_n(rst_n), .go(me_go), .ready(me_ready), .idle(me_idle),
        .i_nout(me_nout), .i_tiles(me_tiles), .i_k(me_k), .i_wsrc(me_wsrc), .i_wbase(me_wbase),
        .i_ts(me_ts), .i_ks(me_ks), .i_js(me_js), .i_xbase(me_xbase), .i_xks(me_xks), .i_xjs(me_xjs),
        .i_xcs(me_xcs), .i_jsh(me_jsh), .i_split(me_split), .i_wcs(me_wcs), .i_round(me_round), .i_obase(me_obase), .i_ots(me_ots), .i_ojs(me_ojs),
        .i_mmode(me_mmode), .i_oen(me_oen), .i_amax(me_amax),
        .wrom_re(me_wrom_re), .wrom_addr(me_wrom_addr), .wrom_q(wrom_q),
        .kv_re(kv_re), .kv_addr(kv_raddr), .kv_q(kv_q),
        .x_re(vx_re), .x_addr(vx_addr), .x_q(vx_q),
        .ov(me_ov), .o_we(vw_me_we), .o_addr(vw_me_addr), .o_mask(vw_me_mask), .o_data(vw_me_data),
        .am_idx(am_idx), .am_val(am_val), .am_any(am_any), .progress(me_progress), .fault(me_fault));
    assign me_oaddr = vw_me_addr;
    assign me_omask = vw_me_mask;
    assign me_odata = vw_me_data;

    ot_hdc_stream #(.W(W), .WR(G * W), .AW(AW), .NW(NW)) u_su (
        .clk(clk), .rst_n(rst_n), .go(su_go), .ready(su_ready), .idle(su_idle),
        .i_nout(su_nout), .i_nin(su_nin),
        .i_asrc(a_src), .i_abase(a_base), .i_aso(a_so), .i_asi(a_si),
        .i_bsrc(b_src), .i_bbase(b_base), .i_bso(b_so), .i_bsi(b_si),
        .i_csrc(c_src), .i_cbase(c_base), .i_cso(c_so), .i_csi(c_si),
        .i_ma(ma), .i_mb(mb), .i_ad(ad), .i_sfu(sfu), .i_mc(mc), .i_md(md),
        .i_dst(dst), .i_dbase(d_base), .i_dso(d_so), .i_dsi(d_si),
        .i_red(red), .i_redsq(redsq), .i_rbase(r_base), .i_rso(r_so), .i_imm1(imm1), .i_imm2(imm2),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q),
        .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q),
        .wrom_re(su_wrom_re), .wrom_addr(su_wrom_addr), .wrom_q(wrom_q),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .vm_we(vw_su_we), .vm_waddr(vw_su_addr), .vm_wdata(vw_su_data),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .red_we(vw_rd_we), .red_addr(vw_rd_addr), .red_data(vw_rd_data),
        .progress(su_progress), .fault(su_fault));

    // The embedding read is the only stream use of the weight ROM; a barrier
    // keeps it apart from matrix-vector reads.
    assign wrom_re = me_wrom_re | su_wrom_re;
    assign wrom_addr = su_wrom_re ? su_wrom_addr : me_wrom_addr;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else if (start && st == S_IDLE) fault <= 1'b0;
        else if (me_fault || su_fault) fault <= 1'b1;
    end
endmodule
