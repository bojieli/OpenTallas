`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Unit bench of the Qwen ROM system control plane:
//   * ot_qwen_sys_rst_seq: the power-up order (host -> links -> HBM -> dies ->
//     ready) with the conditions arriving late, a soft reset that re-runs it,
//     and the two boot faults (+LINK_NEVER: link training never completes,
//     boot_err 1; +HBM_BAD: an HBM check fails, boot_err 3);
//   * ot_qwen_sys_csr: SYS_ID / SYS_STATUS reads through the AXI4-Lite split,
//     sticky FAULT_STATUS, FAULT_FIRST = the lowest new source, the fault
//     interrupt under FAULT_MASK, write-1-to-clear, and a host-interface
//     register access passed through the split;
//   * ot_qwen_tp_seq_sys: the collective tag at positions 5 and 261 (aliased by
//     the W12 tag, distinct with TAG_FULL), a stray collective record (fault
//     code 1) and the wait-bound watchdog (fault code 2).
// ---------------------------------------------------------------------------
module tb_qwen_sys_ctrl (input wire clk);
    integer cyc = 0, bad = 0, phase = 0;
    reg por_n = 0;
    reg link_never = 0, hbm_bad = 0;
    // ---------------------------------------------------------------- reset sequencer
    reg [3:0] lup = 0;
    reg [1:0] bdone = 0, bok = 0;
    wire host_rst_n, link_rst_n, hbm_rst_n, boot_go, die_rst_n, sys_ready, boot_fault;
    wire [3:0] boot_state, boot_err;
    wire [31:0] boot_cycles;
    wire soft_rst;
    ot_qwen_sys_rst_seq #(.NL(4), .ND(2), .T_LINK(500), .T_HBM(500)) u_rst (
        .clk(clk), .por_n(por_n), .soft_rst(soft_rst), .link_up(lup), .boot_done(bdone), .boot_ok(bok),
        .host_rst_n(host_rst_n), .link_rst_n(link_rst_n), .hbm_rst_n(hbm_rst_n), .boot_go(boot_go),
        .die_rst_n(die_rst_n), .sys_ready(sys_ready), .boot_fault(boot_fault), .boot_state(boot_state),
        .boot_err(boot_err), .boot_cycles(boot_cycles));
    // the "links" train 40 cycles after their reset is released; the "HBM checks" answer 30 cycles after boot_go
    integer lt = -1, bt = -1;
    always @(posedge clk) begin
        if (!link_rst_n) begin lup <= 0; lt <= -1; end
        else begin
            if (lt < 0) lt <= cyc;
            if (lt >= 0 && cyc - lt >= 40 && !link_never) lup <= 4'hF;
            else if (lt >= 0 && cyc - lt >= 10 && !link_never) lup <= 4'h5;   // partial training first
        end
        if (!hbm_rst_n) begin bdone <= 0; bok <= 0; bt <= -1; end
        else begin
            if (boot_go) bt <= cyc;
            if (bt >= 0 && cyc - bt == 30) begin bdone <= 2'b11; bok <= hbm_bad ? 2'b01 : 2'b11; end
        end
    end
    // order checks
    always @(posedge clk) if (por_n) begin
        if (hbm_rst_n && lup != 4'hF) begin bad = bad + 1; $display("ORDER: HBM released before every link trained"); end
        if (die_rst_n && !(bdone == 2'b11 && bok == 2'b11)) begin bad = bad + 1; $display("ORDER: dies released before HBM check"); end
        if (sys_ready && !die_rst_n) begin bad = bad + 1; $display("ORDER: ready before dies"); end
        if (!host_rst_n && link_rst_n) begin bad = bad + 1; $display("ORDER: links before host"); end
    end

    // ---------------------------------------------------------------- CSR
    reg s_awvalid = 0, s_wvalid = 0, s_arvalid = 0;
    reg [12:0] s_awaddr = 0, s_araddr = 0;
    reg [31:0] s_wdata = 0;
    wire s_awready, s_wready, s_bvalid, s_arready, s_rvalid;
    wire [31:0] s_rdata;
    wire h_awvalid, h_wvalid, h_arvalid, h_bready, h_rready;
    wire [11:0] h_awaddr, h_araddr;
    wire [31:0] h_wdata;
    reg  h_bvalid = 0, h_rvalid = 0;
    reg  [31:0] h_rdata = 0;
    reg  [31:0] fsrc = 0;
    wire irq;
    ot_qwen_sys_csr #(.NCNT(2)) u_csr (
        .clk(clk), .rst_n(host_rst_n),
        .s_awvalid(s_awvalid), .s_awready(s_awready), .s_awaddr(s_awaddr), .s_wvalid(s_wvalid), .s_wready(s_wready),
        .s_wdata(s_wdata), .s_wstrb(4'hF), .s_bvalid(s_bvalid), .s_bready(1'b1), .s_bresp(),
        .s_arvalid(s_arvalid), .s_arready(s_arready), .s_araddr(s_araddr), .s_rvalid(s_rvalid), .s_rready(1'b1),
        .s_rdata(s_rdata), .s_rresp(),
        .h_awvalid(h_awvalid), .h_awready(h_awvalid && h_wvalid), .h_awaddr(h_awaddr), .h_wvalid(h_wvalid),
        .h_wready(h_awvalid && h_wvalid), .h_wdata(h_wdata), .h_wstrb(), .h_bvalid(h_bvalid), .h_bready(h_bready),
        .h_arvalid(h_arvalid), .h_arready(h_arvalid), .h_araddr(h_araddr), .h_rvalid(h_rvalid), .h_rready(h_rready),
        .h_rdata(h_rdata), .h_irq(1'b0),
        .sys_ready(sys_ready), .boot_fault(boot_fault), .boot_state(boot_state), .boot_err(boot_err),
        .soft_rst(soft_rst), .fault_src(fsrc), .cnt({32'd7, 32'd9}), .irq(irq));
    // a stand-in host-interface slave: one register at 0x0FC
    reg [31:0] hreg = 32'h0;
    always @(posedge clk) begin
        h_bvalid <= 1'b0; h_rvalid <= 1'b0;
        if (h_awvalid && h_wvalid) begin h_bvalid <= 1'b1; if (h_awaddr == 12'h0FC) hreg <= h_wdata; end
        if (h_arvalid) begin h_rvalid <= 1'b1; h_rdata <= (h_araddr == 12'h0FC) ? hreg : 32'hDEAD; end
    end

    // ---------------------------------------------------------------- sequencer successor
    localparam integer NW = 16, DAW = 6, TAGW = 2 + 2 * NW + DAW;
    reg  sq_rst_n = 0, sq_start = 0, sq_core_done = 0, sq_rv = 0;
    reg  [NW-1:0] sq_pos = 0;
    wire [TAGW-1:0] tag_full, tag_w12;
    wire f_full, f_w12;
    wire [2:0] fc_full, fc_w12;
    wire sq_core_start;
    reg  [63:0] sq_desc = 64'd1 | (64'd2 << 10);   // one all-reduce of 2 words, then END
    ot_qwen_tp_seq_sys #(.TAG_FULL(1), .STRAY_FAULT(1), .WDOG(200), .N(4), .NW(NW), .TAGW(TAGW)) u_full (
        .clk(clk), .rst_n(sq_rst_n), .start(sq_start), .token(16'd7), .pos(sq_pos), .done(), .next_token(),
        .next_val(), .fault(f_full), .coll_busy(), .core_start(sq_core_start), .core_token(), .core_pos(),
        .core_done(sq_core_done), .core_next_token(16'd0), .core_next_val(32'd0), .core_fault(1'b0), .prog_base(),
        .desc_re(), .desc_addr(), .desc_q(sq_desc), .vm_re(), .vm_raddr(), .vm_rq(512'd0), .vm_we(), .vm_waddr(),
        .vm_wdata(), .c_valid(), .c_ready(1'b0), .c_data(), .c_last(), .c_mode(), .c_tag(tag_full),
        .r_valid(sq_rv), .r_data(512'd0), .r_last(1'b0), .r_rank(2'd0), .r_err(1'b0), .fault_code(fc_full));
    ot_qwen_tp_seq_sys #(.N(4), .NW(NW), .TAGW(32)) u_w12 (
        .clk(clk), .rst_n(sq_rst_n), .start(sq_start), .token(16'd7), .pos(sq_pos), .done(), .next_token(),
        .next_val(), .fault(f_w12), .coll_busy(), .core_start(), .core_token(), .core_pos(),
        .core_done(sq_core_done), .core_next_token(16'd0), .core_next_val(32'd0), .core_fault(1'b0), .prog_base(),
        .desc_re(), .desc_addr(), .desc_q(sq_desc), .vm_re(), .vm_raddr(), .vm_rq(512'd0), .vm_we(), .vm_waddr(),
        .vm_wdata(), .c_valid(), .c_ready(1'b0), .c_data(), .c_last(), .c_mode(), .c_tag(tag_w12[31:0]),
        .r_valid(sq_rv), .r_data(512'd0), .r_last(1'b0), .r_rank(2'd0), .r_err(1'b0), .fault_code(fc_w12));
    assign tag_w12[TAGW-1:32] = 0;

    // ---------------------------------------------------------------- script
    reg [31:0] rd;
    reg busy = 0, wr_op = 0;
    integer st = 0, t0 = 0;
    reg [TAGW-1:0] tf5, tw5;
    task automatic wr(input [12:0] a, input [31:0] d); begin s_awaddr <= a; s_wdata <= d; s_awvalid <= 1; s_wvalid <= 1; busy <= 1; wr_op <= 1; end endtask
    task automatic rdr(input [12:0] a); begin s_araddr <= a; s_arvalid <= 1; busy <= 1; wr_op <= 0; end endtask
    task automatic expect32(input [31:0] got, input [31:0] exp, input [8*24-1:0] what);
        begin if (got !== exp) begin bad = bad + 1; $display("CHECK %0s got %08x expected %08x", what, got, exp); end end
    endtask
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) por_n <= 1;
        if (s_awvalid && s_awready) begin s_awvalid <= 0; s_wvalid <= 0; end
        if (busy && wr_op && s_bvalid) busy <= 0;
        if (s_arvalid && s_arready) s_arvalid <= 0;
        if (busy && !wr_op && s_rvalid) begin busy <= 0; rd <= s_rdata; end
        sq_start <= 0; sq_rv <= 0; sq_core_done <= 0;
        if (!busy && !s_awvalid && !s_arvalid && host_rst_n) case (st)
            0: begin rdr(13'h1000); st <= 1; end
            1: begin expect32(rd, 32'h5153_5953, "SYS_ID"); st <= 2; end
            2: if (sys_ready || boot_fault) begin rdr(13'h1004); st <= 3; end
            3: begin
                if (link_never || hbm_bad) begin
                    expect32(rd[1], 1, "boot_fault"); expect32(rd[11:8], link_never ? 1 : 3, "boot_err");
                    st <= 50;
                end else begin
                    expect32(rd[0], 1, "sys_ready"); expect32(rd[7:4], 5, "boot_state");
                    $display("BOOT ready after %0d cycles", boot_cycles);
                    st <= 4;
                end
            end
            4: begin wr(13'h1008, 1); st <= 5; end                      // soft reset
            5: begin t0 <= cyc; st <= 6; end
            6: if (!sys_ready) st <= 7;
            7: if (sys_ready) begin $display("SOFT_RESET re-boot in %0d cycles", cyc - t0); st <= 8; end
               else if (cyc - t0 > 2000) begin bad = bad + 1; $display("CHECK soft reset did not complete"); st <= 8; end
            8: begin wr(13'h1014, 32'h0000_0030); st <= 9; end         // FAULT_MASK bits 4, 5
            9: begin fsrc <= 32'h0000_0028; st <= 10; end               // sources 3 and 5 at once
            10: begin fsrc <= 0; rdr(13'h1010); st <= 11; end
            11: begin expect32(rd, 32'h28, "FAULT_STATUS"); rdr(13'h1018); st <= 12; end
            12: begin expect32(rd, 32'h8000_0003, "FAULT_FIRST"); expect32(irq, 1, "irq"); wr(13'h1010, 32'h20); st <= 13; end
            13: begin rdr(13'h1010); st <= 14; end
            14: begin expect32(rd, 32'h08, "FAULT_STATUS after W1C"); expect32(irq, 0, "irq after W1C"); st <= 15; end
            15: begin wr(13'h1010, 32'h08); st <= 16; end
            16: begin rdr(13'h1018); st <= 17; end
            17: begin expect32(rd[31], 0, "FAULT_FIRST cleared"); rdr(13'h1024); st <= 18; end
            18: begin expect32(rd, 32'd7, "counter 1"); wr(13'h00FC, 32'hCAFE_F00D); st <= 19; end
            19: begin rdr(13'h00FC); st <= 20; end
            20: begin expect32(rd, 32'hCAFE_F00D, "host-interface split"); st <= 30; end
            // ---- sequencer successor
            30: begin sq_rst_n <= 1; sq_pos <= 5; st <= 31; end
            31: begin sq_start <= 1; st <= 32; end
            32: if (sq_core_start) begin sq_core_done <= 1; st <= 33; end
            33: if (st == 33) begin st <= 34; end
            34: begin tf5 <= tag_full; tw5 <= tag_w12; sq_rst_n <= 0; st <= 35; end
            35: begin sq_rst_n <= 1; sq_pos <= 261; st <= 36; end
            36: begin sq_start <= 1; st <= 37; end
            37: if (sq_core_start) begin sq_core_done <= 1; st <= 38; end
            38: st <= 39;
            39: begin
                $display("TAG pos 5: full=%h w12=%h  pos 261: full=%h w12=%h", tf5, tw5, tag_full, tag_w12);
                if (tw5 !== tag_w12) begin bad = bad + 1; $display("CHECK w12 tag expected to alias at 256"); end
                if (tf5 === tag_full) begin bad = bad + 1; $display("CHECK full tag must differ"); end
                t0 <= cyc; st <= 40;
            end
            // both sequencers now wait in S_COLL (c_ready = 0): the full one's watchdog must fire
            40: if (f_full) begin
                    expect32(fc_full[2], 1, "watchdog");
                    expect32(f_w12, 0, "default-off w12 never faults");
                    $display("WATCHDOG fired after %0d cycles", cyc - t0);
                    sq_rst_n <= 0; st <= 41;
                end else if (cyc - t0 > 1000) begin bad = bad + 1; $display("CHECK watchdog did not fire"); st <= 41; end
            41: begin sq_rst_n <= 1; st <= 42; end
            42: begin sq_rv <= 1; st <= 43; end                              // a stray record while idle
            43: st <= 44;
            44: begin expect32(fc_full[1], 1, "stray record"); expect32(f_w12, 0, "w12 drops stray silently"); st <= 60; end
            50: st <= 60;
            60: begin
                $display("CTRL mode=%0s mismatches=%0d", link_never ? "link_never" : hbm_bad ? "hbm_bad" : "normal", bad);
                if (bad == 0) $display("PASS"); else $display("FAIL");
                $finish;
            end
            default: ;
        endcase
        if (cyc > 100000) begin $display("TIMEOUT st=%0d", st); $display("FAIL"); $finish; end
    end
    initial begin
        if ($test$plusargs("LINK_NEVER")) link_never = 1;
        if ($test$plusargs("HBM_BAD")) hbm_bad = 1;
    end
endmodule
