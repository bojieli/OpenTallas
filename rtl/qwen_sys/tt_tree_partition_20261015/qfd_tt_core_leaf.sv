`timescale 1ns/1ps
module qfd_tt_core_leaf #(
    parameter integer DCU_M = 2, parameter integer DUC_M = 2,   // in-tile issue / status stations
    parameter integer XW = 24, parameter integer IS = 1, parameter integer OS = 1,
    // PSRAM = 1 (fe-push-qwen-1010, port of the seq_su_bi hardcore-1010 PSRAM; 0 = unchanged): the 64 x 1,024 program
    // store is two ot_sram_1r1w_64x512_m1_r2c2 macros (bit-masked 64-bit writes) instead of 65,536 flops; the read is
    // issued at the prog_re edge with the unregistered address, the macro output captured in prog_q one edge later = the
    // PRL 2 timing of the flop store (0 cycles).  Writes come from registered macro pins (valid, row, bank, one-hot
    // 64-bit slice) one edge after q_pw_v, as the flop store's registered selects.  Contract: the store is written
    // only while no program read of the same word is in flight (boot load; read-before-write macro).
    // PMUT = 1: bench negative control (the read issued one edge late, with the registered address).
    // HQ2 = 1: the controller's FIFO head as two words with a register-only fill enable (FQ_HEAD 2; seq_su fea/feb
    // f3e3d6b6f: feb TT +95.26 after fbb post-CTS -537 on st -> load -> hq_fill -> 1,024-b hq enable).
    // HQ2 = 2: bench negative control (FQ_HEAD 3: a third fill overwrites an unread head word).
    parameter integer PSRAM = 1, parameter integer PMUT = 0, parameter integer HQ2 = 1,
    parameter integer MEREG = 3,  // el1011-q-seq: registered engine clock enable (ctlm_mereg)
    parameter integer RRG = 1,    // el1011-q-seq: replicated tile reset (ctlm_rrg)
    parameter integer PCUT = 1,   // el1011-q-seq: exact controller path cuts (ctrl_pcut)
    // qwen-tp8/seq (2026-10-12): G = lane groups of the die (TP4 6,144; TP8 3,072 = 768 tiles in 3 bands).  It sets the
    // controller's G (dynamic attention rounds, ot_hdc_dyn_ttiles), the tree-top control's GT, and the G-sized ports:
    // NPG = G >> 7 scale groups, NPE = NPG / 4 argmax partials (p_am / p_fault: 2 per band), t_sel_e / t_tv_e
    // $clog2(G) + 1 bits.  The default elaborates to the unchanged TP4 block.
    parameter integer G = 3072,
    parameter integer TPMUT = 0,  // qwen-tp8/seq bench negative controls (0 = off): 1 = DYN_TTILES rounds at the TP4 literal
                                  //   G 6144 (:496-507 left), 2 = the controller instance at G 6144 (:1224 left)
    parameter integer AUD = 33975     // el1011-q-seq: textbook-audit rebuild (ctlm_aud) bits: 1 no x_addr, 2 SRAM tag delays, 4 kv pin flops, 16 die-input pin flops (not p_am), 32 kept output stations, 64 no engine idle clock gate (power; the ICG enable then = the registered supply word); 8 = SRAM one-short mutant; 128 exact prefix cuts (u_tt PK: KS progress subtract + registered u_ttag read; controller FKS: argmax-merge compare / add); 256 = PK negative control, 512 = FKS negative control; 1024 setup cuts SC (fpapk-4e9afc303 classes a-d, exact, 0 cycles: u_tt pre-scale compare from flops, mx write pre-decoded with a registered slot maximum, scale_addr 2-operand, 32 h_rd copies); negative controls 2048 (no rk forwarding), 4096 (>= for >), 8192 (offset without nbs), 16384 (h_rd copy 0 stuck); 32768 p_am pin register at the ctlm pin (coordinator 10-11: routed p_am -> argmax -58 ps, textbook class 3; the argmax loop +1 cycle: am_* / mx_* / idle one edge later, sequence unchanged), 65536 = its negative control (register without the +1 compensation)
) (
    input wire  clk,
    input wire  rst_n,
    output wire [(1+1+1+1+1+4+24+24+3*(18+1)+1+3+1+24+24)-1:0] scale_tag,
    output wire scale_v,
    output wire scale_rst_n,
    output wire [18-1:0] scale_t,

    output wire [XW-1:0] me_acc_o,
    output wire  me_idle_o,
    output wire [15:0] me_prog_o,
    input wire  up_fault,
    input wire [15:0] land_cnt,
    output wire [$clog2(G):0] t_sel_e,
    output wire [$clog2(G):0] t_tv_e,
    input wire [16-1:0] tr_fault,
    output wire  p_v_e2,
    output wire [113-1:0] p_f_e2,
    input wire [((G >> 7) / 4)*51-1:0] p_am,
    input wire [((G >> 7) / 4)-1:0] p_fault,
    input wire  fab_fault,
    output wire  ov,
    output wire  mx_we,
    output wire [24-1:0] mx_addr,
    output wire [16-1:0] mx_mask,
    output wire [16*32-1:0] mx_data,
    input wire [379:0] cmd,
    output wire [94:0] ret
);
    wire rs;
    assign scale_rst_n=rs;
    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk),.rst_n(rst_n),.rst_q(rs));
    // Static tree owns no duplicate/shadow instruction controller. Every assigned
    // production edge clocks the real engine; schedule violations fault upstream.
    wire ec=clk;
    wire up_fault_c, fab_fault_c; wire [15:0] land_cnt_c; wire [16-1:0] tr_fault_c;
    localparam integer NPE = (G >> 7) / 4, DPW = 34 + NPE;   // DPW: 47 at the TP4 default
    wire [NPE-1:0] p_fault_c;
    wire [DPW-1:0] dpin = {up_fault, land_cnt, tr_fault, p_fault, fab_fault};
    generate if ((AUD & 16) != 0) begin : g_dpin
        reg [DPW-1:0] dpin_q;    // AUD 16: die-input pin flops (status / count / fault inputs; p_am stays direct)
        always @(posedge clk) dpin_q <= dpin;
        assign {up_fault_c, land_cnt_c, tr_fault_c, p_fault_c, fab_fault_c} = dpin_q;
    end else begin : g_ddir
        assign {up_fault_c, land_cnt_c, tr_fault_c, p_fault_c, fab_fault_c} = dpin;
    end endgenerate
    wire [0:0] u_me_go;
    wire [17:0] u_me_i_nout;
    wire [17:0] u_me_i_tiles;
    wire [17:0] u_me_i_k;
    wire [0:0] u_me_i_wsrc;
    wire [23:0] u_me_i_wbase;
    wire [23:0] u_me_i_ts;
    wire [23:0] u_me_i_ks;
    wire [23:0] u_me_i_js;
    wire [23:0] u_me_i_xbase;
    wire [23:0] u_me_i_xks;
    wire [23:0] u_me_i_xjs;
    wire [23:0] u_me_i_xcs;
    wire [2:0] u_me_i_jsh;
    wire [3:0] u_me_i_split;
    wire [23:0] u_me_i_wcs;
    wire [0:0] u_me_i_round;
    wire [23:0] u_me_i_obase;
    wire [23:0] u_me_i_ots;
    wire [23:0] u_me_i_ojs;
    wire [0:0] u_me_i_mmode;
    wire [0:0] u_me_i_oen;
    wire [0:0] u_me_i_amax;
    wire [0:0] u_me_i_rmax;
    wire [23:0] u_me_i_mbase;
    wire [0:0] u_me_ready;
    wire [0:0] u_me_idle;
    wire [0:0] u_me_wrom_re;
    wire [23:0] u_me_wrom_addr;
    wire [17:0] u_me_am_idx;
    wire [31:0] u_me_am_val;
    wire [0:0] u_me_am_any;
    wire [15:0] u_me_progress;
    wire [0:0] u_me_fault;
    reg [379:1] cmd_data;
    reg cmd_go;
    always @(posedge ec) cmd_data<=cmd[379:1];
    always @(posedge ec or negedge rs) if(!rs) cmd_go<=0; else cmd_go<=cmd[0];
    wire [379:0] cq_raw={cmd_data,cmd_go};
`ifdef OT_TT_SPLIT_MUT
    wire [379:0] cq=cq_raw ^ (cmd_go ? ({380{1'b0}} | (380'd1 << 19)) : 380'd0);
`else
    wire [379:0] cq=cq_raw;
`endif
    assign {u_me_i_mbase, u_me_i_rmax, u_me_i_amax, u_me_i_oen, u_me_i_mmode, u_me_i_ojs, u_me_i_ots, u_me_i_obase, u_me_i_round, u_me_i_wcs, u_me_i_split, u_me_i_jsh, u_me_i_xcs, u_me_i_xjs, u_me_i_xks, u_me_i_xbase, u_me_i_js, u_me_i_ks, u_me_i_ts, u_me_i_wbase, u_me_i_wsrc, u_me_i_k, u_me_i_tiles, u_me_i_nout, u_me_go} = cq;
    reg [94:0] ret_q;
    always @(posedge ec or negedge rs) if(!rs) ret_q<=0; else ret_q<={u_me_fault, u_me_progress, u_me_am_any, u_me_am_val, u_me_am_idx, u_me_wrom_addr, u_me_wrom_re, u_me_idle, u_me_ready};
    assign ret=ret_q;
    ot_qwen_tt_core_ctl #(.W(16), .IL(8), .AW(24), .NW(18), .GT(G), .TG(4), .SMIN(7), .SMAX(11), .TCUT(7), .XD(105), .XVM(15), .ORD(7), .ACC_LAT(7), .TREE_LAT(7), .MUL_LAT(6), .FAST_ISSUE(1), .KV_PREP(3), .SCALE_LAT(6), .LANDED(1), .BAND(1), .LNK(0), .CLNK(0), .AMR(1), .SPRE(2), .IS(0), .OS(OS), .XADDR(((AUD & 1) != 0) ? 0 : 1), .RDMEM(((AUD & 8) != 0) ? 2 : ((AUD & 2) != 0) ? 1 : 0), .OKEEP(((AUD & 32) != 0) ? 1 : 0), .PK(((AUD & 256) != 0) ? 2 : ((AUD & 128) != 0) ? 1 : 0), .SC(((AUD & 1024) != 0) ? (1 | ((AUD >> 10) & 14)) : 0), .AMI(((AUD & 65536) != 0) ? 2 : ((AUD & 32768) != 0) ? 1 : 0)) u_tt (
        .clk(ec), .rst_n(rs), .up_fault(up_fault_c), .land_cnt(land_cnt_c), .go(u_me_go), .ready(u_me_ready),
        .idle(u_me_idle), .i_nout(u_me_i_nout), .i_tiles(u_me_i_tiles), .i_k(u_me_i_k), .i_wsrc(u_me_i_wsrc), .i_wbase(u_me_i_wbase), .i_ts(u_me_i_ts), .i_ks(u_me_i_ks), .i_js(u_me_i_js), .i_xbase(u_me_i_xbase), .i_xks(u_me_i_xks), .i_xjs(u_me_i_xjs), .i_xcs(u_me_i_xcs), .i_jsh(u_me_i_jsh), .i_split(u_me_i_split), .i_wcs(u_me_i_wcs), .i_round(u_me_i_round), .i_obase(u_me_i_obase), .i_ots(u_me_i_ots), .i_ojs(u_me_i_ojs), .i_mmode(u_me_i_mmode), .i_oen(u_me_i_oen), .i_amax(u_me_i_amax), .i_rmax(u_me_i_rmax), .i_mbase(u_me_i_mbase),
        .wrom_re(u_me_wrom_re), .wrom_addr(u_me_wrom_addr), .kv_re(),
        .scale_tag(scale_tag), .scale_v(scale_v), .scale_t(scale_t),
        .x_dv(), .x_dc(), .x_dcs(), .x_dsp(),
        .t_sel_e(t_sel_e), .t_tv_e(t_tv_e), .tr_fault(tr_fault_c),
        .p_v_e2(p_v_e2), .p_f_e2(p_f_e2), .p_am(p_am), .p_fault(p_fault_c), .fab_fault(fab_fault_c),
        .ov(ov), .am_idx(u_me_am_idx), .am_val(u_me_am_val), .am_any(u_me_am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .progress(u_me_progress), .fault(u_me_fault));
    reg [XW-1:0] me_acc;
    always @(posedge ec or negedge rs) if(!rs) me_acc<=0; else if(u_me_go) me_acc<=me_acc+1'b1;
    ot_hdc_delay #(.W(XW+17),.D(OS),.RESET(1)) u_snap(.clk(clk),.rst_n(rs),.d({me_acc,u_me_idle,u_me_progress}),.q({me_acc_o,me_idle_o,me_prog_o}));
endmodule
