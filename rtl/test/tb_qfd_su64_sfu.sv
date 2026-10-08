`timescale 1ns/1ps
// qwen-missing 2026-10-07: the qfd_sp_su64_sfu master (ot_qfd_sp_su64_sfu, pin stations IS / OS) against the bare
// stream unit (ot_hdc_vstream, instantiated and wired independently in this bench): random instructions (bounded loop counts, every
// operand source / SFU / reduction / destination class) and random memory read data every cycle; every output of
// the master must equal the bare unit's output IS + OS cycles earlier, bit for bit (4-state).  MUT = 1 flips one
// input-station bit (lane 0 va_q bit 0): the bench must FAIL.
module tb_qfd_su64_sfu;
    parameter integer SW = 64, IS = 1, OS = 1, MUT = 0, CYCLES = 4000, SEED = 7;
    localparam integer AW = 24, NW = 18, L = IS + OS;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg go;
    reg [NW-1:0] nout, nin;
    reg asrc, bsrc, csrc, mc, md, redsq;
    reg [AW-1:0] abase, aso, asi, bbase, bso, bsi, cbase, cso, csi, dbase, dso, dsi, rbase, rso;
    reg [1:0] ma, mb, dst, red;
    reg [2:0] ad, sfu;
    reg [31:0] imm1, imm2;
    reg [SW*32-1:0] vaq, vbq, vcq;
    reg [SW*64-1:0] crq;
    // outputs, packed: {ready, idle, re x6, red_we, fault, wrom, progress, rows, addresses, data}
    localparam integer OW = 2 + 6*SW + 3 + 32 + 6*SW*AW + 2*SW*32 + AW + 32;
    wire [OW-1:0] o_m, o_r;
`define SU_INST(name, is_, os_, mut_, out) \
    wire [SW-1:0] name``_va_re, name``_vb_re, name``_vc_re, name``_crom_re, name``_vm_we, name``_kv_we; \
    wire [SW*AW-1:0] name``_va_addr, name``_vb_addr, name``_vc_addr, name``_crom_addr, name``_vm_waddr, name``_kv_waddr; \
    wire [SW*32-1:0] name``_vm_wdata, name``_kv_wdata; \
    wire name``_ready, name``_idle, name``_red_we, name``_fault, name``_wf; \
    wire [AW-1:0] name``_red_addr; wire [31:0] name``_red_data; wire [15:0] name``_pr, name``_rows; \
    ot_qfd_sp_su64_sfu #(.SW(SW), .IS(is_), .OS(os_), .MUT(mut_)) name ( \
        .clk(clk), .rst_n(rst_n), .go(go), .ready(name``_ready), .idle(name``_idle), .i_nout(nout), .i_nin(nin), \
        .i_asrc(asrc), .i_abase(abase), .i_aso(aso), .i_asi(asi), .i_bsrc(bsrc), .i_bbase(bbase), .i_bso(bso), \
        .i_bsi(bsi), .i_csrc(csrc), .i_cbase(cbase), .i_cso(cso), .i_csi(csi), .i_ma(ma), .i_mb(mb), .i_ad(ad), \
        .i_sfu(sfu), .i_mc(mc), .i_md(md), .i_dst(dst), .i_dbase(dbase), .i_dso(dso), .i_dsi(dsi), .i_red(red), \
        .i_redsq(redsq), .i_rbase(rbase), .i_rso(rso), .i_imm1(imm1), .i_imm2(imm2), \
        .va_re(name``_va_re), .va_addr(name``_va_addr), .va_q(vaq), .vb_re(name``_vb_re), .vb_addr(name``_vb_addr), \
        .vb_q(vbq), .vc_re(name``_vc_re), .vc_addr(name``_vc_addr), .vc_q(vcq), .crom_re(name``_crom_re), \
        .crom_addr(name``_crom_addr), .crom_q(crq), .vm_we(name``_vm_we), .vm_waddr(name``_vm_waddr), \
        .vm_wdata(name``_vm_wdata), .kv_we(name``_kv_we), .kv_waddr(name``_kv_waddr), .kv_wdata(name``_kv_wdata), \
        .red_we(name``_red_we), .red_addr(name``_red_addr), .red_data(name``_red_data), .progress(name``_pr), \
        .progress_rows(name``_rows), .fault(name``_fault), .wrom_fault(name``_wf)); \
    assign out = {name``_ready, name``_idle, name``_va_re, name``_vb_re, name``_vc_re, name``_crom_re, name``_vm_we, \
                  name``_kv_we, name``_red_we, name``_fault, name``_wf, name``_pr, name``_rows, name``_va_addr, \
                  name``_vb_addr, name``_vc_addr, name``_crom_addr, name``_vm_waddr, name``_kv_waddr, name``_vm_wdata, \
                  name``_kv_wdata, name``_red_addr, name``_red_data};
    `SU_INST(dut, IS, OS, MUT, o_m)
    // the reference: the bare stream unit (ot_hdc_vstream, the u_su of ot_qwen_rom_core), wired here independently
    wire [SW-1:0] ref0_va_re, ref0_vb_re, ref0_vc_re, ref0_crom_re, ref0_vm_we, ref0_kv_we;
    wire [SW*AW-1:0] ref0_va_addr, ref0_vb_addr, ref0_vc_addr, ref0_crom_addr, ref0_vm_waddr, ref0_kv_waddr;
    wire [SW*32-1:0] ref0_vm_wdata, ref0_kv_wdata;
    wire ref0_ready, ref0_idle, ref0_red_we, ref0_fault, ref0_wf;
    wire [AW-1:0] ref0_red_addr, ref0_wa; wire [31:0] ref0_red_data; wire [15:0] ref0_pr, ref0_rows;
    ot_hdc_vstream #(.SW(SW), .LV(7), .WR(16), .AW(AW), .NW(NW), .KV_FP8(1)) ref0 (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ref0_ready), .idle(ref0_idle), .i_nout(nout), .i_nin(nin),
        .i_asrc(asrc), .i_abase(abase), .i_aso(aso), .i_asi(asi), .i_bsrc(bsrc), .i_bbase(bbase), .i_bso(bso),
        .i_bsi(bsi), .i_csrc(csrc), .i_cbase(cbase), .i_cso(cso), .i_csi(csi), .i_ma(ma), .i_mb(mb), .i_ad(ad),
        .i_sfu(sfu), .i_mc(mc), .i_md(md), .i_dst(dst), .i_dbase(dbase), .i_dso(dso), .i_dsi(dsi), .i_red(red),
        .i_redsq(redsq), .i_rbase(rbase), .i_rso(rso), .i_imm1(imm1), .i_imm2(imm2),
        .va_re(ref0_va_re), .va_addr(ref0_va_addr), .va_q(vaq), .vb_re(ref0_vb_re), .vb_addr(ref0_vb_addr), .vb_q(vbq),
        .vc_re(ref0_vc_re), .vc_addr(ref0_vc_addr), .vc_q(vcq), .wrom_re(ref0_wf), .wrom_addr(ref0_wa), .wrom_q(256'd0),
        .crom_re(ref0_crom_re), .crom_addr(ref0_crom_addr), .crom_q(crq), .vm_we(ref0_vm_we), .vm_waddr(ref0_vm_waddr),
        .vm_wdata(ref0_vm_wdata), .kv_we(ref0_kv_we), .kv_waddr(ref0_kv_waddr), .kv_wdata(ref0_kv_wdata),
        .red_we(ref0_red_we), .red_addr(ref0_red_addr), .red_data(ref0_red_data), .progress(ref0_pr),
        .progress_rows(ref0_rows), .fault(ref0_fault));
    assign o_r = {ref0_ready, ref0_idle, ref0_va_re, ref0_vb_re, ref0_vc_re, ref0_crom_re, ref0_vm_we, ref0_kv_we,
                  ref0_red_we, ref0_fault, ref0_wf, ref0_pr, ref0_rows, ref0_va_addr, ref0_vb_addr, ref0_vc_addr,
                  ref0_crom_addr, ref0_vm_waddr, ref0_kv_waddr, ref0_vm_wdata, ref0_kv_wdata, ref0_red_addr,
                  ref0_red_data};
    // the reference's outputs delayed by the stations' total latency
    reg [OW-1:0] hist [0:L];
    integer i, cyc, bad, gos, ops_done, first_bad;
    always @(posedge clk) begin
        for (i = L; i > 0; i = i - 1) hist[i] <= hist[i-1];
        hist[0] <= o_r;
    end
    wire [OW-1:0] o_rd = (L == 0) ? o_r : hist[L-1];
    function [31:0] rf32(input integer k);    // a random finite-ish FP32 (exponent 100..150)
        reg [31:0] r;
        begin r = $random(seed); rf32 = {r[31], 8'd100 + r[30:26] + r[25:24], r[22:0]}; end
    endfunction
    integer seed;
    task randomize_instr;
        reg [31:0] r;
        begin
            r = $random(seed);
            nout = 1 + ($random(seed) & 3); nin = 1 + ($random(seed) & 255);
            asrc = 0; bsrc = r[0]; csrc = r[1]; mc = r[2]; md = r[3]; redsq = r[4];
            ma = r[6:5]; mb = r[8:7]; dst = r[10:9]; red = r[12:11]; ad = r[15:13]; sfu = r[18:16];
            abase = $random(seed) & 24'hffff; aso = $random(seed) & 24'h3ff; asi = $random(seed) & 3;
            bbase = $random(seed) & 24'hffff; bso = $random(seed) & 24'h3ff; bsi = $random(seed) & 3;
            cbase = $random(seed) & 24'hffff; cso = $random(seed) & 24'h3ff; csi = $random(seed) & 3;
            dbase = $random(seed) & 24'hffff; dso = $random(seed) & 24'h3ff; dsi = $random(seed) & 3;
            rbase = $random(seed) & 24'hffff; rso = $random(seed) & 24'h3ff;
            imm1 = rf32(0); imm2 = rf32(0);
        end
    endtask
    initial begin
        seed = SEED; bad = 0; gos = 0; first_bad = -1;
        go = 0; randomize_instr;
        for (i = 0; i < SW; i = i + 1) begin vaq[i*32 +: 32] = 0; vbq[i*32 +: 32] = 0; vcq[i*32 +: 32] = 0; crq[i*64 +: 64] = 0; end
        for (i = 0; i <= L; i = i + 1) hist[i] = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            // compare (after the reset-release window)
            if (cyc > L + 2 && o_m !== o_rd) begin
                bad = bad + 1;
                if (first_bad < 0) first_bad = cyc;
            end
            // stimulus for the next edge: memory data every cycle, a go when the bare unit is ready
            for (i = 0; i < SW; i = i + 1) begin
                vaq[i*32 +: 32] = rf32(0); vbq[i*32 +: 32] = rf32(0); vcq[i*32 +: 32] = rf32(0);
                crq[i*64 +: 64] = {rf32(0), rf32(0)};
            end
            go = 0;
            if (ref0_ready && ($random(seed) & 3) == 0) begin randomize_instr; go = 1; gos = gos + 1; end
        end
        if (bad == 0 && gos > 20)
            $display("PASS qfd_su64_sfu SW=%0d IS=%0d OS=%0d cycles=%0d ops=%0d outputs=%0d bits latency+%0d", SW, IS, OS, CYCLES, gos, OW, L);
        else
            $display("FAIL qfd_su64_sfu mismatching cycles=%0d first=%0d ops=%0d", bad, first_bad, gos);
        $finish;
    end
endmodule
