// ot_hgi_seq_split.sv -- wires-only parent of the R25GQ sequencer split (el1013-hbm-seq-split, 2026-10-13).
// Same parameters and ports as ot_hgi_seq; three hardened children (own reset synchroniser each) and the five
// registered seams of ot_hgi_seq_seam.svh.  NO flop, NO gate here: every seam net is child TX flop -> child RX flop.
// Child placement on the 347.76 x 272.16 slot: FE (0, 0) 248.4 x 211.68, BE (259.2, 0) 88.56 x 211.68, AU (0, 216) 347.76 x 56.16.
`default_nettype none
module ot_hgi_seq_split #(
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
    output wire [17:0]   vr_addr,
    input  wire          vr_rsp_v,
    input  wire [31:0]   vr_rsp_data,
    // unit dispatch (index = HGI unit code; CTL = 0 is internal)
    output wire [15:0]   u_v,
    input  wire [15:0]   u_rdy,
    output wire [127:0]  d_hdr,
    output wire [255:0]  d_sut,
    output wire [1791:0] d_desc,         // {I, R, O, D, C, B, A} effective
    output wire [146:0]  d_n,            // 7 x 21-bit effective n, A in bits 20:0
    output wire [20:0]   d_pos1,
    output wire [20:0]   d_pslot1,
    output wire [15:0]   d_L,
    output wire [15:0]   d_L1,
    input  wire [15:0]   u_done,         // retire pulses (one per dispatched record)
    input  wire [15:0]   u_fault,
    input  wire          wr_quiet,       // every posted HBM write is visible
    // completion {token, pos, job, gen, status, cycles}
    output wire          cpl_v,
    input  wire          cpl_rdy,
    output wire [17:0]   cpl_token,
    output wire [19:0]   cpl_pos,
    output wire [31:0]   cpl_job,
    output wire [3:0]    cpl_gen,
    output wire [3:0]    cpl_status,
    output wire [31:0]   cpl_cycles,    // = {cc_hi, cc_lo} (combinational copy of two flop halves)
    // CTL.TOKX (Q-MTP-1, hbm-forks 2026-10-09): the committed tokens of the step, up to 16, carried on the completion
    output wire          cpl_tokx       // 1: this completion beat is a CTL.TOKX committed token (status 0), END follows
);
    localparam integer QB = (QD <= 2) ? 1 : $clog2(QD);
    wire            be_jl_v;    // be -> fe, au
    wire [1:0]      be_jl_entry;    // be -> fe
    wire [3:0]      be_jl_kernel;    // be -> fe
    wire [31:0]     be_jl_loff;    // be -> fe
    wire [19:0]     be_jl_pos;    // be -> fe, au
    wire            be_js;    // be -> fe, au
    wire            be_stop;    // be -> fe
    wire            be_qpop;    // be -> fe
    wire            be_lv_v;    // be -> fe
    wire [15:0]     be_lv_cnt;    // be -> fe
    wire            be_inj_hold;    // be -> fe
    wire            fe_kz;    // fe -> be
    wire            au_tbl_ok;    // au -> fe
    wire            fe_s1_v;    // fe -> au
    wire [39:0]     fe_s1_base;    // fe -> au
    wire [31:0]     fe_s1_lstr;    // fe -> au
    wire [31:0]     fe_s1_l1str;    // fe -> au
    wire [31:0]     fe_s1_str;    // fe -> au
    wire [26:0]     fe_s1_dmul;    // fe -> au
    wire [5:0]      fe_s1_dsel;    // fe -> au
    wire [5:0]      fe_s1_nsel;    // fe -> au
    wire [19:0]     fe_s1_n;    // fe -> au
    wire            fe_s1_idx;    // fe -> au
    wire [1:0]      fe_s1_sp;    // fe -> au
    wire [15:0]     fe_s1_L;    // fe -> au
    wire [15:0]     fe_s1_L1;    // fe -> au
    wire [2:0]      fe_s1_slot;    // fe -> au
    wire [2:0]      fe_s1_j;    // fe -> au
    wire [QB-1:0]   fe_s1_tag;    // fe -> au
    wire            fe_s1_last;    // fe -> au
    wire            fe_s1_isI;    // fe -> au
    wire            fe_s1_hi;    // fe -> au
    wire            fe_s1_et;    // fe -> au
    wire [2:0]      fe_hslot;    // fe -> au
    wire            fe_s2a_v;    // fe -> be
    wire [QB-1:0]   fe_s2a_tag;    // fe -> be
    wire [127:0]    fe_s2a_hdr;    // fe -> be
    wire [2:0]      fe_s2a_kind;    // fe -> be
    wire            fe_s2a_rdy0;    // fe -> be
    wire [15:0]     fe_s2a_L;    // fe -> be
    wire [15:0]     fe_s2a_L1;    // fe -> be
    wire            fe_s2i_v;    // fe -> be
    wire [255:0]    fe_s2i_d;    // fe -> be
    wire [QB-1:0]   fe_s2i_tag;    // fe -> be
    wire [2:0]      fe_s2i_slot;    // fe -> be
    wire            fe_s2i_sut;    // fe -> be
    wire            fe_s2i_np0;    // fe -> be
    wire [17:0]     be_jl_token;    // be -> au
    wire            be_s4_v;    // be -> au
    wire [23:0]     be_s4_ph;    // be -> au
    wire [39:0]     be_s4_base;    // be -> au
    wire [26:0]     be_s4_dmul;    // be -> au
    wire [1:0]      be_s4_sp;    // be -> au
    wire [31:0]     be_s4_x;    // be -> au
    wire [2:0]      be_s4_j;    // be -> au
    wire [QB-1:0]   be_s4_tag;    // be -> au
    wire            au_s3_v;    // au -> be
    wire            au_s3_be;    // au -> be
    wire [QB-1:0]   au_s3_tag;    // au -> be
    wire [2:0]      au_s3_j;    // au -> be
    wire            au_s3_last;    // au -> be
    wire            au_s3_isI;    // au -> be
    wire [63:0]     au_s3_acc;    // au -> be
    wire [20:0]     au_s3_n;    // au -> be
    wire            au_s3_px;    // au -> be
    wire            au_s3_pn;    // au -> be
    wire            au_s3_flt;    // au -> be
    wire            au_s3_badd;    // au -> be
    wire [17:0]     au_s3_iax;    // au -> be
    wire            au_s3_ixb;    // au -> be
    wire [17:0]     au_s3_ian;    // au -> be
    wire            au_s3_inb;    // au -> be
    wire            au_s3_ihbm;    // au -> be
    ot_hgi_seq_fe
`ifndef OT_HGI_SEQ_HARD            // hardened children (ref_tile cluster) are built at the routed parameters
        #(.RW(RW), .NOS(NOS), .USE_MACRO(USE_MACRO), .DS_TPL(DS_TPL), .DS_WIN(DS_WIN), .DS_SCAN(DS_SCAN), .DS_TOPK(DS_TOPK), .DS_HDL(DS_HDL), .QD(QD), .FD(FD), .IKS_I(IKS_I))
