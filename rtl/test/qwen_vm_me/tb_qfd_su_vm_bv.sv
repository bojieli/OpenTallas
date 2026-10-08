`timescale 1ns/1ps
// qwen-vm-me 2026-10-08: the stream-unit master with banked-VM ports (ot_qfd_sp_su64_sfu_bv) ON the banked vector
// memory (ot_qfd_sp_vector_memory_bv: 3 SU replica copies, descriptor reads at 1 + VL, lane-row writes, reducer skid)
// against the base: the bare stream unit (ot_hdc_vstream, ML = 0) + ot_qfd_su_embed on the token bench's behavioural
// memory (one-edge registered lane reads, lane writes, reducer write).  Same initial image (the banked one preloaded
// through its sequencer row-write port), same constant / embedding ROM contents.  A go is issued to both when both are
// idle; op k writes half k mod 2 and reads half (k + 1) mod 2, so every op reads what the previous op wrote (cross-op
// RAW through the banks); operand strides {0, 1} (the Qwen program's).  Compared in order: every operand read descriptor (lane 0 / lane 1 strobe and address), every VM write
// cycle (lane mask, lane addresses, data), every reducer write, every KV write cycle; both final VM images (the banked
// one read back through its row-read port); no w_fault / w_hazard.  MUT = 1 (SU master): constant-ROM bit flip;
// VMUT = 1 (VM): the SU lane select one lane off.  Both must FAIL.  On a failure the first differing operand / lane-output
// / reducer / write events are printed (diagnostics; the banked memory's answers are also checked against a model of
// the base port driven by the master's own traffic, vm_answer_bad).
module tb_qfd_su_vm_bv;
    parameter integer SW = 8, IS = 1, OS = 1, CRX = 2, MUT = 0, VMUT = 0, OPS = 120, SEED = 11, MAXCYC = 400000;
    parameter integer VL = 7;
    localparam integer AW = 24, NW = 18, VMN = 32768, HID = 4096;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    integer seed;
    // ---- instruction ----
    reg go_r, go_d;
    reg [NW-1:0] nout, nin;
    reg bsrc, csrc, mc, md, redsq, a_src;
    reg [AW-1:0] abase, aso, asi, bbase, bso, bsi, cbase, cso, csi, dbase, dso, dsi, rbase, rso;
    reg [1:0] ma, mb, dst, red;
    reg [2:0] ad, sfu;
    reg [31:0] imm1, imm2;
    reg [NW-1:0] tok;
    function [31:0] h32(input [31:0] x);
        reg [31:0] h;
        begin h = x * 32'h9E3779B1; h = h ^ (h >> 15); h = h * 32'h85EBCA6B; h = h ^ (h >> 13); h32 = h; end
    endfunction
    function [31:0] fp(input [31:0] x);        // finite FP32, exponent 110..141
        reg [31:0] h; begin h = h32(x); fp = {h[31], 8'd110 + {3'd0, h[27:23]}, h[22:0]}; end
    endfunction
    function [63:0] crom_word(input [AW-1:0] a); crom_word = {fp({a, 8'h5a}), fp({a, 8'ha5})}; endfunction
    function [511:0] code_word(input [AW-1:0] a);
        integer k; begin for (k = 0; k < 16; k = k + 1) code_word[32*k +: 32] = h32({a, k[7:0]}); end
    endfunction
    function [15:0] scale_of(input [NW-1:0] t); reg [31:0] h; begin h = h32({t, 14'h1234}); scale_of = {h[15], 8'd118 + {5'd0, h[2:0]}, h[13:7]}; end endfunction
    // ---- reference ----
    wire [SW-1:0] r_su_va_re, r_va_re, r_vb_re, r_vc_re, r_crom_re, r_vm_we, r_kv_we;
    wire [SW*AW-1:0] r_su_va_addr, r_va_addr, r_vb_addr, r_vc_addr, r_crom_addr, r_vm_waddr, r_kv_waddr;
    wire [SW*32-1:0] r_vm_wdata, r_kv_wdata, r_su_va_q;
    reg  [SW*32-1:0] r_va_q, r_vb_q, r_vc_q;
    reg  [SW*64-1:0] r_crom_q;
    wire r_ready, r_idle, r_red_we, r_fault, r_wf, r_ecre, r_efault;
    wire [AW-1:0] r_red_addr, r_wa, r_ecaddr; wire [31:0] r_red_data; wire [15:0] r_pr, r_rows;
    reg  [511:0] r_ecq;
    ot_hdc_vstream #(.SW(SW), .LV(7), .WR(16), .AW(AW), .NW(NW), .KV_FP8(1)) ref0 (
        .clk(clk), .rst_n(rst_n), .go(go_r), .ready(r_ready), .idle(r_idle), .i_nout(nout), .i_nin(nin),
        .i_asrc(1'b0), .i_abase(abase), .i_aso(aso), .i_asi(asi), .i_bsrc(bsrc), .i_bbase(bbase), .i_bso(bso),
        .i_bsi(bsi), .i_csrc(csrc), .i_cbase(cbase), .i_cso(cso), .i_csi(csi), .i_ma(ma), .i_mb(mb), .i_ad(ad),
        .i_sfu(sfu), .i_mc(mc), .i_md(md), .i_dst(dst), .i_dbase(dbase), .i_dso(dso), .i_dsi(dsi), .i_red(red),
        .i_redsq(redsq), .i_rbase(rbase), .i_rso(rso), .i_imm1(imm1), .i_imm2(imm2),
        .va_re(r_su_va_re), .va_addr(r_su_va_addr), .va_q(r_su_va_q), .vb_re(r_vb_re), .vb_addr(r_vb_addr), .vb_q(r_vb_q),
        .vc_re(r_vc_re), .vc_addr(r_vc_addr), .vc_q(r_vc_q), .wrom_re(r_wf), .wrom_addr(r_wa), .wrom_q(256'd0),
        .crom_re(r_crom_re), .crom_addr(r_crom_addr), .crom_q(r_crom_q), .vm_we(r_vm_we), .vm_waddr(r_vm_waddr),
        .vm_wdata(r_vm_wdata), .kv_we(r_kv_we), .kv_waddr(r_kv_waddr), .kv_wdata(r_kv_wdata),
        .red_we(r_red_we), .red_addr(r_red_addr), .red_data(r_red_data), .progress(r_pr),
        .progress_rows(r_rows), .fault(r_fault), .obs_active(), .obs_inflight());
    ot_qfd_su_embed #(.SW(SW), .AW(AW), .NW(NW), .HID(HID), .EMB_CODE_LANES(64), .EMB_ADDR_BASE(0), .QWEN_FULLSHAPE(1),
        .INT8_EMBED(1)) ref_emb (.clk(clk), .rst_n(rst_n), .go(go_r), .a_src(a_src), .tok(tok), .scale(scale_of(tok)),
        .su_va_re(r_su_va_re), .su_va_addr(r_su_va_addr), .su_va_q(r_su_va_q), .va_re(r_va_re), .va_addr(r_va_addr),
        .va_q(r_va_q), .embed_code_re(r_ecre), .embed_code_addr(r_ecaddr), .embed_code_q(r_ecq), .fault(r_efault));
    // ---- the master ----
    wire [2:0] d_re0, d_re1; wire [3*AW-1:0] d_a0, d_a1; wire [3*SW*32-1:0] d_sq;
    wire [AW-1:0] d_wa0, d_wa1;
    wire [SW*32-1:0] d_vm_wdata, d_kv_wdata;
    wire [SW-1:0] d_vm_we, d_kv_we, d_crom_re;
    wire [SW*AW-1:0] d_crom_addr, d_kv_waddr;
    wire [SW*64-1:0] d_crom_q;
    wire d_ready, d_idle, d_act, d_red_we, d_fault, d_wf, d_eav, d_eak;
    wire [7:0] d_inf;
    wire [AW-1:0] d_red_addr, d_eaa; wire [31:0] d_red_data; wire [15:0] d_pr, d_rows;
    reg  d_eacr, d_eqv; reg [511:0] d_eqd;
    ot_qfd_sp_su64_sfu_bv #(.SW(SW), .IS(IS), .OS(OS), .CRX(CRX), .VL(VL), .MUT(MUT)) dut (
        .clk(clk), .rst_n(rst_n), .go(go_d), .ready(d_ready), .idle(d_idle), .obs_active(d_act), .obs_inflight(d_inf),
        .i_nout(nout), .i_nin(nin), .i_asrc(1'b0), .i_abase(abase), .i_aso(aso), .i_asi(asi), .i_bsrc(bsrc),
        .i_bbase(bbase), .i_bso(bso), .i_bsi(bsi), .i_csrc(csrc), .i_cbase(cbase), .i_cso(cso), .i_csi(csi), .i_ma(ma),
        .i_mb(mb), .i_ad(ad), .i_sfu(sfu), .i_mc(mc), .i_md(md), .i_dst(dst), .i_dbase(dbase), .i_dso(dso), .i_dsi(dsi),
        .i_red(red), .i_redsq(redsq), .i_rbase(rbase), .i_rso(rso), .i_imm1(imm1), .i_imm2(imm2), .a_src(a_src),
        .tok(tok), .progress(d_pr), .progress_rows(d_rows), .fault(d_fault),
        .s_re0(d_re0), .s_re1(d_re1), .s_a0(d_a0), .s_a1(d_a1), .s_q(d_sq),
        .sw_mask(d_vm_we), .sw_a0(d_wa0), .sw_a1(d_wa1), .sw_data(d_vm_wdata),
        .red_we(d_red_we), .red_addr(d_red_addr), .red_data(d_red_data), .kv_we(d_kv_we),
        .kv_waddr(d_kv_waddr), .kv_wdata(d_kv_wdata), .crom_re(d_crom_re), .crom_addr(d_crom_addr),
        .crom_q(d_crom_q), .ea_v(d_eav), .ea_kind(d_eak), .ea_addr(d_eaa), .ea_cr(d_eacr), .eq_v(d_eqv),
        .eq_data(d_eqd), .wrom_fault(d_wf));
    wire [SW*AW-1:0] d_vm_waddr;
    genvar gw;
    generate for (gw = 0; gw < SW; gw = gw + 1) begin : g_wa
        assign d_vm_waddr[gw*AW +: AW] = d_wa0 + gw * (d_wa1 - d_wa0);
    end endgenerate
    // the banked memory (x path idle; row ports for preload / read-back)
    reg pw_v, pr_v; reg [AW-5:0] pw_row, pr_row; reg [511:0] pw_data;
    wire pr_rdy, pr_qv, m_xf, m_xh, m_wf, m_wh, m_ok; wire [511:0] pr_q; wire [15:0] m_land;
    ot_qfd_sp_vector_memory_bv #(.ELEMS(VMN), .NRB(16), .AW(AW), .SMIN(3), .SMAX(7), .XVM(12), .BMAX(4), .ND(9),
        .DSET({8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0}), .SW(SW), .NSU(3), .NB(6), .MUT(VMUT)) vm (
        .clk(clk), .rst_n(rst_n), .me_en(1'b1), .x_dv(1'b0), .x_dc(24'd0), .x_dcs(24'd1), .x_dsp(4'd3), .x_q(),
        .x_rdy(), .x_fault(m_xf), .x_hazard(m_xh),
        .s_re0(d_re0), .s_re1(d_re1), .s_a0(d_a0), .s_a1(d_a1), .s_q(d_sq),
        .sw_mask(d_vm_we), .sw_a0(d_wa0), .sw_a1(d_wa1), .sw_data(d_vm_wdata),
        .rd_v(d_red_we), .rd_addr(d_red_addr), .rd_data(d_red_data),
        .w_v(pw_v), .w_row(pw_row), .w_mask(16'hffff), .w_data(pw_data),
        .r_v(pr_v), .r_rdy(pr_rdy), .r_row(pr_row), .r_qv(pr_qv), .r_q(pr_q),
        .mx_we(1'b0), .mx_addr(24'd0), .mx_mask(16'd0), .mx_data(512'd0),
        .rb_v(6'd0), .rb_end(6'd0), .rb_nul(6'd0), .rb_row(120'd0), .rb_mask(96'd0), .rb_data(3072'd0), .rb_cr(),
        .rb_ok(6'h3f), .me_ok(m_ok), .land_cnt(m_land), .w_fault(m_wf), .w_hazard(m_wh));
    // ---- memories ----
    reg [31:0] vm_r [0:VMN-1];
    integer l;
    always @(posedge clk) begin
        r_ecq <= code_word(r_ecaddr);
        for (l = 0; l < SW; l = l + 1) begin
            if (r_va_re[l]) r_va_q[32*l +: 32] <= vm_r[r_va_addr[l*AW +: 15]];
            if (r_vb_re[l]) r_vb_q[32*l +: 32] <= vm_r[r_vb_addr[l*AW +: 15]];
            if (r_vc_re[l]) r_vc_q[32*l +: 32] <= vm_r[r_vc_addr[l*AW +: 15]];
            if (r_crom_re[l]) r_crom_q[64*l +: 64] <= crom_word(r_crom_addr[l*AW +: AW]);
        end
        for (l = 0; l < SW; l = l + 1) begin
            if (r_vm_we[l]) vm_r[r_vm_waddr[l*AW +: 15]] <= r_vm_wdata[32*l +: 32];
        end
        if (r_red_we) vm_r[r_red_addr[14:0]] <= r_red_data;
    end
    // diagnostic: the banked memory's answers against a base-semantics model driven by the master's own traffic
    reg [31:0] vm_m [0:VMN-1];
    reg [3*SW*32-1:0] dexp [0:VL];
    reg [2:0] dev [0:VL];
    integer dq, dl, de, vbad;
    always @(posedge clk) if (rst_n) begin : dmod
        reg [3*SW*32-1:0] e; integer si, a;
        e = 0;
        for (dq = 0; dq < 3; dq = dq + 1) begin
            si = (d_re1[dq] && d_a1[dq*AW +: AW] - d_a0[dq*AW +: AW] == 1) ? 1 : 0;
            for (dl = 0; dl < SW; dl = dl + 1) begin a = d_a0[dq*AW +: AW] + dl * si; e[(dq*SW + dl)*32 +: 32] = (a < VMN) ? vm_m[a] : 0; end
        end
        for (de = VL; de > 0; de = de - 1) begin dexp[de] <= dexp[de-1]; dev[de] <= dev[de-1]; end
        dexp[0] <= e; dev[0] <= d_re0;
        for (dl = 0; dl < SW; dl = dl + 1) if (d_vm_we[dl]) vm_m[d_vm_waddr[dl*AW +: AW]] = d_vm_wdata[32*dl +: 32];
        if (d_red_we) vm_m[d_red_addr] = d_red_data;
        if (pw_v) for (dl = 0; dl < 16; dl = dl + 1) vm_m[pw_row * 16 + dl] = pw_data[32*dl +: 32];
        for (dq = 0; dq < 3; dq = dq + 1) if (dev[VL][dq] && d_sq[dq*SW*32 +: SW*32] !== dexp[VL][dq*SW*32 +: SW*32]) begin
            vbad = vbad + 1;
            if (vbad < 4) $display("vm answer mismatch op %0d operand %0d t=%0t", ops, dq, $time);
        end
    end
    // diagnostic: operand data as the lanes receive them, in order (ref one edge after its strobe, master 1 + ML)
    localparam integer MLT = (VL > IS + OS + CRX) ? VL : IS + OS + CRX;
    reg [3*SW-1:0] rre1, dre [0:MLT];
    reg [3*SW*32-1:0] rq_s [0:2047];
    reg [3*SW*32-1:0] dq_s [0:2047];
    reg [3*SW-1:0] rm_s [0:2047];
    reg [3*SW-1:0] dm_s [0:2047];
    integer nrq, ndq, dd2;
    reg [AW-1:0] ra1; reg [AW-1:0] ra_s [0:2047]; reg [15:0] op_s [0:2047];
    always @(posedge clk) if (rst_n) begin
        rre1 <= {r_vc_re, r_vb_re, r_su_va_re}; ra1 <= r_su_va_addr[0 +: AW];
        if (|rre1 && nrq < 2048) begin ra_s[nrq] = ra1; op_s[nrq] = ops; end
        dre[0] <= {dut.vc_re, dut.vb_re, dut.s_va_re};
        for (dd2 = 1; dd2 <= MLT; dd2 = dd2 + 1) dre[dd2] <= dre[dd2-1];
        if (|rre1) begin if (nrq < 2048) begin rq_s[nrq] = {r_vc_q, r_vb_q, r_su_va_q}; rm_s[nrq] = rre1; end nrq = nrq + 1; end
        if (|dre[MLT]) begin if (ndq < 2048) begin dq_s[ndq] = {dut.vcq_m, dut.vbq_m, dut.vaq_m}; dm_s[ndq] = dre[MLT]; end ndq = ndq + 1; end
    end
    // far constant ROM for the master: 1 + CRX edges after its (stationed) strobe
    reg [SW*64-1:0] crl [0:CRX];
    integer c;
    always @(posedge clk) begin
        for (l = 0; l < SW; l = l + 1) if (d_crom_re[l]) crl[0][64*l +: 64] <= crom_word(d_crom_addr[l*AW +: AW]);
        for (c = 1; c <= CRX; c = c + 1) crl[c] <= crl[c-1];
    end
    assign d_crom_q = crl[CRX];
    // embedding ROM model for the master: in-order responses, random latency, CRD = 4 credits
    reg [AW:0] eqq [0:15]; reg [3:0] eq_w, eq_r; reg [7:0] eq_wait;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin eq_w <= 0; eq_r <= 0; d_eqv <= 0; d_eacr <= 0; eq_wait <= 0; end
        else begin
            d_eqv <= 0; d_eacr <= 0;
            if (d_eav) begin eqq[eq_w] <= {d_eak, d_eaa}; eq_w <= eq_w + 1'b1; end
            if (eq_wait != 0) eq_wait <= eq_wait - 1'b1;
            else if (eq_r != eq_w) begin
                d_eqv <= 1; d_eacr <= 1; eq_r <= eq_r + 1'b1; eq_wait <= $random(seed) & 7;
                d_eqd <= eqq[eq_r][AW] ? {496'd0, scale_of(eqq[eq_r][NW-1:0])} : code_word(eqq[eq_r][AW-1:0]);
            end
        end
    end
    // ---- in-order transaction hashes, one stream per port (a port's cycles in order; ports shift independently) ----
    reg [63:0] hr [0:6]; reg [63:0] hd [0:6]; integer nr [0:6]; integer nd [0:6];
    function [63:0] mix(input [63:0] h, input [63:0] v); mix = (h ^ v) * 64'h100000001B3 + 64'h9E3779B97F4A7C15; endfunction
    task ev(input integer side, input integer k, input [SW-1:0] re, input [SW*AW-1:0] ad, input [SW*32-1:0] dat, input use_d);
        integer q; reg [63:0] h;
        begin
            h = (side == 0) ? hr[k] : hd[k];
            for (q = 0; q < SW; q = q + 1) if (re[q]) h = mix(h, {q[7:0], ad[q*AW +: AW], use_d ? dat[32*q +: 32] : 32'd0});
            if (side == 0) begin hr[k] = h; nr[k] = nr[k] + 1; end else begin hd[k] = h; nd[k] = nd[k] + 1; end
        end
    endtask
    always @(posedge clk) if (rst_n) begin
        if (r_va_re[0]) ev(0, 0, 2'b11, {r_va_addr[AW +: AW], r_va_addr[0 +: AW]}, {r_va_re[1], 31'd0}, 1);
        if (d_re0[0]) ev(1, 0, 2'b11, {d_a1[0 +: AW], d_a0[0 +: AW]}, {d_re1[0], 31'd0}, 1);
        if (r_vb_re[0]) ev(0, 1, 2'b11, {r_vb_addr[AW +: AW], r_vb_addr[0 +: AW]}, {r_vb_re[1], 31'd0}, 1);
        if (d_re0[1]) ev(1, 1, 2'b11, {d_a1[AW +: AW], d_a0[AW +: AW]}, {d_re1[1], 31'd0}, 1);
        if (r_vc_re[0]) ev(0, 2, 2'b11, {r_vc_addr[AW +: AW], r_vc_addr[0 +: AW]}, {r_vc_re[1], 31'd0}, 1);
        if (d_re0[2]) ev(1, 2, 2'b11, {d_a1[2*AW +: AW], d_a0[2*AW +: AW]}, {d_re1[2], 31'd0}, 1);
        if (|r_crom_re) ev(0, 3, r_crom_re, r_crom_addr, 0, 0);
        if (|d_crom_re) ev(1, 3, d_crom_re, d_crom_addr, 0, 0);
        if (|r_vm_we) ev(0, 4, r_vm_we, r_vm_waddr, r_vm_wdata, 1);
        if (|d_vm_we) ev(1, 4, d_vm_we, d_vm_waddr, d_vm_wdata, 1);
        if (r_red_we) ev(0, 5, 1, r_red_addr, r_red_data, 1);
        if (d_red_we) ev(1, 5, 1, d_red_addr, d_red_data, 1);
        if (|r_kv_we) ev(0, 6, r_kv_we, r_kv_waddr, r_kv_wdata, 1);
        if (|d_kv_we) ev(1, 6, d_kv_we, d_kv_waddr, d_kv_wdata, 1);
    end
    // diagnostic: first differing VM write event (lane mask, lane 0 address, data)
    reg [SW + AW + SW*32 + 16 - 1:0] wr_r [0:4095];
    reg [SW + AW + SW*32 + 16 - 1:0] wr_d [0:4095];
    integer nwr, nwd, fw;
    function automatic wdiff(input [SW + AW + SW*32 + 16 - 1:0] a, input [SW + AW + SW*32 + 16 - 1:0] b);
        integer q; begin wdiff = 0; for (q = 0; q < SW; q = q + 1) if (a[SW*32 + 16 + AW + q] && a[16 + 32*q +: 32] !== b[16 + 32*q +: 32]) wdiff = 1; end
    endfunction
    always @(posedge clk) if (rst_n) begin
        if (|r_vm_we) begin if (nwr < 4096) wr_r[nwr] = {r_vm_we, r_vm_waddr[0 +: AW], r_vm_wdata, ops[15:0]}; nwr = nwr + 1; end
        if (|d_vm_we) begin if (nwd < 4096) wr_d[nwd] = {d_vm_we, d_wa0, d_vm_wdata, ops[15:0]}; nwd = nwd + 1; end
    end
    reg [AW+32+16-1:0] rr_e [0:1023]; reg [AW+32+16-1:0] rd_e [0:1023]; integer nre, nde;
    always @(posedge clk) if (rst_n) begin
        if (r_red_we) begin if (nre < 1024) rr_e[nre] = {r_red_addr, r_red_data, ops[15:0]}; nre = nre + 1; end
        if (d_red_we) begin if (nde < 1024) rd_e[nde] = {d_red_addr, d_red_data, ops[15:0]}; nde = nde + 1; end
    end
    // lane outputs and constant-ROM data, in order
    reg [SW*32+SW-1:0] lo_r [0:4095]; reg [SW*32+SW-1:0] lo_d [0:4095]; integer nlr, nld;
    reg [SW*64+SW-1:0] cr_r [0:4095]; reg [SW*64+SW-1:0] cr_d [0:4095]; integer ncr, ncd;
    reg [SW-1:0] rcre1; reg [SW-1:0] dcre [0:MLT];
    integer cq;
    always @(posedge clk) if (rst_n) begin
        if (|ref0.l_ov) begin if (nlr < 4096) lo_r[nlr] = {ref0.l_ov, ref0.l_out}; nlr = nlr + 1; end
        if (|dut.u_su.l_ov) begin if (nld < 4096) lo_d[nld] = {dut.u_su.l_ov, dut.u_su.l_out}; nld = nld + 1; end
        rcre1 <= r_crom_re; dcre[0] <= dut.s_crom_re;
        for (cq = 1; cq <= MLT; cq = cq + 1) dcre[cq] <= dcre[cq-1];
        if (|rcre1) begin if (ncr < 4096) cr_r[ncr] = {rcre1, r_crom_q}; ncr = ncr + 1; end
        if (|dcre[MLT]) begin if (ncd < 4096) cr_d[ncd] = {dcre[MLT], dut.crq_q}; ncd = ncd + 1; end
    end
    integer hk, hbad;
    // ---- stimulus ----
    reg [AW-1:0] hr_, hw_;
    task randomize_instr;
        reg [31:0] r;
        begin
            hw_ = (ops & 1) ? 24'h4000 : 24'h0000; hr_ = (ops & 1) ? 24'h0000 : 24'h4000;
            r = $random(seed);
            nout = 1 + ($random(seed) & 3); nin = 1 + ($random(seed) & 63);
            bsrc = r[0]; csrc = r[1]; mc = r[2]; md = r[3]; redsq = r[4];
            ma = r[6:5]; mb = r[8:7]; dst = r[10:9]; red = r[12:11]; ad = r[15:13]; sfu = r[18:16];
            a_src = (r[23:21] == 0);
            if (a_src) begin bsrc = 0; csrc = 0; end
            abase = hr_ | ($random(seed) & 24'h0fff); aso = $random(seed) & 24'h3f; asi = $random(seed) & 1;
            if (($random(seed) & 3) != 0) asi = 1;
            bbase = hr_ | ($random(seed) & 24'h0fff); bso = $random(seed) & 24'h3f; bsi = $random(seed) & 1;
            cbase = hr_ | ($random(seed) & 24'h0fff); cso = $random(seed) & 24'h3f; csi = $random(seed) & 1;
            dbase = hw_ | ($random(seed) & 24'h0fff); dso = $random(seed) & 24'h3f; dsi = 1;
            rbase = hw_ | 24'h2000 | ($random(seed) & 24'h0fff); rso = $random(seed) & 24'h3f;
            imm1 = fp($random(seed)); imm2 = fp($random(seed));
            if (r[27:25] == 0) tok = $random(seed) % 151936;
        end
    endtask
    integer i, cyc, ops, quiet, bad, rb_i, rb_o;
    initial begin
        seed = SEED; ops = 0; quiet = 0; bad = 0;
        for (hk = 0; hk < 7; hk = hk + 1) begin hr[hk] = 0; hd[hk] = 0; nr[hk] = 0; nd[hk] = 0; end
        vbad = 0; nwr = 0; nwd = 0; nrq = 0; ndq = 0; nre = 0; nde = 0; nlr = 0; nld = 0; ncr = 0; ncd = 0;
        for (i = 0; i < VMN; i = i + 1) begin vm_r[i] = fp(i + 7); vm_m[i] = 0; end
        for (i = 0; i <= VL; i = i + 1) dev[i] = 0;
        for (c = 0; c <= CRX; c = c + 1) crl[c] = 0;
        go_r = 0; go_d = 0; tok = 5; pw_v = 0; pr_v = 0; pw_row = 0; pr_row = 0; pw_data = 0; randomize_instr;
        repeat (4) @(negedge clk); rst_n = 1;
        for (i = 0; i < VMN / 16; i = i + 1) begin
            @(negedge clk); pw_v = 1; pw_row = i;
            for (l = 0; l < 16; l = l + 1) pw_data[32*l +: 32] = fp(i * 16 + l + 7);
        end
        @(negedge clk); pw_v = 0;
        repeat (16) @(negedge clk);
        for (cyc = 0; cyc < MAXCYC && ops < OPS; cyc = cyc + 1) begin
            @(negedge clk);
            go_r = 0; go_d = 0;
            quiet = (r_idle && d_idle && !d_act) ? quiet + 1 : 0;
            if (quiet > IS + OS + CRX + 8) begin
                randomize_instr; go_r = 1; go_d = 1; ops = ops + 1; quiet = 0;
                if (ops <= 16) begin : memchk
                    integer mi, mc; mc = 0;
                    for (mi = 0; mi < VMN; mi = mi + 1) if (vm_m[mi] !== vm_r[mi]) begin if (mc < 3) $display("  before op %0d: vm diff @%h ref %h dut %h", ops, mi, vm_r[mi], vm_m[mi]); mc = mc + 1; end
                end
                end
        end
        // drain: both units idle (the master's last go may still be held for an embedding row fetch)
        quiet = 0;
        for (cyc = 0; cyc < 20000 && quiet < 64; cyc = cyc + 1) begin
            @(negedge clk); go_r = 0; go_d = 0;
            quiet = (r_idle && d_idle && !d_act) ? quiet + 1 : 0;
        end
        // read the banked image back through the row-read port (in-order answers, RL edges later)
        rb_i = 0; rb_o = 0;
        while (rb_o < VMN / 16) begin
            @(negedge clk);
            if (pr_qv) begin
                for (l = 0; l < 16; l = l + 1) if (pr_q[32*l +: 32] !== vm_r[rb_o * 16 + l]) bad = bad + 1;
                rb_o = rb_o + 1;
            end
            pr_v = (rb_i < VMN / 16); pr_row = rb_i;
            if (pr_v) rb_i = rb_i + 1;
        end
        pr_v = 0;
        hbad = 0;
        begin : opd
            integer x, y, z, done_; done_ = 0;
            for (x = 0; x < nrq && x < 2048 && !done_; x = x + 1) begin
                if (rm_s[x] !== dm_s[x]) begin $display("operand event %0d: strobe masks differ %h / %h", x, rm_s[x], dm_s[x]); done_ = 1; end
                for (z = 0; z < 3*SW && !done_; z = z + 1)
                    if (rm_s[x][z] && rq_s[x][32*z +: 32] !== dq_s[x][32*z +: 32]) begin
                        $display("operand event %0d: operand %0d lane %0d ref %h dut %h (mask %h) op %0d a-lane0 addr %h now vm_r %h vm_m %h", x, z / SW, z % SW, rq_s[x][32*z +: 32], dq_s[x][32*z +: 32], rm_s[x], op_s[x], ra_s[x], vm_r[ra_s[x]], vm_m[ra_s[x]]);
                        done_ = 1;
                    end
            end
            $display("operand events ref %0d dut %0d", nrq, ndq);
            done_ = 0;
            for (x = 0; x < nlr && x < 4096 && !done_; x = x + 1)
                for (z = 0; z < SW && !done_; z = z + 1)
                    if (lo_r[x][SW*32 + z] !== lo_d[x][SW*32 + z] || (lo_r[x][SW*32 + z] && lo_r[x][32*z +: 32] !== lo_d[x][32*z +: 32])) begin
                        $display("lane-out event %0d lane %0d: ref ov %0d %h dut ov %0d %h", x, z, lo_r[x][SW*32+z], lo_r[x][32*z +: 32], lo_d[x][SW*32+z], lo_d[x][32*z +: 32]); done_ = 1;
                        for (y = (x > 3 ? x - 3 : 0); y <= x + 1; y = y + 1) $display("  ev %0d ref %h | dut %h", y, lo_r[y], lo_d[y]);
                        for (y = 0; y < nrq && y < 2048; y = y + 1) if (op_s[y] == 13) $display("  op13 operand ev %0d mask %h a %h | dut %h", y, rm_s[y], rq_s[y][0 +: SW*32], dq_s[y][0 +: SW*32]);
                        end
            done_ = 0;
            for (x = 0; x < ncr && x < 4096 && !done_; x = x + 1)
                for (z = 0; z < SW && !done_; z = z + 1)
                    if (cr_r[x][SW*64 + z] !== cr_d[x][SW*64 + z] || (cr_r[x][SW*64 + z] && cr_r[x][64*z +: 64] !== cr_d[x][64*z +: 64])) begin
                        $display("crom event %0d lane %0d: ref re %0d %h dut re %0d %h", x, z, cr_r[x][SW*64+z], cr_r[x][64*z +: 64], cr_d[x][SW*64+z], cr_d[x][64*z +: 64]); done_ = 1; end
            $display("lane-out events %0d / %0d, crom events %0d / %0d", nlr, nld, ncr, ncd);
            done_ = 0;
            for (x = 0; x < nre && x < 1024 && !done_; x = x + 1) if (rr_e[x][16 +: AW+32] !== rd_e[x][16 +: AW+32]) begin
                $display("reducer event %0d: ref op %0d addr %h data %h | dut op %0d addr %h data %h", x, rr_e[x][15:0], rr_e[x][48 +: AW], rr_e[x][16 +: 32], rd_e[x][15:0], rd_e[x][48 +: AW], rd_e[x][16 +: 32]);
                done_ = 1;
            end
        end
        for (fw = 0; fw < nwr && fw < 4096; fw = fw + 1) if (wr_r[fw][SW*32 + 16 +: SW + AW] !== wr_d[fw][SW*32 + 16 +: SW + AW] || wdiff(wr_r[fw], wr_d[fw])) begin
            $display("first write diff event %0d (ref op %0d, dut op %0d): mask %h/%h addr %h/%h", fw, wr_r[fw][15:0], wr_d[fw][15:0], wr_r[fw][SW*32+16+AW +: SW], wr_d[fw][SW*32+16+AW +: SW], wr_r[fw][SW*32+16 +: AW], wr_d[fw][SW*32+16 +: AW]);
            for (l = 0; l < SW; l = l + 1) $display("  lane %0d ref %h dut %h", l, wr_r[fw][16 + 32*l +: 32], wr_d[fw][16 + 32*l +: 32]);
            fw = 1 << 30;
        end
        for (hk = 0; hk < 7; hk = hk + 1) if (hr[hk] !== hd[hk] || nr[hk] != nd[hk]) begin
            hbad = hbad + 1; $display("port stream %0d differs: ref %0d events, master %0d", hk, nr[hk], nd[hk]);
        end
        if (vbad == 0 && bad == 0 && hbad == 0 && nr[4] > OPS && d_fault == r_fault && ops == OPS && !m_wf && !m_wh && !m_xf && !m_xh)
            $display("PASS qfd_su_vm_bv SW=%0d IS=%0d OS=%0d CRX=%0d VL=%0d ops=%0d va/vb/vc/crom/vm/red/kv events %0d/%0d/%0d/%0d/%0d/%0d/%0d", SW, IS, OS, CRX, VL, ops, nr[0], nr[1], nr[2], nr[3], nr[4], nr[5], nr[6]);
        else
            $display("FAIL qfd_su_vm_bv vm_answer_bad=%0d vm_mismatch=%0d port_streams_differing=%0d faults r%0d d%0d vm w_fault %0d w_hazard %0d ops=%0d", vbad, bad, hbad, r_fault, d_fault, m_wf, m_wh, ops);
        $finish;
    end
endmodule
