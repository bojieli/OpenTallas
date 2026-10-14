`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hbm-forks 2026-10-09: the HGI-1 command-processor SEQUENCER, NORMATIVE v1.0 encoding (docs/HBM_GENERIC_INTERFACE.md
// 2.2, 3.1-3.5, 4.2, 6.1-6.8; owner approval REVIEW_20261009 ~11:30 PT).  Owner Claude (hbm-forks, item 4: record
// sequencer + indexed descriptors C3b + the 18-bit token).  Contract and vectors: tools/hgi_seq_vectors.py (Ref).
//   * fetch: records come from the program image in HBM (image_base pages + entry offset in 16 B units, MD section D)
//     through one in-order 32 B-sector read port into a PREFETCH RING of RW 16 B words (RW/2 sectors: one
//     ot_sram_1r1w_256x256 macro at RW = 512; behavioural here, 1-cycle registered read);
//   * decode (v2) one 32 B item a cycle: header (16 B) + [SUT 32 B] + one MDESC (32 B) per opnd bit in A, B, C, D, O, R, I order;
//   * predicate ALWAYS / POS0 / NOT_POS0 / LAST_ITER (innermost loop); CTL.LOOP param[15:0] count, [16] level
//     (0 -> L, 1 -> L1), [17] count from U32(VM[imm_a]) after wait bits, valid 1..65535; two levels nested in either order, bodies REPLAYED from the ring (a body must fit: the record
//     ending past RW - 2 words of the outermost body start faults); CTL.FENCE = every unit drained AND every posted
//     HBM write visible (wr_quiet); CTL.END = token U32(VM[A_eff]) after END's wait mask, range-checked against 2^18 and
//     cp_vocab;
//   * effective base = base + L*lstride + L1*l1stride + X*dyn_mul (strides signed 32 b; v2: a pipelined CSA-tree
//     multiplier, one descriptor a cycle), X = DYN[dyn_sel] or U32(VM[I_eff + L]) for an INDEXED descriptor; n = n | DYN[n_sel]
//     (1..62) | U32(VM[I_eff + I.stride + L]) (63, N_FROM_VM).  Everything that needs no VM read is computed BEFORE
//     the wait; the I-table reads come AFTER the record's wait mask is met (the IDX.TOPK writer is ordered by a wait
//     bit, section 3.3), through one VM read port;
//   * DYN 0 ZERO 1 POS 2 POS1 3 TOKEN 4 L 5 RANK 6 SLOT 7 POS_SLOT 8 L1 15 POS_SLOT1; 16..40 the DS full-shape
//     selectors (tools/hdc_isa_v41.FULL_DYN_KEYS order, tools/v41_fullshape_isa.full_dyn) at the slot's position;
//   * dispatch: unit valid/ready, payload {header, SUT, 7 EFFECTIVE MDESCs (base = effective base, n = effective n
//     low 20 b)} + full-width sidebands: 7 x 21-bit effective n, POS1, POS_SLOT1, L, L1;
//   * completion status: 0 OK, 1 unit fault, 3 bad command or range (absent unit: SIMT / 12..15, op outside the unit's
//     list, CTL.TOKX/AMAX/ACCEPT, reserved DYN 9..14 / 41..63, indexed or N_FROM_VM without a proper I, I-table read
//     outside VM, HBM base outside 2^40 / VM base outside 2^18, n from VM >= 2^21, bad LOOP nesting / count 0, ENDLOOP
//     without LOOP, body over the ring, END without a VM A, END token >= 2^18 or >= cp_vocab); a doorbell with
//     token >= cp_vocab or pos >= cp_ctx_max completes at once with status 3.
// Reset = DS (cp_vocab / cp_ctx_max come from the config path's active registers).
// ---------------------------------------------------------------------------------------------------------------------
// tputx-cpf 2026-10-11 (v2, THROUGHPUT RESTRUCTURE; CP.FETCH was 7.36x its price: 234,171 vs 31,831 cycles a DS AR 1M
// token, ~60 cycles a dispatch in word-serial decode + one iterative radix-4 multiplier per descriptor term).  Same
// ports, same HGI-1 v1.0 semantics (tools/hgi_seq_vectors.Ref), decoupled pipeline:
//   FE   sector reader (one 32 B ring sector a cycle) -> 12-word shift FIFO -> parser: header 1 cycle (all header
//        checks from the FIFO head flops, registered), then one 32 B item (SUT / MDESC) a cycle = the price's
//        1 + 1-a-chunk decode; LOOP / ENDLOOP / NOP / predicate skips handled here (ENDLOOP redirects the reader);
//   AU   one descriptor a cycle, 6 stages: DYN lookup from a per-slot table (built at job start) | 60 partial-product
//        rows (base, L*lstride, L1*l1stride, X*dyn_mul) CSA 60->8 | CSA 8->2 (+ I_eff+L, I_eff+L+I.stride) |
//        17-bit chunk adds | carry select | range flags + write into the record queue;
//   RQ   QD-entry record queue (header, SUT, 7 descriptors, n, pending-index state) decouples decode from the
//        wait / indexed-read / dispatch back end;
//   BE   in-order: wait mask, indexed reads (ONE X and ONE N VM read a record: every indexed descriptor of a record
//        reads the same I_eff + L / + I.stride word), pending descriptors re-injected through the AU, dispatch
//        (3 cycles a record), FENCE / END / TOKX / LOOP-from-VM.
// Faults are carried in order as queue entries, so a fault still completes after exactly the records before it.
module ot_hgi_seq #(
    parameter integer RW   = 4096,        // ring words (16 B); a power of two
    parameter integer NOS  = 160,        // fetch sectors outstanding (<= 255).  tputx-cpf: 160 = the priced lane's bandwidth-
                                         // delay product (32 B a cycle x the 160-cycle fetch latency); was 48 (9.6 B/cyc)
    parameter integer USE_MACRO = 0,     // 1: the ring is macros: RW 512 = one ot_sram_1r1w_256x256_m2_r2c2 (8 KB); RW 4096 =
                                         //    two ot_sram_1r1w_1024x256_m2_r2c2 (64 KB: a DFlash verify body of 39.6 KB fits)
    parameter integer DS_TPL = 2,        // DS full-shape DYN: log2 TP (4)
    parameter integer DS_WIN = 128,      //   window
    parameter integer DS_SCAN = 16384,   //   scan cap
    parameter integer DS_TOPK = 512,     //   top-k
    parameter integer DS_HDL = 9,        //   log2 head dim (512)
    parameter integer QD = 4,            // record queue entries (a power of two, 2..8; 8 measured 0.747x vs 4 0.789x)
    parameter integer FD = 12,           // FE word FIFO depth (>= 8)
    parameter integer IKS_I = 0          // 1 (hbmdie-1011): operand I (slot 6) may be HBM space (IDX.INDEX IKS key region): passed
                                         //   through range-checked like any HBM operand, no indexed-read source (an indexed operand
                                         //   of such a record faults as one without I); 0: I must be VM (the legacy rule)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [159:0]  md_d,           // {image_pages, image_base, entry_draft, entry_verify, entry_ar} (cfg master)
    input  wire [17:0]   cfg_vocab,
    input  wire [20:0]   cfg_ctx_max,
    input  wire [7:0]    rank,
    input  wire          hold,           // config commit / settle: doorbells refused
    output wire          busy,           // a job runs or a unit has work outstanding (config E_BUSY)
    // doorbell {token 18, pos 20, job 32, gen 4, entry 2, ncol 4}
    input  wire          db_v,
    output wire          db_rdy,
    input  wire [17:0]   db_token,
    input  wire [19:0]   db_pos,
    input  wire [31:0]   db_job,
    input  wire [3:0]    db_gen,
    input  wire [1:0]    db_entry,
    input  wire [3:0]    db_ncol,       // verify columns: bounds the TOKX count k
    input  wire [3:0]    db_kernel,     // G23: entry 3 = KERNEL, offset = MD word 16 + db_kernel
    input  wire [31:0]   db_loff,       // G26: + L' x kstride for kernels 3 / 7 / 8 (the MTP translator; 0 otherwise)
    input  wire [11*32-1:0] md_k,       // G23: MD words 16 .. 26 (cfg master)
    // record fetch: 32 B sectors, in-order responses
    output wire          f_req_v,
    input  wire          f_req_rdy,
    output wire [39:0]   f_req_addr,
    input  wire          f_rsp_v,
    input  wire [255:0]  f_rsp_data,
    // VM read port (I tables, the END token): one outstanding, in order
    output wire          vr_v,
    input  wire          vr_rdy,
    output reg  [17:0]   vr_addr,
    input  wire          vr_rsp_v,
    input  wire [31:0]   vr_rsp_data,
    // unit dispatch (index = HGI unit code; CTL = 0 is internal)
    output wire [15:0]   u_v,
    input  wire [15:0]   u_rdy,
    output reg  [127:0]  d_hdr,
    output reg  [255:0]  d_sut,
    output reg  [1791:0] d_desc,         // {I, R, O, D, C, B, A} effective
    output reg  [146:0]  d_n,            // 7 x 21-bit effective n, A in bits 20:0
    output reg  [20:0]   d_pos1,
    output reg  [20:0]   d_pslot1,
    output reg  [15:0]   d_L,
    output reg  [15:0]   d_L1,
    input  wire [15:0]   u_done,         // retire pulses (one per dispatched record)
    input  wire [15:0]   u_fault,
    input  wire          wr_quiet,       // every posted HBM write is visible
    // completion {token, pos, job, gen, status, cycles}
    output wire          cpl_v,
    input  wire          cpl_rdy,
    output reg  [17:0]   cpl_token,
    output reg  [19:0]   cpl_pos,
    output reg  [31:0]   cpl_job,
    output reg  [3:0]    cpl_gen,
    output reg  [3:0]    cpl_status,
    output reg  [31:0]   cpl_cycles,    // = {cc_hi, cc_lo} (combinational copy of two flop halves)
    // CTL.TOKX (Q-MTP-1, hbm-forks 2026-10-09): the committed tokens of the step, up to 16, carried on the completion
    output wire          cpl_tokx       // 1: this completion beat is a CTL.TOKX committed token (status 0), END follows
);
    // ---- v2.3 hold-delay stage on every input (route 905100ec5: FF hold -17.85 ps on input -> pin-flop paths, die-context
    // IO hold budget): one kept HB4 delay cell a bit (ot_hgi_seq_hdly N=1 = rtl/lib/ot_hdly, ~38 ps at FF; dont_touch via hdly_dont_touch.tcl at
    // PRE_FLOORPLAN). A wire in simulation: function unchanged.
    wire [160-1:0] md_d_h; ot_hgi_seq_hdly #(.W(160), .N(2)) u_hdly_md_d (.a(md_d), .y(md_d_h));
    wire [18-1:0] cfg_vocab_h; ot_hgi_seq_hdly #(.W(18), .N(2)) u_hdly_cfg_vocab (.a(cfg_vocab), .y(cfg_vocab_h));
    wire [21-1:0] cfg_ctx_max_h; ot_hgi_seq_hdly #(.W(21), .N(2)) u_hdly_cfg_ctx_max (.a(cfg_ctx_max), .y(cfg_ctx_max_h));
    wire [8-1:0] rank_h; ot_hgi_seq_hdly #(.W(8), .N(2)) u_hdly_rank (.a(rank), .y(rank_h));
    wire [1-1:0] hold_h; ot_hgi_seq_hdly #(.W(1), .N(2)) u_hdly_hold (.a(hold), .y(hold_h));
    wire [1-1:0] db_v_h; ot_hgi_seq_hdly #(.W(1), .N(2)) u_hdly_db_v (.a(db_v), .y(db_v_h));
    wire [18-1:0] db_token_h; ot_hgi_seq_hdly #(.W(18), .N(2)) u_hdly_db_token (.a(db_token), .y(db_token_h));
    wire [20-1:0] db_pos_h; ot_hgi_seq_hdly #(.W(20), .N(2)) u_hdly_db_pos (.a(db_pos), .y(db_pos_h));
    wire [32-1:0] db_job_h; ot_hgi_seq_hdly #(.W(32), .N(2)) u_hdly_db_job (.a(db_job), .y(db_job_h));
    wire [4-1:0] db_gen_h; ot_hgi_seq_hdly #(.W(4), .N(2)) u_hdly_db_gen (.a(db_gen), .y(db_gen_h));
    wire [2-1:0] db_entry_h; ot_hgi_seq_hdly #(.W(2), .N(2)) u_hdly_db_entry (.a(db_entry), .y(db_entry_h));
    wire [4-1:0] db_ncol_h; ot_hgi_seq_hdly #(.W(4), .N(2)) u_hdly_db_ncol (.a(db_ncol), .y(db_ncol_h));
    wire [4-1:0] db_kernel_h; ot_hgi_seq_hdly #(.W(4), .N(2)) u_hdly_db_kernel (.a(db_kernel), .y(db_kernel_h));
    wire [32-1:0] db_loff_h; ot_hgi_seq_hdly #(.W(32), .N(2)) u_hdly_db_loff (.a(db_loff), .y(db_loff_h));
    wire [11*32-1:0] md_k_h; ot_hgi_seq_hdly #(.W(11*32), .N(2)) u_hdly_md_k (.a(md_k), .y(md_k_h));
    wire [1-1:0] f_req_rdy_h; ot_hgi_seq_hdly #(.W(1), .N(2)) u_hdly_f_req_rdy (.a(f_req_rdy), .y(f_req_rdy_h));
    wire [1-1:0] f_rsp_v_h; ot_hgi_seq_hdly #(.W(1), .N(2)) u_hdly_f_rsp_v (.a(f_rsp_v), .y(f_rsp_v_h));
    wire [256-1:0] f_rsp_data_h; ot_hgi_seq_hdly #(.W(256), .N(2)) u_hdly_f_rsp_data (.a(f_rsp_data), .y(f_rsp_data_h));
    wire [1-1:0] vr_rdy_h; ot_hgi_seq_hdly #(.W(1), .N(2)) u_hdly_vr_rdy (.a(vr_rdy), .y(vr_rdy_h));
    wire [1-1:0] vr_rsp_v_h; ot_hgi_seq_hdly #(.W(1), .N(2)) u_hdly_vr_rsp_v (.a(vr_rsp_v), .y(vr_rsp_v_h));
    wire [32-1:0] vr_rsp_data_h; ot_hgi_seq_hdly #(.W(32), .N(2)) u_hdly_vr_rsp_data (.a(vr_rsp_data), .y(vr_rsp_data_h));
    wire [16-1:0] u_rdy_h; ot_hgi_seq_hdly #(.W(16), .N(2)) u_hdly_u_rdy (.a(u_rdy), .y(u_rdy_h));
    wire [16-1:0] u_done_h; ot_hgi_seq_hdly #(.W(16), .N(2)) u_hdly_u_done (.a(u_done), .y(u_done_h));
    wire [16-1:0] u_fault_h; ot_hgi_seq_hdly #(.W(16), .N(2)) u_hdly_u_fault (.a(u_fault), .y(u_fault_h));
    wire [1-1:0] wr_quiet_h; ot_hgi_seq_hdly #(.W(1), .N(2)) u_hdly_wr_quiet (.a(wr_quiet), .y(wr_quiet_h));
    wire [1-1:0] cpl_rdy_h; ot_hgi_seq_hdly #(.W(1), .N(2)) u_hdly_cpl_rdy (.a(cpl_rdy), .y(cpl_rdy_h));
    // ---- registered boundary (submit rule X4): every data / status input lands in a pin flop
    reg [159:0] md_d_r; reg [11*32-1:0] md_k_r; reg [17:0] cfg_vocab_r; reg [20:0] cfg_ctx_max_r; reg [7:0] rank_r; reg hold_r;
    reg vr_rsp_v_r; reg [31:0] vr_rsp_data_r; reg [15:0] u_done_r, u_fault_r; reg wr_quiet_r; reg f_rsp_v_r; reg [255:0] f_rsp_data_r;
    // reset: asynchronous assert, synchronous release through two flops; every other control register resets on rn
    (* keep = 1 *) reg [1:0] rs_q, rs_f, rs_m, rs_u;   // one release synchronizer per region (reset fanout <= ~256 a copy)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rs_q <= 2'b00; rs_f <= 2'b00; rs_m <= 2'b00; rs_u <= 2'b00; end
        else begin rs_q <= {rs_q[0], 1'b1}; rs_f <= {rs_f[0], 1'b1}; rs_m <= {rs_m[0], 1'b1}; rs_u <= {rs_u[0], 1'b1}; end
    wire rn = rs_q[1];                   // boundary / small control
    wire rn_f = rs_f[1];                 // FE
    wire rn_m = rs_m[1];                 // BE / job FSM
    wire rn_u = rs_u[1];                 // per-unit outstanding counters
    always @(posedge clk or negedge rn)
        if (!rn) begin hold_r <= 1'b1; vr_rsp_v_r <= 1'b0; u_done_r <= 16'd0; u_fault_r <= 16'd0; wr_quiet_r <= 1'b0; f_rsp_v_r <= 1'b0; end
        else begin hold_r <= hold_h; vr_rsp_v_r <= vr_rsp_v_h; u_done_r <= u_done_h; u_fault_r <= u_fault_h; wr_quiet_r <= wr_quiet_h; f_rsp_v_r <= f_rsp_v_h; end
    always @(posedge clk) begin
        md_d_r <= md_d_h; md_k_r <= md_k_h; cfg_vocab_r <= cfg_vocab_h; cfg_ctx_max_r <= cfg_ctx_max_h; rank_r <= rank_h; vr_rsp_data_r <= vr_rsp_data_h; f_rsp_data_r <= f_rsp_data_h;
    end
    localparam integer RB = $clog2(RW);
    localparam integer RS = RW / 2;                       // sectors
    localparam integer QB = (QD <= 2) ? 1 : $clog2(QD);
    // ------------------------------------------------------------------ field positions (spec.json, v1.0)
    localparam integer H_UNIT = 124, H_OP = 118, H_WAIT = 102, H_PRED = 100, H_OPND = 93, H_TMPL = 92, H_SLOT = 89,
                       H_PARAM = 64;
    localparam integer M_SPACE = 0, M_IBC = 5, M_IDX = 6, M_BASE = 8, M_N = 48, M_M = 68, M_STRIDE = 88,
                       M_LSTR = 136, M_DSEL = 168, M_DMUL = 174, M_NSEL = 201, M_L1STR = 207;
    // ------------------------------------------------------------------ main (back-end) states
    localparam [4:0] S_IDLE = 5'd0, S_DB = 5'd1, S_DB2 = 5'd2, S_DB3 = 5'd3, S_HD = 5'd4,
                     S_DSP = 5'd8, S_FEN = 5'd9, S_LVW = 5'd10, S_LVR = 5'd11, S_ENDRD = 5'd12,
                     S_TOKX = 5'd13, S_TKB = 5'd14, S_CPL = 5'd15;
    // record queue entry kinds
    localparam [2:0] K_DISP = 3'd0, K_END = 3'd1, K_TOKX = 3'd2, K_FENCE = 3'd3, K_LVM = 3'd4, K_FLT = 3'd5;
    reg [4:0]  st;
    reg        run_q;                    // a job runs (FE / AU / queue active): set at the job start, cleared on S_CPL
    (* keep = 1 *) reg run_f;         // v2.3: the FE's own copy of run_q (run_q drove ~hundreds of loads: run_q -> pi -27 ps)
    reg [17:0] token; reg [19:0] pos; reg [1:0] db_entry_q; reg [20:0] pos1_q;
    // ------------------------------------------------------------------ ring + fetch (word pointers, RB+1 bits)
    reg [RB:0]  wp, frp;                 // write (sector aligned), free (outermost loop body start or the parse pointer)
    reg [39:0]  faddr, faddr_n, faddr_nn, img_q;   // faddr_n = faddr + 32 kept registered (the push selects; no 40-bit add)
    reg [7:0]   inflight, drop;
    reg         fetching;
    wire [RB:0] frp_al = {frp[RB:1], 1'b0};
    wire [RB+1:0] used = {1'b0, wp - frp_al} + {{(RB-7){1'b0}}, inflight, 1'b0};
    reg         wv;                      // a sector has landed since the doorbell
    reg [RB:0]  rd_ptr;                  // the ring read address (registered); the sector lands three edges later
    // the ring (unchanged from v1): macro-side flops on both ports; a sector read issued on edge E is valid in the
    // cycle after E + 2 (rd_sec); a write lands one edge after wp advances and every read of that sector samples its
    // address at least one edge after wp advanced (the reader issues on wp - rdp != 0 from flops)
    reg [255:0] rd_sec;
    wire        ring_we = f_rsp_v_r && (drop == 8'd0);
    generate if (USE_MACRO) begin : g_ring_m
        initial if (RW != 512 && RW != 4096) $fatal(1, "ot_hgi_seq: USE_MACRO needs RW 512 or 4096");
        if (RW == 512) begin : g_8k
            wire [255:0] q; reg [255:0] q_r, wd_q; reg we_q; reg [7:0] wa_q;
            always @(posedge clk) begin q_r <= q; we_q <= ring_we; wa_q <= wp[8:1]; if (ring_we) wd_q <= f_rsp_data_r; end
            ot_sram_1r1w_256x256_m2_r2c2 u_ring (.clk(clk), .r_ce_in(1'b1), .r_addr_in(rd_ptr[8:1]), .rd_out(q),
                .w_ce_in(we_q), .w_addr_in(wa_q), .wd_in(wd_q), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            always @* rd_sec = q_r;
        end else begin : g_64k                                  // bank = word pointer bit 11 (sector bit 10)
            wire [255:0] q0, q1; reg rb_q, rb_qq; reg [255:0] q0_r, q1_r, wd0_q, wd1_q; reg we0_q, we1_q; reg [9:0] wa0_q, wa1_q;
            wire [255:0] wd0_d, wd1_d;     // v2.3: hold-delay stage flop -> macro write data (FF hold -4.2 ps)
            ot_hgi_seq_hdly #(.W(256), .N(2)) u_hdly_wd0 (.a(wd0_q), .y(wd0_d));
            ot_hgi_seq_hdly #(.W(256), .N(2)) u_hdly_wd1 (.a(wd1_q), .y(wd1_d));
            // v2.4 (route 8447139d1 FF hold: wd1_q -> u_ring1/wd_in -15.5, we1_q -> w_ce_in -7.6): two kept HB4 stages on
            // the macro write data / enables (flop -> macro hold, the macro's clock pin sits late in the tree)
            wire we0_d, we1_d;
            ot_hgi_seq_hdly #(.W(1), .N(2)) u_hdly_we0 (.a(we0_q), .y(we0_d));
            ot_hgi_seq_hdly #(.W(1), .N(2)) u_hdly_we1 (.a(we1_q), .y(we1_d));
            always @(posedge clk) begin
                rb_q <= rd_ptr[11]; rb_qq <= rb_q;
                if (!rb_q) q0_r <= q0;                          // the bank read on the previous edge
                if (rb_q)  q1_r <= q1;
                we0_q <= ring_we && !wp[11]; wa0_q <= wp[10:1]; if (ring_we && !wp[11]) wd0_q <= f_rsp_data_r;
                we1_q <= ring_we &&  wp[11]; wa1_q <= wp[10:1]; if (ring_we &&  wp[11]) wd1_q <= f_rsp_data_r;
            end
            ot_sram_1r1w_1024x256_m2_r2c2 u_ring0 (.clk(clk), .r_ce_in(!rd_ptr[11]), .r_addr_in(rd_ptr[10:1]), .rd_out(q0),
                .w_ce_in(we0_d), .w_addr_in(wa0_q), .wd_in(wd0_d), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
            ot_sram_1r1w_1024x256_m2_r2c2 u_ring1 (.clk(clk), .r_ce_in(rd_ptr[11]), .r_addr_in(rd_ptr[10:1]), .rd_out(q1),
                .w_ce_in(we1_d), .w_addr_in(wa1_q), .wd_in(wd1_d), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
            always @* rd_sec = rb_qq ? q1_r : q0_r;
        end
    end else begin : g_ring_r
        reg [255:0] ring [0:RS-1]; reg [255:0] rd_sec0;
        always @(posedge clk) begin
            rd_sec0 <= ring[rd_ptr[RB-1:1]]; rd_sec <= rd_sec0;     // the same 3-edge read latency as the macro ring
            if (ring_we) ring[wp[RB-1:1]] <= f_rsp_data_r;
        end
    end endgenerate
    // ------------------------------------------------------------------ fetch request FIFO (unchanged, NOS wide)
    reg [39:0] rqf [0:1]; reg rqh; reg [1:0] rqn;
    wire [1:0] rqn_m1 = rqn - 2'd1, rqn_p1 = rqn + 2'd1;
    assign f_req_v = (rqn != 2'd0);
    assign f_req_addr = rqf[rqh];
    wire [7:0] infl_p1 = inflight + 8'd1, infl_m1 = inflight - 8'd1;
    reg room_q;
    wire       rq_push = fetching && (rqn != 2'd2) && (inflight < NOS) && room_q;
    always @(posedge clk or negedge rn) if (!rn) room_q <= 1'b0; else room_q <= (used + (rq_push ? 2 : 0) + 2 <= RW);
    wire       rq_pop = f_req_v && f_req_rdy_h;
    always @(posedge clk or negedge rn)
        if (!rn) begin rqh <= 1'b0; rqn <= 2'd0; end
        else begin
            if (rq_push) rqf[rqh ^ (rqn != 2'd0)] <= faddr;
            if (rq_pop) rqh <= ~rqh;
            rqn <= rq_pop ? (rq_push ? rqn : rqn_m1) : (rq_push ? rqn_p1 : rqn);
        end
    wire [7:0] fl_after = (rq_push && !f_rsp_v_r) ? infl_p1 : (!rq_push && f_rsp_v_r) ? infl_m1 : inflight;
    // ------------------------------------------------------------------ helpers
    function automatic [3:0] nops(input [3:0] u);
        // = hbm_generic_iface D_OPS (hgi-1010: HC 3 ops since G22 HC_MIX_ROWS / HC_MIX_POST; IDX MERGE / OWNED live)
        case (u) 4'd0: nops = 4'd8; 4'd4: nops = 4'd7; 4'd5: nops = 4'd2; 4'd6: nops = 4'd6; 4'd8: nops = 4'd4;
                 4'd9: nops = 4'd5; 4'd10: nops = 4'd3; 4'd1, 4'd2, 4'd3, 4'd7: nops = 4'd1; default: nops = 4'd0; endcase
    endfunction
    function automatic [2:0] mth(input [6:0] o, input [2:0] m);     // slot of the m-th present descriptor
        integer q; reg [2:0] c; begin mth = 3'd7; c = 0;
            for (q = 0; q < 7; q = q + 1) if (o[q]) begin if (c == m && mth == 3'd7) mth = q[2:0]; c = c + 3'd1; end
        end
    endfunction
    function automatic [63:0] sx32(input [31:0] v); sx32 = {{32{v[31]}}, v}; endfunction
    function automatic [63:0] s3(input [63:0] a, input [63:0] b, input [63:0] c); s3 = a ^ b ^ c; endfunction
    function automatic [63:0] c3(input [63:0] a, input [63:0] b, input [63:0] c);
        c3 = {((a[62:0] & b[62:0]) | (a[62:0] & c[62:0]) | (b[62:0] & c[62:0])), 1'b0};
    endfunction
    // range check of an effective base by space (HBM 2^40 bytes, VM 2^18 words; STREAM / NONE unchecked).  ap = 1
    // (descriptor operands): VM words [2^18, 2^18 + 2^16) are the HC weight aperture.  The CP's own VM reads stay below 2^18.
    function automatic base_bad(input [1:0] sp, input [63:0] a, input ap);
        base_bad = (sp == 2'd0) ? (a[63:40] != 24'd0) :
                   (sp == 2'd1) ? ((a[63:19] != 45'd0) || (a[18] && (!ap || a[17:16] != 2'd0))) : 1'b0;
    endfunction
    function automatic dyn_rsv(input [5:0] c);           // codes with no value on r25
        dyn_rsv = (c >= 6'd9 && c <= 6'd14) || (c >= 6'd41);
    endfunction
    // ------------------------------------------------------------------ outstanding per unit
    reg [7:0] outst [0:15];
    reg [15:0] busy_u;
    integer u;
    always @* for (u = 0; u < 16; u = u + 1) busy_u[u] = (outst[u] != 8'd0);
    function automatic waitok(input [15:0] w, input [15:0] b);
`ifdef OT_HGI_SEQ_MUT_WAIT
        waitok = 1'b1;                                     // NEGATIVE CONTROL: the drain mask ignored
