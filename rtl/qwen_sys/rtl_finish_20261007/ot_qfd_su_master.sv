`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Die master qfd_sp_su64_sfu re-cut from the split-exact partition (qwen-rtl-finish 2026-10-07; successor of the
// qwen-missing ot_qfd_sp_su64_sfu, which stationed every port).
//
//   control ports   go, the NEXT fields, the per-op embedding selector a_src and the token: IS input stations;
//                   ready / idle / progress / rows / fault / obs_active / obs_inflight / the kv write copy: OS output
//                   stations (the controller's ot_qfd_issue_shell absorbs RT = DCU + DUC, crossing classes A-C).
//   VM ports        va / vb / vc reads, the lane writes and the reducer write: NO stations -- the SU and the vector
//                   memory are abutted (tools/qwen_rom_fulldie_b3r2.py su_vm_abut).  The VM answers one edge after
//                   the strobe, as in the token bench.
//   constant ROM    crom_re / crom_addr leave through OS stations and crom_q enters through IS stations: the read
//                   crosses the spine channel (the constant ROM is not adjacent to the SU).  The lanes take every
//                   memory ML = OS + IS + CRX edges later than the base (ot_hdc_vstream_lane ML, CRX = the ROM's
//                   own extra pipeline / relay edges outside this master); the abutted VM answers are delayed ML
//                   inside this master so every operand of an element meets at S1 again.  Values are those of the
//                   base; the stream unit's element latency grows by ML (its writes, reduction and retire move ML
//                   edges later; inflight / idle count them, so the controller's ordering rules hold unchanged).
//   embedding       the INT8 embedding decode (ot_hdc_core_vector_weight g_int8_embed, split-exact class D) sits
//                   here with a token ROW BUFFER: an a_src op's go is held while the 64 code words and the BF16 row
//                   scale of the token are fetched from the embedding ROM (credit / valid request, in-order valid
//                   response: ot_qfd_io_embedding_rom), then released with its fields; the decode reads the buffer
//                   with the ROM's one-edge registered contract.  A token already buffered is not fetched again.
//                   While a go is held the master reports obs_active = 1 and idle = 0 (the shell's rebuilt ready
//                   stays low), so no second go is issued to a busy unit.  FULLSHAPE (token-addressed rows) only.
// MUT = 1 (bench mutant): flips constant-ROM bit 0 of lane 0 at the input station.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_su_embed_pf #(
    parameter integer SW = 64,
    parameter integer AW = 24,
    parameter integer NW = 18,
    parameter integer HID = 4096,
    parameter integer EMB_CODE_LANES = 64,
    parameter integer EMB_ADDR_BASE = 0,
    parameter integer CRD = 4,              // request credits the embedding ROM grants (its request FIFO depth)
    parameter integer FI = 1                // width of the held instruction fields
) (
    input  wire              clk,
    input  wire              rst_n,
    // issue in (stationed) and out (to the stream unit)
    input  wire              go_in,
    input  wire              a_src,
    input  wire [NW-1:0]     tok,
    input  wire [FI-1:0]     f_in,
    output wire              go_out,
    output wire [FI-1:0]     f_out,
    output wire              pend,          // a go is held for a row fetch
    // the stream unit's va port and the VM's
    input  wire [SW-1:0]     su_va_re,
    input  wire [SW*AW-1:0]  su_va_addr,
    output wire [SW*32-1:0]  su_va_q,       // one edge after su_va_re (the caller delays it ML more)
    output wire [SW-1:0]     va_re,
    output wire [SW*AW-1:0]  va_addr,
    input  wire [SW*32-1:0]  va_q,
    // embedding ROM requests (credit) and responses (in order)
    output reg               ea_v,
    output reg               ea_kind,       // 0 code word, 1 row scale
    output reg  [AW-1:0]     ea_addr,
    input  wire              ea_cr,
    input  wire              eq_v,
    input  wire [511:0]      eq_data,
    output reg               fault
);
    localparam integer NWD = HID / EMB_CODE_LANES;      // code words a row (64)
    localparam integer LWD = $clog2(NWD);
    localparam integer ELI = $clog2(EMB_CODE_LANES);
    localparam integer CCW = $clog2(CRD + 1) + 1;
    reg  [511:0] rowbuf [0:NWD-1];
    reg  [15:0]  rscale;
    reg          have;                  // rowbuf holds token btok
    reg  [NW-1:0] btok;
    reg          hold;
    reg  [FI-1:0] f_h;
    reg  [LWD+1:0] nreq, nrsp;          // requests issued / responses landed (NWD code words + 1 scale)
    reg  [CCW-1:0] cred;
    wire need = go_in && a_src && !(have && btok == tok);
    wire fill_done = hold && nrsp == NWD + 1;
    assign go_out = (go_in && !need && !hold) || fill_done;
    assign f_out = hold ? f_h : f_in;
    assign pend = hold;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hold <= 1'b0; have <= 1'b0; nreq <= 0; nrsp <= 0; cred <= CRD[CCW-1:0]; ea_v <= 1'b0; fault <= 1'b0;
        end else begin
            ea_v <= 1'b0;
            if (need && !hold) begin
                hold <= 1'b1; have <= 1'b0; btok <= tok; f_h <= f_in; nreq <= 0; nrsp <= 0;
            end else if (fill_done) begin
                hold <= 1'b0; have <= 1'b1;
            end
            if (hold && nreq != NWD + 1 && (cred != 0 || ea_cr)) begin
                ea_v <= 1'b1;
                ea_kind <= (nreq == NWD);
                ea_addr <= (nreq == NWD) ? {{(AW-NW){1'b0}}, btok} : (btok * NWD + nreq);
                nreq <= nreq + 1'b1;
            end
            cred <= cred + (ea_cr ? 1'b1 : 1'b0) - ((hold && nreq != NWD + 1 && (cred != 0 || ea_cr)) ? 1'b1 : 1'b0);
            if (eq_v) begin
                if (!hold || nrsp >= nreq) fault <= 1'b1;
                nrsp <= nrsp + 1'b1;
            end
            if ((go_in && hold) || (ea_cr && cred == CRD[CCW-1:0])) fault <= 1'b1;
        end
    end
    always @(posedge clk) begin
        if (eq_v && nrsp < NWD) rowbuf[nrsp[LWD-1:0]] <= eq_data;
        if (eq_v && nrsp == NWD) rscale <= eq_data[15:0];
    end
    // ---- the decode (ot_qfd_su_embed term for term, the code ROM replaced by the row buffer) ----
    reg embed_active;
    reg [SW-1:0] embed_sel;
    reg [SW*ELI-1:0] embed_lanes;
    reg [511:0] code_q;
    wire code_re = |(su_va_re & {SW{embed_active}});
    wire [AW-1:0] word = ((su_va_addr[0 +: AW] - EMB_ADDR_BASE) & (HID - 1)) / EMB_CODE_LANES;
    always @(posedge clk) if (code_re) code_q <= rowbuf[word[LWD-1:0]];
    assign va_re = su_va_re & ~({SW{embed_active}});
    assign va_addr = su_va_addr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            embed_active <= 1'b0;
            embed_sel <= 0;
        end else begin
            if (go_out) embed_active <= hold ? 1'b1 : a_src;
            embed_sel <= su_va_re & {SW{embed_active}};
        end
    end
    wire [SW-1:0] bad;
    genvar el;
    generate for (el = 0; el < SW; el = el + 1) begin : g_dec
        always @(posedge clk) embed_lanes[el*ELI +: ELI] <= su_va_addr[el*AW +: ELI];
        wire [31:0] decoded;
        ot_hdc_qwen_int8_embed_decode u_decode (
            .code(code_q[8*embed_lanes[el*ELI +: ELI] +: 8]), .scale(rscale), .value(decoded), .fault(bad[el]));
        assign su_va_q[el*32 +: 32] = embed_sel[el] ? decoded : va_q[el*32 +: 32];
    end endgenerate
endmodule


module ot_qfd_sp_su64_sfu_ab #(
    parameter integer SW = 64,
    parameter integer LV = 7,
    parameter integer W = 16,
    parameter integer AW = 24,
    parameter integer NW = 18,
    parameter integer KV_FP8 = 1,
    parameter integer IS = 1,
    parameter integer OS = 1,
    parameter integer CRX = 2,              // constant-ROM edges outside this master beyond the base's one
    parameter integer HID = 4096,
    parameter integer CRD = 4,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    // control (stationed)
    input  wire              go,
    output wire              ready,
    output wire              idle,
    output wire              obs_active,
    output wire [7:0]        obs_inflight,
    input  wire [NW-1:0]     i_nout, i_nin,
    input  wire              i_asrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi,
    input  wire              i_bsrc,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_csrc,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire [1:0]        i_ma, i_mb,
    input  wire [2:0]        i_ad, i_sfu,
    input  wire              i_mc, i_md,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire [1:0]        i_red,
    input  wire              i_redsq,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2,
    input  wire              a_src,          // the embedding selector (po_su_asrc_raw)
    input  wire [NW-1:0]     tok,            // the token (static from the token start)
    output wire [15:0]       progress,
    output wire [15:0]       progress_rows,
    output wire              fault,
    // vector memory (abutted, no stations)
    output wire [SW-1:0]     va_re,
    output wire [SW*AW-1:0]  va_addr,
    input  wire [SW*32-1:0]  va_q,
    output wire [SW-1:0]     vb_re,
    output wire [SW*AW-1:0]  vb_addr,
    input  wire [SW*32-1:0]  vb_q,
    output wire [SW-1:0]     vc_re,
    output wire [SW*AW-1:0]  vc_addr,
    input  wire [SW*32-1:0]  vc_q,
    output wire [SW-1:0]     vm_we,
    output wire [SW*AW-1:0]  vm_waddr,
    output wire [SW*32-1:0]  vm_wdata,
    output wire              red_we,
    output wire [AW-1:0]     red_addr,
    output wire [31:0]       red_data,
    // KV write (posted, stationed) and its copy for the controller's flush
    output wire [SW-1:0]     kv_we,
    output wire [SW*AW-1:0]  kv_waddr,
    output wire [SW*32-1:0]  kv_wdata,
    // constant ROM across the channel (stationed; answers 1 + CRX edges after the far strobe)
    output wire [SW-1:0]     crom_re,
    output wire [SW*AW-1:0]  crom_addr,
    input  wire [SW*64-1:0]  crom_q,
    // embedding ROM (stationed both ways)
    output wire              ea_v,
    output wire              ea_kind,
    output wire [AW-1:0]     ea_addr,
    input  wire              ea_cr,
    input  wire              eq_v,
    input  wire [511:0]      eq_data,
    output wire              wrom_fault
);
    localparam integer ML = OS + IS + CRX;
    localparam integer FI = 2*NW + 1 + 3*AW + 1 + 3*AW + 1 + 3*AW + 2 + 2 + 3 + 3 + 1 + 1 + 2 + 3*AW + 2 + 1 + 2*AW + 64;
    wire rs;
    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk), .rst_n(rst_n), .rst_q(rs));
    // ---- input stations ----
    wire [FI-1:0] f_d = {i_nout, i_nin, i_asrc, i_abase, i_aso, i_asi, i_bsrc, i_bbase, i_bso, i_bsi, i_csrc, i_cbase,
                         i_cso, i_csi, i_ma, i_mb, i_ad, i_sfu, i_mc, i_md, i_dst, i_dbase, i_dso, i_dsi, i_red,
                         i_redsq, i_rbase, i_rso, i_imm1, i_imm2};
    wire [FI-1:0] f_q, f_go;
    wire go_q, asrc_q, cr_q, eqv_q, go_s;
    wire [NW-1:0] tok_q;
    wire [511:0] eqd_q;
    wire [SW*64-1:0] crq_q;
    wire [SW*64-1:0] crom_m = (MUT != 0) ? (crom_q ^ {{(SW*64-1){1'b0}}, 1'b1}) : crom_q;
    ot_hdc_delay #(.W(FI + NW + SW*64 + 512), .D(IS)) u_if (.clk(clk), .rst_n(rst_n),
        .d({f_d, tok, crom_m, eq_data}), .q({f_q, tok_q, crq_q, eqd_q}));
    ot_hdc_delay #(.W(4), .D(IS), .RESET(1)) u_ig (.clk(clk), .rst_n(rst_n), .d({go, a_src, ea_cr, eq_v}),
        .q({go_q, asrc_q, cr_q, eqv_q}));
    // ---- embedding row buffer + decode; the go is held while a row is fetched ----
    wire [SW-1:0] s_va_re, e_va_re;
    wire [SW*AW-1:0] s_va_addr, e_va_addr;
    wire [SW*32-1:0] e_va_q;
    wire e_pend, e_fault, e_v, e_kind;
    wire [AW-1:0] e_addr;
    ot_qfd_su_embed_pf #(.SW(SW), .AW(AW), .NW(NW), .HID(HID), .CRD(CRD), .FI(FI)) u_emb (
        .clk(clk), .rst_n(rs), .go_in(go_q), .a_src(asrc_q), .tok(tok_q), .f_in(f_q), .go_out(go_s), .f_out(f_go),
        .pend(e_pend), .su_va_re(s_va_re), .su_va_addr(s_va_addr), .su_va_q(e_va_q), .va_re(e_va_re),
        .va_addr(e_va_addr), .va_q(va_q), .ea_v(e_v), .ea_kind(e_kind), .ea_addr(e_addr), .ea_cr(cr_q),
        .eq_v(eqv_q), .eq_data(eqd_q), .fault(e_fault));
    assign va_re = e_va_re;
    assign va_addr = e_va_addr;
    // ---- the abutted VM answers meet the far constant ROM's at S1: ML more edges here ----
    wire [SW*32-1:0] vaq_m, vbq_m, vcq_m;
    ot_hdc_delay #(.W(3*SW*32), .D(ML)) u_vml (.clk(clk), .rst_n(rst_n), .d({e_va_q, vb_q, vc_q}),
        .q({vaq_m, vbq_m, vcq_m}));
    wire [NW-1:0] q_nout, q_nin;
    wire q_asrc, q_bsrc, q_csrc, q_mc, q_md, q_redsq;
    wire [AW-1:0] q_abase, q_aso, q_asi, q_bbase, q_bso, q_bsi, q_cbase, q_cso, q_csi, q_dbase, q_dso, q_dsi, q_rbase, q_rso;
    wire [1:0] q_ma, q_mb, q_dst, q_red;
    wire [2:0] q_ad, q_sfu;
    wire [31:0] q_imm1, q_imm2;
    assign {q_nout, q_nin, q_asrc, q_abase, q_aso, q_asi, q_bsrc, q_bbase, q_bso, q_bsi, q_csrc, q_cbase,
            q_cso, q_csi, q_ma, q_mb, q_ad, q_sfu, q_mc, q_md, q_dst, q_dbase, q_dso, q_dsi, q_red,
            q_redsq, q_rbase, q_rso, q_imm1, q_imm2} = f_go;
    wire s_ready, s_idle, s_fault, s_wrom_re, s_active;
    wire [7:0] s_inflight;
    wire [SW-1:0] s_crom_re, s_kv_we;
    wire [SW*AW-1:0] s_crom_addr, s_kv_waddr;
    wire [SW*32-1:0] s_kv_wdata;
    wire [AW-1:0] s_wrom_addr;
    wire [15:0] s_progress, s_rows;
    ot_hdc_vstream #(.SW(SW), .LV(LV), .WR(W), .AW(AW), .NW(NW), .KV_FP8(KV_FP8), .ML(ML)) u_su (
        .clk(clk), .rst_n(rs), .go(go_s), .ready(s_ready), .idle(s_idle),
        .i_nout(q_nout), .i_nin(q_nin),
        .i_asrc(q_asrc), .i_abase(q_abase), .i_aso(q_aso), .i_asi(q_asi),
        .i_bsrc(q_bsrc), .i_bbase(q_bbase), .i_bso(q_bso), .i_bsi(q_bsi),
        .i_csrc(q_csrc), .i_cbase(q_cbase), .i_cso(q_cso), .i_csi(q_csi),
        .i_ma(q_ma), .i_mb(q_mb), .i_ad(q_ad), .i_sfu(q_sfu), .i_mc(q_mc), .i_md(q_md),
        .i_dst(q_dst), .i_dbase(q_dbase), .i_dso(q_dso), .i_dsi(q_dsi),
        .i_red(q_red), .i_redsq(q_redsq), .i_rbase(q_rbase), .i_rso(q_rso), .i_imm1(q_imm1), .i_imm2(q_imm2),
        .va_re(s_va_re), .va_addr(s_va_addr), .va_q(vaq_m),
        .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vbq_m),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vcq_m),
        .wrom_re(s_wrom_re), .wrom_addr(s_wrom_addr), .wrom_q({(W*16){1'b0}}),
        .crom_re(s_crom_re), .crom_addr(s_crom_addr), .crom_q(crq_q),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .kv_we(s_kv_we), .kv_waddr(s_kv_waddr), .kv_wdata(s_kv_wdata),
        .red_we(red_we), .red_addr(red_addr), .red_data(red_data),
        .progress(s_progress), .progress_rows(s_rows), .fault(s_fault),
        .obs_active(s_active), .obs_inflight(s_inflight));
    // ---- output stations ----
    localparam integer FS = 1 + 1 + 1 + 8 + 1 + 1 + 1 + 1 + SW + SW + 32;
    localparam integer FD = SW*AW + SW*AW + SW*32 + AW;
    ot_hdc_delay #(.W(FS), .D(OS), .RESET(1)) u_os (.clk(clk), .rst_n(rst_n),
        .d({s_ready && !e_pend, s_idle && !e_pend, s_active || e_pend, s_inflight, s_fault || e_fault, s_wrom_re,
            e_v, e_kind, s_crom_re, s_kv_we, s_progress, s_rows}),
        .q({ready, idle, obs_active, obs_inflight, fault, wrom_fault, ea_v, ea_kind, crom_re, kv_we, progress,
            progress_rows}));
    ot_hdc_delay #(.W(FD), .D(OS)) u_od (.clk(clk), .rst_n(rst_n),
        .d({s_crom_addr, s_kv_waddr, s_kv_wdata, e_addr}), .q({crom_addr, kv_waddr, kv_wdata, ea_addr}));
endmodule
