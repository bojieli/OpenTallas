`timescale 1ps/1ps
// QK-CORES-6 2026-10-27: transaction miter of qkd_host_native_qm_debt ENG_PREG=1 (registered-pin ingest_eng core,
// qkd_host_native_engine_preg) against ENG_PREG=0 (the unchanged engine), each in its own harness (host link with
// credits, die fabric with credits), same native fixture (tools/qwen_host/native_fixture.py), same host gap / fabric
// stall seeds.  The registered core changes cycle timing by design, so the miter compares the ORDERED streams: every
// die-face word (o_we, o_addr, o_d) and every completion word t_d, plus the fault output, and the golden sector image.
// Prints QM_PREG_EQUIV PASS|FAIL ...
module qm_preg_harness #(parameter integer ENG_PREG = 0, parameter integer SAMECLK = 0) (
    input wire clk_h, input wire clk_i, input wire ck, input wire rst_n,
    input integer nd, input integer nsector, input integer hgap, input integer mstall, input integer share,
    input integer seed0,
    output integer n_o, output integer n_t, output reg fault_seen, output integer sectors, output integer marks,
    output integer dones, output reg finished
);
    localparam integer AW = 32, HFA = 4, OCRED = 8;
    reg          h_v = 0;
    reg  [1:0]   h_cls = 0;
    reg  [511:0] h_d = 0;
    reg          t_cr = 0, o_cr = 0;
    wire [HFA:0] h_crn;
    wire         t_v, o_v, o_we, fault, qh, qi, qc;
    wire [63:0]  t_d;
    wire [AW-1:0] o_addr;
    wire [255:0] o_d;
    qkd_host_native_qm_debt #(.AW(32), .HDMAX(128), .KVHMAX(2), .RMW_EN(0), .QPIPE(2), .NATIVE_ROWS(1), .MUT(0),
                              .SAMECLK(SAMECLK), .ENG_PREG(ENG_PREG)) u_qm (
        .rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v), .t_d(t_d),
        .t_cr(t_cr), .clk_i(clk_i), .clk_i_bank({clk_i, clk_i}), .clk_i_out(clk_i), .ck(ck), .o_v(o_v), .o_we(o_we),
        .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr), .i_rv(1'b0), .i_rd(256'd0), .fault(fault),
        .quiet_h(qh), .quiet_i(qi), .quiet_c(qc));
    reg [255:0] dmem [0:255];
    reg [511:0] pmem [0:8191];
    reg [31:0]  nbm  [0:255];
    reg [288:0] ostream [$];
    reg [63:0]  tstream [$];
    integer seed;
    initial begin
        $readmemh("desc.mem", dmem); $readmemh("pay.mem", pmem); $readmemh("nb.mem", nbm);
        n_o = 0; n_t = 0; fault_seen = 0; sectors = 0; marks = 0; dones = 0; finished = 0; seed = seed0;
    end
    integer hcred = 1 << HFA, di = 0, pi = 0, pleft = 0, csr_done = 0, hup = 0, mark_sent = 0;
    reg [31:0] rnd_h;
    wire host_done = csr_done && di == nd && pleft == 0 && mark_sent;
    always @(posedge clk_h) begin
        rnd_h = $random(seed);
        h_v <= 1'b0; t_cr <= 1'b0;
        if (rst_n) hup <= hup + 1;
        if (rst_n && hup >= 8) begin
            if (hcred + h_crn > 0 && !host_done && (rnd_h % 100) >= hgap) begin
                h_v <= 1'b1;
                if (!csr_done) begin
                    h_cls <= 2'd0; h_d <= {448'd0, 23'd0, share[8:0], 32'd0}; csr_done <= 1;
                end else if (di == nd && pleft == 0) begin
                    h_cls <= 2'd0; h_d <= {382'd0, 2'd0, 32'h1234abcd, nsector[31:0], 56'd0, 8'd2}; mark_sent <= 1;
                end else if (pleft > 0) begin
                    h_cls <= 2'd2; h_d <= pmem[pi]; pi <= pi + 1; pleft <= pleft - 1;
                end else begin
                    h_cls <= 2'd1; h_d <= {256'd0, dmem[di]}; pleft <= nbm[di]; di <= di + 1;
                end
                hcred <= hcred + h_crn - 1;
            end else hcred <= hcred + h_crn;
            if (t_v) begin
                t_cr <= 1'b1; tstream.push_back(t_d); n_t <= n_t + 1;
                if (t_d[63:56] == 8'h01) dones <= dones + 1;
            end
        end
    end
    integer fw = 0, fr = 0, ccyc = 0, idle = 0;
    reg          fq_we [0:OCRED-1];
    reg [AW-1:0] fq_a  [0:OCRED-1];
    reg [255:0]  fq_d  [0:OCRED-1];
    reg [31:0] rnd_c;
    always @(posedge ck) begin
        ccyc <= ccyc + 1;
        rnd_c = $random(seed);
        o_cr <= 1'b0;
        if (fault) fault_seen <= 1'b1;
        if (o_v) begin
            fq_we[fw % OCRED] <= o_we; fq_a[fw % OCRED] <= o_addr; fq_d[fw % OCRED] <= o_d; fw <= fw + 1;
            ostream.push_back({o_we, o_addr, o_d}); n_o <= n_o + 1;
        end
        if (fr != fw && (rnd_c % 100) >= mstall) begin
            if (fq_we[fr % OCRED] && fq_a[fr % OCRED] == 32'hFFFFFFFF) marks <= marks + 1;
            else if (fq_we[fr % OCRED]) sectors <= sectors + 1;
            fr <= fr + 1; o_cr <= 1'b1;
        end
        idle <= (host_done && fr == fw && !o_v && marks >= 1) ? idle + 1 : 0;
        if (idle >= 400 || ccyc > 3000000) finished <= 1'b1;
    end
endmodule

module tb_qm_preg_equiv;
    integer hp, ip, cp, nd, np, nsector, hgap, mstall, seed, share, sameclk;
    reg clk_h = 0, clk_i = 0, ck = 0, rst_n = 0;
    initial begin
        if (!$value$plusargs("HP=%d", hp)) hp = 1000;
        if (!$value$plusargs("IP=%d", ip)) ip = 1666;
        if (!$value$plusargs("CP=%d", cp)) cp = 833;
        if (!$value$plusargs("ND=%d", nd)) nd = 1;
        if (!$value$plusargs("NP=%d", np)) np = 1;
        if (!$value$plusargs("NSECTOR=%d", nsector)) nsector = 0;
        if (!$value$plusargs("HGAP=%d", hgap)) hgap = 0;
        if (!$value$plusargs("MSTALL=%d", mstall)) mstall = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("SHARE=%d", share)) share = 0;
        #(20 * hp) rst_n = 1;
    end
    initial begin #1; forever begin #(hp / 2) clk_h = ~clk_h; #(hp - hp / 2) clk_h = ~clk_h; end end
    initial begin #1; forever begin #(ip / 2) clk_i = ~clk_i; #(ip - ip / 2) clk_i = ~clk_i; end end
    initial begin #1; forever begin #(cp / 2) ck = ~ck; #(cp - cp / 2) ck = ~ck; end end
    integer a_o, a_t, a_s, a_m, a_d, b_o, b_t, b_s, b_m, b_d;
    wire a_f, b_f, a_fin, b_fin;
`ifdef QM_PREG_SAMECLK
    localparam integer SC = 1;
    wire ch = ck, ci = ck;
