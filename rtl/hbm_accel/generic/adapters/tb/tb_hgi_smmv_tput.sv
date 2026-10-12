`timescale 1ns/1ps
// el1011-hbm-smmv-b (2026-10-12): SM.MATVEC THROUGHPUT bench for the TRACK-B record engine.  Same production shape,
// vectors, HBM model (+LAT, +BWX10), real VM and golden check as tb_hgi_sm_tput, but records are DISPATCHED ON rec_rdy
// (the engine keeps up to W in flight) and the service of record i = ret_i - max(disp_i, ret_(i-1)) (retire to retire).
// ot_hgi_smmv (engine, NSM 32) -> ot_hgi_sm_xload (NXC 4, BD with XBD) -> x-write relay (slot base) -> 32 SMs (2 real
// ot_hbm_accel_smh + 30 shadows) -> ot_hgi_smmv_pub (record-pipelined) -> ot_hgi_vm_unit.
// Shadows: SM s replays real SM (s mod 2); per record r it is active iff M_r > s Q_r, emits rows < R_s(r) of the op the
// real SM is emitting (row pointer) and toggles its own arrive only for ops it is active in (arrive pointer).
// Mutants (must FAIL): MUT_ROW (pub drops s Q), MUT_SLOT (every x at slot 0), MUT_EARLY (retire on issue).
// B2 (+define+NCL=4): NCL cluster engines of NSM/NCL SMs each (strap sm_base = c NSM/NCL), each with its own x loader
// and record-pipelined pub on the VM; every record goes to all clusters (accepted when all are ready) and retires when
// the last cluster retires it.  Real SMs 0/1 sit in cluster 0; x writes of clusters > 0 reach shadows only.
module tb_hgi_smmv_tput;
`ifdef MUT_ROW
    localparam integer MW = 1;
`else
    localparam integer MW = 0;
`endif
`ifdef MUT_SLOT
    localparam integer MS = 1;
`else
    localparam integer MS = 0;
`endif
`ifdef MUT_EARLY
    localparam integer ME = 1;
`else
    localparam integer ME = 0;
`endif
`ifndef WIN
`define WIN 4
`endif
`ifndef NCL
`define NCL 1
`endif
    `include "tput_sizes.svh"
    localparam integer NSM = 32, NREAL = 2, CW = 106, NXC = 4, NPC = 4, NCL = `NCL, NSL = NSM / NCL;
    reg clk = 0;
    always #1 clk = ~clk;
    reg [937:0] recm [0:NREC-1]; reg [119:0] infm [0:NREC-1]; reg [2063:0] xwm [0:NXW-1];
    reg [287:0] vmim [0:NVMI-1]; reg [63:0] vmem [0:NVME-1]; reg [1119:0] linem [0:NLINE-1];
    reg [1087:0] lmem [0:LSPAN-1]; reg lhas [0:LSPAN-1];
    reg [8*256-1:0] dir; integer i, lat, bwx10;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("LAT=%d", lat)) lat = 104;
        if (!$value$plusargs("BWX10=%d", bwx10)) bwx10 = 31667;
        $readmemh({dir, "/tput_rec.mem"}, recm); $readmemh({dir, "/tput_info.mem"}, infm);
        $readmemh({dir, "/tput_vmi.mem"}, vmim); $readmemh({dir, "/tput_vme.mem"}, vmem); $readmemh({dir, "/tput_lines.mem"}, linem);
        for (i = 0; i < LSPAN; i = i + 1) lhas[i] = 1'b0;
        for (i = 0; i < NLINE; i = i + 1) begin lmem[linem[i][1119:1088] - LBASE] = linem[i][1087:0]; lhas[linem[i][1119:1088] - LBASE] = 1'b1; end
    end
    integer errors = 0, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [937:0] cur; reg rec_v = 0;
    wire rec_rdy; wire [NCL-1:0] c_rdy, c_done, c_fault, c_halt, c_pfault, c_xfault; wire [NCL*3-1:0] c_iss;
    wire fault = |c_fault;
    assign rec_rdy = &c_rdy;
    wire [NSM*CW-1:0] sm_cmd; wire [NSM*4-1:0] sm_ret; wire [2:0] iss_seq = c_iss[2:0];
    wire xw_en; wire [6:0] xw_addr, xw_grp; wire [2047:0] xw_data;
    wire [NSM-1:0] rv; wire [NSM*12-1:0] rrow; wire [NSM*256-1:0] rdata;