`endif
        u_fe (
        .clk(clk),
        .rst_n(rst_n),
        .md_d(md_d),
        .md_k(md_k),
        .f_req_v(f_req_v),
        .f_req_rdy(f_req_rdy),
        .f_req_addr(f_req_addr),
        .f_rsp_v(f_rsp_v),
        .f_rsp_data(f_rsp_data),
        .be_jl_v(be_jl_v),
        .be_jl_entry(be_jl_entry),
        .be_jl_kernel(be_jl_kernel),
        .be_jl_loff(be_jl_loff),
        .be_jl_pos(be_jl_pos),
        .be_js(be_js),
        .be_stop(be_stop),
        .be_qpop(be_qpop),
        .be_lv_v(be_lv_v),
        .be_lv_cnt(be_lv_cnt),
        .be_inj_hold(be_inj_hold),
        .fe_kz(fe_kz),
        .au_tbl_ok(au_tbl_ok),
        .fe_s1_v(fe_s1_v),
        .fe_s1_base(fe_s1_base),
        .fe_s1_lstr(fe_s1_lstr),
        .fe_s1_l1str(fe_s1_l1str),
        .fe_s1_str(fe_s1_str),
        .fe_s1_dmul(fe_s1_dmul),
        .fe_s1_dsel(fe_s1_dsel),
        .fe_s1_nsel(fe_s1_nsel),
        .fe_s1_n(fe_s1_n),
        .fe_s1_idx(fe_s1_idx),
        .fe_s1_sp(fe_s1_sp),
        .fe_s1_L(fe_s1_L),
        .fe_s1_L1(fe_s1_L1),
        .fe_s1_slot(fe_s1_slot),
        .fe_s1_j(fe_s1_j),
        .fe_s1_tag(fe_s1_tag),
        .fe_s1_last(fe_s1_last),
        .fe_s1_isI(fe_s1_isI),
        .fe_s1_hi(fe_s1_hi),
        .fe_s1_et(fe_s1_et),
        .fe_hslot(fe_hslot),
        .fe_s2a_v(fe_s2a_v),
        .fe_s2a_tag(fe_s2a_tag),
        .fe_s2a_hdr(fe_s2a_hdr),
        .fe_s2a_kind(fe_s2a_kind),
        .fe_s2a_rdy0(fe_s2a_rdy0),
        .fe_s2a_L(fe_s2a_L),
        .fe_s2a_L1(fe_s2a_L1),
        .fe_s2i_v(fe_s2i_v),
        .fe_s2i_d(fe_s2i_d),
        .fe_s2i_tag(fe_s2i_tag),
        .fe_s2i_slot(fe_s2i_slot),
        .fe_s2i_sut(fe_s2i_sut),
        .fe_s2i_np0(fe_s2i_np0)
    );
    ot_hgi_seq_au
`ifndef OT_HGI_SEQ_HARD            // hardened children (ref_tile cluster) are built at the routed parameters
        #(.RW(RW), .NOS(NOS), .USE_MACRO(USE_MACRO), .DS_TPL(DS_TPL), .DS_WIN(DS_WIN), .DS_SCAN(DS_SCAN), .DS_TOPK(DS_TOPK), .DS_HDL(DS_HDL), .QD(QD), .FD(FD), .IKS_I(IKS_I))
