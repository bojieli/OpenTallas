// KV-CDC2 (2026-10-18): leaf-local CDC fork of rtl/qwen_sys/host_20261013/qkd_host_native_qm_debt.sv for the HOST-cluster CDC leaves (qkd_hr_cdc_host /
// qkd_hr_ingest_qm, tools/qwen_kv_die/host_cluster/gen_cluster.py FORKS). The shared original is unchanged (it binds
// the closed core children and the flat root). Same ports and parameters as the original. Change: (1) the clk_i -> ck fault synchroniser fs samples a
// register f_any_q (+1 clk_i), not the f_code != 0 compare; (2) quiet_h reads the fault through a clk_i -> clk_h
// two-flop synchroniser (fh_s) of a registered sticky copy f_any_h instead of the ck-domain fault_c.
// (3) HKV-HROOT 10-18: CSR0 hold/acknowledge (CSR_HOLD_ACK, below).
// (4) SQK-INGEST 10-21 (SAFE item 5, results/arch/safe_audit_1019/kv.md): the payload
//     storage of the host receive FIFO u_hx (16 x 514 b) and of the request FIFO u_ox (16 x 289 b) moves out of flops into
//     dual-clock 1R1W SRAM macros u_hxm / u_oxm (ot_sram_1r1w2c_32x546_m1_p192_mir, the reviewed HOST-SRAM master; 16 of 32 rows
//     used, address MSB 0). The Gray pointers, synchronisers, full/empty/freed/count and ovf stay the reviewed
//     ot_link_afifo instances, now 1 bit wide (no payload). Shadow binary pointers (same reset, same push / pop) give
//     the macro addresses; the read address is the NEXT read pointer, so the registered macro read returns the head
//     on the same edge the flop FIFO's combinational mem[rbin] did: first-word fall-through, cycle-exact (0 schedule
//     cycles; witness rtl/test/qwen_host/qm_sram_1021). A slot is written >= 1 reader edge before its pointer is
//     visible (2-flop Gray synchroniser), and the writer never writes the slot under the head (full is conservative).
//     RMW_EN 0: the read-return FIFO u_rx is absent (it was never written: irv_q is 0), rx_empty 1.
//     Data-only registers (o_we / o_addr / o_d, t_d, cx_w, e_rdd) are no longer reset: reset reaches control/valid only.
// (5) QKO-HROOT2 10-21 ENGINE SPLIT (scratch/qko-hroot/INGEST_PLAN.txt): qkd_hr_ingest_cdc_shell = qkd_hr_native_qm_cdc
//     (QKC-HROOT a4442089b form) WITHOUT the ingest engine. The engine is its own single-clock hardened tile
//     (qkd_hr_ingest_eng: native32 netlist qkd_host_native_engine_n32); its ports are ck_ingest-domain ports of this shell
//     (e_*), wired directly (touching tiles, one ck_ingest region, no added cycles). Everything else is cycle-identical:
//     (a) completion FIFO u_cx = ONE 1-bit reviewed ot_link_afifo + shadow pointers + a third reviewed dual-clock SRAM
//         u_cxm (exactly the u_hx / u_ox pattern; replaces the 64-slice qkc_afifo_bits form and the 64 x 64 b flops);
//     (b) cx_w is loaded every clk_i edge with (e_done ? done word : fault word): it is written into u_cx only when cx_wr,
//         which is exactly when the old enabled load happened, so every pushed word is identical (data-only register);
//         the three parts select on the engine's done_v copies (e_done_c / e_done_a / e_done_b, <= 32 loads each);
//     (c) die-face capture o_we / o_addr / o_d (289 b) and the request word ox_w (289 b) use kept copies of the pop /
//         marker / engine-write selects (qkd_hr_keep_and3/and5, one per <= 30-bit chunk; the engine sends KW copies of
//         w_v), so no select drives more than 32 loads; same function, same cycle;
//     (d) the engine reset is two dedicated leaves of the clk_i reset bank u_rsi (same landing flop, same release edge).
//     RMW_EN 0 only (the read-return path stays absent); MUT 3/4 (engine QMUT) belong to the engine tile.

