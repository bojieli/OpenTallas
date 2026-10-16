`timescale 1ns/1ps
// hgi-1010/g (2026-10-10): SM.MATVEC THROUGHPUT bench at production width.  Records back to back ->
// ot_hgi_sm_record (NSM 32, LEGACY 0) -> ot_hgi_sm_xload (NXC 4) -> 32 SMs -> ot_hgi_sm_pub (NSM 32, NPC 4) -> the REAL
// HGI VM (ot_hgi_vm_unit NC 9: client 8 = this bench).  SMs 0, 1 are REAL ot_hbm_accel_smh (ENABLE_INT8, PIPE_INT8) at
// the production row slice Q = ceil(M / 32) and full K; SMs 2..31 are shadows replaying real SM (s mod 2) port for port
// (see tools/hgi_adapters/sm_tput_bench.py for why that is the production timing).  Weight lines: an HBM model per real
// SM, in-order, first access LAT (+LAT=, default 104 = hgi_sim MEAS hbm.first_access) and the SM's share of the die's
// HBM bandwidth (+BWX10=, default 31667 = 3,166.7 B/cycle; one line every LB x 32 / BW cycles).  Per record: dispatch
// (rec_v && rec_rdy edge) and retire (rec_done) cycles -> "TPUT k disp D ret R"; after the last record every O word of
// every record (all 32 SMs' rows) == golden.  FP8 / FP4 records: x-load proxy (the tb writes the quantised fragments
// while the real x-load runs in BF16 mode on the same A; its x_done gates the start).  Prints HGI_SM_TPUT PASS / FAIL.
// Mutants (must FAIL): MUT_ROW (publication drops s x Q: rows land on the wrong words), MUT_EARLY (the adapter retires
// a record when its SMs start: the next record's x load overwrites the x store under the running matvec).
module tb_hgi_sm_tput;
`ifdef MUT_ROW
    localparam integer MW = 1;
`else
    localparam integer MW = 0;
`endif
`ifdef MUT_EARLY
    localparam integer ME = 1;
`else
    localparam integer ME = 0;