`else
        waitok = ((w & 16'hFFFE) & b) == 16'd0;
`endif
    endfunction
    reg busy_q;
    always @(posedge clk or negedge rn) if (!rn) busy_q <= 1'b0; else busy_q <= (st != S_IDLE) || (busy_u != 16'd0);
    assign busy = busy_q;
    // ------------------------------------------------------------------ DYN: per-slot table, built at job start
    // The DS full-shape selectors depend on (pos, slot, rank) only: pos and rank are fixed for a job, so the 7-stage
    // registered bank (v1's, unchanged arithmetic) is run once per slot at the job start (8 cycles a slot, 64 in all,
    // hidden under the first record fetch) and captured into trow[slot] = {DS 40 .. 16, p1, ps} (27 x 32 b).
    function automatic [20:0] mn(input [20:0] a, input [20:0] b); mn = (a < b) ? a : b; endfunction
    function automatic [20:0] cdv(input [20:0] a, input integer sh);       // ceil(a / 2^sh)
        cdv = (a + ((21'd1 << sh) - 21'd1)) >> sh;
    endfunction
    reg [6:0]  tbc;                      // table build counter: slot tbc[5:3], capture at tbc[2:0] == 7; done at 64
    wire       tbl_ok = tbc[6];
    wire [2:0] h_slot = tbc[5:3];
    reg [20:0] ps, p1, q_p1, q_n2, q_ns1, q_ns2, q_win, q_sc1, q_sc2, q_scr, q_ps;
    wire [19:0] pos_d; ot_hgi_seq_hdly #(.W(20), .N(2)) u_hdly_pos (.a(pos), .y(pos_d));   // v2.3: FF hold -8.6 ps pos -> p1
    reg [20:0] q_sc1b, q_psb;
    reg [31:0] dsq [16:40];
    wire [28:0] rp0 = rank_r[0] ? {8'd0, q_sc1}       : 29'd0, rp1 = rank_r[1] ? {7'd0, q_sc1, 1'b0} : 29'd0,
                rp2 = rank_r[2] ? {6'd0, q_sc1, 2'b0} : 29'd0, rp3 = rank_r[3] ? {5'd0, q_sc1, 3'b0} : 29'd0,
                rp4 = rank_r[4] ? {4'd0, q_sc1, 4'b0} : 29'd0, rp5 = rank_r[5] ? {3'd0, q_sc1, 5'b0} : 29'd0,
                rp6 = rank_r[6] ? {2'd0, q_sc1, 6'b0} : 29'd0, rp7 = rank_r[7] ? {1'd0, q_sc1, 7'b0} : 29'd0;
    function automatic [57:0] fa3(input [28:0] a, input [28:0] b, input [28:0] c);   // {carry << 1, sum}
        fa3 = {((a & b) | (a & c) | (b & c)) << 1, a ^ b ^ c};
    endfunction
    wire [57:0] ra = fa3(rp0, rp1, rp2), rb = fa3(rp3, rp4, rp5);
    wire [57:0] rc = fa3(ra[28:0], ra[57:29], rb[28:0]), rd = fa3(rb[57:29], rp6, rp7);
    wire [57:0] re = fa3(rc[28:0], rc[57:29], rd[28:0]);
    wire [57:0] rf = fa3(re[28:0], re[57:29], rd[57:29]);
    reg [28:0] rs_s, rs_c; reg [15:0] rs_l; reg [13:0] rs_hs, rs_hc; reg [28:0] q_rsc_r;
    reg [20:0] q_psc, q_psd, q_sc1c, q_sc1d, q_sc1e; reg [20:0] r_diff; reg r_ge;
    always @(posedge clk) begin
        ps <= {1'b0, pos} + {18'd0, h_slot};                                   // stage 1
        p1 <= {1'b0, pos_d} + {18'd0, h_slot} + 21'd1;
        q_ps <= ps; q_p1 <= p1; q_n2 <= {1'b0, p1[20:1]};                       // stage 2
        q_ns1 <= mn(p1, DS_TOPK); q_ns2 <= mn({1'b0, p1[20:1]}, DS_TOPK); q_win <= mn(p1, DS_WIN);
        q_sc1 <= cdv(p1, DS_TPL); q_sc2 <= cdv({1'b0, p1[20:1]}, DS_TPL); q_scr <= cdv(mn(p1, DS_SCAN), DS_TPL);
        rs_s <= rf[28:0]; rs_c <= rf[57:29];                                     // stage 3 (carry-save rank x sc1)
        q_sc1b <= q_sc1; q_psb <= q_ps;
        dsq[16] <= q_win;            dsq[17] <= q_p1;             dsq[18] <= q_n2;             dsq[19] <= q_ns1;
        dsq[20] <= q_ns2;            dsq[21] <= q_win;            dsq[22] <= q_win + q_ns1;    dsq[23] <= q_win + q_ns2;
        dsq[24] <= q_sc1;            dsq[25] <= q_sc2;            dsq[26] <= q_scr;            dsq[27] <= mn(q_sc1, DS_TOPK);
        dsq[28] <= mn(q_sc2, DS_TOPK); dsq[29] <= mn(q_scr, DS_TOPK);
        dsq[30] <= cdv(q_sc1, 4);    dsq[31] <= cdv(q_sc1, 3);    dsq[32] <= cdv(q_sc2, 4);    dsq[33] <= cdv(q_scr, 4);
        dsq[34] <= cdv(q_win, 5);    dsq[35] <= cdv(dsq[22], 5);  dsq[36] <= cdv(dsq[23], 5);
        dsq[37] <= q_win - 21'd1;    dsq[38] <= {11'd0, q_win} << DS_HDL; dsq[39] <= {11'd0, q_win - 21'd1} << DS_HDL;
        rs_l <= {1'b0, rs_s[14:0]} + {1'b0, rs_c[14:0]}; rs_hs <= rs_s[28:15]; rs_hc <= rs_c[28:15];
        q_psc <= q_psb; q_sc1c <= q_sc1b;
        q_rsc_r <= {rs_hs + rs_hc + {13'd0, rs_l[15]}, rs_l[14:0]};
        q_psd <= q_psc; q_sc1d <= q_sc1c;
        r_ge <= (q_rsc_r[28:21] == 8'd0) && (q_psd >= q_rsc_r[20:0]); r_diff <= q_psd - q_rsc_r[20:0];
        q_sc1e <= q_sc1d;
        dsq[40] <= (r_ge && (r_diff < q_sc1e)) ? {11'd0, r_diff >> 3} : {11'd0, cdv(q_sc1e, 3)};      // stage 7
    end
    localparam integer TRW = 27 * 32;
    reg [8*TRW-1:0] trow;                // slot t at [t*TRW +: TRW]: field 0 ps, 1 p1, 2 + (c - 16) DS code c
    integer ti;
    always @(posedge clk) if (!tbc[6] && tbc[2:0] == 3'd7)
        for (ti = 0; ti < 8; ti = ti + 1) if (h_slot == ti[2:0])
            trow[ti*TRW +: TRW] <= {dsq[40], dsq[39], dsq[38], dsq[37], dsq[36], dsq[35], dsq[34], dsq[33], dsq[32],
                                    dsq[31], dsq[30], dsq[29], dsq[28], dsq[27], dsq[26], dsq[25], dsq[24], dsq[23],
                                    dsq[22], dsq[21], dsq[20], dsq[19], dsq[18], dsq[17], dsq[16], {11'd0, p1}, {11'd0, ps}};
    // (every module value a function reads is an argument: simulators re-evaluate a continuous assign on its arguments)
    function automatic [TRW-1:0] trow_of(input [8*TRW-1:0] tv, input [2:0] s);
        integer q; begin trow_of = {TRW{1'b0}}; for (q = 0; q < 8; q = q + 1) if (s == q[2:0]) trow_of = tv[q*TRW +: TRW]; end
    endfunction
    // ================================================================== FE: ring reader, word FIFO, record parser
    localparam [2:0] F_H = 3'd0, F_P = 3'd1, F_LVW = 3'd2, F_HALT = 3'd3;
    localparam [1:0] RC_DSP = 2'd0, RC_DISC = 2'd1, RC_FLT = 2'd2;
    reg [2:0]  fs;
    reg [RB:0] rp, rdp;                  // record header pointer / next ring word to read
    reg        ep;                       // FIFO epoch (a redirect drops older reads)
    reg [2:0]  rv, rodd, rep;            // read pipe: valid, started at an odd word, epoch
    reg [FD*128-1:0] fqv;                // shift FIFO: word 0 is the head
    reg [4:0]  fq_n, fcred;              // words held / free credits (FD - held - in the read pipe)
    reg [FD+1:0] fq_th;                  // v2.3: thermometer copy of fq_n (fq_th[j] = j < fq_n), registered
    // the current record (registered at the header cycle)
    reg [127:0] h;
    reg [1:0]  rcl; reg rskip;
    reg [4:0]  hq_rlen; reg [RB:0] hq_rpn; reg [3:0] hq_nit; reg [2:0] hq_np; reg [20:0] hq_sl;
    reg [QB-1:0] ctag;                  // its queue entry
    reg [3:0]  pi;                       // items popped
    reg [1:0]  settle;                   // loop state changed: the registered loop flags settle before the next header
    // loops
    reg [1:0]  depth;
    reg        lv_lvl [0:1]; reg [15:0] lv_cnt [0:1]; reg [RB:0] lv_body [0:1];
    reg [15:0] Lc, L1c;
    wire       in_lvl = (depth == 2'd2) ? lv_lvl[1] : lv_lvl[0];
    wire [15:0] in_cnt = (depth == 2'd2) ? lv_cnt[1] : lv_cnt[0];
    wire [15:0] in_ctr = in_lvl ? L1c : Lc;
    reg [15:0] in_ctr_q, in_cnt_q; reg in_dep_q;
    always @(posedge clk) begin in_ctr_q <= in_ctr; in_cnt_q <= in_cnt; in_dep_q <= (depth != 2'd0); end
    reg        last_iter;
    always @(posedge clk) last_iter <= in_dep_q && (in_ctr_q + 16'd1 == in_cnt_q);
    wire [1:0] top = depth - 2'd1;
    wire       top_lvl = lv_lvl[top[0]];
    wire [15:0] top_ctr = top_lvl ? L1c : Lc;
    reg [15:0] top_ctr_q, top_cnt_q;
    always @(posedge clk) begin top_ctr_q <= top_ctr; top_cnt_q <= lv_cnt[top[0]]; end
`ifdef OT_HGI_SEQ_MUT_LOOP
    wire more_c = top_ctr_q + 16'd2 < top_cnt_q;          // NEGATIVE CONTROL: one iteration short
`else
    wire more_c = top_ctr_q + 16'd1 < top_cnt_q;
`endif
    reg more;
    always @(posedge clk) more <= more_c;
    // ---- header evaluation from the FIFO head (flops): every decision flag is registered at the header pop
    // v2.4 LAZY-SHIFT FIFO (route 8447139d1: run_q -> be_inj -> pc -> 1.5k fqv data flops TT -48.25, 22-24 levels; pc
    // fanned out to ~4.6k mux selects): the storage fqv lags the view by the PREVIOUS cycle's pop count pq (registered,
    // one keep'd copy per entry / reader group).  View word i = fqv[i + pq].  Storage update: keep view words below
    // fq_n (registered thermometer), pushes at fq_n / fq_n + 1 -- this cycle's pop decision pc reaches only pq, fq_n /
    // fq_th and the FE counters, never the FIFO data.  Readers add one 3:1 select from flops.
    wire [127:0] fv0, fv1;               // view words 0 and 1
    wire [127:0] hw = fv0;
    wire [3:0]  hw_unit = hw[H_UNIT +: 4];
    wire [5:0]  hw_op   = hw[H_OP +: 6];
    wire [1:0]  hw_pred = hw[H_PRED +: 2];
    wire [6:0]  hw_opnd = hw[H_OPND +: 7];
    wire        hw_tmpl = hw[H_TMPL];
    wire [24:0] hw_param = hw[H_PARAM +: 25];
    wire [2:0]  hw_np = hw_opnd[0] + hw_opnd[1] + hw_opnd[2] + hw_opnd[3] + hw_opnd[4] + hw_opnd[5] + hw_opnd[6];
    wire [4:0]  hw_rlen = 5'd1 + {3'd0, hw_tmpl, 1'b0} + {1'b0, hw_np, 1'b0};
    // body-over-the-ring check against a REGISTERED limit (RW - 2 - (rp - frp)): no subtract in the header cycle
    reg  [4:0]  lim5; reg lim_big;
    wire        hw_recbad = (depth != 2'd0) && !lim_big && (hw_rlen > lim5);
    wire        hw_bad = (hw_unit >= 4'd11) || (hw_op >= {2'd0, nops(hw_unit)});
    reg         hw_pok;
    always @* case (hw_pred) 2'd0: hw_pok = 1'b1; 2'd1: hw_pok = (pos == 20'd0); 2'd2: hw_pok = (pos != 20'd0);
                             default: hw_pok = last_iter; endcase
    wire        hw_isctl = (hw_unit == 4'd0);
    wire        hw_ctl = hw_isctl && hw_op != 6'd3 && hw_op != 6'd5;
    wire        hw_noa = hw_isctl && !hw_opnd[0];
    wire        hw_loopbad = (!hw_param[17] && hw_param[15:0] == 16'd0) || (hw_param[17] && hw[63:50] != 14'd0) ||
                             depth == 2'd2 || (depth == 2'd1 && lv_lvl[0] == hw_param[16]);
    // record class: the v1 evaluation order (body over the ring, bad unit / op, predicate, CTL, END / TOKX without A)
    wire [1:0]  hw_rc = (hw_recbad || hw_bad) ? RC_FLT : !hw_pok ? RC_DISC :
                        hw_ctl ? ((hw_op == 6'd0 || hw_op == 6'd4) ? RC_DISC :
                                  (hw_op == 6'd1) ? (hw_loopbad ? RC_FLT : RC_DISC) :
                                  (hw_op == 6'd2) ? ((depth == 2'd0) ? RC_FLT : RC_DISC) : RC_FLT) :
                        hw_noa ? RC_FLT : RC_DSP;
    // ---- record queue occupancy (FE allocates, BE frees)
    reg [QB:0] q_cnt; reg [QB-1:0] qh, qt;
    // ---- FE control (combinational from flops)
    wire        job_start;               // S_DB3 with a good doorbell (main FSM)
    wire        be_inj;                  // the indexed resolver owns the AU input this cycle
    wire        fe_hcap  = run_f && fs == F_H && fq_th[0] && settle == 2'd0 && tbl_ok && q_cnt < QD;
    wire        fe_halloc = fe_hcap && hw_rc != RC_DISC;               // dispatch / END / TOKX / header fault entry
    // v2.3 (route 905100ec5 limiter hw -> e_hdr, TT -187): the header's queue entry is written the cycle AFTER the
    // header pop from registered state (h, hq_kind, hq_rdy0) under a per-entry registered enable (ha_e) -- the
    // header decode ends in a few flops instead of fanning out to every entry's ~200 data flops.
    reg         ha_v; reg [QD-1:0] ha_e; reg [2:0] hq_kind; reg hq_rdy0;
    wire        fe_inp   = run_f && fs == F_P && rcl != RC_FLT;
    wire        fe_pop2  = fe_inp && (pi != hq_nit) && fq_th[1] && !(rcl == RC_DSP && be_inj);
    wire        fe_sut   = fe_pop2 && rcl == RC_DSP && h[H_TMPL] && pi == 4'd0;
    wire        fe_item  = fe_pop2 && rcl == RC_DSP && !(h[H_TMPL] && pi == 4'd0);
    wire        fe_done  = fe_inp && (hq_nit == 4'd0 || (fe_pop2 && pi + 4'd1 == hq_nit));
    wire [5:0]  h_op = h[H_OP +: 6];
    wire        h_lvm = h[H_PARAM + 17];
    wire        fe_aalloc = fe_done && rcl == RC_DISC && !rskip && (h_op == 6'd4 || (h_op == 6'd1 && h_lvm));   // FENCE / LOOP-from-VM
    wire        fe_redir = fe_done && rcl == RC_DISC && !rskip && h_op == 6'd2 && more;
    wire        fe_flush = job_start || fe_redir;
    wire [1:0]  pc = fe_hcap ? 2'd1 : fe_pop2 ? 2'd2 : 2'd0;
    wire        q_alloc = ha_v || fe_aalloc;
    reg  [2:0]  q_akind;                 // the header's entry kind (registered into hq_kind at the pop)
    always @* begin
        if (hw_rc == RC_FLT) q_akind = K_FLT;
        else if (hw_isctl && hw_op == 6'd3) q_akind = K_END;
        else if (hw_isctl && hw_op == 6'd5) q_akind = K_TOKX;
        else q_akind = K_DISP;
    end
    wire [2:0]  fe_sl = hq_sl[(pi - {3'd0, h[H_TMPL]}) * 3 +: 3];      // the item's descriptor slot
    wire [255:0] fe_it = {fv1, fv0};                                    // the item (two words)
    // ---- reader: one sector a cycle while the ring has it and the FIFO has room
    wire [RB:0] ravail = wv ? (wp - rdp) : {(RB+1){1'b0}};
    wire        rd_iss = run_f && !fe_flush && (ravail != {(RB+1){1'b0}}) && fcred >= 5'd2;
    wire        push_ok = rv[2] && (rep[2] == ep) && !fe_flush;
    wire [1:0]  sc = !push_ok ? 2'd0 : rodd[2] ? 2'd1 : 2'd2;
    wire [127:0] pw0 = rodd[2] ? rd_sec[255:128] : rd_sec[127:0];
    wire [127:0] pw1 = rd_sec[255:128];
    // ---- loop-from-VM reply (BE)
    reg         lv_rsp; reg [15:0] lv_rcnt;
    // ---- FIFO data (no reset), v2.4 lazy shift: storage entry i takes storage word i + pq when i < fq_n (view kept),
    // pushed word 0 at i == fq_n, pushed word 1 at i == fq_n + 1.  Writes in a flush cycle are harmless (fq_th clears),
    // so the data path carries the raw push (no fe_flush cone).
    wire [FD+4:0] feq = {3'b000, fq_th[FD:0] & ~fq_th[FD+1:1], !fq_th[0]};    // feq[m] = (m == fq_n)
    wire        push_raw = rv[2] && (rep[2] == ep);
    wire [1:0]  scr = !push_raw ? 2'd0 : rodd[2] ? 2'd1 : 2'd2;
    wire [1:0]  pq_n = fe_flush ? 2'd0 : pc;
    genvar gi;
    generate for (gi = 0; gi < FD; gi = gi + 1) begin : g_fq
        (* keep = 1 *) reg [1:0] pq;      // this entry's copy of the previous pop count (one-hot-ish: 0 / 1 / 2)
        always @(posedge clk or negedge rn_f) if (!rn_f) pq <= 2'd0; else pq <= pq_n;
        wire [127:0] s0 = fqv[gi*128 +: 128];
        wire [127:0] s1 = (gi + 1 < FD) ? fqv[((gi + 1) % FD)*128 +: 128] : 128'd0;
        wire [127:0] s2 = (gi + 2 < FD) ? fqv[((gi + 2) % FD)*128 +: 128] : 128'd0;
        wire [127:0] cur = pq[1] ? s2 : pq[0] ? s1 : s0;
        wire keep = fq_th[gi];
        wire e0 = feq[gi];
        wire e1 = (gi >= 1) ? feq[(gi >= 1) ? gi - 1 : 0] : 1'b0;
        always @(posedge clk)
            if (keep) fqv[gi*128 +: 128] <= cur;
            else if (e0 && scr != 2'd0) fqv[gi*128 +: 128] <= pw0;
            else if (e1 && scr == 2'd2) fqv[gi*128 +: 128] <= pw1;
    end endgenerate
    // view readers: 4 x 32-bit groups (view words 0 and 1), each with its own pq copy
    generate for (gi = 0; gi < 4; gi = gi + 1) begin : g_fr
        (* keep = 1 *) reg [1:0] pr;
        always @(posedge clk or negedge rn_f) if (!rn_f) pr <= 2'd0; else pr <= pq_n;
        assign fv0[gi*32 +: 32] = pr[1] ? fqv[256 + gi*32 +: 32] : pr[0] ? fqv[128 + gi*32 +: 32] : fqv[gi*32 +: 32];
        assign fv1[gi*32 +: 32] = pr[1] ? fqv[384 + gi*32 +: 32] : pr[0] ? fqv[256 + gi*32 +: 32] : fqv[128 + gi*32 +: 32];
    end endgenerate
    // v2.4: the thermometer moves by d = sc - pc (-2..+2): five shifted copies from flops, selected by d
    wire [FD+1:0] th_m2 = {2'b00, fq_th[FD+1:2]}, th_m1 = {1'b0, fq_th[FD+1:1]}, th_p1 = {fq_th[FD:0], 1'b1},
                  th_p2 = {fq_th[FD-1:0], 2'b11};
    wire [FD+1:0] th_n = (pc == 2'd2) ? ((sc == 2'd2) ? fq_th : (sc == 2'd1) ? th_m1 : th_m2) :
                         (pc == 2'd1) ? ((sc == 2'd2) ? th_p1 : (sc == 2'd1) ? fq_th : th_m1) :
                                        ((sc == 2'd2) ? th_p2 : (sc == 2'd1) ? th_p1 : fq_th);
    always @(posedge clk or negedge rn_f)
        if (!rn_f) fq_th <= {(FD+2){1'b0}};
        else if (fe_flush) fq_th <= {(FD+2){1'b0}};
        else fq_th <= th_n;
    // ---- ring-limit register: rpd = rp - frp after this cycle's update, lim = RW - 2 - rpd
    reg  [RB:0] rpd;
    wire        fe_adv = run_f && !job_start && fs == F_P && fe_done &&
                         (rcl == RC_DSP || rskip || h_op == 6'd0 || h_op == 6'd4);      // rp <= hq_rpn, no settle
    wire [RB:0] rpd_n = job_start ? {(RB+1){1'b0}} : (settle != 2'd0) ? (rp - frp) :
                        fe_adv ? ((depth == 2'd0) ? {(RB+1){1'b0}} : rpd + {{(RB-4){1'b0}}, hq_rlen}) : rpd;
    wire [RB:0] lim_n = RW - 2 - rpd_n;
    always @(posedge clk) begin rpd <= rpd_n; lim5 <= lim_n[4:0]; lim_big <= |lim_n[RB:5]; end
    integer fk2;
    always @(posedge clk or negedge rn_f)
        if (!rn_f) begin ha_v <= 1'b0; ha_e <= {QD{1'b0}}; end
        else begin
            ha_v <= !job_start && fe_halloc;
            for (fk2 = 0; fk2 < QD; fk2 = fk2 + 1) ha_e[fk2] <= !job_start && fe_halloc && qt == fk2;
        end
    // ---- FE sequential
    integer fk;
    always @(posedge clk or negedge rn_f) begin
        if (!rn_f) begin
            fs <= F_HALT; rp <= 0; rdp <= 0; frp <= 0; ep <= 1'b0; rv <= 3'b000; rodd <= 3'b000; rep <= 3'b000;
            fq_n <= 5'd0; fcred <= FD; depth <= 2'd0; Lc <= 16'd0; L1c <= 16'd0; settle <= 2'd0; pi <= 4'd0;
            rd_ptr <= 0; rcl <= RC_DISC; rskip <= 1'b0;
        end else begin
            // reader pipe
            rv <= {rv[1:0], rd_iss}; rodd <= {rodd[1:0], rdp[0]}; rep <= {rep[1:0], ep};
            if (rd_iss) begin rd_ptr <= rdp; rdp <= {rdp[RB:1] + {{(RB-1){1'b0}}, 1'b1}, 1'b0}; end
            if (settle != 2'd0) settle <= settle - 2'd1;
            // FIFO occupancy / credits (pops return credits, issues take them)
            if (fe_flush) begin fq_n <= 5'd0; fcred <= FD; end
            else begin
                fq_n <= fq_n - {3'd0, pc} + {3'd0, sc};
                fcred <= fcred + {3'd0, pc} - (rd_iss ? (rdp[0] ? 5'd1 : 5'd2) : 5'd0);
            end
            if (job_start) begin
                fs <= F_H; rp <= {{RB{1'b0}}, img_q[4]}; rdp <= {{RB{1'b0}}, img_q[4]}; frp <= {{RB{1'b0}}, img_q[4]};
                ep <= ~ep; depth <= 2'd0; Lc <= 16'd0; L1c <= 16'd0; settle <= 2'd0; pi <= 4'd0;
            end else if (run_f) begin
                case (fs)
                    F_H: if (fe_hcap) begin
                        h <= hw; hq_kind <= q_akind; hq_rdy0 <= (hw_rc == RC_FLT) || (!hw_tmpl && hw_np == 3'd0); rcl <= hw_rc; rskip <= !hw_pok && !(hw_recbad || hw_bad);
                        hq_rlen <= hw_rlen; hq_rpn <= rp + {{(RB-4){1'b0}}, hw_rlen};
                        hq_nit <= {3'd0, hw_tmpl} + {1'b0, hw_np}; hq_np <= hw_np;
                        for (fk = 0; fk < 7; fk = fk + 1) hq_sl[fk*3 +: 3] <= mth(hw_opnd, fk[2:0]);
                        ctag <= qt; pi <= 4'd0;
                        fs <= F_P;
                    end
                    F_P: begin
                        if (rcl == RC_FLT) fs <= F_HALT;            // the fault entry is queued; decode stops
                        if (fe_pop2) pi <= pi + 4'd1;
                        if (fe_done) begin
                            if (rcl == RC_DSP) begin
                                rp <= hq_rpn; if (depth == 2'd0) frp <= hq_rpn;
                                fs <= (h[H_UNIT +: 4] == 4'd0 && h_op == 6'd3) ? F_HALT : F_H;   // END: decode stops
                            end else if (rskip || h_op == 6'd0 || h_op == 6'd4) begin             // skip / NOP / FENCE
                                rp <= hq_rpn; if (depth == 2'd0) frp <= hq_rpn; fs <= F_H;
                            end else if (h_op == 6'd1) begin                                       // LOOP
                                if (h_lvm) fs <= F_LVW;
                                else begin
                                    lv_lvl[depth[0]] <= h[H_PARAM + 16]; lv_cnt[depth[0]] <= h[H_PARAM +: 16];
                                    lv_body[depth[0]] <= hq_rpn;
                                    if (h[H_PARAM + 16]) L1c <= 16'd0; else Lc <= 16'd0;
                                    depth <= depth + 2'd1; rp <= hq_rpn;
                                    if (depth == 2'd0) frp <= hq_rpn;
                                    settle <= 2'd2; fs <= F_H;
                                end
                            end else begin                                                         // ENDLOOP
                                if (more) begin
                                    if (top_lvl) L1c <= L1c + 16'd1; else Lc <= Lc + 16'd1;
                                    rp <= lv_body[top[0]]; rdp <= lv_body[top[0]]; ep <= ~ep;      // replay from the ring
                                end else begin
                                    if (top_lvl) L1c <= 16'd0; else Lc <= 16'd0;
                                    depth <= depth - 2'd1; rp <= hq_rpn;
                                    if (depth == 2'd1) frp <= hq_rpn;
                                end
                                settle <= 2'd2; fs <= F_H;
                            end
                        end
                    end
                    F_LVW: if (lv_rsp) begin                                                       // the count arrived
                        lv_lvl[depth[0]] <= h[H_PARAM + 16]; lv_cnt[depth[0]] <= lv_rcnt;
                        lv_body[depth[0]] <= hq_rpn;
                        if (h[H_PARAM + 16]) L1c <= 16'd0; else Lc <= 16'd0;
                        depth <= depth + 2'd1; rp <= hq_rpn;
                        if (depth == 2'd0) frp <= hq_rpn;
                        settle <= 2'd2; fs <= F_H;
                    end
                    default: ;
                endcase
            end
        end
    end
    // ================================================================== AU: one descriptor a cycle
    // sideband bundle {isI, last, j, tag, sp, pn, px, flt, n[21], be}
    localparam integer SBW = 32 + QB;
    localparam integer SB_N = 1, SB_FLT = 22, SB_PX = 23, SB_PN = 24, SB_SP = 25, SB_TAG = 27, SB_J = 27 + QB,
                       SB_LAST = 30 + QB, SB_ISI = 31 + QB;
    reg [5:0] av;                        // stage valids A0 .. A5
    // A0: the item (FE pop or BE re-injection)
    reg        a0_be, a0_idx, a0_last, a0_isI, a0_hi, a0_et;
    reg [63:0] a0_b64; reg [31:0] a0_lstr, a0_l1str, a0_str, a0_x; reg [26:0] a0_dmul; reg [5:0] a0_dsel, a0_nsel;
    reg [19:0] a0_n; reg [1:0] a0_sp; reg [15:0] a0_L, a0_L1; reg [2:0] a0_slot, a0_j; reg [QB-1:0] a0_tag;
    // re-injection source (the resolver's entry ir_e, descriptor be_j): wires defined with the queue below
    wire [2:0]  be_j; wire [255:0] be_d; wire [23:0] be_ph; wire be_xj;
    reg  [31:0] Xv; reg [20:0] Nv;
    always @(posedge clk) begin
        if (be_inj) begin
            a0_be <= 1'b1; a0_b64 <= {be_ph, be_d[M_BASE +: 40]}; a0_lstr <= 32'd0; a0_l1str <= 32'd0; a0_str <= 32'd0;
            a0_x <= be_xj ? Xv : 32'd0; a0_dmul <= be_d[M_DMUL +: 27]; a0_dsel <= 6'd0; a0_nsel <= 6'd0; a0_n <= 20'd0;
            a0_idx <= 1'b0; a0_sp <= be_d[M_SPACE +: 2]; a0_L <= 16'd0; a0_L1 <= 16'd0; a0_slot <= 3'd0; a0_j <= be_j;
            a0_tag <= inj_e; a0_last <= 1'b0; a0_isI <= 1'b0; a0_hi <= 1'b0; a0_et <= 1'b0;
        end else begin
            a0_be <= 1'b0; a0_b64 <= {24'd0, fe_it[M_BASE +: 40]}; a0_lstr <= fe_it[M_LSTR +: 32];
            a0_l1str <= fe_it[M_L1STR +: 32]; a0_str <= fe_it[M_STRIDE +: 32]; a0_x <= 32'd0; a0_dmul <= fe_it[M_DMUL +: 27];
            a0_dsel <= fe_it[M_DSEL +: 6]; a0_nsel <= fe_it[M_NSEL +: 6]; a0_n <= fe_it[M_N +: 20]; a0_idx <= fe_it[M_IDX];
            a0_sp <= fe_it[M_SPACE +: 2]; a0_L <= Lc; a0_L1 <= L1c; a0_slot <= h[H_SLOT +: 3]; a0_j <= fe_sl; a0_tag <= ctag;
            a0_last <= (pi + 4'd1 == hq_nit); a0_isI <= (fe_sl == 3'd6); a0_hi <= h[H_OPND + 6];
            a0_et <= (h[H_UNIT +: 4] == 4'd0) && (h_op == 6'd3 || h_op == 6'd5);
        end
    end
    // A1: DYN lookups (table row of the record's slot), n, the per-descriptor checks
    function automatic [31:0] dynx(input [5:0] c, input [TRW-1:0] row, input [2:0] s, input [15:0] L, input [15:0] L1,
                                   input [19:0] pv, input [20:0] p1v, input [17:0] tv, input [7:0] rv);
        integer q; begin
            case (c)
                6'd0: dynx = 32'd0;
                6'd1: dynx = {12'd0, pv};
                6'd2: dynx = {11'd0, p1v};
                6'd3: dynx = {14'd0, tv};
                6'd4: dynx = {16'd0, L};
                6'd5: dynx = {24'd0, rv};
                6'd6: dynx = {29'd0, s};
                6'd7: dynx = row[0 +: 32];
                6'd8: dynx = {16'd0, L1};
                6'd15: dynx = row[32 +: 32];
                default: begin dynx = 32'd0; for (q = 16; q <= 40; q = q + 1) if (c == q[5:0]) dynx = row[(q - 14)*32 +: 32]; end
            endcase
        end
    endfunction
    // v2.3 (route 905100ec5: a0_slot -> 8:1 row mux -> 27:1 code mux -> a1_x): the record's table row is registered
    // from h (fixed for the record; an item reaches A1 >= 2 cycles after its header pop, h of the next record lands
    // >= 1 cycle after the last item's A1)
    reg [TRW-1:0] hrow_q;
    always @(posedge clk) hrow_q <= trow_of(trow, h[H_SLOT +: 3]);
    wire [TRW-1:0] a0_row = hrow_q;
    wire [31:0] dyn_d = dynx(a0_dsel, a0_row, a0_slot, a0_L, a0_L1, pos, pos1_q, token, rank_r),
                dyn_n = dynx(a0_nsel, a0_row, a0_slot, a0_L, a0_L1, pos, pos1_q, token, rank_r);
    wire a0_flt = !a0_be && ((a0_isI && (a0_idx || a0_nsel == 6'd63 || (a0_sp != 2'd1 && !(IKS_I != 0 && a0_sp == 2'd0)))) ||
                             (!a0_isI && (a0_idx || a0_nsel == 6'd63) && !a0_hi) ||
                             (!a0_idx && dyn_rsv(a0_dsel)) ||
                             (a0_nsel != 6'd0 && a0_nsel != 6'd63 && dyn_rsv(a0_nsel)) ||
                             (a0_et && a0_j == 3'd0 && a0_sp != 2'd1));
    reg [63:0] a1_b64; reg [31:0] a1_lstr, a1_l1str, a1_x, a1_str; reg [26:0] a1_dmul; reg [15:0] a1_L, a1_L1;
    reg [SBW-1:0] a1_sb;
    always @(posedge clk) begin
        a1_b64 <= a0_b64; a1_lstr <= a0_lstr; a1_l1str <= a0_l1str; a1_dmul <= a0_dmul; a1_L <= a0_L; a1_L1 <= a0_L1; a1_str <= a0_str;
        a1_x <= a0_be ? a0_x : (a0_idx ? 32'd0 : dyn_d);
        a1_sb <= {a0_isI, a0_last, a0_j, a0_tag, a0_sp, !a0_be && !a0_isI && a0_nsel == 6'd63, !a0_be && !a0_isI && a0_idx,
                  a0_flt, (a0_nsel == 6'd0) ? {1'b0, a0_n} : dyn_n[20:0], a0_be};
    end
    // A2: 60 partial-product rows (base, L x lstride, L1 x l1stride, X x dyn_mul) -> CSA 60 -> 40 -> 27 -> 18 -> 12 -> 8
    reg [60*64-1:0] pr; reg [40*64-1:0] v1; reg [27*64-1:0] v2; reg [18*64-1:0] v3; reg [12*64-1:0] v4; reg [8*64-1:0] v5;
    integer q2;
    always @* begin
        pr[0 +: 64] = a1_b64;
        for (q2 = 0; q2 < 16; q2 = q2 + 1) begin
            pr[(1 + q2)*64 +: 64]  = a1_L[q2]  ? (sx32(a1_lstr) << q2)  : 64'd0;
            pr[(17 + q2)*64 +: 64] = a1_L1[q2] ? (sx32(a1_l1str) << q2) : 64'd0;
        end
        for (q2 = 0; q2 < 27; q2 = q2 + 1) pr[(33 + q2)*64 +: 64] = a1_dmul[q2] ? ({32'd0, a1_x} << q2) : 64'd0;
        for (q2 = 0; q2 < 20; q2 = q2 + 1) begin
            v1[(2*q2)*64 +: 64]     = s3(pr[(3*q2)*64 +: 64], pr[(3*q2+1)*64 +: 64], pr[(3*q2+2)*64 +: 64]);
            v1[(2*q2+1)*64 +: 64]   = c3(pr[(3*q2)*64 +: 64], pr[(3*q2+1)*64 +: 64], pr[(3*q2+2)*64 +: 64]);
        end
        for (q2 = 0; q2 < 13; q2 = q2 + 1) begin
            v2[(2*q2)*64 +: 64]     = s3(v1[(3*q2)*64 +: 64], v1[(3*q2+1)*64 +: 64], v1[(3*q2+2)*64 +: 64]);
            v2[(2*q2+1)*64 +: 64]   = c3(v1[(3*q2)*64 +: 64], v1[(3*q2+1)*64 +: 64], v1[(3*q2+2)*64 +: 64]);
        end
        v2[26*64 +: 64] = v1[39*64 +: 64];
        for (q2 = 0; q2 < 9; q2 = q2 + 1) begin
            v3[(2*q2)*64 +: 64]     = s3(v2[(3*q2)*64 +: 64], v2[(3*q2+1)*64 +: 64], v2[(3*q2+2)*64 +: 64]);
            v3[(2*q2+1)*64 +: 64]   = c3(v2[(3*q2)*64 +: 64], v2[(3*q2+1)*64 +: 64], v2[(3*q2+2)*64 +: 64]);
        end
        for (q2 = 0; q2 < 6; q2 = q2 + 1) begin
            v4[(2*q2)*64 +: 64]     = s3(v3[(3*q2)*64 +: 64], v3[(3*q2+1)*64 +: 64], v3[(3*q2+2)*64 +: 64]);
            v4[(2*q2+1)*64 +: 64]   = c3(v3[(3*q2)*64 +: 64], v3[(3*q2+1)*64 +: 64], v3[(3*q2+2)*64 +: 64]);
        end
        for (q2 = 0; q2 < 4; q2 = q2 + 1) begin
            v5[(2*q2)*64 +: 64]     = s3(v4[(3*q2)*64 +: 64], v4[(3*q2+1)*64 +: 64], v4[(3*q2+2)*64 +: 64]);
            v5[(2*q2+1)*64 +: 64]   = c3(v4[(3*q2)*64 +: 64], v4[(3*q2+1)*64 +: 64], v4[(3*q2+2)*64 +: 64]);
        end
    end
    reg [8*64-1:0] a2_r; reg [15:0] a2_L; reg [31:0] a2_str; reg [SBW-1:0] a2_sb;
    always @(posedge clk) begin a2_r <= v5; a2_L <= a1_L; a2_str <= a1_str; a2_sb <= a1_sb; end
    // A3: CSA 8 -> 6 -> 4 -> 3 -> 2, then (+ L) and (+ L + I.stride): the I-table read addresses I_eff + L, + stride
    reg [6*64-1:0] w1; reg [4*64-1:0] w2; reg [3*64-1:0] w3; reg [63:0] fs0, fc0, fs1, fc1, fs2, fc2;
    always @* begin
        w1[0 +: 64] = s3(a2_r[0 +: 64], a2_r[64 +: 64], a2_r[128 +: 64]);   w1[64 +: 64] = c3(a2_r[0 +: 64], a2_r[64 +: 64], a2_r[128 +: 64]);
        w1[128 +: 64] = s3(a2_r[192 +: 64], a2_r[256 +: 64], a2_r[320 +: 64]); w1[192 +: 64] = c3(a2_r[192 +: 64], a2_r[256 +: 64], a2_r[320 +: 64]);
        w1[256 +: 64] = a2_r[384 +: 64]; w1[320 +: 64] = a2_r[448 +: 64];
        w2[0 +: 64] = s3(w1[0 +: 64], w1[64 +: 64], w1[128 +: 64]);     w2[64 +: 64] = c3(w1[0 +: 64], w1[64 +: 64], w1[128 +: 64]);
        w2[128 +: 64] = s3(w1[192 +: 64], w1[256 +: 64], w1[320 +: 64]); w2[192 +: 64] = c3(w1[192 +: 64], w1[256 +: 64], w1[320 +: 64]);
        w3[0 +: 64] = s3(w2[0 +: 64], w2[64 +: 64], w2[128 +: 64]);     w3[64 +: 64] = c3(w2[0 +: 64], w2[64 +: 64], w2[128 +: 64]);
        w3[128 +: 64] = w2[192 +: 64];
        fs0 = s3(w3[0 +: 64], w3[64 +: 64], w3[128 +: 64]);             fc0 = c3(w3[0 +: 64], w3[64 +: 64], w3[128 +: 64]);
        fs1 = s3(fs0, fc0, {48'd0, a2_L});                               fc1 = c3(fs0, fc0, {48'd0, a2_L});
        fs2 = s3(fs1, fc1, sx32(a2_str));                                fc2 = c3(fs1, fc1, sx32(a2_str));
    end
    reg [63:0] a3_s0, a3_c0, a3_s1, a3_c1, a3_s2, a3_c2; reg [SBW-1:0] a3_sb;
    always @(posedge clk) begin a3_s0 <= fs0; a3_c0 <= fc0; a3_s1 <= fs1; a3_c1 <= fc1; a3_s2 <= fs2; a3_c2 <= fc2; a3_sb <= a2_sb; end
    // A4: 16-bit chunks, both carries (17-bit adds only)
    reg [3*4*17-1:0] a4_z0, a4_z1; reg [SBW-1:0] a4_sb;
    integer q4;
    always @(posedge clk) begin
        for (q4 = 0; q4 < 4; q4 = q4 + 1) begin
            a4_z0[(0*4 + q4)*17 +: 17] <= {1'b0, a3_s0[q4*16 +: 16]} + {1'b0, a3_c0[q4*16 +: 16]};
            a4_z1[(0*4 + q4)*17 +: 17] <= {1'b0, a3_s0[q4*16 +: 16]} + {1'b0, a3_c0[q4*16 +: 16]} + 17'd1;
            a4_z0[(1*4 + q4)*17 +: 17] <= {1'b0, a3_s1[q4*16 +: 16]} + {1'b0, a3_c1[q4*16 +: 16]};
            a4_z1[(1*4 + q4)*17 +: 17] <= {1'b0, a3_s1[q4*16 +: 16]} + {1'b0, a3_c1[q4*16 +: 16]} + 17'd1;
            a4_z0[(2*4 + q4)*17 +: 17] <= {1'b0, a3_s2[q4*16 +: 16]} + {1'b0, a3_c2[q4*16 +: 16]};
            a4_z1[(2*4 + q4)*17 +: 17] <= {1'b0, a3_s2[q4*16 +: 16]} + {1'b0, a3_c2[q4*16 +: 16]} + 17'd1;
        end
        a4_sb <= a3_sb;
    end
    // A5: carry select -> acc = the effective base, iax = acc + L, ian = acc + L + sx(I.stride)
    reg [3*64-1:0] csel; reg [16:0] cz; reg ccy; integer q5, p5;
    always @* begin
        for (p5 = 0; p5 < 3; p5 = p5 + 1) begin
            ccy = 1'b0;
            for (q5 = 0; q5 < 4; q5 = q5 + 1) begin
                cz = ccy ? a4_z1[(p5*4 + q5)*17 +: 17] : a4_z0[(p5*4 + q5)*17 +: 17];
                csel[p5*64 + q5*16 +: 16] = cz[15:0]; ccy = cz[16];
            end
        end
    end
    reg [63:0] a5_acc, a5_iax, a5_ian; reg [SBW-1:0] a5_sb;
    always @(posedge clk) begin a5_acc <= csel[0 +: 64]; a5_iax <= csel[64 +: 64]; a5_ian <= csel[128 +: 64]; a5_sb <= a4_sb; end
    // A6: range flags; the result is written into its queue entry (FE item) or returned to the BE (re-injection)
    wire        a5_be = a5_sb[0];
    wire [20:0] a5_n = a5_sb[SB_N +: 21];
    wire        a5_flt = a5_sb[SB_FLT], a5_px = a5_sb[SB_PX], a5_pn = a5_sb[SB_PN];
    wire [1:0]  a5_sp = a5_sb[SB_SP +: 2];
    wire [QB-1:0] a5_tag = a5_sb[SB_TAG +: QB];
    wire [2:0]  a5_j = a5_sb[SB_J +: 3];
    wire        a5_last = a5_sb[SB_LAST], a5_isI = a5_sb[SB_ISI];
    wire        a6_bad_d = base_bad(a5_sp, a5_acc, 1'b1), a6_bad_vm = base_bad(2'd1, a5_acc, 1'b0);
`ifdef OT_HGI_SEQ_MUT_IDXL
    wire [63:0] a6_iax = a5_acc;                          // NEGATIVE CONTROL: the indexed read ignores L
`else
    wire [63:0] a6_iax = a5_iax;
`endif
    wire        a6_ixb = (a6_iax[63:18] != 46'd0), a6_inb = (a5_ian[63:18] != 46'd0);
    wire        a6_fe = av[5] && !a5_be;
    wire        a6_be = av[5] && a5_be;
    wire        a6_ihbm = (IKS_I != 0) && a5_isI && a5_sp == 2'd0;      // IKS: an HBM-space I (range-checked as HBM)
    wire        a6_flt = a5_flt || (a5_isI ? (a6_ihbm ? a6_bad_d : a6_bad_vm) : (!(a5_px || a5_pn) && a6_bad_d));
    // ================================================================== RQ: the record queue (one generate block an entry)
    localparam integer EW_D = 7*256, EW_N = 7*21, EW_PH = 6*24;
    wire [QD*128-1:0] all_hdr; wire [QD*3-1:0] all_kind; wire [QD*256-1:0] all_sut; wire [QD*EW_D-1:0] all_dsc;
    wire [QD*EW_N-1:0] all_n; wire [QD*EW_PH-1:0] all_ph; wire [QD*6-1:0] all_px, all_pn; wire [QD*18-1:0] all_ixa, all_ina;
    wire [QD-1:0] all_ixb, all_inb, all_rdy, all_flt; wire [QD*16-1:0] all_L, all_L1; wire [QD*21-1:0] all_ps1;
    wire        be_pclr;                 // the resolver's entry has every pending descriptor resolved
    reg  [QB-1:0] rd_e, inj_e;         // the resolver's reader entry (VM reads) / injector entry (AU pass)
    reg         ir_flt;                  // the reader found a fault in rd_e (reported when rd_e reaches the head)
    wire [TRW-1:0] h_row = trow_of(trow, h[H_SLOT +: 3]);
    // v2.3 (route 905100ec5: pi -> fe_sl -> 7k s_dsc enables): an FE item / SUT is written into its entry one cycle
    // after the pop from a staging register, under per-(entry, slot) registered enables
    reg [255:0] it_d; reg [QD*7-1:0] it_we; reg [QD-1:0] su_we; reg su_np0; integer qe7;
    always @(posedge clk) begin it_d <= fe_it; su_np0 <= (hq_np == 3'd0); end
    always @(posedge clk or negedge rn_f)
        if (!rn_f) begin it_we <= {(QD*7){1'b0}}; su_we <= {QD{1'b0}}; end
        else for (qe7 = 0; qe7 < QD*7; qe7 = qe7 + 1) begin
            it_we[qe7] <= fe_item && ctag == qe7 / 7 && fe_sl == qe7 % 7;
            if (qe7 < QD) su_we[qe7] <= fe_sut && ctag == qe7;
        end
    genvar ge, gs;
    generate for (ge = 0; ge < QD; ge = ge + 1) begin : g_q
        reg [127:0] e_hdr; reg [2:0] e_kind; reg [255:0] e_sut;
        reg [17:0] e_ixa, e_ina; reg e_ixb, e_inb, e_rdy, e_flt; reg [15:0] e_L, e_L1; reg [20:0] e_ps1;
        wire [EW_D-1:0] e_dsc; wire [EW_N-1:0] e_n; wire [EW_PH-1:0] e_ph; wire [6:0] e_px7, e_pn7;
        wire al = ha_e[ge] || (fe_aalloc && qt == ge);
        wire fw = a6_fe && a5_tag == ge;
        wire bw = a6_be && inj_e == ge;
        wire pclr = al || (be_pclr && inj_e == ge);
        always @(posedge clk) begin
            if (al) begin
                e_hdr <= h; e_kind <= fe_aalloc ? ((h_op == 6'd4) ? K_FENCE : K_LVM) : hq_kind; e_L <= Lc; e_L1 <= L1c;
                e_ps1 <= h_row[32 +: 21]; e_flt <= 1'b0;
                e_rdy <= fe_aalloc || hq_rdy0;
            end
            if (su_we[ge]) begin e_sut <= it_d; if (su_np0) e_rdy <= 1'b1; end
            if (fw) begin
                if (a5_isI) begin e_ixa <= a6_iax[17:0]; e_ixb <= a6_ixb; e_ina <= a5_ian[17:0]; e_inb <= a6_inb; end
                if (a6_flt) e_flt <= 1'b1;
                if (a5_last) e_rdy <= 1'b1;
            end
            if ((ir_flt && rd_e == ge) || (bw && a6_bad_d)) e_flt <= 1'b1;
            // IKS: an HBM-space I is no indexed-read source: an indexed / N_FROM_VM operand of the record faults (as without I)
            if (fw && a6_ihbm && ((|e_px7[5:0]) || (|e_pn7[5:0]))) e_flt <= 1'b1;
        end
        // one descriptor slot: raw at the pop, base / n patched by the AU (FE pass) and by the BE (indexed pass)
        for (gs = 0; gs < 7; gs = gs + 1) begin : g_s
            reg [255:0] s_dsc; reg [20:0] s_n; reg [23:0] s_ph; reg s_px, s_pn;
            wire [20:0] nf = s_pn ? Nv : s_n;
            always @(posedge clk) begin
                if (it_we[ge*7 + gs]) s_dsc <= it_d;
                if (pclr) begin s_px <= 1'b0; s_pn <= 1'b0; end
                if (fw && a5_j == gs) begin
                    s_dsc[M_BASE +: 40] <= a5_acc[39:0]; s_dsc[M_N +: 20] <= a5_n[19:0]; s_n <= a5_n;
                    s_ph <= a5_acc[63:40]; s_px <= a5_px; s_pn <= a5_pn;
                end
                if (bw && a5_j == gs) begin
                    s_dsc[M_BASE +: 40] <= a5_acc[39:0]; s_dsc[M_N +: 20] <= nf[19:0]; s_n <= nf;
                end
            end
            assign e_dsc[gs*256 +: 256] = s_dsc; assign e_n[gs*21 +: 21] = s_n;
            assign e_px7[gs] = s_px; assign e_pn7[gs] = s_pn;
            if (gs < 6) begin : g_ph assign e_ph[gs*24 +: 24] = s_ph; end
        end
        assign all_hdr[ge*128 +: 128] = e_hdr; assign all_kind[ge*3 +: 3] = e_kind; assign all_sut[ge*256 +: 256] = e_sut;
        assign all_dsc[ge*EW_D +: EW_D] = e_dsc; assign all_n[ge*EW_N +: EW_N] = e_n; assign all_ph[ge*EW_PH +: EW_PH] = e_ph;
        assign all_px[ge*6 +: 6] = e_px7[5:0]; assign all_pn[ge*6 +: 6] = e_pn7[5:0]; assign all_ixa[ge*18 +: 18] = e_ixa;
        assign all_ina[ge*18 +: 18] = e_ina; assign all_ixb[ge] = e_ixb; assign all_inb[ge] = e_inb; assign all_rdy[ge] = e_rdy;
        assign all_flt[ge] = e_flt; assign all_L[ge*16 +: 16] = e_L; assign all_L1[ge*16 +: 16] = e_L1; assign all_ps1[ge*21 +: 21] = e_ps1;
    end endgenerate
    // the head entry: each 64-bit chunk of the packed entry is selected by its own head-pointer copy (qh_cp)
    reg [127:0] hd_hdr; reg [2:0] hd_kind; reg [255:0] hd_sut; reg [EW_D-1:0] hd_dsc; reg [EW_N-1:0] hd_n;
    reg [5:0] hd_px, hd_pn; reg hd_rdy, hd_flt; reg [15:0] hd_L, hd_L1; reg [20:0] hd_ps1;
    wire [QD*NQC*64-1:0] ent_all;
    wire [NQC*64-1:0] hd_vec;
    genvar gv, gc;
    generate for (gv = 0; gv < QD; gv = gv + 1) begin : g_ev
        assign ent_all[gv*NQC*64 +: NQC*64] = {{(NQC*64 - HVW){1'b0}}, all_ps1[gv*21 +: 21], all_L1[gv*16 +: 16], all_L[gv*16 +: 16],
            all_flt[gv], all_rdy[gv], all_pn[gv*6 +: 6], all_px[gv*6 +: 6], all_n[gv*EW_N +: EW_N], all_dsc[gv*EW_D +: EW_D],
            all_sut[gv*256 +: 256], all_kind[gv*3 +: 3], all_hdr[gv*128 +: 128]};
    end
    for (gc = 0; gc < NQC; gc = gc + 1) begin : g_hc
        reg [63:0] m; integer qe;
        always @* begin
            m = ent_all[gc*64 +: 64];
            for (qe = 1; qe < QD; qe = qe + 1) if (qh_cp[gc*QB +: QB] == qe) m = ent_all[(qe*NQC + gc)*64 +: 64];
        end
        assign hd_vec[gc*64 +: 64] = m;
    end endgenerate
    always @* {hd_ps1, hd_L1, hd_L, hd_flt, hd_rdy, hd_pn, hd_px, hd_n, hd_dsc, hd_sut, hd_kind, hd_hdr} = hd_vec[HVW-1:0];
    // ================================================================== IR: the indexed resolver
    // An entry's I-table reads (ONE X read at I_eff + L, ONE N read at I_eff + I.stride + L) are made as soon as the
    // entry's wait mask is met with every OLDER queued dispatch counted busy (those dispatch before it, so its wait
    // would hold for them) -- the same producer-retired condition the head would see, earlier.  Its pending
    // descriptors are then re-injected through the AU (X x dyn_mul + the pre-sum) and patched in place; a read or
    // range fault marks the entry (status 3 when it reaches the head, after the records before it).  Oldest first;
    // the scan stops at an entry still in the AU, a fault, FENCE or LOOP-from-VM.
    // two halves, overlapped: the READER makes the VM reads of one entry while the INJECTOR re-injects the previous one
    localparam [1:0] I_IDLE = 2'd0, I_XR = 2'd1, I_NR = 2'd2, I_HAND = 2'd3;     // reader
    localparam [1:0] J_IDLE = 2'd0, J_INJ = 2'd1, J_IW = 2'd2;                   // injector
    reg [1:0] ir_st, jst; reg ir_sv; reg [QB-1:0] ir_se; reg [31:0] rXv; reg [20:0] rNv;
    reg [5:0] rem; reg [3:0] ninj, nres;
    // v2.3 (route 905100ec5: rd_e -> 4:1 entry mux -> vr_addr): the reader entry's N-read operands, registered (rd_e
    // and the entry are fixed while the X read is in flight; its response is >= 2 cycles after rd_e is set)
    reg [17:0] rd_ina_q; reg rd_pn_q, rd_inb_q;
    always @(posedge clk) begin rd_ina_q <= all_ina[rd_e*18 +: 18]; rd_pn_q <= |all_pn[rd_e*6 +: 6]; rd_inb_q <= all_inb[rd_e]; end
    // per-entry scan inputs
    // the per-entry scan inputs are registered (one cycle stale is conservative: an entry only becomes ready /
    // resolved / faulted, busy only drops apart from dispatches of entries still in the queue, which the scan counts)
    reg [QD-1:0] en_blk, en_pend, en_disp; reg [QD*16-1:0] en_um, en_w; integer qa;
    always @(posedge clk) for (qa = 0; qa < QD; qa = qa + 1) begin
        en_blk[qa] <= !all_rdy[qa] || all_flt[qa] || all_kind[qa*3 +: 3] == K_FLT || all_kind[qa*3 +: 3] == K_FENCE ||
                     all_kind[qa*3 +: 3] == K_LVM;
        en_pend[qa] <= (all_px[qa*6 +: 6] | all_pn[qa*6 +: 6]) != 6'd0 && !(ir_st != I_IDLE && rd_e == qa) &&
                      !(jst != J_IDLE && inj_e == qa);         // an entry the resolver holds counts as resolved
        en_disp[qa] <= all_kind[qa*3 +: 3] == K_DISP;
        en_um[qa*16 +: 16] <= 16'd1 << all_hdr[qa*128 + H_UNIT +: 4];
        en_w[qa*16 +: 16] <= all_hdr[qa*128 + H_WAIT +: 16];
    end
    // v2.5 (drain rule, HGI-1 4.1 / 4.3): the compiler drops a wait bit a record would need when an OLDER record already
    // waits for that unit ("since that unit last drained": in order, the older record's wait drains it for both).  The
    // head sees that drain; a resolver ahead of the head does not, unless it also honours the wait masks of the older
    // queued entries (ow).  Without ow the I table of an indexed reader behind e.g. a DMA.FENCE that waits for IDX was
    // read while IDX.TOPK was still running (DS route.gather: stale ids, a wrong effective base).
    reg ir_cv, sblk; reg [QB-1:0] ir_ce, se; reg [15:0] om, ow, ir_cm, ir_cw; integer si, sj;
    always @* begin
        ir_cv = 1'b0; ir_ce = {QB{1'b0}}; ir_cm = 16'd0; ir_cw = 16'd0; sblk = 1'b0; om = 16'd0; ow = 16'd0;
        for (si = 0; si < QD; si = si + 1) begin
            se = qh + si[QB-1:0];
            if (si < q_cnt && !sblk && !ir_cv)
                for (sj = 0; sj < QD; sj = sj + 1) if (se == sj[QB-1:0]) begin
                    if (en_blk[sj]) sblk = 1'b1;
                    else if (en_pend[sj]) begin ir_cv = 1'b1; ir_ce = se; ir_cm = om; ir_cw = en_w[sj*16 +: 16] | ow; end
                    else begin
`ifdef OT_HGI_SEQ_MUT_DRAIN
                        ow = 16'd0;                           // NEGATIVE CONTROL: older waits ignored (the v2.1 .. v2.4 rule)
`else
                        ow = ow | en_w[sj*16 +: 16];
`endif
                        if (en_disp[sj]) om = om | en_um[sj*16 +: 16];
                    end
                end
        end
    end
    // the injector's source: {ph 24, dmul 27, base 40, space 2} of each slot 0..5 of entry inj_e, and its pending bits
    localparam integer IJW = 93;
    wire [QD*6*IJW-1:0] inj_all;
    genvar gi2, gs2;
    generate for (gi2 = 0; gi2 < QD; gi2 = gi2 + 1) begin : g_ij
        for (gs2 = 0; gs2 < 6; gs2 = gs2 + 1) begin : g_ijs
            assign inj_all[(gi2*6 + gs2)*IJW +: IJW] = {all_ph[gi2*EW_PH + gs2*24 +: 24], all_dsc[gi2*EW_D + gs2*256 + M_DMUL +: 27],
                                                        all_dsc[gi2*EW_D + gs2*256 + M_BASE +: 40], all_dsc[gi2*EW_D + gs2*256 + M_SPACE +: 2]};
        end
    end endgenerate
    reg [6*IJW-1:0] ij_e; reg [5:0] ir_px, ir_pn; integer qr;
    always @* begin
        ij_e = inj_all[0 +: 6*IJW]; ir_px = all_px[0 +: 6]; ir_pn = all_pn[0 +: 6];
        for (qr = 1; qr < QD; qr = qr + 1) if (inj_e == qr) begin
            ij_e = inj_all[qr*6*IJW +: 6*IJW]; ir_px = all_px[qr*6 +: 6]; ir_pn = all_pn[qr*6 +: 6];
        end
    end
    reg [2:0] bj; integer qj;
    always @* begin bj = 3'd0; for (qj = 5; qj >= 0; qj = qj - 1) if (rem[qj]) bj = qj[2:0]; end
    reg [IJW-1:0] bsel; integer qk;
    always @* begin bsel = ij_e[0 +: IJW]; for (qk = 1; qk < 6; qk = qk + 1) if (bj == qk) bsel = ij_e[qk*IJW +: IJW]; end
    wire [255:0] bd = {{(256 - M_DMUL - 27){1'b0}}, bsel[42 +: 27], {(M_DMUL - M_BASE - 40){1'b0}}, bsel[2 +: 40], {(M_BASE - 2){1'b0}}, bsel[0 +: 2]};
    wire [23:0] bph = bsel[69 +: 24];
    assign be_j = bj; assign be_d = bd; assign be_ph = bph; assign be_xj = ir_px[bj];
    assign be_inj = run_q && (jst == J_INJ) && (rem != 6'd0);
    // ---- dispatch payload: loaded from the head entry when the BE dispatches it (absent operands read 0)
    wire        hd_wok = waitok(hd_hdr[H_WAIT +: 16], busy_u);
    wire        hd_pend = |(hd_px | hd_pn);
    wire        be_go = run_q && (st == S_HD) && (q_cnt != 0) && hd_kind == K_DISP && hd_rdy && !hd_flt && hd_wok && !hd_pend &&
                        !(|(u_fault_r & ~16'd1));
    // v2.3 (route 905100ec5: outst -> busy_u -> wait rule -> be_go -> 2.4k d_* enables): the payload follows the head
    // entry every S_HD cycle (enable = a state decode, no wait / ready logic); units sample d_* only under u_v (S_DSP),
    // and the value loaded in the be_go cycle is the same head entry as before.
    wire        d_ld = (st == S_HD);
    integer qd2;
    always @(posedge clk) if (d_ld) begin
        d_hdr <= hd_hdr; d_sut <= hd_hdr[H_TMPL] ? hd_sut : 256'd0; d_L <= hd_L; d_L1 <= hd_L1; d_pos1 <= pos1_q; d_pslot1 <= hd_ps1;
        for (qd2 = 0; qd2 < 7; qd2 = qd2 + 1) begin
            d_desc[qd2*256 +: 256] <= hd_hdr[H_OPND + qd2] ? hd_dsc[qd2*256 +: 256] : 256'd0;
            d_n[qd2*21 +: 21] <= hd_hdr[H_OPND + qd2] ? hd_n[qd2*21 +: 21] : 21'd0;
        end
    end
    // ================================================================== BE + job control (main FSM)
    // VM read request (timing pass 6 of v1): the FSM sets vr_vr with a vr_new pulse, vr_tk marks the request taken
    reg vr_vr, vr_new, vr_tk;
    assign vr_v = vr_vr & ~vr_tk;
    always @(posedge clk or negedge rn)
        if (!rn) vr_tk <= 1'b0;
        else vr_tk <= vr_new ? (vr_v & vr_rdy_h) : (vr_tk | (vr_v & vr_rdy_h));
    integer k;
    wire [15:0] u_acc = u_v & u_rdy_h;
    reg db_rdy_q;
    always @(posedge clk or negedge rn)
        if (!rn) db_rdy_q <= 1'b0;
        else db_rdy_q <= (st == S_IDLE) && !hold_r && !hold_h && !(db_v_h && db_rdy_q) && !db_pend;
    assign db_rdy = db_rdy_q;
    reg db_pend; reg [17:0] dbq_token; reg [19:0] dbq_pos; reg [31:0] dbq_job; reg [3:0] dbq_gen, dbq_ncol, dbq_kernel; reg [1:0] dbq_entry; reg [31:0] dbq_loff;
    always @(posedge clk or negedge rn)
        if (!rn) db_pend <= 1'b0;
        else if (db_v_h && db_rdy_q) db_pend <= 1'b1;
        else if (st == S_IDLE) db_pend <= 1'b0;
    always @(posedge clk) if (db_rdy_q) begin
        dbq_token <= db_token_h; dbq_pos <= db_pos_h; dbq_job <= db_job_h; dbq_gen <= db_gen_h; dbq_ncol <= db_ncol_h; dbq_entry <= db_entry_h; dbq_kernel <= db_kernel_h; dbq_loff <= db_loff_h;
    end
    reg cpl_v_q, cpl_tokx_q;
    wire cpl_hs = cpl_v_q & cpl_rdy_h;
    reg  cpl_hs_q;
    always @(posedge clk or negedge rn) if (!rn) cpl_hs_q <= 1'b0; else cpl_hs_q <= cpl_hs;
    always @(posedge clk or negedge rn)
        if (!rn) begin cpl_v_q <= 1'b0; cpl_tokx_q <= 1'b0; end
        else begin
            cpl_v_q <= ((st == S_CPL) || (st == S_TKB)) && !cpl_hs && !cpl_hs_q;
            cpl_tokx_q <= (st == S_TKB) && !cpl_hs && !cpl_hs_q;
        end
    assign cpl_v = cpl_v_q;
    assign cpl_tokx = cpl_tokx_q;
    reg db_bad;
    reg [15:0] cc_lo, cc_hi; reg cc_c;
    always @(*) cpl_cycles = {cc_hi, cc_lo};
    // dispatch: u_vr is set / cleared from flops only; u_tk marks a valid already taken, u_v = u_vr & ~u_tk
    reg [15:0] u_vr, u_tk, iss_q;
    always @(posedge clk or negedge rn)
        if (!rn) u_tk <= 16'd0;
        else u_tk <= (u_vr == 16'd0) ? 16'd0 : (u_tk | (u_v & u_rdy_h));
    assign u_v = u_vr & ~u_tk;
    reg [3:0] kern_q;
    reg [31:0] kern_off;
    wire [31:0] kern_base = (dbq_kernel > 4'd10) ? 32'd0 : md_k_r[dbq_kernel*32 +: 32];
    wire kern_pl = dbq_kernel == 4'd3 || dbq_kernel == 4'd7 || dbq_kernel == 4'd8;
    wire [39:0] entry_off = {4'd0, (db_entry_q == 2'd0) ? md_d_r[31:0] : (db_entry_q == 2'd1) ? md_d_r[63:32] :
                             (db_entry_q == 2'd2) ? md_d_r[95:64] : kern_off, 4'd0};
    wire [39:0] img_a = {md_d_r[123:96], 12'd0};
    reg [20:0] img_l; reg [19:0] img_ha, img_hb;
    reg [4:0]  tk_i, tk_n; reg [17:0] tk_base; reg tk_k; reg [3:0] ncol; reg [19:0] tk_pos;
    assign job_start = (st == S_DB3) && !db_bad;
    wire [3:0] nres_n = nres + {3'd0, a6_be};
    assign be_pclr = run_q && (jst == J_IW) && (nres_n == ninj);
    wire        hd_fault = |(u_fault_r & ~16'd1);
    wire        vm_free = (ir_st == I_IDLE) && !ir_sv;      // the BE may issue its own VM read (reader idle, nothing selected)
    task fault3;
        begin st <= S_CPL; run_q <= 1'b0; run_f <= 1'b0; cpl_status <= 4'd3; cpl_token <= 18'd0; fetching <= 1'b0; u_vr <= 16'd0;
              vr_vr <= 1'b0; end
    endtask
    // the BE frees the head (one comb term per pop site; mirrors the FSM below)
    wire be_abort = |(u_fault_r & ~16'd1) && st != S_IDLE && st != S_CPL;
    wire q_pop = !be_abort && ((st == S_DSP && |u_tk) || (st == S_FEN && (busy_u & 16'hFFFE) == 16'd0 && wr_quiet_r) ||
                 (st == S_LVR && vr_rsp_v_r && !(vr_rsp_data_r == 32'd0 || vr_rsp_data_r[31:16] != 16'd0)) ||
                 (st == S_TKB && cpl_hs_q && tk_i == tk_n));
    // outstanding records per unit: +1 at the dispatch decision (iss_q, registered), -1 on retire (done or fault)
    always @(posedge clk or negedge rn_u)
        if (!rn_u) for (k = 0; k < 16; k = k + 1) outst[k] <= 8'd0;
        else for (k = 0; k < 16; k = k + 1)
            if (iss_q[k] && !(u_done_r[k] | u_fault_r[k])) outst[k] <= outst[k] + 8'd1;
            else if (!iss_q[k] && (u_done_r[k] | u_fault_r[k]) && outst[k] != 8'd0) outst[k] <= outst[k] - 8'd1;
    // head-pointer copies: one per 64-bit chunk of the head mux (qh alone drove 7.7k mux loads)
    localparam integer HVW = 128 + 3 + 256 + EW_D + EW_N + 6 + 6 + 1 + 1 + 16 + 16 + 21;
    localparam integer NQC = (HVW + 63) / 64;
    wire [NQC*QB-1:0] qh_cp;
    genvar gk;
    generate for (gk = 0; gk < NQC; gk = gk + 1) begin : g_qc
        (* keep = 1 *) reg [QB-1:0] qc;
        always @(posedge clk or negedge rn_m)
            if (!rn_m) qc <= {QB{1'b0}};
            else if (job_start) qc <= {QB{1'b0}};
            else if (q_pop) qc <= qc + 1'b1;
        assign qh_cp[gk*QB +: QB] = qc;
    end endgenerate
    always @(posedge clk or negedge rn_m) begin
        if (!rn_m) begin
            st <= S_IDLE; run_q <= 1'b0; run_f <= 1'b0; wp <= 0; wv <= 1'b0; inflight <= 0; drop <= 0; fetching <= 1'b0;
            u_vr <= 16'd0; iss_q <= 16'd0; vr_vr <= 1'b0; vr_new <= 1'b0; tbc <= 7'd0; av <= 6'd0;
            ir_st <= I_IDLE; jst <= J_IDLE; ir_sv <= 1'b0; ir_flt <= 1'b0; rd_e <= {QB{1'b0}}; inj_e <= {QB{1'b0}};
            cpl_status <= 0; cpl_token <= 0; cc_c <= 0;
            qh <= 0; qt <= 0; q_cnt <= 0; lv_rsp <= 1'b0; rem <= 6'd0; ninj <= 4'd0; nres <= 4'd0;
        end else begin
            iss_q <= 16'd0;
            if (st != S_IDLE && st != S_CPL) {cc_c, cc_lo} <= {1'b0, cc_lo} + 17'd1; else cc_c <= 1'b0;
            if (cc_c) cc_hi <= cc_hi + 16'd1;
            inflight <= fl_after;
            if (!tbc[6]) tbc <= tbc + 7'd1;
            vr_new <= 1'b0; lv_rsp <= 1'b0;
            if (rq_push) begin faddr <= faddr_n; faddr_n <= faddr_nn; faddr_nn <= faddr_nn + 40'd32; end   // v2.3: no add after the push decision
            if (f_rsp_v_r) begin
                if (drop != 0) drop <= drop - 8'd1;
                else begin wp <= wp + 2'd2; wv <= 1'b1; end
            end
            // AU stage valids (a job start flushes the pipe)
            av <= job_start ? 6'd0 : {av[4:0], be_inj | fe_item};
            // ---- indexed resolver (owns the VM port while it works; the BE's own reads wait for vm_free)
            ir_flt <= 1'b0;
            ir_sv <= run_q && ir_cv && waitok(ir_cw, busy_u | ir_cm);
            ir_se <= ir_ce;
            if (!run_q || job_start) begin ir_st <= I_IDLE; jst <= J_IDLE; end
            else begin
                case (ir_st)                                          // reader
                    I_IDLE: if (ir_sv && (all_px[ir_se*6 +: 6] | all_pn[ir_se*6 +: 6]) != 6'd0 && !(jst != J_IDLE && inj_e == ir_se) &&
                                st != S_ENDRD && st != S_TOKX && st != S_TKB && st != S_LVR) begin
                        rd_e <= ir_se;
                        if (|all_px[ir_se*6 +: 6]) begin
                            if (all_ixb[ir_se]) ir_flt <= 1'b1;
                            else begin vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= all_ixa[ir_se*18 +: 18]; ir_st <= I_XR; end
                        end else begin
                            if (all_inb[ir_se]) ir_flt <= 1'b1;
                            else begin vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= all_ina[ir_se*18 +: 18]; ir_st <= I_NR; end
                        end
                    end
                    I_XR: if (vr_rsp_v_r) begin
                        rXv <= vr_rsp_data_r;
                        if (rd_pn_q) begin
                            if (rd_inb_q) begin ir_flt <= 1'b1; ir_st <= I_IDLE; end
                            else begin vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= rd_ina_q; ir_st <= I_NR; end
                        end else ir_st <= I_HAND;
                    end
                    I_NR: if (vr_rsp_v_r) begin
                        if (vr_rsp_data_r[31:21] != 11'd0) begin ir_flt <= 1'b1; ir_st <= I_IDLE; end
                        else begin rNv <= vr_rsp_data_r[20:0]; ir_st <= I_HAND; end
                    end
                    default: ;                                        // I_HAND: the injector takes it below
                endcase
                case (jst)                                            // injector
                    J_IDLE: if (ir_st == I_HAND) begin
                        inj_e <= rd_e; Xv <= rXv; Nv <= rNv; rem <= all_px[rd_e*6 +: 6] | all_pn[rd_e*6 +: 6];
                        ninj <= 4'd0; nres <= 4'd0; jst <= J_INJ; ir_st <= I_IDLE;
                    end
                    default: begin                                    // J_INJ / J_IW: re-inject, collect, patch
                        if (be_inj) begin rem <= rem & ~(6'd1 << bj); ninj <= ninj + 4'd1; end
                        if (a6_be) nres <= nres_n;
                        if (jst == J_INJ && be_inj && (rem & ~(6'd1 << bj)) == 6'd0) jst <= J_IW;
                        if (be_pclr) jst <= J_IDLE;
                    end
                endcase
            end
            if (|(u_fault_r & ~16'd1) && st != S_IDLE && st != S_CPL) begin
                st <= S_CPL; run_q <= 1'b0; run_f <= 1'b0; cpl_status <= 4'd1; cpl_token <= 0; u_vr <= 0; vr_vr <= 1'b0; fetching <= 1'b0;
            end else case (st)
                S_IDLE: if (db_pend) begin
                    token <= dbq_token; pos <= dbq_pos; cpl_job <= dbq_job; cpl_gen <= dbq_gen; cpl_pos <= dbq_pos;
                    db_entry_q <= dbq_entry; kern_q <= dbq_kernel;
                    kern_off <= (kern_base == 32'd0) ? 32'd0 : kern_pl ? kern_base + dbq_loff : kern_base;
`ifdef OT_HGI_SEQ_CC_PRESET
                    cc_lo <= 16'hFF00; cc_hi <= 16'd0; cc_c <= 1'b0;   // bench: start near the low half's wrap
`else
                    cc_lo <= 16'd0; cc_hi <= 16'd0; cc_c <= 1'b0;
`endif
                    cpl_token <= 0; cpl_status <= 0; st <= S_DB; tbc <= 7'd0;
                    ncol <= dbq_ncol;
                end
                S_DB: begin
                    pos1_q <= {1'b0, pos} + 21'd1;
                    db_bad <= (token >= cfg_vocab_r || {1'b0, pos} >= cfg_ctx_max_r) || (db_entry_q == 2'd3 && kern_off == 32'd0);
                    img_l <= {1'b0, img_a[19:0]} + {1'b0, entry_off[19:0]};
                    img_ha <= img_a[39:20]; img_hb <= entry_off[39:20];
                    st <= S_DB2;
                end
                S_DB2: begin img_q <= {img_ha + img_hb + {19'd0, img_l[20]}, img_l[19:0]}; st <= S_DB3; end
                S_DB3: begin
                    if (db_bad) begin
                        st <= S_CPL; cpl_status <= 4'd3;
                    end else begin
                        faddr <= {img_q[39:5], 5'd0}; faddr_n <= {img_q[39:5] + 35'd1, 5'd0}; faddr_nn <= {img_q[39:5] + 35'd2, 5'd0}; fetching <= 1'b1;
                        wp <= 0; wv <= 1'b0; drop <= fl_after; run_q <= 1'b1; run_f <= 1'b1;
                        qh <= 0; qt <= 0; q_cnt <= 0;
                        st <= S_HD;
                    end
                end
                // ---- the head record: fault, FENCE, LOOP count, or wait mask -> indexed reads -> dispatch / END / TOKX
                S_HD: if (q_cnt != 0) begin
                    if (hd_kind == K_FLT) fault3;
                    else if (hd_rdy) begin
                        if (hd_flt) fault3;
                        else if (hd_kind == K_FENCE) st <= S_FEN;
                        else if (hd_kind == K_LVM) st <= S_LVW;
                        else if (hd_wok) begin
                            if (hd_pend) ;                                  // the resolver patches it
                            else if (hd_kind == K_DISP) begin
                                u_vr <= 16'd1 << hd_hdr[H_UNIT +: 4]; iss_q <= 16'd1 << hd_hdr[H_UNIT +: 4]; st <= S_DSP;
                            end else if (!vm_free) ;                        // the resolver owns the VM port
                            else if (hd_kind == K_END) begin
                                vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= hd_dsc[M_BASE +: 18]; st <= S_ENDRD;
                            end else begin                                  // TOKX: A[0] = k, then A[1..k]
                                if ({3'd0, hd_dsc[M_BASE +: 18]} + 21'd17 > 21'h40000) fault3;
                                else begin
                                    tk_base <= hd_dsc[M_BASE +: 18]; tk_i <= 5'd0; tk_k <= 1'b1; tk_pos <= pos;
                                    vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= hd_dsc[M_BASE +: 18]; st <= S_TOKX;
                                end
                            end
                        end
                    end
                end
                S_DSP: if (|u_tk) begin u_vr <= 16'd0; st <= S_HD; end
                S_FEN: if ((busy_u & 16'hFFFE) == 16'd0 && wr_quiet_r) st <= S_HD;
                S_LVW: if (hd_wok && vm_free) begin vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= hd_hdr[49:32]; st <= S_LVR; end
                S_LVR: if (vr_rsp_v_r) begin
                    if (vr_rsp_data_r == 32'd0 || vr_rsp_data_r[31:16] != 16'd0) fault3;
                    else begin lv_rsp <= 1'b1; lv_rcnt <= vr_rsp_data_r[15:0]; st <= S_HD; end
                end
                S_ENDRD: if (vr_rsp_v_r) begin
                    st <= S_CPL; run_q <= 1'b0; run_f <= 1'b0; fetching <= 1'b0; cpl_pos <= pos;
                    cpl_token <= vr_rsp_data_r[17:0];
                    cpl_status <= (vr_rsp_data_r[31:18] != 14'd0 || vr_rsp_data_r[17:0] >= cfg_vocab_r) ? 4'd3 : 4'd0;
                end
                // CTL.TOKX (HGI-1 7.4, Q-MTP-1): each committed token is a completion beat {token A[i], pos + i - 1, 0}
                S_TOKX: if (vr_rsp_v_r) begin
                    if (tk_k) begin
                        if (vr_rsp_data_r == 32'd0 || vr_rsp_data_r > {27'd0, ncol == 4'd0, ncol}) fault3;
                        else begin
                            tk_k <= 1'b0; tk_n <= vr_rsp_data_r[4:0]; tk_i <= 5'd1;
                            vr_vr <= 1'b1; vr_new <= 1'b1; vr_addr <= tk_base + 18'd1;
                        end
                    end else if (vr_rsp_data_r[31:18] != 14'd0 || vr_rsp_data_r[17:0] >= cfg_vocab_r) fault3;
                    else begin cpl_token <= vr_rsp_data_r[17:0]; cpl_pos <= tk_pos; cpl_status <= 4'd0; st <= S_TKB; end
                end
                S_TKB: if (cpl_hs_q) begin
                    tk_pos <= tk_pos + 20'd1;
                    if (tk_i == tk_n) st <= S_HD;
                    else begin
                        tk_i <= tk_i + 5'd1; vr_vr <= 1'b1; vr_new <= 1'b1; st <= S_TOKX;
`ifdef OT_HGI_SEQ_MUT_TOKX
                        vr_addr <= tk_base + {13'd0, tk_i};       // NEGATIVE CONTROL: the token address does not advance
`else
                        vr_addr <= tk_base + {13'd0, tk_i} + 18'd1;
`endif
                    end
                end
                S_CPL: if (cpl_hs_q) st <= S_IDLE;
                default: st <= S_IDLE;
            endcase
            if (st != S_DB3 || db_bad) begin
                if (q_alloc) qt <= qt + 1'b1;
                if (q_pop) qh <= qh + 1'b1;
                q_cnt <= q_cnt + {{QB{1'b0}}, q_alloc} - {{QB{1'b0}}, q_pop};
            end
        end
    end
endmodule
`default_nettype wire

// v2.3 hold-delay stage (a local copy of rtl/lib/ot_hdly, so every consumer that compiles ot_hgi_seq.sv by -y keeps
// building): N kept HB4xp67 delay cells a bit under SYNTHESIS (dont_touch'ed by physical/qwen_die_masters/
// hdly_dont_touch.tcl on instance names *u_hdly_*), a wire in simulation -- function is identity.
`default_nettype none
module ot_hgi_seq_hdly #(parameter integer W = 1, parameter integer N = 0) (input wire [W-1:0] a, output wire [W-1:0] y);
`ifdef SYNTHESIS
    if (N == 0) begin : g_w
        assign y = a;
    end else begin : g_d
        genvar b, k;
        for (b = 0; b < W; b = b + 1) begin : g_b
            wire [N:0] c;
            assign c[0] = a[b];
            for (k = 0; k < N; k = k + 1) begin : g_k
                (* keep *) HB4xp67_ASAP7_75t_R u_hb (.A(c[k]), .Y(c[k+1]));
            end
            assign y[b] = c[N];
        end
    end
`else
    assign y = a;
`endif
endmodule
`default_nettype wire
