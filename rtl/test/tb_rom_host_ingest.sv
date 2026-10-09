`timescale 1ps/1ps
// ---------------------------------------------------------------------------
// End-to-end exact bench of the ROM dies' host block (ot_rom_host_ingest): host link stream -> CDC -> KV ingest
// engine (clk_i) -> CDC -> die fabric (ck) -> HBM image, compared sector by sector with the golden's image
// (tools/kv_ingest_ref.py, through tools/rtl_rom_host_ingest_bench.py).  Three unrelated clocks.
// Files (run directory): desc.mem (256-b descriptors), pay.mem (512-b beats), nb.mem (payload beats of each
// descriptor), init.mem / exp.mem (HBM image before / expected after, 32-B sectors).
// Host: CSR share (+SHARE, x256), then descriptor k and its nb[k] beats, credit-limited, +HGAP % idle cycles.
// Completions: every fenced descriptor must complete once, tags in order, no fault word.
// Fabric: takes a word per credit; drains it after +MSTALL % stall cycles; writes land, reads return in order after
// LAT ck cycles.  Prints one line: HING ... errors=E ...
// ---------------------------------------------------------------------------
module tb_rom_host_ingest #(
    parameter integer MEMW   = 65536,
    parameter integer ND     = 64,
    parameter integer NP     = 4096,
    parameter integer HDMAX  = 128,
    parameter integer KVHMAX = 2,
    parameter integer QKV_EN = 1,
    parameter integer RMW_EN = 1,
    parameter integer MUT    = 0,
    parameter integer HP     = 1000,     // clk_h period (ps)
    parameter integer IP     = 1666,     // clk_i period (ps): the die clock / 2
    parameter integer CP     = 833,      // ck period (ps)
    parameter integer LAT    = 40
) ();
    localparam integer AW = 32, HFA = 4, OCRED = 8;
    reg clk_h = 0, clk_i = 0, ck = 0, rst_n = 0;
    always #(HP / 2) clk_h = ~clk_h;
    always #(IP / 2) clk_i = ~clk_i;
    always #(CP / 2) ck = ~ck;

    reg [255:0] dmem [0:ND-1];
    reg [511:0] pmem [0:NP-1];
    reg [31:0]  nbm  [0:ND-1];
    reg [255:0] hbm  [0:MEMW-1];
    reg [255:0] expm [0:MEMW-1];
    integer nd, np, share, hgap, mstall, maxcyc, seed, nfence, i;
    initial begin
        if (!$value$plusargs("ND=%d", nd)) nd = ND;
        if (!$value$plusargs("NP=%d", np)) np = NP;
        if (!$value$plusargs("SHARE=%d", share)) share = 0;
        if (!$value$plusargs("HGAP=%d", hgap)) hgap = 0;
        if (!$value$plusargs("MSTALL=%d", mstall)) mstall = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 4000000;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        $readmemh("desc.mem", dmem);
        $readmemh("pay.mem", pmem);
        $readmemh("nb.mem", nbm);
        $readmemh("init.mem", hbm);
        $readmemh("exp.mem", expm);
        nfence = 0;
        for (i = 0; i < nd; i = i + 1) if (dmem[i][7]) nfence = nfence + 1;
        #(20 * HP) rst_n = 1;
    end

    // ---- DUT ------------------------------------------------------------------------------------------------------
    reg          h_v;
    reg  [1:0]   h_cls;
    reg  [511:0] h_d;
    wire [HFA:0] h_crn;
    wire         t_v;
    wire [63:0]  t_d;
    reg          t_cr;
    wire         o_v, o_we;
    wire [AW-1:0] o_addr;
    wire [255:0] o_d;
    reg          o_cr, i_rv;
    reg  [255:0] i_rd;
    wire         fault;
    ot_rom_host_ingest #(.AW(AW), .HDMAX(HDMAX), .KVHMAX(KVHMAX), .QKV_EN(QKV_EN), .RMW_EN(RMW_EN), .HFA(HFA),
                         .OCRED(OCRED), .MUT(MUT)) dut (
        .rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v), .t_d(t_d),
        .t_cr(t_cr), .clk_i(clk_i), .ck(ck), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr),
        .i_rv(i_rv), .i_rd(i_rd), .fault(fault));

    // ---- host (clk_h) ---------------------------------------------------------------------------------------------
    integer hcred = 1 << HFA, di = 0, pi = 0, pleft = 0, csr_done = 0, hcyc = 0;
    integer dones = 0, fwords = 0, tag_err = 0, exp_tag_i = 0, hup = 0;
    reg [31:0] rnd_h;
    integer bootend, bcount, breg, mark_sent = 0;
    initial begin
        if (!$value$plusargs("BOOTEND=%d", bootend)) bootend = 0;
        if (!$value$plusargs("BCOUNT=%d", bcount)) bcount = 0;
        if (!$value$plusargs("BREG=%d", breg)) breg = 0;
    end
    wire host_done = csr_done && di == nd && pleft == 0 && (bootend == 0 || mark_sent);
    always @(posedge clk_h) begin
        hcyc <= hcyc + 1;
        rnd_h = $random(seed);
        h_v <= 1'b0; t_cr <= 1'b0;
        if (rst_n) hup <= hup + 1;
        if (rst_n && hup >= 8) begin                              // link up: the block's synchronised resets are released
            if (hcred + h_crn > 0 && !host_done && (rnd_h % 100) >= hgap) begin
                h_v <= 1'b1;
                if (!csr_done) begin
                    h_cls <= 2'd0; h_d <= {448'd0, 23'd0, share[8:0], 32'd0}; csr_done <= 1;
                end else if (di == nd && pleft == 0) begin
                    h_cls <= 2'd0; h_d <= {382'd0, breg[1:0], 32'h1234abcd, bcount[31:0], 56'd0, 8'd2}; mark_sent <= 1;
                end else if (pleft > 0) begin
                    h_cls <= 2'd2; h_d <= pmem[pi]; pi <= pi + 1; pleft <= pleft - 1;
                end else begin
                    h_cls <= 2'd1; h_d <= {256'd0, dmem[di]}; pleft <= nbm[di]; di <= di + 1;
                end
                hcred <= hcred + h_crn - 1;
            end else hcred <= hcred + h_crn;
            // completions
            if (t_v) begin
                t_cr <= 1'b1;
                if (t_d[63:56] == 8'h01) begin
                    // fenced descriptors complete in order: the k-th done word carries the k-th fenced tag
                    while (exp_tag_i < nd && !dmem[exp_tag_i][7]) exp_tag_i = exp_tag_i + 1;
                    if (exp_tag_i >= nd || t_d[47:40] != dmem[exp_tag_i][15:8]) tag_err <= tag_err + 1;
                    exp_tag_i = exp_tag_i + 1;
                    dones <= dones + 1;
                end else fwords <= fwords + 1;
            end
        end
    end

    // ---- die fabric + HBM (ck) ------------------------------------------------------------------------------------
    reg          fq_we  [0:OCRED-1];
    reg [AW-1:0] fq_a   [0:OCRED-1];
    reg [255:0]  fq_d   [0:OCRED-1];
    integer fw = 0, fr = 0, rq_w = 0, rq_r = 0, ccyc = 0, errors = 0, oob = 0, sectors = 0, reads = 0, idle = 0;
    integer last_dn = 0, first_o = -1, marks = 0, mark_bad = 0;
    reg [255:0] rq_d [0:255];
    integer     rq_t [0:255];
    reg [31:0] rnd_c;
    always @(posedge ck) begin
        ccyc <= ccyc + 1;
        rnd_c = $random(seed);
        o_cr <= 1'b0; i_rv <= 1'b0;
        if (o_v) begin
            fq_we[fw % OCRED] <= o_we; fq_a[fw % OCRED] <= o_addr; fq_d[fw % OCRED] <= o_d; fw <= fw + 1;
            if (fw - fr >= OCRED) oob <= oob + 1000;              // the block ignored its credits
        end
        if (fr != fw && (rnd_c % 100) >= mstall) begin
            if (fq_a[fr % OCRED] >= MEMW && fq_a[fr % OCRED] != 32'hFFFFFFFF) oob <= oob + 1;
            else if (fq_we[fr % OCRED] && fq_a[fr % OCRED] == 32'hFFFFFFFF) begin
                marks <= marks + 1;
                if (fq_d[fr % OCRED][65:0] != {breg[1:0], 32'h1234abcd, bcount[31:0]} || sectors != bcount) mark_bad <= mark_bad + 1;
            end else if (fq_we[fr % OCRED]) begin hbm[fq_a[fr % OCRED]] <= fq_d[fr % OCRED]; sectors <= sectors + 1; end
            else begin
                rq_d[rq_w % 256] <= hbm[fq_a[fr % OCRED]]; rq_t[rq_w % 256] <= ccyc + LAT; rq_w <= rq_w + 1;
                reads <= reads + 1;
            end
            fr <= fr + 1; o_cr <= 1'b1;
        end
        if (rq_r != rq_w && rq_t[rq_r % 256] <= ccyc) begin
            i_rv <= 1'b1; i_rd <= rq_d[rq_r % 256]; rq_r <= rq_r + 1;
        end
        idle <= (host_done && dones >= nfence && fr == fw && rq_r == rq_w && !o_v) ? idle + 1 : 0;
        if (rst_n && (idle >= 400 || ccyc > maxcyc || (fwords > 0 && idle >= 0 && ccyc > last_dn + 4000))) begin
            for (i = 0; i < MEMW; i = i + 1)
                if (hbm[i] !== expm[i]) begin
                    if (errors < 4) $display("MISMATCH sector=%0d got=%h exp=%h", i, hbm[i], expm[i]);
                    errors = errors + 1;
                end
            $writememh("final.mem", hbm);
            $display("HING descs=%0d beats=%0d/%0d sectors=%0d reads=%0d errors=%0d oob=%0d dones=%0d/%0d tag_err=%0d fault_words=%0d fault=%0d ck_cycles=%0d timeout=%0d share=%0d first_o=%0d last_o=%0d marks=%0d mark_bad=%0d",
                     di, pi, np, sectors, reads, errors, oob, dones, nfence, tag_err, fwords, fault, ccyc, ccyc > maxcyc,
                     dut.share_c, first_o, last_dn, marks, mark_bad);
            $finish;
        end
        if (o_v) begin last_dn <= ccyc; if (first_o < 0) first_o <= ccyc; end
    end
endmodule