`endif
    `include "tput_sizes.svh"
    localparam integer NSM = 32, NREAL = 2, CW = 106, NXC = 4, NPC = 4;
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
        $readmemh({dir, "/tput_xw.mem"}, xwm);
        $readmemh({dir, "/tput_vmi.mem"}, vmim); $readmemh({dir, "/tput_vme.mem"}, vmem); $readmemh({dir, "/tput_lines.mem"}, linem);
        for (i = 0; i < LSPAN; i = i + 1) lhas[i] = 1'b0;
        for (i = 0; i < NLINE; i = i + 1) begin lmem[linem[i][1119:1088] - LBASE] = linem[i][1087:0]; lhas[linem[i][1119:1088] - LBASE] = 1'b1; end
    end
    integer errors = 0, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [937:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted;
    wire x_v, x_rdy, x_done, x_fault, pub_v, pub_rdy, pub_done, pub_fault;
    wire [39:0] x_base, pub_base; wire [20:0] x_n; wire [3:0] x_p, pub_p; wire [31:0] x_stride, pub_stride;
    wire [1:0] x_space, x_fmt, pub_space; wire [19:0] pub_m; wire [12:0] pub_q; wire pub_bf16;
    wire [NSM*CW-1:0] sm_cmd; wire [NSM*4-1:0] sm_ret;
    ot_hgi_sm_record #(.NSM(NSM), .LEGACY(0), .MUT_EARLY(ME)) u_a (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_o(cur[895:640]), .rec_n_a(cur[916:896]),
        .rec_n_b(cur[937:917]), .rec_done(done), .rec_fault(fault), .halted(halted), .x_v(x_v), .x_rdy(x_rdy),
        .x_base(x_base), .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space), .x_fmt(x_fmt), .x_done(x_done),
        .x_fault(x_fault), .pub_v(pub_v), .pub_rdy(pub_rdy), .pub_base(pub_base), .pub_stride(pub_stride),
        .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16), .pub_done(pub_done),
        .pub_fault(pub_fault), .lg_cmd({NSM*CW{1'b0}}), .lg_ret(), .sm_cmd(sm_cmd), .sm_ret(sm_ret), .sm_cg_en());
    // x load: FP8 / FP4 run the real loader in BF16 mode (timing proxy); its writes are replaced by the tb's fragments
`ifdef NATIVE
    // hgi-1010/d: the x-load runs FP8 / FP4 natively (block-dot quantiser); no proxy -- the tb checks the x-store image
    // it wrote against the golden fragments instead
    wire proxy_f = 1'b0;
`else
    wire proxy_f = (x_fmt == 2'd1 || x_fmt == 2'd2);
`endif
    reg  proxy_q = 1'b0;
    wire xl_en; wire [6:0] xl_addr, xl_grp; wire [2047:0] xl_data;
    reg  tx_en = 1'b0; reg [6:0] tx_addr = 0, tx_grp = 0; reg [2047:0] tx_data = 0;
    wire xw_en = proxy_q ? tx_en : xl_en;
    wire [6:0] xw_addr = proxy_q ? tx_addr : xl_addr, xw_grp = proxy_q ? tx_grp : xl_grp;
    wire [2047:0] xw_data = proxy_q ? tx_data : xl_data;
    wire [NXC*338-1:0] xq; wire [NXC*274-1:0] xr; wire [NPC*338-1:0] pq; wire [NPC*274-1:0] pr;
    wire [273:0] tr; reg [337:0] tq = 0;
`ifdef WVM
    // the die form: x-load on the E-group wide VM read lanes (client 0 of a K 3 lane arbiter, die relays), VM RP 32
`ifndef WLQ
`define WLQ 16
`endif
`ifndef WRLY
`define WRLY 2
`endif
    wire rg_req, rg_gnt_x; wire [32*16-1:0] wrq_x, g_q; wire [31:0] wcr_x, g_cr; wire [32*257-1:0] wrr_x, g_rsp;
    wire [2:0] a_gnt; wire [3*32-1:0] a_cr; wire [3*32*257-1:0] a_rsp;
    ot_hgi_vm_lanearb #(.K(3), .REQW(16), .RSPW(257), .RLY(`WRLY)) u_arb (.clk(clk), .rst_n(rst_n), .c_req({2'b00, rg_req}),
        .c_gnt(a_gnt), .c_q({{2*32*16{1'b0}}, wrq_x}), .c_cr(a_cr), .c_rsp(a_rsp), .g_q(g_q), .g_cr(g_cr), .g_rsp(g_rsp));
    assign rg_gnt_x = a_gnt[0]; assign wcr_x = a_cr[0 +: 32]; assign wrr_x = a_rsp[0 +: 32*257];
    ot_hgi_sm_xload #(.NXC(NXC), .WVM(1), .WLQ(`WLQ)) u_x (.clk(clk), .rst_n(rst_n), .x_v(x_v), .x_rdy(x_rdy), .x_base(x_base),
        .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space), .x_fmt(proxy_f ? 2'd0 : x_fmt), .x_done(x_done),
        .x_fault(x_fault), .xw_en(xl_en), .xw_addr(xl_addr), .xw_grp(xl_grp), .xw_data(xl_data), .vmq(xq), .vmr(xr),
        .rg_req(rg_req), .rg_gnt(rg_gnt_x), .wrq(wrq_x), .wrq_cr(wcr_x), .wrr(wrr_x));
`else
    ot_hgi_sm_xload #(.NXC(NXC)) u_x (.clk(clk), .rst_n(rst_n), .x_v(x_v), .x_rdy(x_rdy), .x_base(x_base),
        .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space), .x_fmt(proxy_f ? 2'd0 : x_fmt), .x_done(x_done),
        .x_fault(x_fault), .xw_en(xl_en), .xw_addr(xl_addr), .xw_grp(xl_grp), .xw_data(xl_data), .vmq(xq), .vmr(xr));
`endif
    wire [NSM-1:0] rv; wire [NSM*12-1:0] rrow; wire [NSM*256-1:0] rdata;
    ot_hgi_sm_pub #(.NSM(NSM), .NPC(NPC), .MUT_ROW(MW)) u_p (.clk(clk), .rst_n(rst_n), .pub_v(pub_v), .pub_rdy(pub_rdy),
        .pub_base(pub_base), .pub_stride(pub_stride), .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p),
        .pub_bf16(pub_bf16), .pub_done(pub_done), .pub_fault(pub_fault), .sm_rv(rv), .sm_rrow(rrow), .sm_rdata(rdata), .vmq(pq), .vmr(pr),
        .s0_v(), .s0_idx(), .s0_data());
`ifdef WVM
    ot_hgi_vm_unit #(.NC(NXC + NPC + 1), .RP(32), .LQ(`WLQ)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, pq, xq}), .cr({tr, pr, xr}),
        .status(), .rq(g_q), .rq_cr(g_cr), .rr(g_rsp));