`else
    localparam integer SC = 0;
    wire ch = clk_h, ci = clk_i;
`endif
    qm_preg_harness #(.ENG_PREG(1), .SAMECLK(SC)) A (.clk_h(ch), .clk_i(ci), .ck(ck), .rst_n(rst_n), .nd(nd),
        .nsector(nsector), .hgap(hgap), .mstall(mstall), .share(share), .seed0(seed), .n_o(a_o), .n_t(a_t),
        .fault_seen(a_f), .sectors(a_s), .marks(a_m), .dones(a_d), .finished(a_fin));
    qm_preg_harness #(.ENG_PREG(0), .SAMECLK(SC)) B (.clk_h(ch), .clk_i(ci), .ck(ck), .rst_n(rst_n), .nd(nd),
        .nsector(nsector), .hgap(hgap), .mstall(mstall), .share(share), .seed0(seed), .n_o(b_o), .n_t(b_t),
        .fault_seen(b_f), .sectors(b_s), .marks(b_m), .dones(b_d), .finished(b_fin));
    integer mis, k, ccy = 0;
    always @(posedge ck) begin
        ccy <= ccy + 1;
        if (a_fin && b_fin) begin
            mis = 0;
            if (A.ostream.size() != B.ostream.size()) mis = mis + 1;
            else for (k = 0; k < A.ostream.size(); k++) if (A.ostream[k] !== B.ostream[k]) begin
                if (mis < 4) $display("QM_PREG_EQUIV MISMATCH o word %0d A we%0d a%h d%h B we%0d a%h d%h", k, A.ostream[k][288], A.ostream[k][287:256], A.ostream[k][63:0], B.ostream[k][288], B.ostream[k][287:256], B.ostream[k][63:0]); mis = mis + 1; end
            if (A.tstream.size() != B.tstream.size()) mis = mis + 1;
            else for (k = 0; k < A.tstream.size(); k++) if (A.tstream[k] !== B.tstream[k]) begin
                if (mis < 4) $display("QM_PREG_EQUIV MISMATCH t word %0d", k); mis = mis + 1; end
            if (mis == 0 && !a_f && !b_f && a_s == nsector && a_m == 1 && a_d > 0)
                $display("QM_PREG_EQUIV PASS o_words=%0d t_words=%0d sectors=%0d dones=%0d marks=%0d (ref o=%0d t=%0d) last_o_ck A=%0d B=%0d",
                         a_o, a_t, a_s, a_d, a_m, b_o, b_t, A.ccyc, B.ccyc);
            else
                $display("QM_PREG_EQUIV FAIL mis=%0d fault=%0d/%0d sectors=%0d/%0d/%0d marks=%0d/%0d dones=%0d/%0d o=%0d/%0d t=%0d/%0d",
                         mis, a_f, b_f, a_s, b_s, nsector, a_m, b_m, a_d, b_d, a_o, b_o, a_t, b_t);
            $finish;
        end
    end
endmodule