`endif
        u_au (
        .clk(clk),
        .rst_n(rst_n),
        .rank(rank),
        .be_jl_v(be_jl_v),
        .be_jl_pos(be_jl_pos),
        .be_jl_token(be_jl_token),
        .be_js(be_js),
        .au_tbl_ok(au_tbl_ok),
        .fe_s1_v(fe_s1_v),
        .fe_s1_base(fe_s1_base),
        .fe_s1_lstr(fe_s1_lstr),
        .fe_s1_l1str(fe_s1_l1str),
        .fe_s1_str(fe_s1_str),
        .fe_s1_dmul(fe_s1_dmul),
        .fe_s1_dsel(fe_s1_dsel),
        .fe_s1_nsel(fe_s1_nsel),
        .fe_s1_n(fe_s1_n),
        .fe_s1_idx(fe_s1_idx),
        .fe_s1_sp(fe_s1_sp),
        .fe_s1_L(fe_s1_L),
        .fe_s1_L1(fe_s1_L1),
        .fe_s1_slot(fe_s1_slot),
        .fe_s1_j(fe_s1_j),
        .fe_s1_tag(fe_s1_tag),
        .fe_s1_last(fe_s1_last),
        .fe_s1_isI(fe_s1_isI),
        .fe_s1_hi(fe_s1_hi),
        .fe_s1_et(fe_s1_et),
        .fe_hslot(fe_hslot),
        .be_s4_v(be_s4_v),
        .be_s4_ph(be_s4_ph),
        .be_s4_base(be_s4_base),
        .be_s4_dmul(be_s4_dmul),
        .be_s4_sp(be_s4_sp),
        .be_s4_x(be_s4_x),
        .be_s4_j(be_s4_j),
        .be_s4_tag(be_s4_tag),
        .au_s3_v(au_s3_v),
        .au_s3_be(au_s3_be),
        .au_s3_tag(au_s3_tag),
        .au_s3_j(au_s3_j),
        .au_s3_last(au_s3_last),
        .au_s3_isI(au_s3_isI),
        .au_s3_acc(au_s3_acc),
        .au_s3_n(au_s3_n),
        .au_s3_px(au_s3_px),
        .au_s3_pn(au_s3_pn),
        .au_s3_flt(au_s3_flt),
        .au_s3_badd(au_s3_badd),
        .au_s3_iax(au_s3_iax),
        .au_s3_ixb(au_s3_ixb),
        .au_s3_ian(au_s3_ian),
        .au_s3_inb(au_s3_inb),
        .au_s3_ihbm(au_s3_ihbm)
    );
    ot_hgi_seq_be
`ifndef OT_HGI_SEQ_HARD            // hardened children (ref_tile cluster) are built at the routed parameters
        #(.RW(RW), .NOS(NOS), .USE_MACRO(USE_MACRO), .DS_TPL(DS_TPL), .DS_WIN(DS_WIN), .DS_SCAN(DS_SCAN), .DS_TOPK(DS_TOPK), .DS_HDL(DS_HDL), .QD(QD), .FD(FD), .IKS_I(IKS_I))