`else
    ot_hgi_vm_unit #(.NC(NXC + NPC + 1)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, pq, xq}), .cr({tr, pr, xr}), .status());
`endif
`ifdef NATIVE
    // x-store image check: the beats the x-load writes vs the record's golden fragments (tput_xw: {addr, grp, beat})
    reg [2047:0] xsb [0:127][0:15]; reg [15:0] xsv [0:127];
    always @(posedge clk) if (xl_en) begin xsb[xl_addr][xl_grp[3:0]] <= xl_data; xsv[xl_addr][xl_grp[3:0]] <= 1'b1; end
`endif
    // current record's M / Q (for the shadows' row clamp)
    reg [19:0] cur_m = 0; reg [15:0] cur_q = 0;
    integer lines_req [0:NREAL-1];
    genvar s;
    generate for (s = 0; s < NREAL; s = s + 1) begin : g_sm
        wire [CW-1:0] c = sm_cmd[s*CW +: CW];
        wire start_ready, d_ready, req_v, fault_s, arrive, released, busy; wire [31:0] req_addr; wire [9:0] req_tag;
        wire [7:0] rrow8;
        reg rsp_v = 0; reg [9:0] rsp_tag; reg [1087:0] rsp_data;
        assign sm_ret[s*4 +: 4] = {fault_s, arrive, d_ready, start_ready};
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
    // shadows: SM s replays real SM (s mod 2); result rows past R_s = clamp(M - s Q, 0, Q) are not emitted
    generate for (s = NREAL; s < NSM; s = s + 1) begin : g_sh
        localparam integer SR = s % NREAL;
        wire [31:0] rs_ = (cur_m > s * cur_q) ? (((cur_m - s * cur_q) > cur_q) ? cur_q : (cur_m - s * cur_q)) : 0;
        assign sm_ret[s*4 +: 4] = sm_ret[SR*4 +: 4];
        assign rv[s] = rv[SR] && ({20'd0, rrow[SR*12 +: 12]} < rs_);
        assign rrow[s*12 +: 12] = rrow[SR*12 +: 12];
        assign rdata[s*256 +: 256] = rdata[SR*256 +: 256];
    end endgenerate
    task automatic vm_sec(input we, input [31:0] sec, input [255:0] data, output [255:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, sec[26:0], 5'd0, data, 32'hFFFFFFFF, 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            qd = tr[255:0];
        end
    endtask
    integer j, t, k, nf, r, td, tr_, prev_ret, xi, busy_sum;
    // tput2-sm per-stage timestamps of the record in flight (cycles; -1 = not seen): x issue / x done / SM0 start /
    // SM0 first + last weight request / last weight response / SM0 first + last result row / pub done
    integer e_xi = -1, e_xd = -1, e_st = -1, e_rq0 = -1, e_rq1 = -1, e_rs1 = -1, e_rv0 = -1, e_rv1 = -1, e_pd = -1;
    always @(posedge clk) if (rst_n) begin
        if (x_v && x_rdy && e_xi < 0) e_xi = cyc;
        if (x_done && e_xd < 0) e_xd = cyc;
        if (sm_cmd[0] && sm_ret[0] && e_st < 0) e_st = cyc;
        if (g_sm[0].req_v) begin if (e_rq0 < 0) e_rq0 = cyc; e_rq1 = cyc; end
        if (g_sm[0].rsp_v) e_rs1 = cyc;
        if (rv[0]) begin if (e_rv0 < 0) e_rv0 = cyc; e_rv1 = cyc; end
        if (pub_done && e_pd < 0) e_pd = cyc;
    end
    reg [255:0] qd; reg [31:0] lastsec; reg [119:0] inf;
    always @(posedge clk) begin if (rst_n && done) k = k + 1; if (rst_n && fault) nf = nf + 1; end
    // proxy fragment writer: one beat an edge from dispatch; checked to finish before the x-load's x_done
    integer px0 = 0, pxn = 0, pxi = 0; reg px_go = 0;
    always @(posedge clk) begin
        tx_en <= 1'b0;
        if (px_go && pxi < pxn) begin
            tx_en <= 1'b1; tx_addr <= xwm[px0 + pxi][2062:2056]; tx_grp <= xwm[px0 + pxi][2054:2048]; tx_data <= xwm[px0 + pxi][2047:0];
            pxi <= pxi + 1;
        end
        if (px_go && x_done && pxi < pxn) begin $display("ERR proxy fragments not written before x_done"); errors = errors + 1; end
    end
    initial begin
        lines_req[0] = 0; lines_req[1] = 0;
        repeat (3) @(posedge clk);
        rst_n = 0; repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
        for (j = 0; j < NVMI; j = j + 1) vm_sec(1'b1, vmim[j][287:256], vmim[j][255:0], qd);
        $display("x loaded: %0d sectors at cycle %0d (LAT %0d BWX10 %0d)", NVMI, cyc, lat, bwx10); $fflush;
        k = 0; nf = 0; prev_ret = 0; busy_sum = 0;
        for (r = 0; r < NREC; r = r + 1) begin
            inf = infm[r];
            @(negedge clk); cur = recm[r]; rec_v = 1;
            cur_q = inf[115:100]; cur_m = inf[99:80];
            t = 0; while (!rec_rdy && t < 100000) begin @(negedge clk); t = t + 1; end
            e_xi = -1; e_xd = -1; e_st = -1; e_rq0 = -1; e_rq1 = -1; e_rs1 = -1; e_rv0 = -1; e_rv1 = -1; e_pd = -1;
            @(posedge clk); td = cyc; #0.1 rec_v = 0;
            proxy_q = (inf[119:116] == 1 || inf[119:116] == 2); px0 = inf[47:16]; pxn = inf[15:0]; pxi = 0; px_go = proxy_q;
            t = 0; while (k < r + 1 && nf == 0 && t < 2000000) begin @(posedge clk); t = t + 1; end
            tr_ = cyc; px_go = 0; proxy_q = 0;
`ifdef NATIVE
            begin : xchk
                integer xi2, xb2; xb2 = 0;
                for (xi2 = 0; xi2 < inf[15:0]; xi2 = xi2 + 1) begin : one
                    reg [6:0] aa, gg; aa = xwm[inf[47:16] + xi2][2062:2056]; gg = xwm[inf[47:16] + xi2][2054:2048];
                    if (xsb[aa][gg[3:0]] !== xwm[inf[47:16] + xi2][2047:0]) begin
                        if (xb2 < 4) begin : dd
                            integer bb; for (bb = 0; bb < 2048; bb = bb + 266)
                                if (xsb[aa][gg[3:0]][bb +: 266] !== xwm[inf[47:16] + xi2][bb +: 266]) begin
                                    $display("ERR record %0d x-store a %0d beat %0d bits [%0d +: 266] %h expected %h", r, aa, gg, bb,
                                             xsb[aa][gg[3:0]][bb +: 266], xwm[inf[47:16] + xi2][bb +: 266]); bb = 2048; end
                        end
                        xb2 = xb2 + 1; errors = errors + 1;
                    end
                end
                for (xi2 = 0; xi2 < 128; xi2 = xi2 + 1) xsv[xi2] = 16'd0;
            end
`endif
            if (k != r + 1 || nf != 0) begin $display("ERR record %0d: retired %0d faults %0d (x_fault %0d pub_fault %0d)", r, k, nf, x_fault, pub_fault); errors = errors + 1; r = NREC; end
            else begin
                $display("TPUT %0d disp %0d ret %0d service %0d lines %0d %0d", r, td, tr_, tr_ - (td > prev_ret ? td : prev_ret), lines_req[0], lines_req[1]); $fflush;
                $display("STAGE %0d xi %0d xd %0d st %0d rq0 %0d rq1 %0d rs1 %0d rv0 %0d rv1 %0d pd %0d ret %0d", r,
                         e_xi - td, e_xd - td, e_st - td, e_rq0 - td, e_rq1 - td, e_rs1 - td, e_rv0 - td, e_rv1 - td, e_pd - td, tr_ - td);
                busy_sum = busy_sum + tr_ - (td > prev_ret ? td : prev_ret);
                prev_ret = tr_;
            end
        end
        lastsec = 32'hFFFFFFFF;
        for (j = 0; j < NVME; j = j + 1) begin
            if (vmem[j][63:35] != lastsec) begin lastsec = vmem[j][63:35]; vm_sec(1'b0, {3'd0, lastsec}, 256'd0, qd); end
            if (qd[32 * vmem[j][34:32] +: 32] !== vmem[j][31:0]) begin
                if (errors < 30) $display("ERR O[%0d] = %h expected %h", vmem[j][63:32], qd[32 * vmem[j][34:32] +: 32], vmem[j][31:0]);
                errors = errors + 1; end
        end
        $display("summary: %0d SM.MATVEC records back to back, service sum %0d cycles, %0d result words checked", NREC, busy_sum, NVME);
        if (errors == 0) $display("HGI_SM_TPUT PASS"); else $display("HGI_SM_TPUT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
