`timescale 1ns/1ps
`default_nettype none
// VEH-FMT-SFU (10-19): arithmetic pre-check of sfu_fused_compile.py programmes on the REAL sfucore_SW arithmetic grid
// (ot_hgi_sfu_arithmetic_grid_m85 from the sw2 bundle master ot_hgi_sfu_core_split3.sv: 16 ot_su12_sfu lanes, the
// slice's parameters).  compiler_control = one row of <CTL> a cycle (as sfup_SW delivers it).  The VM is a word
// memory with a one-cycle synchronous read on every lane stream (rd_addr of cycle n -> rd_q in cycle n+1, the lane's
// capture contract); vm_we writes land at the edge.  The operand delivery itself (sfup
// io_word prefetch -> ot_hgi_sfu_vm_static_bridge -> sfr_SW relays -> sfu_SW taps) is NOT in this bench.
// Checks: every written word of <EXP> equals the fixture golden bit-exactly, no other address written, no lane
// fault / coll, no gather (vi_re), no KV write, every rd_src = VM.  Prints SFUGRID PASS / FAIL.
module tb_sfu_grid;
    parameter integer NCTL = 2048;      // sfup_SW rows; programmes are zero-padded (no emit)
    localparam integer AWM = 17;
    string CTL = "ctl.hex", VMF = "vm.txt", EXPF = "exp.txt";
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    reg [1741:0] ctl_mem [0:NCTL-1];
    reg [1741:0] control = 0;
    reg [31:0] vm [0:(1<<AWM)-1];
    reg [31:0] ex [0:(1<<AWM)-1];
    reg        exv [0:(1<<AWM)-1];
    reg        wr [0:(1<<AWM)-1];
    wire [15:0] vi_re, vm_we, kv_we, ro_v, fault, coll;
    wire [383:0] vi_addr, vm_waddr, kv_waddr;
    wire [1535:0] rd_addr; wire [63:0] rd_re; wire [127:0] rd_src;
    wire [511:0] vm_wdata, kv_wdata, ro_x;
    reg  [2047:0] rd_q = 0;
    ot_hgi_sfu_arithmetic_grid_m85 #(.BTREE(0)) dut(
        .clk_lane({16{clk}}), .clk_map({16{clk}}), .rst_lane_n({16{rst_n}}), .rst_map_n({16{rst_n}}),
        .control(control), .vi_q(512'd0), .rd_q(rd_q), .vi_re(vi_re), .vm_we(vm_we), .kv_we(kv_we), .ro_v(ro_v),
        .fault(fault), .coll(coll), .vi_addr(vi_addr), .vm_waddr(vm_waddr), .kv_waddr(kv_waddr), .rd_addr(rd_addr),
        .rd_re(rd_re), .rd_src(rd_src), .vm_wdata(vm_wdata), .kv_wdata(kv_wdata), .ro_x(ro_x));
    integer fd, r, i, j, s, cnt = -1, nexp = 0, nw = 0, bad = 0, stray = 0, ffault = 0, fcoll = 0, fgat = 0, fkv = 0;
    integer fsrc = 0, fhi = 0, last_w = -1, first_w = -1, maxp = 6;
    reg [31:0] a32, w32;
    // memory: rd_addr of cycle n answered on rd_q in cycle n + RDLAT (default 1: a synchronous read -- the lane's tag
    // pipe m_v -> capture cr_q samples rd_q at the second edge after rd_addr: "capture two cycles later (CAPR: three)",
    // ot_hdc_v41x_vec_lane_c12.sv)
    integer rdlat = 1, jj, ss, hh;
    reg [1535:0] ah [0:7];
    always @(posedge clk) begin
        ah[0] <= rd_addr;
        for (hh = 1; hh < 8; hh = hh + 1) ah[hh] <= ah[hh-1];
    end
    always @(*) begin
        for (jj = 0; jj < 16; jj = jj + 1)
            for (ss = 0; ss < 4; ss = ss + 1)
                rd_q[jj*128 + ss*32 +: 32] = vm[(rdlat == 0 ? rd_addr[jj*96 + ss*24 +: AWM] : ah[rdlat-1][jj*96 + ss*24 +: AWM])];
    end
    initial begin
        if (!$value$plusargs("CTL=%s", CTL)) CTL = "ctl.hex";
        if (!$value$plusargs("VM=%s", VMF)) VMF = "vm.txt";
        if (!$value$plusargs("EXP=%s", EXPF)) EXPF = "exp.txt";
        if (!$value$plusargs("MAXP=%d", maxp)) maxp = 6;
        if (!$value$plusargs("RDLAT=%d", rdlat)) rdlat = 1;
        for (i = 0; i < (1<<AWM); i = i + 1) begin vm[i] = 32'h7fc00001; exv[i] = 0; wr[i] = 0; end
        $readmemh(CTL, ctl_mem);
        fd = $fopen(VMF, "r"); if (fd == 0) $fatal(1, "no vm file");
        while (!$feof(fd)) begin r = $fscanf(fd, "%h %h\n", a32, w32); if (r == 2) vm[a32[AWM-1:0]] = w32; end
        $fclose(fd);
        fd = $fopen(EXPF, "r"); if (fd == 0) $fatal(1, "no exp file");
        while (!$feof(fd)) begin
            r = $fscanf(fd, "%h %h\n", a32, w32);
            if (r == 2) begin ex[a32[AWM-1:0]] = w32; exv[a32[AWM-1:0]] = 1; nexp = nexp + 1; end
        end
        $fclose(fd);
        repeat (8) @(posedge clk); rst_n = 1;
        repeat (8) @(posedge clk);
        cnt = 0;
    end