`endif
        u_be (
        .clk(clk),
        .rst_n(rst_n),
        .cfg_vocab(cfg_vocab),
        .cfg_ctx_max(cfg_ctx_max),
        .hold(hold),
        .busy(busy),
        .db_v(db_v),
        .db_rdy(db_rdy),
        .db_token(db_token),
        .db_pos(db_pos),
        .db_job(db_job),
        .db_gen(db_gen),
        .db_entry(db_entry),
        .db_ncol(db_ncol),
        .db_kernel(db_kernel),
        .db_loff(db_loff),
        .vr_v(vr_v),
        .vr_rdy(vr_rdy),
        .vr_addr(vr_addr),
        .vr_rsp_v(vr_rsp_v),
        .vr_rsp_data(vr_rsp_data),
        .u_v(u_v),
        .u_rdy(u_rdy),
        .d_hdr(d_hdr),
        .d_sut(d_sut),
        .d_desc(d_desc),
        .d_n(d_n),
        .d_pos1(d_pos1),
        .d_pslot1(d_pslot1),
        .d_L(d_L),
        .d_L1(d_L1),
        .u_done(u_done),
        .u_fault(u_fault),
        .wr_quiet(wr_quiet),
        .cpl_v(cpl_v),
        .cpl_rdy(cpl_rdy),
        .cpl_token(cpl_token),
        .cpl_pos(cpl_pos),
        .cpl_job(cpl_job),
        .cpl_gen(cpl_gen),
        .cpl_status(cpl_status),
        .cpl_cycles(cpl_cycles),
        .cpl_tokx(cpl_tokx),
        .be_jl_v(be_jl_v),
        .be_jl_entry(be_jl_entry),
        .be_jl_kernel(be_jl_kernel),
        .be_jl_loff(be_jl_loff),
        .be_jl_pos(be_jl_pos),
        .be_jl_token(be_jl_token),
        .be_js(be_js),
        .be_stop(be_stop),
        .be_qpop(be_qpop),
        .be_lv_v(be_lv_v),
        .be_lv_cnt(be_lv_cnt),
        .be_inj_hold(be_inj_hold),
        .fe_kz(fe_kz),
        .fe_s2a_v(fe_s2a_v),
        .fe_s2a_tag(fe_s2a_tag),
        .fe_s2a_hdr(fe_s2a_hdr),
        .fe_s2a_kind(fe_s2a_kind),
        .fe_s2a_rdy0(fe_s2a_rdy0),
        .fe_s2a_L(fe_s2a_L),
        .fe_s2a_L1(fe_s2a_L1),
        .fe_s2i_v(fe_s2i_v),
        .fe_s2i_d(fe_s2i_d),
        .fe_s2i_tag(fe_s2i_tag),
        .fe_s2i_slot(fe_s2i_slot),
        .fe_s2i_sut(fe_s2i_sut),
        .fe_s2i_np0(fe_s2i_np0),
        .au_s3_v(au_s3_v),
        .au_s3_be(au_s3_be),
        .au_s3_tag(au_s3_tag),
        .au_s3_j(au_s3_j),
        .au_s3_last(au_s3_last),
        .au_s3_isI(au_s3_isI),
        .au_s3_acc(au_s3_acc),
        .au_s3_n(au_s3_n),
        .au_s3_px(au_s3_px),
        .au_s3_pn(au_s3_pn),
        .au_s3_flt(au_s3_flt),
        .au_s3_badd(au_s3_badd),
        .au_s3_iax(au_s3_iax),
        .au_s3_ixb(au_s3_ixb),
        .au_s3_ian(au_s3_ian),
        .au_s3_inb(au_s3_inb),
        .au_s3_ihbm(au_s3_ihbm),
        .be_s4_v(be_s4_v),
        .be_s4_ph(be_s4_ph),
        .be_s4_base(be_s4_base),
        .be_s4_dmul(be_s4_dmul),
        .be_s4_sp(be_s4_sp),
        .be_s4_x(be_s4_x),
        .be_s4_j(be_s4_j),
        .be_s4_tag(be_s4_tag)
    );
endmodule
`default_nettype wire