// Production native6-entry clock variant; allfour ingest entries are one
// compensated600MHz synchronous phasefamily. h/core crossings stay originalCDC.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_rom_host_ingest (stream ingest, 2026-10-08): the ROM dies' host-side block.  It puts the unchanged KV ingest
// engine (ot_hdc_kv_ingest) between a host link and the die's HBM write fabric, so a GPU-prefilled KV image (QKV /
// ROWS / IKEY descriptors) or any boot image (RAW: e.g. the Qwen embedding table in HBM, emb-hbm) lands in the
// attached HBM exactly where decode reads it.  Spec: claude-takeover-20261007/review_queue/ingest.md, the engine's
// own spec docs/ARCH_SPEC_QWEN3.md section 16 (R-P1..R-P5).
//
// Three clock domains, every crossing a Gray-pointer async FIFO (ot_link_afifo) or a toggle-qualified static CSR:
//   clk_h  host link user clock (PCIe / board-SerDes controller side).  Pin flops on every input and output.
//   clk_i  the ingest core clock.  The engine is OFF the token path, so it runs on a slow clock of its own (the
//          die's 1.2 GHz divided by 2 = 600 MHz, a separate CTS root, no clock gating): its 64 FP8 quantisers and
//          granule walk get 1.667 ns, and nothing in this domain times against the 833 ps die clock.
//   ck     the die core clock: the HBM write fabric face (sector words with credits), pin flops.
// Host stream (clk_h, valid + 2-b class + 512 b; the sender holds 2^HFA credits, h_crn returns freed entries):
//   class 0 CSR write  d[7:0] index, d[63:32] value:  0 = share (ingest sectors per die cycle x 256, 0 = unpaced;
//                      change it only while the block is idle), 1 = reserved;  2 = BOOT END: once the engine is idle
//                      (every sector of the descriptors before it has left the engine), one marker word goes out on the
//                      die face in order behind them: o_we 1, o_addr all ones (never a data sector), o_d[63:0] =
//                      d[127:64] (the emb-hbm BOOT_END {checksum[63:32], expected sectors[31:0]}).
//   Address convention (runtime): o_addr[31] = 0 the die's linear KV sector space (Qwen: PC = a[6:0], PC-local
//   sector = a >> 7, the decode map); o_addr[31] = 1 a static / boot region (Qwen: the embedding's logical sector E).
//   class 1 descriptor d[255:0] (the engine's 256-b descriptor).  The host sends a descriptor, then its payload;
//                      at most DQ (4) descriptors ahead of their payloads.
//   class 2 payload    one 512-b beat.
//   class 3 reserved   (fault).
// Completion stream (clk_h, t_v / t_d, one host credit t_cr per word taken; TCRED credits at reset):
//   {8'h01, 8'b0, tag[7:0], 8'b0, sectors written so far[31:0]} per fenced descriptor done (engine done_v);
//   {8'hFF, 48'b0, code[7:0]} once, on the first fault.
// Die face (ck): o_v / o_we / o_addr / o_d = one 32-B sector write (o_we 1) or an RMW sector read (o_we 0), sent
//   only against a downstream credit (OCRED at reset, o_cr returns one) and the share pacer; the read data returns
//   in request order on i_rv / i_rd.  RMW_EN 0: the read path is absent and an rmw descriptor is a fault.
// Fault codes (sticky, fail closed: after a fault the host stream is drained and dropped): 1 QKV descriptor with
//   QKV_EN 0, 2 rmw descriptor with RMW_EN 0, 3 reserved class, 4 host overflow (sender ignored credits),
//   5 completion FIFO overflow, 6 read-return overflow (die fabric returned more reads than issued).
// MUT (bench mutants, must FAIL): 1 flips bit 30 (element 0 exponent MSB) of the 7th payload beat; 2 reports done tags + 1.
// ---------------------------------------------------------------------------
module qkd_hr_ingest_cdc_shell #(
    // HKV-HROOT 10-18: CSR0 (share) crosses clk_i -> ck as a toggle event with a held payload. CSR_HOLD_ACK 1 (fork
    // default) holds the host-FIFO head of the next CSR0 write until ck has captured the previous one (csr_ack, two-flop
    // synchronised back): share_i is stable through every capture. Flow control sits only at the off-die host credit
    // boundary (CSR0 is host configuration, not a compiled per-token path). 0 = legacy: a legal 8-write credit burst
    // overwrote share_i before capture (rtl/test/qwen_host/tb_hkv_cdc_csr_temporal.sv FAIL witness).
    parameter integer CSR_HOLD_ACK=1,
    parameter integer QUIET_MUT=0,
    parameter integer AW     = 32,
    parameter integer HDMAX  = 128,
    parameter integer KVHMAX = 2,      // Qwen3-8B TP4: 8 KV heads / 4 dies
    parameter integer QKV_EN = 1,      // 0: ROWS / IKEY / RAW only (V4.1 dies), a QKV descriptor is a fault
    parameter integer RMW_EN = 0,
    parameter integer HFA    = 4,      // host receive FIFO, 2^HFA entries = the host's credits
    parameter integer OFA    = 4,      // request FIFO clk_i -> ck
    parameter integer RFA    = 4,      // read-return FIFO ck -> clk_i (= the RMW reads in flight)
    parameter integer CFA    = 4,      // completion FIFO clk_i -> clk_h
    parameter integer OCRED  = 8,      // die-fabric credits at reset
    parameter integer TCRED  = 4,      // host completion credits at reset
    parameter integer PCAP   = 16,     // pacer burst (sectors)
    parameter integer MUT    = 0,
    // sys-takeover 2026-10-09 (opt-in): ENG_TRIM = 1 with QKV_EN = 0 builds the engine without its QKV path (unreachable:
    // a QKV descriptor is failed closed above); APIPE = 1 registers the engine's stream address terms (ot_hdc_kv_ingest).
    parameter integer ENG_TRIM = 0,
    parameter integer APIPE  = 0,
    // QPIPE = 1 (qwen-1010/c 2026-10-10, qfd_io_host): the engine's pipelined, lane-banked QKV path (ot_hdc_kv_ingest
    // QPIPE).  It is write-only, so it implies RMW_EN 0 here (an rmw descriptor fails closed, code 2).  MUT 3 / 4 = the
    // engine's QMUT 1 (K lane bank) / 2 (stale slot fields).
    parameter integer NATIVE_ROWS=1,
    parameter integer QPIPE  = 2,
    parameter integer KW     = 20      // engine w_v copies (e_wv_c), one per ox_w chunk (<= 15 b)
) (
    input  wire              rst_n,
    // host link face
    input  wire              clk_h,
    input  wire              h_v,
    input  wire [1:0]        h_cls,
    input  wire [511:0]      h_d,
    output reg  [HFA:0]      h_crn,
    output reg               t_v,
    output reg  [63:0]       t_d,
    input  wire              t_cr,
    // ingest core clock
    input  wire              clk_i,
    // engine face (clk_i domain, to / from the engine tile qkd_hr_ingest_eng; direct wires, no pin registers)
    output wire [1:0]        e_rst_n,      // two dedicated u_rsi leaves (engine reset, same release edge as rn_i)
    output wire              e_dv,         // engine d_v
    output wire [255:0]      e_ddata,      // engine d_data (u_hxm read)
    output wire              e_inv_a,      // engine in_v      (kept copy a)
    output wire              e_inv_b,      // engine in_v__c1  (kept copy b)
    output wire [511:0]      e_indata,     // engine in_data (u_hxm read)
    output wire              e_wrdy_o,     // engine w_rdy
    input  wire              e_drdy,
    input  wire              e_inrdy,
    input  wire              e_wv,         // engine w_v (control / quiet loads)
    input  wire [KW-1:0]     e_wv_c,       // engine w_v copies (ox_w chunk selects)
    input  wire [AW-1:0]     e_waddr,
    input  wire [255:0]      e_wdata,
    input  wire              e_rv,
    input  wire [AW-1:0]     e_raddr,
    input  wire              e_done,       // engine done_v
    input  wire              e_done_a,     // engine done_v__c1 (cx_w[31:16] select)
    input  wire              e_done_c,     // engine done_v__c1 kept BUF copy (cx_w[15:0] select)
    input  wire              e_done_b,     // engine done_v__c2 (cx_w[63:32] select)
    input  wire [7:0]        e_tag,
    input  wire              e_busy,
    input  wire [31:0]       e_nsec,
    // die face
    input  wire              ck,
    output reg               o_v,
    output reg               o_we,
    output reg  [AW-1:0]     o_addr,
    output reg  [255:0]      o_d,
    input  wire              o_cr,
    input  wire              i_rv,
    input  wire [255:0]      i_rd,
    output wire              fault,
    output reg quiet_h,quiet_i,quiet_c
);
    // Independent actual source-domain debt observations, all registered.
    // FIFO empty/count are the implemented Gray-pointer FIFO observations.
    always @(posedge clk_h or negedge rn_h)
     if(!rn_h)quiet_h<=0;
     else quiet_h<=!h_v&&!hv_q&&hx_freed==0&&!t_v&&cx_empty&&tcr==TCRED&&!t_cr&&!tcr_q&&!fault_h;
    always @(posedge clk_i or negedge rn_i)
     if(!rn_i)quiet_i<=0;
     else quiet_i<=hx_empty&&!hx_pop&&(QUIET_MUT==1||!e_busy)&&!e_wv&&!e_rv&&!e_done&&!e_rdv&&
      !ox_wr&&outst==0&&rx_empty&&!rx_pop&&!cx_wr&&!f_any&&!hx_ovf_i&&!rx_ovf_i;
    always @(posedge ck or negedge rn_c)
     if(!rn_c)quiet_c<=0;
     else quiet_c<=ox_empty&&!ox_pop&&!o_v&&ocr==OCRED&&!o_cr&&!ocr_q&&!i_rv&&!irv_q&&!fault;
    // SQK-INGEST 10-21 (SAFE items 3 / 8): each domain's 2-stage reset synchroniser is the reviewed reset bank
    // (rtl/physical/ot_host_die_cdc_sram.sv ot_host_reset_bank: 1 landing flop -> RB_* KEPT identical leaves, same
    // 2-edge release as ot_reset_sync). The RTL uses leaf 0; synthesis (kit reset_relay_split, ot_rst_copies) spreads the
    // reset loads over the leaves at <= 32 each (the native census limit). Release edges unchanged.
    localparam integer RB_H = 4, RB_I = 20, RB_C = 4;   // u_rsi leaves 18 / 19 = engine reset (e_rst_n); local root outputs drive 5/21/5 ASR contacts; raw host_rst_n drives 2 ASR contacts per domain root (6 total)
    wire rn_h, rn_i, rn_c;
    wire [RB_H-1:0] rb_h;
    wire [RB_I-1:0] rb_i;
    wire [RB_C-1:0] rb_c;
    // NEW QUIESCENT_SYSTEM_RESET contract: raw async assertion, four local
    // release edges. Peers must flush old traffic AND credit returns before
    // rearm; this is not equivalent to the old core2 + local2 schedule.
    wire rst_root_h, rst_root_i, rst_root_c;
    ot_host_reset_bank #(.N(1)) u_rrh (.clk(clk_h), .async_rst_n(rst_n), .sync_rst_n(rst_root_h));
    ot_host_reset_bank #(.N(1)) u_rri (.clk(clk_i), .async_rst_n(rst_n), .sync_rst_n(rst_root_i));
    ot_host_reset_bank #(.N(1)) u_rrc (.clk(ck),    .async_rst_n(rst_n), .sync_rst_n(rst_root_c));
    ot_host_reset_bank #(.N(RB_H)) u_rsh (.clk(clk_h), .async_rst_n(rst_root_h), .sync_rst_n(rb_h));
    ot_host_reset_bank #(.N(RB_I)) u_rsi (.clk(clk_i), .async_rst_n(rst_root_i), .sync_rst_n(rb_i));
    ot_host_reset_bank #(.N(RB_C)) u_rsc (.clk(ck),    .async_rst_n(rst_root_c), .sync_rst_n(rb_c));
    assign rn_h = rb_h[0];
    assign rn_i = rb_i[0];
    assign rn_c = rb_c[0];
    assign e_rst_n = rb_i[19:18];
    // cross-domain nets (declared ahead of use)
    wire         hx_ovf_i, rx_ovf_i, ox_pop, cx_pop;
    reg          irv_q;
    reg  [255:0] ird_q;

    // =============================================================================================================
    // host face (clk_h): pin flops -> host receive FIFO
    // =============================================================================================================
    reg          hv_q;
    reg [1:0]    hc_q;
    reg [511:0]  hd_q;
    always @(posedge clk_h) begin hc_q <= h_cls; hd_q <= h_d; end
    always @(posedge clk_h or negedge rn_h) if (!rn_h) hv_q <= 1'b0; else hv_q <= h_v;
    wire         hx_full, hx_empty, hx_ovf;
    wire [HFA:0] hx_freed, hx_cnt;
    wire [513:0] hx_head;
    reg          hx_pop;
    initial if (HFA > 5 || OFA > 5 || AW + 257 > 546)
        $fatal(1, "qkd_hr_native_qm_cdc SRAM FIFOs: the 32 x 546 macro holds <= 32 entries of <= 546 b");
    wire         hx_nd;
    ot_link_afifo #(.W(1), .AW(HFA)) u_hx (
        .wclk(clk_h), .wrst_n(rn_h), .wr(hv_q), .wdata(1'b0), .wfull(hx_full), .wfreed(hx_freed), .ovf(hx_ovf),
        .rclk(clk_i), .rrst_n(rn_i), .rd(hx_pop), .rempty(hx_empty), .rdata(hx_nd), .rcount(hx_cnt));
    // shadow binary pointers = u_hx wbin / rbin (same resets, push = wr && !wfull, pop = rd && !rempty)
    reg  [HFA:0] hx_wp, hx_rp;
    wire         hx_push = hv_q && !hx_full;
    wire [HFA:0] hx_rp_i = hx_rp + ((hx_pop && !hx_empty) ? 1'b1 : 1'b0);
