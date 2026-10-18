`timescale 1ns/1ps
// q3h central-SU reference latency (for pricing Q-DV's root): the q3h SU core exactly as the TP8 compute die builds it
// inside ot_qfd_sp_su64_static_entries -- ot_hdc_vstream_static_entries #(SW 64, LV 7, ML 15, LT 1 (lane tiles, RD 2
// relays each way), LOFF 1, RED_ENTRIES 1 (the regional64 reducer)) -- on a behavioural VM answering 1 + ML edges after
// a read.  Op 1: the residual add over 4,096 elements with the sum of squares chased on it (red_sq) -> SSX; op 2 (issued
// on the first edge the core is ready after SSX is written): r = rsqrt(SSX * 2^-12 + eps) -> RX.  Prints the edges
// from the last vector issue of op 1 to SSX and to r, and checks r against the golden value computed by the caller
// (+R=<hex>).  The su64 wrapper adds IS = 1 (issue pin) and OS = 1 (output) edges around the core, not modelled here.
module tb_q3h_su_lat;
    localparam integer SW = 64, AW = 24, NW = 18, ML = 15;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg go = 0;
    reg [NW-1:0] nout, nin;
    reg [AW-1:0] abase, aso, asi, cbase, cso, csi, dbase, dso, dsi, rbase, rso;
    reg [1:0] ma, ad_hi, dst, red; reg [2:0] ad, sfu; reg redsq;
    reg [31:0] imm1, imm2;
    wire ready, idle, red_we, fault;
    wire [SW-1:0] va_re, vb_re, vc_re, vm_we, kv_we, cr_re;
    wire [SW*AW-1:0] va_addr, vb_addr, vc_addr, vm_waddr, kv_waddr, cr_addr;
    wire [SW*32-1:0] vm_wdata, kv_wdata;
    reg  [SW*32-1:0] va_q, vb_q, vc_q;
    wire [AW-1:0] red_addr, wrom_addr;
    wire [31:0] red_data;
    wire wrom_re;
    wire [15:0] prog, rows;
    wire [7:0] infl;
    wire act;
    ot_hdc_vstream_static_entries #(.SW(SW), .LV(7), .WR(16), .AW(AW), .NW(NW), .KV_FP8(1), .ML(ML), .LT(1), .LOFF(1),
        .RD(2), .RED_ENTRIES(1)) u (
        .ck_head({SW{clk}}), .ck_exp({SW{clk}}), .ck_rcp({SW{clk}}), .ck_rsq({SW{clk}}), .ck_lane({SW{clk}}),
        .ck_red({9{clk}}), .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(nout), .i_nin(nin), .i_asrc(1'b0), .i_abase(abase), .i_aso(aso), .i_asi(asi),
        .i_bsrc(1'b0), .i_bbase({AW{1'b0}}), .i_bso({AW{1'b0}}), .i_bsi({AW{1'b0}}),
        .i_csrc(1'b0), .i_cbase(cbase), .i_cso(cso), .i_csi(csi), .i_ma(ma), .i_mb(2'd0), .i_ad(ad), .i_sfu(sfu),
        .i_mc(1'b0), .i_md(1'b0), .i_dst(dst), .i_dbase(dbase), .i_dso(dso), .i_dsi(dsi), .i_red(red), .i_redsq(redsq),
        .i_rbase(rbase), .i_rso(rso), .i_imm1(imm1), .i_imm2(imm2),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q), .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q), .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(256'd0),
        .crom_re(cr_re), .crom_addr(cr_addr), .crom_q({SW{64'd0}}), .vm_we(vm_we), .vm_waddr(vm_waddr),
        .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .red_we(red_we), .red_addr(red_addr), .red_data(red_data), .progress(prog), .progress_rows(rows),
        .fault(fault), .obs_active(act), .obs_inflight(infl));
    // ---------------------------------------------------------------- VM: answer 1 + ML edges after the read
    reg [31:0] mem [0:16383];
    reg [SW*32-1:0] pa [0:ML], pb [0:ML], pc [0:ML];
    integer l, s;
    always @(posedge clk) begin
        for (l = 0; l < SW; l = l + 1) begin
            pa[0][32*l +: 32] <= mem[va_addr[AW*l +: 14]];
            pb[0][32*l +: 32] <= mem[vb_addr[AW*l +: 14]];
            pc[0][32*l +: 32] <= mem[vc_addr[AW*l +: 14]];
        end
        for (s = 1; s <= ML; s = s + 1) begin pa[s] <= pa[s-1]; pb[s] <= pb[s-1]; pc[s] <= pc[s-1]; end
        for (l = 0; l < SW; l = l + 1) if (vm_we[l]) mem[vm_waddr[AW*l +: 14]] <= vm_wdata[32*l +: 32];
        if (red_we) mem[red_addr[13:0]] <= red_data;
    end
    always @(*) begin va_q = pa[ML]; vb_q = pb[ML]; vc_q = pc[ML]; end   // 1 + ML edges after the request
    // ---------------------------------------------------------------- stimulus and measurement
    integer cyc = 0, t_last = -1, t_ss = -1, t_go2 = -1, t_r = -1, i;
    reg [31:0] rexp, eps;
    always @(posedge clk) cyc <= cyc + 1;
    always @(negedge clk) begin
        if (red_we && t_ss < 0) t_ss = cyc;
        if (vm_we[0] && vm_waddr[13:0] == 14'd12296 && t_r < 0) t_r = cyc;
    end
    initial begin
        if (!$value$plusargs("R=%h", rexp)) rexp = 0;
        if (!$value$plusargs("EPS=%h", eps)) eps = 32'h358637bd;
        $readmemh("q3h_x.hex", mem, 0, 8191);
        nout = 0; nin = 0; abase = 0; aso = 0; asi = 0; cbase = 0; cso = 0; csi = 0; dbase = 0; dso = 0; dsi = 0;
        rbase = 0; rso = 0; ma = 0; ad = 0; sfu = 0; dst = 0; red = 0; redsq = 0; imm1 = 0; imm2 = 0;
        repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk); #0.1;
        // op 1: residual + sum of squares (4,096 = 64 vectors)
        nout = 1; nin = 4096; abase = 0; asi = 1; cbase = 4096; csi = 1; ad = 3'd2; dst = 2'd1; dbase = 0; dsi = 1;
        red = 2'd1; redsq = 1; rbase = 12288; rso = 1;
        go = 1; @(posedge clk); #0.1; go = 0;
        t_last = cyc + 64 - 1;                       // the 64th vector issues 63 edges after the first
        while (t_ss < 0) begin @(posedge clk); #0.1; end
        // op 2 at the first ready edge after SSX is in the VM
        nout = 1; nin = 1; abase = 12288; asi = 0; cbase = 0; csi = 0; ma = 2'd3; imm1 = 32'h39800000; ad = 3'd4;
        imm2 = eps; sfu = 3'd3; dst = 2'd1; dbase = 12296; dsi = 0; red = 0; redsq = 0;
        @(posedge clk); #0.1;
        while (!ready) begin @(posedge clk); #0.1; end
        t_go2 = cyc;
        go = 1; @(posedge clk); #0.1; go = 0;
        while (t_r < 0) begin @(posedge clk); #0.1; end
        repeat (4) @(posedge clk);
        $display("Q3H_SU last vector issue -> SSX written: %0d edges; SSX -> rsqrt op go: %0d; go -> r written: %0d;",
                 t_ss - t_last, t_go2 - t_ss, t_r - t_go2);
        $display("Q3H_SU last vector issue -> r: %0d edges (core; + IS 1 + OS 1 in ot_qfd_sp_su64_static_entries)", t_r - t_last);
        $display("%s r %h golden %h fault %0d", (mem[12296] == rexp && !fault) ? "PASS" : "FAIL", mem[12296], rexp, fault);
        $finish;
    end
endmodule
