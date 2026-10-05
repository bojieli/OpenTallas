`timescale 1ns/1ps
// Performance and arithmetic bench of the vector stream unit (ot_hdc_vstream):
// SW lanes, behavioural vector memory loaded from +DIR/vm.hex.  Runs four ops
// back to back, each after the unit drains:
//   0 COPY  vm[B + i] = vm[A + i]            (no SFU, no reduction)  n elements
//   1 SUM   r[0] = sum vm[A + i]              (R-ARITH)               n elements
//   2 MAX   r[1] = max vm[A + i]                                      n elements
//   3 SSQ   r[2] = sum vm[A + i]^2  over nseg segments of n/nseg elements
// For each op it prints the go cycle, the first and last element write, and the
// reducer result writes, so tools/rtl_hdc_vstream_perf_campaign.py can check
// the throughput (SW elements a cycle), the pipeline depths and every result
// bit for bit against tools/hdc_golden.py.
module tb_hdc_vstream_perf #(
    parameter integer SW = 8,
    parameter integer LV = 4
) (input wire clk);
    localparam integer AW = 24, NW = 16, VM = 65536;
    reg [31:0] vm [0:VM-1];
    reg rst_n = 1'b0, go = 1'b0;
    reg [NW-1:0] nout, nin;
    reg [AW-1:0] abase, aso, dbase, dso, rbase;
    reg [1:0] red, dst;
    reg redsq;
    wire ready, idle;
    wire [SW-1:0] va_re, vb_re, vc_re, crom_re, vm_we, kv_we;
    wire [SW*AW-1:0] va_addr, vb_addr, vc_addr, crom_addr, vm_waddr, kv_waddr;
    reg  [SW*32-1:0] va_q;
    wire [SW*32-1:0] vm_wdata, kv_wdata;
    wire wrom_re, red_we, fault;
    wire [AW-1:0] wrom_addr, red_addr;
    wire [31:0] red_data;
    wire [15:0] progress;
    ot_hdc_vstream #(.SW(SW), .LV(LV), .WR(64), .AW(AW), .NW(NW)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(nout), .i_nin(nin),
        .i_asrc(1'b0), .i_abase(abase), .i_aso(aso), .i_asi(24'd1),
        .i_bsrc(1'b0), .i_bbase(24'd0), .i_bso(24'd0), .i_bsi(24'd0),
        .i_csrc(1'b0), .i_cbase(24'd0), .i_cso(24'd0), .i_csi(24'd0),
        .i_ma(2'd0), .i_mb(2'd0), .i_ad(3'd0), .i_sfu(3'd0), .i_mc(1'b0), .i_md(1'b0),
        .i_dst(dst), .i_dbase(dbase), .i_dso(dso), .i_dsi(24'd1),
        .i_red(red), .i_redsq(redsq), .i_rbase(rbase), .i_rso(24'd1), .i_imm1(32'd0), .i_imm2(32'd0),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q),
        .vb_re(vb_re), .vb_addr(vb_addr), .vb_q({(SW*32){1'b0}}),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q({(SW*32){1'b0}}),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q({(64*16){1'b0}}),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q({(SW*64){1'b0}}),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .red_we(red_we), .red_addr(red_addr), .red_data(red_data),
        .progress(progress), .fault(fault));
    integer q, cyc = 0, op = 0, phase = 0, go_cyc = 0, first_w = -1, last_w = -1, n_el = 1024, n_seg = 8;
    reg [8*512-1:0] dir;
    always @(posedge clk) begin
        for (q = 0; q < SW; q = q + 1) begin
            if (va_re[q]) va_q[32*q +: 32] <= vm[va_addr[q*AW +: 16]];
            if (vm_we[q]) vm[vm_waddr[q*AW +: 16]] <= vm_wdata[32*q +: 32];
        end
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("N=%d", n_el)) n_el = 1024;
        if (!$value$plusargs("NSEG=%d", n_seg)) n_seg = 8;
        $readmemh({dir, "/vm.hex"}, vm);
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        go <= 1'b0;
        if (cyc == 5) rst_n <= 1'b1;
        if (|vm_we) begin
            if (first_w < 0) first_w = cyc;
            last_w = cyc;
        end
        if (red_we) $display("RED op=%0d cyc=%0d addr=%0d data=%08h", op, cyc, red_addr, red_data);
        if (cyc > 10) case (phase)
            0: if (idle && ready) begin
                   // issue op `op`
                   abase <= 0; aso <= n_el / (op == 3 ? n_seg : 1); rbase <= 60000 + op; redsq <= (op == 3);
                   nout <= (op == 3) ? n_seg : 1; nin <= (op == 3) ? n_el / n_seg : n_el;
                   dst <= (op == 0) ? 2'd1 : 2'd0; dbase <= 32768; dso <= 0;
                   red <= (op == 0) ? 2'd0 : (op == 2) ? 2'd2 : 2'd1;
                   go <= 1'b1; go_cyc = cyc + 1; first_w = -1; last_w = -1; phase <= 1;
               end
            1: phase <= 2;
            2: if (idle && !go) begin
                   $display("OP op=%0d go=%0d first_write=%0d last_write=%0d idle=%0d fault=%0d",
                            op, go_cyc, first_w, last_w, cyc, fault);
                   if (op == 3) begin $display("DONE"); $finish; end
                   op <= op + 1; phase <= 0;
               end
        endcase
        if (cyc > 200000) begin $display("TIMEOUT"); $finish; end
    end
endmodule
