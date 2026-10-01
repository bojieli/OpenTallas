`timescale 1ns/1ps
// W19 production host-loader integration: timing-faithful HBM -> expert fetch -> payload/tag
// adapter -> unchanged SM bulk-copy/SRAM/arithmetic. All exponent bytes traverse
// DRAM. Uses the existing full-K real-operand packing and golden result format.
module tb_w19_payload_loader;
    parameter integer SUB = 4, LBS = 2, LSB = 16, NC = 2, XDEPTH = 128, RMAX = 256, LEV = 4;
    localparam integer RW = $clog2(RMAX);
    localparam integer FRAGW = NC * (SUB * LBS * 266 + SUB * LSB * 16);
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg start = 0;
    reg [RW:0] op_rows; reg [15:0] op_c; reg [7:0] op_g; reg op_scale; reg op_gs; reg [1:0] op_fmt;
    wire busy;
    reg d_valid = 0; wire d_ready; reg [31:0] d_base = 0; reg [23:0] d_lines;
    wire req_v; wire [31:0] req_addr; wire [9:0] req_tag;
    wire rsp_v; wire [9:0] rsp_tag; wire [1087:0] rsp_data;
    reg xw_en = 0; reg [$clog2(XDEPTH)-1:0] xw_addr; reg [6:0] xw_grp; reg [8*256-1:0] xw_data; integer gg;
    wire rv; wire [RW-1:0] rrow; wire [NC*32-1:0] rdata; wire fault; wire arrive; wire released;
    reg release_in = 0;
    ot_gpu_sm_v #(.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .RMAX(RMAX), .LEV(LEV), .XD(XDEPTH), .MAX_OUT(512)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g), .op_gs(op_gs),
        .op_fmt(op_fmt), .busy(busy), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base),
        .d_lines(d_lines), .req_v(req_v), .req_ready(adapter_req_ready && allow_req), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp),
        .xw_data(xw_data), .rv(rv), .rrow(rrow), .rdata(rdata), .fault(fault), .arrive(arrive),
        .release_in(release_in), .released(released));
    reg [1087:0] lines [0:65535];
    reg [FRAGW+2047:0] xwords [0:XDEPTH-1];
    reg [31:0] cfg [0:7];
    // Compact transport: consecutive 136-B payloads, final HBM line padding only.
    // No weights or exponents reach rsp_data except through the HBM model.
    // The tag FIFO joins independent SM read requests to the ordered fetch
    // stream; all ready/valid transfers are counted at the sampling edge.
    localparam integer AW = 24, NPC = 32, MEMW = 262144;
    wire fqv, fqr, evr, fidle, fsv;
    wire [AW-1:0] fa;
    wire [5:0] fn;
    wire [15:0] ft;
    wire [NPC-1:0] hv, hr;
    wire [NPC*16-1:0] ht;
    wire [NPC*5-1:0] hb;
    wire [NPC*256-1:0] hd;
    wire [1023:0] fsd;
    reg ev = 0;
    reg [8:0] expert_id;
    wire [15:0] transport_lines = (nlines * 136 + 127) / 128;
    wire [21:0] expert_base = expert_id * transport_lines;
    wire stall_mode = cfg[7][0];
    wire allow_req = !stall_mode || (cyc % 17 >= 7);
    wire allow_line = !stall_mode || (cyc % 13 >= 5);
    wire adapter_req_ready, adapter_idle, adapter_fault;
    wire [3:0] sv, sr;
    wire [95:0] si;
    wire [63:0] se;
    wire [1023:0] sd;
    wire fsready;
    ot_gpu_payload_line_bridge bridge (.clk(clk), .rst_n(rst_n), .start(start), .epoch({7'd0,expert_id}),
        .line_valid(fsv), .line_ready(fsready), .line_data(fsd), .sector_valid(sv),
        .sector_ready(sr & {4{allow_line}}), .sector_index(si), .sector_epoch(se), .sector_data(sd));
    ot_gpu_payload_assemble #(.ENABLE(1)) adapter (.clk(clk), .rst_n(rst_n), .cfg_valid(start), .cfg_ready(),
        .cfg_payloads(d_lines), .cfg_req_base(32'd0), .cfg_epoch({7'd0,expert_id}),
        .sector_valid(sv & {4{allow_line}}), .sector_ready(sr), .sector_index(si), .sector_epoch(se), .sector_data(sd),
        .req_valid(req_v && allow_req), .req_ready(adapter_req_ready), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_valid(rsp_v), .rsp_ready(1'b1), .rsp_tag(rsp_tag), .rsp_data(rsp_data),
        .idle(adapter_idle), .fault(adapter_fault));
    ot_gpu_expert_fetch #(.NSM(1), .NPC(NPC), .DEPTH(64), .MAX_OUT(32), .DQ(4)) fetch (
        .clk(clk), .rst_n(rst_n), .cfg_base(22'd0), .cfg_exp_lines(transport_lines),
        .cfg_off(16'd0), .cfg_lines(transport_lines), .e_valid(ev), .e_ready(evr), .e_id(expert_id),
        .req_v(fqv), .req_rdy(fqr), .req_addr(fa), .req_len(fn), .req_tag(ft),
        .rsp_v(hv), .rsp_rdy(hr), .rsp_tag(ht), .rsp_beat(hb), .rsp_data(hd),
        .s_valid(fsv), .s_ready(fsready), .s_data(fsd), .idle(fidle));
    ot_hdc_hbm_model #(.NPC(NPC), .AW(AW), .MEM_WORDS(MEMW), .TAGW(16), .LENW(6), .BEATW(5),
        .CLK_PS(833), .REQ_PS(15000), .RSP_PS(15000), .PC_RDY(1), .QD(64), .RQD(32)) hbm (
        .clk(clk), .rst_n(rst_n), .req_v(fqv), .req_rdy(fqr), .pc_room(), .req_we(1'b0),
        .req_addr(fa), .req_len(fn), .req_tag(ft), .req_wdata(256'd0),
        .rsp_v(hv), .rsp_rdy(hr), .rsp_tag(ht), .rsp_beat(hb), .rsp_data(hd));
    integer nlines, i, ii, kk, fo, seed, pick, cyc, t0, t_first, t_last, nres, t_lastline, consumed;
    integer fetched = 0, returned = 0, first_req = -1, first_sector = -1, first_payload = -1, stalls = 0;
    reg [1023:0] dir;
    always @(posedge clk) if (rst_n) begin
        if (ev && evr) ev <= 0;
        if (start) ev <= 1;
        if (fqv && fqr && first_req < 0) first_req = cyc;
        if (|(hv & hr)) if (first_sector < 0) first_sector = cyc;
        if (fsv && !fsready) stalls = stalls + 1;
        if (fsv && fsready) fetched = fetched + 1;
        if (rsp_v) begin
            returned = returned + 1;
            if (first_payload < 0) first_payload = cyc;
        end
        if (adapter_fault) $fatal(1, "production adapter fault");
    end
    always @(posedge clk) cyc <= cyc + 1;
    always @(posedge clk) if (dut.w_valid && dut.w_ready) begin consumed = consumed + 1; t_lastline = $time; end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        seed = 7; cyc = 0; nres = 0; consumed = 0;
        $readmemh({dir, "/cfg.hex"}, cfg);
        op_rows = cfg[0]; op_c = cfg[1]; op_g = cfg[2]; op_fmt = cfg[3]; nlines = cfg[4]; op_gs = cfg[5];
        $readmemh({dir, "/lines.hex"}, lines);
        expert_id = cfg[6];
        // The host loader supplies every weight/exponent byte and padding.
        if (cfg[7][2:1] != 0) $fatal(1,"fault injection belongs to retained sector proof");
        $readmemh({dir, "/payload_sectors.hex"}, hbm.mem);
        $readmemh({dir, "/x.hex"}, xwords);
        fo = $fopen({dir, "/out.txt"}, "w");
        repeat (4) @(posedge clk);
        rst_n = 1;
        @(posedge clk);
        for (ii = 0; ii < XDEPTH; ii = ii + 1)
            for (gg = 0; gg < (FRAGW + 2047) / 2048; gg = gg + 1) begin
                @(negedge clk); xw_en = 1; xw_addr = ii; xw_grp = gg; xw_data = xwords[ii][gg * 2048 +: 2048];
            end
        @(negedge clk); xw_en = 0; d_valid = 1; d_lines = nlines;
        @(negedge clk); d_valid = 0; start = 1;
        t0 = $time;
        @(negedge clk); start = 0;
    end
    reg [RMAX-1:0] seen_rows = 0;
    always @(posedge clk) if (rv) begin
        if (rrow >= op_rows || seen_rows[rrow]) $fatal(1, "duplicate or out-of-range SM result");
        seen_rows[rrow] = 1;
        if (nres == 0) t_first = $time;
        t_last = $time;
        $fwrite(fo, "%0d %h\n", rrow, rdata);
        nres = nres + 1;
    end
    always @(posedge clk) release_in <= arrive;
    initial begin
        #5;
        wait (rst_n); wait (start); wait (!start); wait (busy); wait (!busy);
        repeat (4) @(posedge clk);
        $fwrite(fo, "# cycles_start_to_done %0d first_result %0d last_result %0d lines %0d consumed %0d fault %0d released %0d drain_last_line_to_last_result %0d\n",
                ($time - t0), t_first - t0, t_last - t0, nlines, consumed, fault, released, t_last - t_lastline);
        if (nres != op_rows || consumed != nlines || fault) $fatal(1, "SM result/count/fault");
        if (fetched != (nlines*136+127)/128 || returned != nlines || !adapter_idle || !fidle)
            $fatal(1, "fetch did not drain exactly");
        $fwrite(fo, "# fetched %0d returned %0d first_req %0d first_sector %0d first_payload %0d fetch_stalls %0d refreshes %0d\n",
            fetched, returned, first_req, first_sector, first_payload, stalls, hbm.st_ref[0]);
        $fclose(fo);
        $finish;
    end
    initial begin #20000; $fwrite(fo, "# TIMEOUT\n"); $fclose(fo); $finish; end
endmodule
