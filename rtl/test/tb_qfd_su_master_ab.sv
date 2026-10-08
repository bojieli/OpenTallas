`timescale 1ns/1ps
// qwen-rtl-finish 2026-10-07: the re-cut qfd_sp_su64_sfu master (ot_qfd_sp_su64_sfu_ab: IS / OS control stations,
// abutted VM ports, constant ROM across the channel at 1 + ML edges, embedding row buffer) against the base: the bare
// stream unit (ot_hdc_vstream, ML = 0) + the split's SU-side decode (ot_qfd_su_embed) with a one-edge constant ROM and a
// one-edge embedding ROM.  Each side has its OWN vector memory (same initial image, one-edge registered reads, lane
// writes, reducer write) and the same constant / embedding ROM contents.  A go is issued to both when both are idle
// (open after the dut's station delay); ops read [0, 0x4000) and write [0x4000, 0x8000) (no in-op RAW).  Compared in
// order (transaction level; the master is ML edges later per element): every VM read strobe/address cycle, every VM
// write cycle (lane mask, addresses, data), every reducer write, every KV write cycle, and the op count; plus both
// final VM images.  MUT = 1 flips a constant-ROM bit in the master: must FAIL.
module tb_qfd_su_master_ab;
    parameter integer SW = 8, IS = 1, OS = 1, CRX = 2, MUT = 0, OPS = 120, SEED = 11, MAXCYC = 400000;
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
    wire [SW-1:0] d_va_re, d_vb_re, d_vc_re, d_crom_re, d_vm_we, d_kv_we;
    wire [SW*AW-1:0] d_va_addr, d_vb_addr, d_vc_addr, d_crom_addr, d_vm_waddr, d_kv_waddr;
    wire [SW*32-1:0] d_vm_wdata, d_kv_wdata;
    reg  [SW*32-1:0] d_va_q, d_vb_q, d_vc_q;
    wire [SW*64-1:0] d_crom_q;
    wire d_ready, d_idle, d_act, d_red_we, d_fault, d_wf, d_eav, d_eak;
    wire [7:0] d_inf;
    wire [AW-1:0] d_red_addr, d_eaa; wire [31:0] d_red_data; wire [15:0] d_pr, d_rows;
    reg  d_eacr, d_eqv; reg [511:0] d_eqd;
    ot_qfd_sp_su64_sfu_ab #(.SW(SW), .IS(IS), .OS(OS), .CRX(CRX), .MUT(MUT)) dut (
        .clk(clk), .rst_n(rst_n), .go(go_d), .ready(d_ready), .idle(d_idle), .obs_active(d_act), .obs_inflight(d_inf),
        .i_nout(nout), .i_nin(nin), .i_asrc(1'b0), .i_abase(abase), .i_aso(aso), .i_asi(asi), .i_bsrc(bsrc),
        .i_bbase(bbase), .i_bso(bso), .i_bsi(bsi), .i_csrc(csrc), .i_cbase(cbase), .i_cso(cso), .i_csi(csi), .i_ma(ma),
        .i_mb(mb), .i_ad(ad), .i_sfu(sfu), .i_mc(mc), .i_md(md), .i_dst(dst), .i_dbase(dbase), .i_dso(dso), .i_dsi(dsi),
        .i_red(red), .i_redsq(redsq), .i_rbase(rbase), .i_rso(rso), .i_imm1(imm1), .i_imm2(imm2), .a_src(a_src),
        .tok(tok), .progress(d_pr), .progress_rows(d_rows), .fault(d_fault),
        .va_re(d_va_re), .va_addr(d_va_addr), .va_q(d_va_q), .vb_re(d_vb_re), .vb_addr(d_vb_addr), .vb_q(d_vb_q),
        .vc_re(d_vc_re), .vc_addr(d_vc_addr), .vc_q(d_vc_q), .vm_we(d_vm_we), .vm_waddr(d_vm_waddr),
        .vm_wdata(d_vm_wdata), .red_we(d_red_we), .red_addr(d_red_addr), .red_data(d_red_data), .kv_we(d_kv_we),
        .kv_waddr(d_kv_waddr), .kv_wdata(d_kv_wdata), .crom_re(d_crom_re), .crom_addr(d_crom_addr),
        .crom_q(d_crom_q), .ea_v(d_eav), .ea_kind(d_eak), .ea_addr(d_eaa), .ea_cr(d_eacr), .eq_v(d_eqv),
        .eq_data(d_eqd), .wrom_fault(d_wf));
    // ---- memories ----
    reg [31:0] vm_r [0:VMN-1];
    reg [31:0] vm_d [0:VMN-1];
    integer l;
    always @(posedge clk) begin
        r_ecq <= code_word(r_ecaddr);
        for (l = 0; l < SW; l = l + 1) begin
            if (r_va_re[l]) r_va_q[32*l +: 32] <= vm_r[r_va_addr[l*AW +: 15]];
            if (r_vb_re[l]) r_vb_q[32*l +: 32] <= vm_r[r_vb_addr[l*AW +: 15]];
            if (r_vc_re[l]) r_vc_q[32*l +: 32] <= vm_r[r_vc_addr[l*AW +: 15]];
            if (r_crom_re[l]) r_crom_q[64*l +: 64] <= crom_word(r_crom_addr[l*AW +: AW]);
            if (d_va_re[l]) d_va_q[32*l +: 32] <= vm_d[d_va_addr[l*AW +: 15]];
            if (d_vb_re[l]) d_vb_q[32*l +: 32] <= vm_d[d_vb_addr[l*AW +: 15]];
            if (d_vc_re[l]) d_vc_q[32*l +: 32] <= vm_d[d_vc_addr[l*AW +: 15]];
        end
        for (l = 0; l < SW; l = l + 1) begin
            if (r_vm_we[l]) vm_r[r_vm_waddr[l*AW +: 15]] <= r_vm_wdata[32*l +: 32];
            if (d_vm_we[l]) vm_d[d_vm_waddr[l*AW +: 15]] <= d_vm_wdata[32*l +: 32];
        end
        if (r_red_we) vm_r[r_red_addr[14:0]] <= r_red_data;
        if (d_red_we) vm_d[d_red_addr[14:0]] <= d_red_data;
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
        if (|r_va_re) ev(0, 0, r_va_re, r_va_addr, 0, 0);
        if (|d_va_re) ev(1, 0, d_va_re, d_va_addr, 0, 0);
        if (|r_vb_re) ev(0, 1, r_vb_re, r_vb_addr, 0, 0);
        if (|d_vb_re) ev(1, 1, d_vb_re, d_vb_addr, 0, 0);
        if (|r_vc_re) ev(0, 2, r_vc_re, r_vc_addr, 0, 0);
        if (|d_vc_re) ev(1, 2, d_vc_re, d_vc_addr, 0, 0);
        if (|r_crom_re) ev(0, 3, r_crom_re, r_crom_addr, 0, 0);
        if (|d_crom_re) ev(1, 3, d_crom_re, d_crom_addr, 0, 0);
        if (|r_vm_we) ev(0, 4, r_vm_we, r_vm_waddr, r_vm_wdata, 1);
        if (|d_vm_we) ev(1, 4, d_vm_we, d_vm_waddr, d_vm_wdata, 1);
        if (r_red_we) ev(0, 5, 1, r_red_addr, r_red_data, 1);
        if (d_red_we) ev(1, 5, 1, d_red_addr, d_red_data, 1);
        if (|r_kv_we) ev(0, 6, r_kv_we, r_kv_waddr, r_kv_wdata, 1);
        if (|d_kv_we) ev(1, 6, d_kv_we, d_kv_waddr, d_kv_wdata, 1);
    end
    integer hk, hbad;
    // ---- stimulus ----
    task randomize_instr;
        reg [31:0] r;
        begin
            r = $random(seed);
            nout = 1 + ($random(seed) & 3); nin = 1 + ($random(seed) & 63);
            bsrc = r[0]; csrc = r[1]; mc = r[2]; md = r[3]; redsq = r[4];
            ma = r[6:5]; mb = r[8:7]; dst = r[10:9]; red = r[12:11]; ad = r[15:13]; sfu = r[18:16];
            a_src = (r[23:21] == 0);
            if (a_src) begin bsrc = 0; csrc = 0; end
            abase = $random(seed) & 24'h0fff; aso = $random(seed) & 24'h3f; asi = 1 + ($random(seed) & 1);
            bbase = $random(seed) & 24'h0fff; bso = $random(seed) & 24'h3f; bsi = $random(seed) & 3;
            cbase = $random(seed) & 24'h0fff; cso = $random(seed) & 24'h3f; csi = $random(seed) & 3;
            dbase = 24'h4000 | ($random(seed) & 24'h0fff); dso = $random(seed) & 24'h3f; dsi = 1;
            rbase = 24'h6000 | ($random(seed) & 24'h0fff); rso = $random(seed) & 24'h3f;
            imm1 = fp($random(seed)); imm2 = fp($random(seed));
            if (r[27:25] == 0) tok = $random(seed) % 151936;
        end
    endtask
    integer i, cyc, ops, quiet, bad;
    initial begin
        seed = SEED; ops = 0; quiet = 0; bad = 0;
        for (hk = 0; hk < 7; hk = hk + 1) begin hr[hk] = 0; hd[hk] = 0; nr[hk] = 0; nd[hk] = 0; end
        for (i = 0; i < VMN; i = i + 1) begin vm_r[i] = fp(i + 7); vm_d[i] = fp(i + 7); end
        for (c = 0; c <= CRX; c = c + 1) crl[c] = 0;
        go_r = 0; go_d = 0; tok = 5; randomize_instr;
        repeat (4) @(negedge clk); rst_n = 1;
        for (cyc = 0; cyc < MAXCYC && ops < OPS; cyc = cyc + 1) begin
            @(negedge clk);
            go_r = 0; go_d = 0;
            quiet = (r_idle && d_idle && !d_act) ? quiet + 1 : 0;
            if (quiet > IS + OS + CRX + 8) begin
                randomize_instr; go_r = 1; go_d = 1; ops = ops + 1; quiet = 0; end
        end
        // drain: both units idle (the master's last go may still be held for an embedding row fetch)
        quiet = 0;
        for (cyc = 0; cyc < 20000 && quiet < 64; cyc = cyc + 1) begin
            @(negedge clk); go_r = 0; go_d = 0;
            quiet = (r_idle && d_idle && !d_act) ? quiet + 1 : 0;
        end
        for (i = 0; i < VMN; i = i + 1) if (vm_r[i] !== vm_d[i]) bad = bad + 1;
        hbad = 0;
        for (hk = 0; hk < 7; hk = hk + 1) if (hr[hk] !== hd[hk] || nr[hk] != nd[hk]) begin
            hbad = hbad + 1; $display("port stream %0d differs: ref %0d events, master %0d", hk, nr[hk], nd[hk]);
        end
        if (bad == 0 && hbad == 0 && nr[4] > OPS && d_fault == r_fault && ops == OPS)
            $display("PASS qfd_su_master_ab SW=%0d IS=%0d OS=%0d CRX=%0d ML=%0d ops=%0d va/vb/vc/crom/vm/red/kv events %0d/%0d/%0d/%0d/%0d/%0d/%0d", SW, IS, OS, CRX, IS+OS+CRX, ops, nr[0], nr[1], nr[2], nr[3], nr[4], nr[5], nr[6]);
        else
            $display("FAIL qfd_su_master_ab vm_mismatch=%0d port_streams_differing=%0d faults r%0d d%0d ops=%0d", bad, hbad, r_fault, d_fault, ops);
        $finish;
    end
endmodule