`ifdef SFU_DBG
    integer nd = 0;
    always @(posedge clk) if (cnt >= 0 && fault[0] && nd < 8) begin
        nd = nd + 1;
        $display("DBG fault lane0 edge %0d", cnt);
    end
    always @(posedge clk) if (cnt >= 0 && nd < 8 && (dut.g_lane[0].u_sfu.u.u.f_m1 | dut.g_lane[0].u_sfu.u.u.f_q |
        dut.g_lane[0].u_sfu.u.u.f_ad | dut.g_lane[0].u_sfu.u.u.f_m2 | dut.g_lane[0].u_sfu.u.u.f_sfu |
        dut.g_lane[0].u_sfu.u.u.f_e1m | dut.g_lane[0].u_sfu.u.u.f_e1a | dut.g_lane[0].u_sfu.u.u.f_e2 | dut.g_lane[0].u_sfu.u.u.f_d1))
        $display("DBG edge %0d m1 %0d q %0d ad %0d m2 %0d sfu %0d e1m %0d e1a %0d e2 %0d d1 %0d", cnt,
            dut.g_lane[0].u_sfu.u.u.f_m1, dut.g_lane[0].u_sfu.u.u.f_q, dut.g_lane[0].u_sfu.u.u.f_ad,
            dut.g_lane[0].u_sfu.u.u.f_m2, dut.g_lane[0].u_sfu.u.u.f_sfu, dut.g_lane[0].u_sfu.u.u.f_e1m,
            dut.g_lane[0].u_sfu.u.u.f_e1a, dut.g_lane[0].u_sfu.u.u.f_e2, dut.g_lane[0].u_sfu.u.u.f_d1);
`endif
    always @(posedge clk) if (cnt >= 0) begin
        control <= (cnt < NCTL) ? ctl_mem[cnt] : 1742'd0;
        for (j = 0; j < 16; j = j + 1) begin
            if (fault[j]) ffault = ffault + 1;
            if (coll[j]) fcoll = fcoll + 1;
            if (vi_re[j]) fgat = fgat + 1;
            if (kv_we[j]) fkv = fkv + 1;
            if (rd_re[j*4 +: 4] != 0 && rd_src[j*8 +: 8] != 0) fsrc = fsrc + 1;
            if (rd_re[j*4 +: 4] != 0 && (rd_addr[j*96 + AWM +: 24-AWM] | rd_addr[j*96 + 24 + AWM +: 24-AWM] |
                rd_addr[j*96 + 48 + AWM +: 24-AWM] | rd_addr[j*96 + 72 + AWM +: 24-AWM]) != 0) fhi = fhi + 1;
            if (vm_we[j]) begin
                a32 = {8'd0, vm_waddr[j*24 +: 24]};
                vm[a32[AWM-1:0]] <= vm_wdata[j*32 +: 32];
                wr[a32[AWM-1:0]] = 1;
                nw = nw + 1;
                if (first_w < 0) first_w = cnt;
                last_w = cnt;
                if (a32[23:AWM] != 0 || !exv[a32[AWM-1:0]]) begin
                    stray = stray + 1; if (stray < 5) $display("STRAY write lane %0d addr %0h edge %0d", j, a32, cnt);
                end
            end
        end
        cnt <= cnt + 1;
        if (cnt == NCTL + 200) begin
            for (i = 0; i < (1<<AWM); i = i + 1)
                if (exv[i] && (vm[i] !== ex[i] || !wr[i])) begin
                    bad = bad + 1;
                    if (bad < maxp) $display("MISMATCH addr %0h got %08h exp %08h written %0d", i, vm[i], ex[i], wr[i]);
                end
            $display("SFUGRID rows=%0d writes=%0d expected=%0d mismatches=%0d stray=%0d first_write=%0d last_write=%0d",
                     NCTL, nw, nexp, bad, stray, first_w, last_w);
            $display("SFUGRID fault=%0d coll=%0d gather=%0d kv=%0d non_vm_src=%0d addr_hi=%0d", ffault, fcoll, fgat,
                     fkv, fsrc, fhi);
            if (bad == 0 && stray == 0 && ffault == 0 && fcoll == 0 && fgat == 0 && fkv == 0 && fsrc == 0 && fhi == 0)
                $display("SFUGRID PASS");
            else $display("SFUGRID FAIL");
            $finish;
        end
    end
endmodule
`default_nettype wire
