`timescale 1ns/1ps
module qfd_tt_tree_partition #(parameter integer MUT=0,
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
    input wire ck_core, input wire ck_scale,
    input wire  rst_n,
    output wire [XW-1:0] me_acc_o,
    output wire  me_idle_o,
    output wire [15:0] me_prog_o,
    input wire  up_fault,
    input wire [15:0] land_cnt,
    output wire  scale_re,
    output wire [(G >> 7)-1:0] scale_gre,
    output wire [(G >> 7)*24-1:0] scale_addr,
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
    wire [166:0] scale_tag; wire scale_v; wire [17:0] scale_t; wire scale_rst_n;
    qfd_tt_core_leaf u_core(.clk(ck_core),
      .rst_n(rst_n),.me_acc_o(me_acc_o),.me_idle_o(me_idle_o),.me_prog_o(me_prog_o),.up_fault(up_fault),.land_cnt(land_cnt),.t_sel_e(t_sel_e),.t_tv_e(t_tv_e),.tr_fault(tr_fault),.p_v_e2(p_v_e2),.p_f_e2(p_f_e2),.p_am(p_am),.p_fault(p_fault),.fab_fault(fab_fault),.ov(ov),.mx_we(mx_we),.mx_addr(mx_addr),.mx_mask(mx_mask),.mx_data(mx_data),.cmd(cmd),.ret(ret),
      .scale_tag(scale_tag),.scale_v(scale_v),.scale_t(scale_t),.scale_rst_n(scale_rst_n));
    wire [166:0] scale_tag_m=scale_tag ^ ((MUT==1) ? 167'd1 : 167'd0);
    generate if(MUT==2)begin:g_mut_station
      ot_qwen_tt_scale_body u_scale(.clk(ck_scale),.rst_n(scale_rst_n),.s3_tag(scale_tag_m),
        .s3_v(scale_v),.s3_t(scale_t),.scale_re(scale_re),.scale_gre(scale_gre),.scale_addr(scale_addr));
    end else begin:g_scale
      qfd_tt_scale_leaf u_scale(.clk(ck_scale),.rst_n(scale_rst_n),.s3_tag(scale_tag_m),
        .s3_v(scale_v),.s3_t(scale_t),.scale_re(scale_re),.scale_gre(scale_gre),.scale_addr(scale_addr));
    end endgenerate
endmodule
