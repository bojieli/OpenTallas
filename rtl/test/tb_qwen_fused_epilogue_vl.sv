`timescale 1ns/1ps
// Fused post-all-reduce epilogue gate (tools/qwen_fused_epilogue_gate.py), Verilator.
// The production vector stream unit (ot_hdc_vstream, SW lanes) with a
// behavioural vector memory (+DIR/vm.hex) and constant ROM (+DIR/crom.hex,
// {hi, lo} = {0, post-TP scale}).  Runs ONE of two programs over 4,096 elements:
//   +MODE=0  the pinned two-op epilogue (tools/hdc_qwen_fullshape_program_w12.py
//            insert_post_tp_scales + the residual op):
//              op A: T1 = T1 x crom[S]          (MC_C, c from the constant ROM)
//              op B: X  = X + T1, r = sum X^2   (AD_C, reducer sum of squares)
//   +MODE=1  the fused op (tools/qwen_rom_async_coll.py):
//              X = (T1 x crom[S]) + X, r = sum X^2   (MA_AB with b from the
//              constant ROM, then AD_C with c = X; same reducer)
// The fused op issues with the residual op's shape; each op issues when the unit
// is idle.  Dumps X and the reducer result; prints the fault cycles.
module tb_qwen_fused_epilogue_vl #(
    parameter integer SW = 64,
    parameter integer LV = 7
);
    reg clk = 1'b0;
    always #5 clk = ~clk;
    localparam integer AW = 24, NW = 16, VM = 16384, NEL = 4096;
    localparam integer T1 = 0, X = 4096, S = 0, R = 16160;
    reg [31:0] vm [0:VM-1];
    reg [63:0] crom [0:NEL-1];
    reg rst_n = 1'b0, go = 1'b0;
    reg [NW-1:0] nout, nin;
    reg [AW-1:0] abase, bbase, cbase, dbase;
    reg bsrc, csrc, mc, redsq;
    reg [1:0] ma, red, dst;
    reg [2:0] ad;
    wire ready, idle;
    wire [SW-1:0] va_re, vb_re, vc_re, crom_re, vm_we, kv_we;
    wire [SW*AW-1:0] va_addr, vb_addr, vc_addr, crom_addr, vm_waddr, kv_waddr;
    reg  [SW*32-1:0] va_q, vb_q, vc_q;
    reg  [SW*64-1:0] crom_q;
    wire [SW*32-1:0] vm_wdata, kv_wdata;
    wire wrom_re, red_we, fault;
    wire [AW-1:0] wrom_addr, red_addr;
    wire [31:0] red_data;
    wire [15:0] progress, progress_rows;
    ot_hdc_vstream #(.SW(SW), .LV(LV), .WR(64), .AW(AW), .NW(NW)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(nout), .i_nin(nin),
        .i_asrc(1'b0), .i_abase(abase), .i_aso(24'd0), .i_asi(24'd1),
        .i_bsrc(bsrc), .i_bbase(bbase), .i_bso(24'd0), .i_bsi(24'd1),
        .i_csrc(csrc), .i_cbase(cbase), .i_cso(24'd0), .i_csi(24'd1),
        .i_ma(ma), .i_mb(2'd0), .i_ad(ad), .i_sfu(3'd0), .i_mc(mc), .i_md(1'b0),
        .i_dst(dst), .i_dbase(dbase), .i_dso(24'd0), .i_dsi(24'd1),
        .i_red(red), .i_redsq(redsq), .i_rbase(24'(R)), .i_rso(24'd1), .i_imm1(32'd0), .i_imm2(32'd0),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q),
        .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q({(64*16){1'b0}}),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .red_we(red_we), .red_addr(red_addr), .red_data(red_data),
        .progress(progress), .progress_rows(progress_rows), .fault(fault));
    integer q, cyc = 0, mode = 0, phase = 0, nops = 0, fault_cycles = 0, go_cyc = 0, busy_cycles = 0, k;
    reg [8*512-1:0] dir;
    always @(posedge clk) begin
        for (q = 0; q < SW; q = q + 1) begin
            if (va_re[q]) va_q[32*q +: 32] <= vm[va_addr[q*AW +: 14]];
            if (vb_re[q]) vb_q[32*q +: 32] <= vm[vb_addr[q*AW +: 14]];
            if (vc_re[q]) vc_q[32*q +: 32] <= vm[vc_addr[q*AW +: 14]];
            if (crom_re[q]) crom_q[64*q +: 64] <= crom[crom_addr[q*AW +: 12]];
            if (vm_we[q]) vm[vm_waddr[q*AW +: 14]] <= vm_wdata[32*q +: 32];
        end
        if (red_we) vm[red_addr[13:0]] <= red_data;
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("MODE=%d", mode)) mode = 0;
        $readmemh({dir, "/vm.hex"}, vm);
        $readmemh({dir, "/crom.hex"}, crom);
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        go <= 1'b0;
        if (cyc == 5) rst_n <= 1'b1;
        if (fault) fault_cycles = fault_cycles + 1;
        if (red_we) $display("RED cyc=%0d addr=%0d data=%08h", cyc, red_addr, red_data);
        if (cyc > 10) case (phase)
            0: if (idle && ready && !go) begin
                   nout <= 1; nin <= NEL; dst <= 2'd1; csrc <= 1'b0; bsrc <= 1'b0; mc <= 1'b0; ma <= 2'd0;
                   ad <= 3'd0; red <= 2'd0; redsq <= 1'b0; cbase <= 0; bbase <= 0;
                   if (mode == 0 && nops == 0) begin           // op A: T1 = T1 x crom[S]
                       abase <= T1; csrc <= 1'b1; cbase <= S; mc <= 1'b1; dbase <= T1;
                   end else if (mode == 0) begin                // op B: X = X + T1, sum of squares
                       abase <= X; cbase <= T1; ad <= 3'd2; dbase <= X; red <= 2'd1; redsq <= 1'b1;
                   end else begin                               // fused: X = T1 x crom[S] + X, sum of squares
                       abase <= T1; bsrc <= 1'b1; bbase <= S; ma <= 2'd1; cbase <= X; ad <= 3'd2;
                       dbase <= X; red <= 2'd1; redsq <= 1'b1;
                   end
                   go <= 1'b1; go_cyc = cyc; nops = nops + 1; phase <= 1;
               end
            1: phase <= 2;
            2: if (idle && ready) begin
                   busy_cycles = busy_cycles + (cyc - go_cyc);
                   phase <= (nops == (mode == 0 ? 2 : 1)) ? 4 : 0;
                   go_cyc = cyc;
               end
            4: if (cyc - go_cyc > 400) phase <= 3;
            3: begin
                   for (k = 0; k < NEL; k = k + 1) $display("X %0d %08h", k, vm[X + k]);
                   $display("FUSEDEPI DONE mode=%0d ops=%0d busy_cycles=%0d fault_cycles=%0d r=%08h",
                            mode, nops, busy_cycles, fault_cycles, vm[R]);
                   $finish;
               end
            default: ;
        endcase
        if (cyc > 200000) $fatal(1, "timeout");
    end
endmodule