`ifdef QKD_HR_QM_SRAM_MUT
    wire [HFA:0] hx_rp_n = hx_rp;                               // bench mutant: the macro reads the current pointer
`else
    wire [HFA:0] hx_rp_n = hx_rp_i;
`endif
    always @(posedge clk_h or negedge rn_h) if (!rn_h) hx_wp <= 0; else if (hx_push) hx_wp <= hx_wp + 1'b1;
    always @(posedge clk_i or negedge rn_i) if (!rn_i) hx_rp <= 0; else hx_rp <= hx_rp_i;
    wire [545:0] hx_q;
    ot_sram_1r1w2c_32x546_m1_p192_mir u_hxm (.wclk(clk_h), .rclk(clk_i), .r_ce_in(1'b1),
        .r_addr_in(5'(hx_rp_n[HFA-1:0])), .rd_out(hx_q), .w_ce_in(hx_push), .w_addr_in(5'(hx_wp[HFA-1:0])),
        .wd_in({28'd0, hc_q, hc_q, hc_q, hd_q}), .w_mask_in({546{1'b1}}));
    // QKC-HROOT 10-21: the 2 class bits are stored THREE times in spare macro columns (513:512 / 515:514 / 517:516)
    // and each copy feeds one consumer group (accept / pop+CSR mark / CSR+fault): every macro read pin <= 32 loads
    // in the native32 primitive copy (a macro output cannot be replicated). Identical stored bits -> same behaviour.
    assign hx_head = hx_q[513:0];
    wire [1:0] hcl_b = hx_q[515:514], hcl_c = hx_q[517:516];
    always @(posedge clk_h or negedge rn_h) if (!rn_h) h_crn <= 0; else h_crn <= hx_freed;

    // =============================================================================================================
    // ingest core (clk_i)
    // =============================================================================================================
    reg  [7:0]   f_code;                    // first fault (sticky)
    wire         f_any = f_code != 8'd0;
    wire [1:0]   hcl = hx_head[513:512];
    wire [255:0] hdesc = hx_head[255:0];
    wire         dq_qkv = hdesc[3:0] == 4'd1;
    wire         bad_qkv = (QKV_EN == 0) && dq_qkv;
    wire         bad_rmw = (RMW_EN == 0 || QPIPE != 0) && dq_qkv && hdesc[6];
    // Native K/V rows require production CTX8192/HD128 descriptor strides.
    // Reduced-layout descriptors must not be silently reinterpreted.
    wire[31:0]native_kspan=(hdesc[219:216]==1)?32'd1179648:32'd2359296;
    wire bad_native=NATIVE_ROWS&&dq_qkv&&(
        hdesc[171:168]!=7||hdesc[219:216]<1||hdesc[219:216]>2||
        hdesc[111:80]!=32'd32768||hdesc[143:112]!=32'd32768||
        hdesc[47:16]>=native_kspan||hdesc[21:16]!=0||
        (hdesc[219:216]==2&&hdesc[31])||
        hdesc[79:48]!=(hdesc[47:16]+native_kspan));

    // engine face (the engine is the separate tile qkd_hr_ingest_eng; e_* are ports)
    // RMW_EN must be 0 (no read-return face) and MUT < 3 (engine mutants live in the engine tile)
    generate if (RMW_EN != 0 || MUT >= 3) begin : g_bad_cfg QKD_HR_INGEST_SHELL_RMW_EN0_ONLY refuse(); end endgenerate
    reg          e_rdv;
    reg  [255:0] e_rdd;
    wire         e_wrdy, e_rrdy;
    reg  [3:0]   pcnt;                      // payload beats seen (MUT 1)
    wire [511:0] pay = (MUT == 1 && pcnt == 4'd6) ? (hx_head[511:0] ^ (512'd1 << 30)) : hx_head[511:0];
    wire         hv_i = !hx_empty;
    wire         take_d = hv_i && !f_any && hcl == 2'd1 && !bad_qkv && !bad_rmw && !bad_native;
    wire         take_p = hv_i && !f_any && hcl == 2'd2;
    // engine inputs: d_v / d_data / in_v (two kept copies, the engine's in_v / in_v__c1) / in_data / w_rdy.
    // RMW_EN 0: r_rdy, rd_v, rd_data are the constants 0 (e_rrdy, e_rdv, e_rdd below), tied in the engine tile.
    assign e_dv = take_d;
    assign e_ddata = hdesc;
    assign e_indata = pay;
    assign e_wrdy_o = e_wrdy;
    qkd_hr_keep_and3 u_take_a (.a(hv_i), .b(!f_any), .c(hcl == 2'd2), .y(e_inv_a));
    qkd_hr_keep_and3 u_take_b (.a(hv_i), .b(!f_any), .c(hcl == 2'd2), .y(e_inv_b));
    always @(*) begin
        hx_pop = 1'b0;
        if (hv_i) begin
            if (f_any) hx_pop = 1'b1;                                   // fail closed: drain and drop
            else case (hcl_b)
                2'd0: hx_pop = (hx_head[7:0] == 8'd2) ? mark_go :
                              ((CSR_HOLD_ACK != 0 && hx_head[7:0] == 0) ? csr_ready : 1'b1);
                2'd1: hx_pop = (bad_qkv || bad_rmw || bad_native) ? 1'b1 : e_drdy;
                2'd2: hx_pop = e_inrdy;
                default: hx_pop = 1'b1;
            endcase
        end
    end
    // CSRs
    reg  [8:0]   share_i;
    reg          csr_tgl;
    reg          csr_ack;
    (* async_reg = "true" *) reg csr_ac1,csr_ac2;
    wire csr_ready = csr_tgl == csr_ac2;
    always @(posedge clk_i or negedge rn_i)
        if (!rn_i) begin csr_ac1<=0;csr_ac2<=0;end
        else begin csr_ac1<=csr_ack;csr_ac2<=csr_ac1;end
    reg          all_done;                  // reserved (bit 0 of CSR 1); completions follow the descriptor fence bit
    // request FIFO clk_i -> ck: {we, addr, data}; writes before reads, reads capped by the return FIFO
    wire         ox_full, ox_empty, ox_ovf;
    wire [OFA:0] ox_freed, ox_cnt;
    wire [AW+256:0] ox_head;
    reg  [RFA+1:0] outst;                   // RMW reads issued, not yet handed to the engine
    wire         rd_room = outst < (1 << RFA);
    // CSR 2 (boot end): one marker word, in order after every sector of the descriptors before it
    wire         csr_mark = hv_i && !f_any && hcl_b == 2'd0 && hx_head[7:0] == 8'd2;
    wire         mark_go = csr_mark && !e_busy && !e_wv && !e_rv && !ox_full;
    assign e_wrdy = !ox_full;
    assign e_rrdy = (RMW_EN != 0 && QPIPE == 0) && !e_wv && !ox_full && rd_room;
    wire         ox_wr = (e_wv && e_wrdy) || (e_rv && e_rrdy) || mark_go;
    // Preserve the optional marker region in bits65:64. Existing markers use
    // zero there and retain their exact low64 payload / RoPE dispatch behavior.
    // QKO-HROOT2: the 289-b request word selects on kept copies, one per KC-bit chunk: mark_c[k] = mark_go (same
    // function of the same nets) and e_wv_c[k] = the engine's k-th w_v copy; every select drives <= 2*KC loads.
    localparam integer OXW = AW + 257, KC = (OXW + KW - 1) / KW;
    generate if (KC > 15) begin : g_bad_kw QKD_HR_INGEST_SHELL_KW_TOO_SMALL refuse(); end endgenerate
    wire [AW+256:0] ox_mark = {1'b1, {AW{1'b1}}, 190'd0, hx_head[129:64]};
    wire [AW+256:0] ox_eng = {1'b1, e_waddr, e_wdata};
    wire [AW+256:0] ox_rd = {1'b0, e_raddr, 256'd0};
    wire [AW+256:0] ox_w;
    wire [KW-1:0]   mark_c;
    for (genvar k = 0; k < KW; k = k + 1) begin : g_oxw
        qkd_hr_keep_and5 u_mark (.a(csr_mark), .b(!e_busy), .c(!e_wv_c[k]), .d(!e_rv), .e(!ox_full), .y(mark_c[k]));
        for (genvar b = k * KC; b < (k + 1) * KC && b < OXW; b = b + 1) begin : g_b
            assign ox_w[b] = mark_c[k] ? ox_mark[b] : (e_wv_c[k] ? ox_eng[b] : ox_rd[b]);
        end
    end
    // read returns ck -> clk_i
    wire         rx_full, rx_empty, rx_ovf;
    wire [RFA:0] rx_freed, rx_cnt;
    wire [255:0] rx_head;
    wire         rx_pop = !rx_empty;
    // completions clk_i -> clk_h
    wire         cx_full, cx_empty, cx_ovf;
    wire [CFA:0] cx_freed, cx_cnt;
    wire [63:0]  cx_head;
    reg          cx_wr;
    reg  [63:0]  cx_w;
    reg          f_sent;
    always @(posedge clk_i or negedge rn_i) begin
        if (!rn_i) begin
            f_code <= 0; share_i <= 0; csr_tgl <= 1'b0; all_done <= 1'b0; pcnt <= 0; outst <= 0;
            e_rdv <= 1'b0; cx_wr <= 1'b0; f_sent <= 1'b0;
        end else begin
            if (hv_i && !f_any && hcl_c == 2'd0) begin
                if (hx_head[7:0] == 8'd0 && (CSR_HOLD_ACK == 0 || csr_ready)) begin
                    share_i <= hx_head[40:32]; csr_tgl <= ~csr_tgl;
                end
                if (hx_head[7:0] == 8'd1) all_done <= hx_head[32];
            end
            if (take_p && e_inrdy && pcnt != 4'd15) pcnt <= pcnt + 4'd1;
            // faults: the first one wins
            if (!f_any) begin
                if (hv_i && hcl_c == 2'd1 && bad_qkv)      f_code <= 8'd1;
                else if (hv_i && hcl_c == 2'd1 && bad_rmw) f_code <= 8'd2;
                else if (hv_i && hcl_c == 2'd1 && bad_native) f_code <= 8'd7;
                else if (hv_i && hcl_c == 2'd3)            f_code <= 8'd3;
                else if (hx_ovf_i)                        f_code <= 8'd4;
                else if (cx_ovf)                          f_code <= 8'd5;
                else if (rx_ovf_i)                        f_code <= 8'd6;
            end
            // read return: registered into the engine (it always accepts)
            e_rdv <= rx_pop;
            outst <= outst + ((e_rv && e_rrdy) ? 1 : 0) - (rx_pop ? 1 : 0);
            // completions: done words, then the fault word once
            cx_wr <= 1'b0;
            if (e_done) begin
                cx_wr <= 1'b1;
            end else if (f_any && !f_sent) begin
                cx_wr <= 1'b1; f_sent <= 1'b1;
            end
        end
    end
    // data-only registers (SQK-INGEST 10-21): no reset; their valids (e_rdv, cx_wr) are reset above
    always @(posedge clk_i) begin
        e_rdd <= rx_head;
        // QKO-HROOT2: loaded every edge; pushed only when cx_wr (= e_done, or the first f_any && !f_sent), exactly the
        // edges the enabled load used, so every word written into u_cx is identical. Halves select on done copies.
        cx_w[15:0]  <= e_done_c ? e_nsec[15:0] : {8'd0, f_code};
        cx_w[31:16] <= e_done_a ? e_nsec[31:16] : 16'd0;
        cx_w[63:32] <= e_done_b ? {8'h01, 8'd0, (MUT == 2) ? e_tag + 8'd1 : e_tag, 8'd0} : {8'hFF, 24'd0};
    end
    // overflow flags from the other domains, synchronised (sticky at their source)
    (* async_reg = "true" *) reg [1:0] hov_s, rov_s;
    assign hx_ovf_i = hov_s[1];
    assign rx_ovf_i = rov_s[1];
    // KV-CDC2: the sticky fault leaves clk_i only from registers, never from the f_code compare: f_any_q feeds the ck
    // synchroniser fs, f_any_h (its own sticky copy, one source register per synchroniser) feeds the clk_h synchroniser
    // fh_s, which replaces the die-clock fault_c in quiet_h
    reg f_any_q, f_any_h;
    always @(posedge clk_i or negedge rn_i)
        if (!rn_i) begin f_any_q <= 1'b0; f_any_h <= 1'b0; end
        else begin f_any_q <= f_any; f_any_h <= f_any_h | f_any; end
    (* async_reg = "true" *) reg [1:0] fh_s;
    wire fault_h = fh_s[1];
    always @(posedge clk_h or negedge rn_h) if (!rn_h) fh_s <= 2'b0; else fh_s <= {fh_s[0], f_any_h};
    always @(posedge clk_i or negedge rn_i)
        if (!rn_i) begin hov_s <= 0; rov_s <= 0; end
        else begin hov_s <= {hov_s[0], hx_ovf}; rov_s <= {rov_s[0], rx_ovf}; end

    wire         ox_nd;
    ot_link_afifo #(.W(1), .AW(OFA)) u_ox (
        .wclk(clk_i), .wrst_n(rn_i), .wr(ox_wr), .wdata(1'b0), .wfull(ox_full), .wfreed(ox_freed), .ovf(ox_ovf),
        .rclk(ck), .rrst_n(rn_c), .rd(ox_pop), .rempty(ox_empty), .rdata(ox_nd), .rcount(ox_cnt));
    reg  [OFA:0] ox_wp, ox_rp;
    wire         ox_push = ox_wr && !ox_full;
    wire [OFA:0] ox_rp_n = ox_rp + ((ox_pop && !ox_empty) ? 1'b1 : 1'b0);
    always @(posedge clk_i or negedge rn_i) if (!rn_i) ox_wp <= 0; else if (ox_push) ox_wp <= ox_wp + 1'b1;
    always @(posedge ck or negedge rn_c) if (!rn_c) ox_rp <= 0; else ox_rp <= ox_rp_n;
    wire [545:0] ox_q;
    ot_sram_1r1w2c_32x546_m1_p192_mir u_oxm (.wclk(clk_i), .rclk(ck), .r_ce_in(1'b1),
        .r_addr_in(5'(ox_rp_n[OFA-1:0])), .rd_out(ox_q), .w_ce_in(ox_push), .w_addr_in(5'(ox_wp[OFA-1:0])),
        .wd_in({{(546 - (AW + 257)){1'b0}}, ox_w}), .w_mask_in({546{1'b1}}));
    assign ox_head = ox_q[AW+256:0];
    generate if (RMW_EN != 0) begin : g_rx
        ot_link_afifo #(.W(256), .AW(RFA)) u_rx (
            .wclk(ck), .wrst_n(rn_c), .wr(irv_q), .wdata(ird_q), .wfull(rx_full), .wfreed(rx_freed), .ovf(rx_ovf),
            .rclk(clk_i), .rrst_n(rn_i), .rd(rx_pop), .rempty(rx_empty), .rdata(rx_head), .rcount(rx_cnt));
    end else begin : g_norx
        // RMW_EN 0: irv_q is constant 0, so the read-return FIFO is never written (empty, no overflow)
        assign rx_full = 1'b0; assign rx_empty = 1'b1; assign rx_ovf = 1'b0; assign rx_freed = 0; assign rx_cnt = 0;
        assign rx_head = 256'd0;
    end endgenerate
    // QKO-HROOT2: completion FIFO = the u_hx / u_ox pattern: 1-bit reviewed ot_link_afifo (Gray pointers, sync, full /
    // empty / freed / ovf) + shadow binary pointers + the third reviewed dual-clock SRAM u_cxm (write clk_i, read clk_h);
    // read address = next read pointer -> first-word fall-through, cycle-exact with the 64-b flop FIFO.
    generate if (CFA > 5) begin : g_bad_cfa QKD_HR_INGEST_SHELL_CFA_LE5 refuse(); end endgenerate
    wire         cx_nd;
    ot_link_afifo #(.W(1), .AW(CFA)) u_cx (
        .wclk(clk_i), .wrst_n(rn_i), .wr(cx_wr), .wdata(1'b0), .wfull(cx_full), .wfreed(cx_freed), .ovf(cx_ovf),
        .rclk(clk_h), .rrst_n(rn_h), .rd(cx_pop), .rempty(cx_empty), .rdata(cx_nd), .rcount(cx_cnt));
    reg  [CFA:0] cx_wp, cx_rp;
    wire         cx_push = cx_wr && !cx_full;
`ifdef QKD_HR_QM_CX_MUT
    wire [CFA:0] cx_rp_n = cx_rp;                               // bench mutant: u_cxm reads the current pointer