`ifdef XBD
    localparam integer XB = 1;
`else
    localparam integer XB = 0;
    initial $fatal(1, "tb_hgi_smmv_tput needs +define+XBD (native block-dot x)");
`endif
    wire [NCL*NXC*338-1:0] xq; wire [NCL*NXC*274-1:0] xr; wire [NCL*NPC*338-1:0] pq; wire [NCL*NPC*274-1:0] pr;
    wire [273:0] tr; reg [337:0] tq = 0;
    genvar cl;
    generate for (cl = 0; cl < NCL; cl = cl + 1) begin : g_cl
        wire x_v, x_rdy, x_done, x_fault, pub_v, pub_rdy, pub_done, pub_fault;
        wire [39:0] x_base, pub_base; wire [20:0] x_n; wire [3:0] x_p, pub_p; wire [31:0] x_stride, pub_stride;
        wire [1:0] x_space, x_fmt, pub_space; wire pub_bf16; wire [19:0] pub_m; wire [12:0] pub_q; wire [6:0] x_xb;
        wire l_en; wire [6:0] l_addr, l_grp; wire [2047:0] l_data;
        ot_hgi_smmv #(.NSM(NSL), .W(`WIN), .MUT_SLOT(MS), .MUT_EARLY(ME)) u_a (.clk(clk), .rst_n(rst_n), .sm_base(5'(cl * NSL)),
            .rec_v(rec_v && rec_rdy), .rec_rdy(c_rdy[cl]),
            .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_o(cur[895:640]), .rec_n_a(cur[916:896]),
            .rec_n_b(cur[937:917]), .rec_done(c_done[cl]), .rec_fault(c_fault[cl]), .halted(c_halt[cl]), .x_v(x_v), .x_rdy(x_rdy),
            .x_base(x_base), .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space), .x_fmt(x_fmt), .x_xb(x_xb),
            .x_done(x_done), .x_fault(x_fault), .pub_v(pub_v), .pub_rdy(pub_rdy), .pub_base(pub_base),
            .pub_stride(pub_stride), .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16),
            .pub_done(pub_done), .pub_fault(pub_fault), .sm_cmd(sm_cmd[cl*NSL*CW +: NSL*CW]), .sm_ret(sm_ret[cl*NSL*4 +: NSL*4]),
            .sm_cg_en(), .dbg_iss_seq(c_iss[cl*3 +: 3]));
        ot_hgi_sm_xload #(.NXC(NXC), .BD(XB)) u_x (.clk(clk), .rst_n(rst_n), .x_v(x_v), .x_rdy(x_rdy), .x_base(x_base),
            .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space), .x_fmt(x_fmt), .x_xb(x_xb), .x_done(x_done),
            .x_fault(x_fault), .xw_en(l_en), .xw_addr(l_addr), .xw_grp(l_grp), .xw_data(l_data),
            .vmq(xq[cl*NXC*338 +: NXC*338]), .vmr(xr[cl*NXC*274 +: NXC*274]),
            .rg_req(), .rg_gnt(1'b0), .wrq(), .wrq_cr(32'd0), .wrr({32*257{1'b0}}));
        if (cl == 0) begin : g_xw
            assign xw_en = l_en; assign xw_addr = l_addr; assign xw_grp = l_grp; assign xw_data = l_data;
        end
        ot_hgi_smmv_pub #(.NSM(NSL), .NPC(NPC), .W(`WIN), .MUT_ROW(MW)) u_p (.clk(clk), .rst_n(rst_n), .sm_base(5'(cl * NSL)),
            .pub_v(pub_v), .pub_rdy(pub_rdy),
            .pub_base(pub_base), .pub_stride(pub_stride), .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16),
            .pub_done(pub_done), .pub_fault(pub_fault), .sm_rv(rv[cl*NSL +: NSL]), .sm_rrow(rrow[cl*NSL*12 +: NSL*12]),
            .sm_rdata(rdata[cl*NSL*256 +: NSL*256]), .vmq(pq[cl*NPC*338 +: NPC*338]), .vmr(pr[cl*NPC*274 +: NPC*274]),
            .s0_v(), .s0_idx(), .s0_data());
        assign c_pfault[cl] = pub_fault; assign c_xfault[cl] = x_fault;
    end endgenerate
    ot_hgi_vm_unit #(.NC(NCL * (NXC + NPC) + 1)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, pq, xq}), .cr({tr, pr, xr}), .status());
    integer lines_req [0:NREAL-1];
    wire [NREAL-1:0] arr_real;
    // record being issued (the engine's issue pointer advances once a record)
    integer rec_iss = 0; reg [2:0] iss_q = 0;
    always @(posedge clk) begin iss_q <= iss_seq; if (rst_n && iss_seq != iss_q) rec_iss = rec_iss + 1; end
    function automatic integer rows_of(input integer r, input integer s_);
        reg [119:0] f; integer q_, m_;
        begin f = infm[r]; q_ = f[115:100]; m_ = f[99:80];
              rows_of = (m_ > s_ * q_) ? (((m_ - s_ * q_) > q_) ? q_ : (m_ - s_ * q_)) : 0; end
    endfunction
    genvar s;
    generate for (s = 0; s < NREAL; s = s + 1) begin : g_sm
        wire [CW-1:0] c = sm_cmd[s*CW +: CW];
        wire start_ready, d_ready, req_v, fault_s, arrive, released, busy; wire [31:0] req_addr; wire [9:0] req_tag;
        wire [7:0] rrow8;
        reg rsp_v = 0; reg [9:0] rsp_tag; reg [1087:0] rsp_data;
        assign sm_ret[s*4 +: 4] = {fault_s, arrive, d_ready, start_ready};
        assign arr_real[s] = arrive;
        assign rrow[s*12 +: 12] = {4'd0, rrow8};
        ot_hbm_accel_smh #(.ENABLE_INT8(1), .PIPE_INT8(1), .RMAX(256)) u_sm (.clk(clk), .rst_n(rst_n), .start(c[0]),
            .start_ready(start_ready), .op_rows(c[9:1]), .op_c(c[29:14]), .op_g(c[37:30]), .op_gs(c[38]),
            .op_fmt(c[40:39]), .op_xb(c[47:41]), .busy(busy), .d_valid(c[48]), .d_ready(d_ready), .d_base(c[80:49]),
            .d_lines(c[104:81]), .req_v(req_v), .req_ready(1'b1), .req_addr(req_addr), .req_tag(req_tag), .rsp_v(rsp_v),
            .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data),
            .rv(rv[s]), .rrow(rrow8), .rdata(rdata[s*256 +: 256]), .fault(fault_s), .arrive(arrive),
            .release_in(c[105]), .released(released));
        // HBM line model: in-order, ready at max(request + LAT, previous ready + LB x 32 / BW) (milli-cycles)
        reg [31:0] qa [0:4095]; reg [9:0] qt [0:4095]; longint qc [0:4095]; integer qh = 0, qtl = 0;
        longint nxt = 0; longint ival;
        always @(posedge clk) begin
            rsp_v <= 1'b0;
            ival = (((c[40:39] == 2'd3) ? 160 : 136) * 32 * 10000) / bwx10;   // milli-cycles a line
            if (req_v) begin
                longint t0; t0 = (cyc + lat) * 1000; if (t0 < nxt + ival) t0 = nxt + ival; nxt = t0;
                qa[qtl % 4096] = req_addr; qt[qtl % 4096] = req_tag; qc[qtl % 4096] = t0; qtl = qtl + 1;
                lines_req[s] = lines_req[s] + 1;
                if (qtl - qh > 4096) begin $display("ERR SM %0d HBM model queue overflow", s); errors = errors + 1; end
                if (req_addr < LBASE || req_addr >= LBASE + LSPAN || !lhas[req_addr - LBASE]) begin $display("ERR SM %0d read an unwritten line %0d", s, req_addr); errors = errors + 1; end
            end
            if (qh != qtl && qc[qh % 4096] <= longint'(cyc) * 1000) begin
                rsp_v <= 1'b1; rsp_tag <= qt[qh % 4096];
                rsp_data <= (qa[qh % 4096] >= LBASE && qa[qh % 4096] < LBASE + LSPAN) ? lmem[qa[qh % 4096] - LBASE] : 1088'd0;
                qh = qh + 1;
            end
            if (rst_n && fault_s) begin $display("ERR SM %0d fault", s); errors = errors + 1; end
        end
    end endgenerate

    // per real SM: the list of records it took (start handshakes), a row pointer and an arrive pointer into it
    integer opl [0:NREAL-1][0:4095]; integer opn [0:NREAL-1]; integer rowp [0:NREAL-1]; integer rown [0:NREAL-1];
    integer arrp [0:NREAL-1]; reg [NREAL-1:0] arr_q;
    integer rr0, ar0, rr1, ar1;               // front records (row / arrive) of real SM 0 / 1
    always @* begin rr0 = (rowp[0] < opn[0]) ? opl[0][rowp[0]] : 0; rr1 = (rowp[1] < opn[1]) ? opl[1][rowp[1]] : 0; end
    integer q0;
    always @(posedge clk) if (rst_n) begin
        for (q0 = 0; q0 < NREAL; q0 = q0 + 1) begin
            if (sm_cmd[q0*CW] && sm_ret[q0*4]) begin opl[q0][opn[q0]] = rec_iss; opn[q0] = opn[q0] + 1; end
            if (rv[q0]) begin rown[q0] = rown[q0] + 1; if (rown[q0] == rows_of(opl[q0][rowp[q0]], q0)) begin rown[q0] = 0; rowp[q0] = rowp[q0] + 1; end end
        end
    end
    // shadows
    reg [NSM-1:0] sh_arr = 0;
    generate for (s = NREAL; s < NSM; s = s + 1) begin : g_sh
        localparam integer SR = s % NREAL;
        wire [31:0] rfront = (SR == 0) ? rr0 : rr1;
        wire [31:0] rs_ = rows_of(rfront, s);
        assign sm_ret[s*4 +: 4] = {sm_ret[SR*4 + 3], sh_arr[s], sm_ret[SR*4 + 1], sm_ret[SR*4 + 0]};
        assign rv[s] = rv[SR] && ({20'd0, rrow[SR*12 +: 12]} < rs_);
        assign rrow[s*12 +: 12] = rrow[SR*12 +: 12];
        assign rdata[s*256 +: 256] = rdata[SR*256 +: 256];
    end endgenerate
    // arrive pointer: a real SM's toggle completes its op at arrp; each shadow active in that record toggles too
    integer s3;
    always @(posedge clk) if (rst_n) begin
        for (q0 = 0; q0 < NREAL; q0 = q0 + 1) begin
            arr_q[q0] <= arr_real[q0];
            if (arr_real[q0] != arr_q[q0]) begin
                for (s3 = NREAL; s3 < NSM; s3 = s3 + 1)
                    if (s3 % NREAL == q0 && rows_of(opl[q0][arrp[q0]], s3) > 0) sh_arr[s3] <= ~sh_arr[s3];
                arrp[q0] = arrp[q0] + 1;
            end
        end
    end
    task automatic vm_sec(input we, input [31:0] sec, input [255:0] data, output [255:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, sec[26:0], 5'd0, data, 32'hFFFFFFFF, 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            qd = tr[255:0];
        end
    endtask
    integer j, t, k, nf, r, prev_ret, busy_sum;
    integer disp [0:NREC-1]; integer retc [0:NREC-1];
    reg [255:0] qd; reg [31:0] lastsec;
    integer kc [0:NCL-1]; integer kmin, c2;
    always @(posedge clk) begin
        for (c2 = 0; c2 < NCL; c2 = c2 + 1) if (rst_n && c_done[c2]) kc[c2] = kc[c2] + 1;
        kmin = kc[0]; for (c2 = 1; c2 < NCL; c2 = c2 + 1) if (kc[c2] < kmin) kmin = kc[c2];
        while (k < kmin) begin retc[k] = cyc; k = k + 1; end
        if (rst_n && fault) nf = nf + 1;
    end
    initial begin
        for (j = 0; j < NREAL; j = j + 1) begin lines_req[j] = 0; opn[j] = 0; rowp[j] = 0; rown[j] = 0; arrp[j] = 0; end
        arr_q = 0; k = 0; for (j = 0; j < NCL; j = j + 1) kc[j] = 0;
        repeat (3) @(posedge clk);
        rst_n = 0; repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
        for (j = 0; j < NVMI; j = j + 1) vm_sec(1'b1, vmim[j][287:256], vmim[j][255:0], qd);
        $display("x loaded: %0d sectors at cycle %0d (LAT %0d BWX10 %0d W %0d NCL %0d)", NVMI, cyc, lat, bwx10, `WIN, NCL); $fflush;
        k = 0; nf = 0;
        for (r = 0; r < NREC && nf == 0; r = r + 1) begin
            @(negedge clk); cur = recm[r]; rec_v = 1;
            t = 0; while (!rec_rdy && t < 2000000 && nf == 0) begin @(negedge clk); t = t + 1; end
            @(posedge clk); disp[r] = cyc; #0.1 rec_v = 0;
        end
        t = 0; while (k < NREC && nf == 0 && t < 4000000) begin @(posedge clk); t = t + 1; end
        repeat (8) @(posedge clk);
        if (k != NREC || nf != 0) begin $display("ERR retired %0d of %0d, faults %0d (x_fault %b pub_fault %b)", k, NREC, nf, c_xfault, c_pfault); errors = errors + 1; end
        prev_ret = 0; busy_sum = 0;
        for (r = 0; r < k; r = r + 1) begin
            $display("TPUT %0d disp %0d ret %0d service %0d", r, disp[r], retc[r], retc[r] - (disp[r] > prev_ret ? disp[r] : prev_ret)); 
            busy_sum = busy_sum + retc[r] - (disp[r] > prev_ret ? disp[r] : prev_ret); prev_ret = retc[r];
        end
        $display("lines real SM0 %0d SM1 %0d", lines_req[0], lines_req[1]);
        lastsec = 32'hFFFFFFFF;
        for (j = 0; j < NVME; j = j + 1) begin
            if (vmem[j][63:35] != lastsec) begin lastsec = vmem[j][63:35]; vm_sec(1'b0, {3'd0, lastsec}, 256'd0, qd); end
            if (qd[32 * vmem[j][34:32] +: 32] !== vmem[j][31:0]) begin
                if (errors < 30) $display("ERR O[%0d] = %h expected %h", vmem[j][63:32], qd[32 * vmem[j][34:32] +: 32], vmem[j][31:0]);
                errors = errors + 1; end
        end
        $display("summary: %0d SM.MATVEC records (window %0d, clusters %0d), service sum %0d cycles, %0d result words checked", NREC, `WIN, NCL, busy_sum, NVME);
        if (errors == 0) $display("HGI_SMMV_TPUT PASS"); else $display("HGI_SMMV_TPUT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