`else
    wire [CFA:0] cx_rp_n = cx_rp + ((cx_pop && !cx_empty) ? 1'b1 : 1'b0);
`endif
    always @(posedge clk_i or negedge rn_i) if (!rn_i) cx_wp <= 0; else if (cx_push) cx_wp <= cx_wp + 1'b1;
    always @(posedge clk_h or negedge rn_h) if (!rn_h) cx_rp <= 0; else cx_rp <= cx_rp_n;
    wire [545:0] cx_q;
    ot_sram_1r1w2c_32x546_m1_p192_mir u_cxm (.wclk(clk_i), .rclk(clk_h), .r_ce_in(1'b1),
        .r_addr_in(5'(cx_rp_n[CFA-1:0])), .rd_out(cx_q), .w_ce_in(cx_push), .w_addr_in(5'(cx_wp[CFA-1:0])),
        .wd_in({482'd0, cx_w}), .w_mask_in({546{1'b1}}));
    assign cx_head = cx_q[63:0];

    // =============================================================================================================
    // completion face (clk_h): host credits, pin flops
    // =============================================================================================================
    reg  [7:0] tcr;
    reg        tcr_q;
    assign     cx_pop = !cx_empty && tcr != 0;
    always @(posedge clk_h or negedge rn_h) begin
        if (!rn_h) begin t_v <= 1'b0; tcr <= TCRED; tcr_q <= 1'b0; end
        else begin
            tcr_q <= t_cr;
            tcr <= tcr + (tcr_q ? 8'd1 : 8'd0) - (cx_pop ? 8'd1 : 8'd0);
            t_v <= cx_pop;
        end
    end
    // data only, no reset (t_v is the valid); capture enable = kept copies of cx_pop, one per 16-b chunk
    wire [3:0] cx_pop_c;
    for (genvar k = 0; k < 4; k = k + 1) begin : g_tdc
        qkd_hr_keep_and3 u_pop (.a(!cx_empty), .b(tcr != 0), .c(1'b1), .y(cx_pop_c[k]));
        always @(posedge clk_h) if (cx_pop_c[k]) t_d[16*k +: 16] <= cx_head[16*k +: 16];
    end

    // =============================================================================================================
    // die face (ck): share CSR (toggle-qualified), pacer, credits, pin flops
    // =============================================================================================================
    (* async_reg = "true" *) reg [2:0] tg_s;
    reg  [8:0]  share_c;
    always @(posedge ck or negedge rn_c)
        if (!rn_c) begin tg_s <= 0; share_c <= 0; csr_ack <= 0; end
        else begin
            tg_s <= {tg_s[1:0], csr_tgl};
            if (CSR_HOLD_ACK != 0 ? tg_s[2] != csr_ack : tg_s[2] != tg_s[1]) begin
                share_c <= share_i;
                csr_ack <= tg_s[2];
            end
        end
    localparam integer PW = $clog2(PCAP * 256 + 512) + 1;
    reg  [PW-1:0] tok;
    reg  [7:0]    ocr;
    reg           ocr_q;
    wire          pace_ok = (share_c == 9'd0) || (tok >= 256);
    assign        ox_pop = !ox_empty && ocr != 0 && pace_ok;
    always @(posedge ck or negedge rn_c) begin
        if (!rn_c) begin
            o_v <= 1'b0; ocr <= OCRED; ocr_q <= 1'b0; tok <= 0;
        end else begin
            ocr_q <= o_cr;
            ocr <= ocr + (ocr_q ? 8'd1 : 8'd0) - (ox_pop ? 8'd1 : 8'd0);
            if (share_c == 9'd0) tok <= 0;
            else tok <= ((tok + share_c > PCAP * 256) ? PCAP * 256 : tok + share_c) - (ox_pop ? 256 : 0);
            o_v <= ox_pop;
        end
    end
    // data only, no reset (o_v is the valid)
    // QKO-HROOT2: the 289-b capture enable is a kept copy of ox_pop per 15-b chunk (same function of the same nets)
    localparam integer OPC = (AW + 257 + 14) / 15;
    wire          ocr_nz = ocr != 0;
    wire [OPC-1:0] ox_pop_c;
    reg  [AW+256:0] o_word;
    for (genvar k = 0; k < OPC; k = k + 1) begin : g_opc
        qkd_hr_keep_and3 u_pop (.a(!ox_empty), .b(ocr_nz), .c(pace_ok), .y(ox_pop_c[k]));
        for (genvar b = 15 * k; b < 15 * (k + 1) && b < AW + 257; b = b + 1) begin : g_b
            always @(posedge ck) if (ox_pop_c[k]) o_word[b] <= ox_head[b];
        end
    end
    always @(*) begin o_we = o_word[AW+256]; o_addr = o_word[AW+255:256]; o_d = o_word[255:0]; end
    always @(posedge ck) ird_q <= i_rd;
    always @(posedge ck or negedge rn_c) if (!rn_c) irv_q <= 1'b0; else irv_q <= i_rv && (RMW_EN != 0);
    // sticky fault, seen in the die domain
    (* async_reg = "true" *) reg [1:0] fs;
    reg         fault_c;
    always @(posedge ck or negedge rn_c)
        if (!rn_c) begin fs <= 0; fault_c <= 1'b0; end
        else begin fs <= {fs[0], f_any_q}; fault_c <= fault_c | fs[1]; end   // ox_ovf cannot happen (writes need !ox_full)
    assign fault = fault_c;
endmodule

// QKO-HROOT2 10-21: kept select copies. Synthesis: a chain of KEPT AND2x2 cells per instance (the only mapped cell the
// reviewed CDC elaboration admits), so neither opt_merge nor ABC folds the copies back into one driver; simulation: RTL.
module qkd_hr_keep_and3(input wire a, b, c, output wire y);
`ifdef SYNTHESIS
    wire m;
    (* keep *) AND2x2_ASAP7_75t_R u_a0 (.A(a), .B(b), .Y(m));
    (* keep *) AND2x2_ASAP7_75t_R u_a1 (.A(m), .B(c), .Y(y));
`else
    assign y = a & b & c;
`endif
endmodule
module qkd_hr_keep_and5(input wire a, b, c, d, e, output wire y);
`ifdef SYNTHESIS
    wire [2:0] m;
    (* keep *) AND2x2_ASAP7_75t_R u_a0 (.A(a), .B(b), .Y(m[0]));
    (* keep *) AND2x2_ASAP7_75t_R u_a1 (.A(m[0]), .B(c), .Y(m[1]));
    (* keep *) AND2x2_ASAP7_75t_R u_a2 (.A(m[1]), .B(d), .Y(m[2]));
    (* keep *) AND2x2_ASAP7_75t_R u_a3 (.A(m[2]), .B(e), .Y(y));
`else
    assign y = a & b & c & d & e;
`endif
endmodule
