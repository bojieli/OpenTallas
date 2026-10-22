`timescale 1ps/1ps
// SQK-INGEST 10-21: cycle-exact miter of the HOST-cluster ingest_qm CDC fork qkd_hr_native_qm_cdc (SRAM_FIFO 1: u_hx /
// u_ox payload in dual-clock SRAM macros) against the frozen pre-change fork (qkd_hr_native_qm_cdc_ref.sv, flop FIFOs),
// both driven by the same stimulus on three unrelated clocks (periods / phases from plusargs).  Stimulus = the native
// fixture (tools/qwen_host/native_fixture.py: desc.mem / pay.mem / nb.mem / native.mem) plus a CSR share and a BOOT END
// marker, host idle gaps HGAP %, fabric stalls MSTALL %.  Every output of every domain is compared on each falling
// edge of its clock (data ports while their valid is 1).  The new DUT's sector image is also checked against the
// golden.  Prints QM_SRAM_EQUIV PASS|FAIL ...
module tb_qm_sram_equiv;
    localparam integer AW = 32, HFA = 4, OCRED = 8;
    integer hp, ip, cp, hph, iph, cph;
    reg clk_h = 0, clk_i = 0, ck = 0, rst_n = 0;
    initial begin
        if (!$value$plusargs("HP=%d", hp)) hp = 1000;
        if (!$value$plusargs("IP=%d", ip)) ip = 1666;
        if (!$value$plusargs("CP=%d", cp)) cp = 833;
        if (!$value$plusargs("HPH=%d", hph)) hph = 0;
        if (!$value$plusargs("IPH=%d", iph)) iph = 0;
        if (!$value$plusargs("CPH=%d", cph)) cph = 0;
    end
    initial begin #(hph + 1); forever begin #(hp / 2) clk_h = ~clk_h; #(hp - hp / 2) clk_h = ~clk_h; end end
    initial begin #(iph + 1); forever begin #(ip / 2) clk_i = ~clk_i; #(ip - ip / 2) clk_i = ~clk_i; end end
    initial begin #(cph + 1); forever begin #(cp / 2) ck = ~ck; #(cp - cp / 2) ck = ~ck; end end

    reg [255:0] dmem [0:255];
    reg [511:0] pmem [0:8191];
    reg [31:0]  nbm  [0:255];
    reg [255:0] hbm [int unsigned], expm [int unsigned];
    reg [287:0] gold [0:8191];
    int unsigned ea;
    integer nd, np, nsector, hgap, mstall, maxcyc, seed, share, i, nfence;
    initial begin
        if (!$value$plusargs("ND=%d", nd)) nd = 1;
        if (!$value$plusargs("NP=%d", np)) np = 1;
        if (!$value$plusargs("NSECTOR=%d", nsector)) nsector = 0;
        if (!$value$plusargs("HGAP=%d", hgap)) hgap = 0;
        if (!$value$plusargs("MSTALL=%d", mstall)) mstall = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 2000000;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("SHARE=%d", share)) share = 0;
        $readmemh("desc.mem", dmem);
        $readmemh("pay.mem", pmem);
        $readmemh("nb.mem", nbm);
        $readmemh("native.mem", gold);
        for (integer x = 0; x < nsector; x++) begin expm[gold[x][31:0]] = gold[x][287:32]; hbm[gold[x][31:0]] = 0; end
        nfence = 0;
        for (i = 0; i < nd; i = i + 1) if (dmem[i][7]) nfence = nfence + 1;
        #(20 * hp) rst_n = 1;
    end

    reg          h_v = 0;
    reg  [1:0]   h_cls = 0;
    reg  [511:0] h_d = 0;
    reg          t_cr = 0, o_cr = 0;
    wire [HFA:0] h_crn, r_h_crn;
    wire         t_v, r_t_v, o_v, r_o_v, o_we, r_o_we, fault, r_fault;
    wire [63:0]  t_d, r_t_d;
    wire [AW-1:0] o_addr, r_o_addr;
    wire [255:0] o_d, r_o_d;
    wire         qh, qi, qc, r_qh, r_qi, r_qc;
    qkd_hr_native_qm_cdc #(.AW(32), .HDMAX(128), .KVHMAX(2), .RMW_EN(0), .MUT(0), .NATIVE_ROWS(1), .QPIPE(2)) dut (
        .rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v), .t_d(t_d),
        .t_cr(t_cr), .clk_i(clk_i), .clk_i_bank({clk_i, clk_i}), .clk_i_out(clk_i), .ck(ck), .o_v(o_v), .o_we(o_we),
        .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr), .i_rv(1'b0), .i_rd(256'd0), .fault(fault),
        .quiet_h(qh), .quiet_i(qi), .quiet_c(qc));
    qkd_hr_native_qm_cdc_ref #(.AW(32), .HDMAX(128), .KVHMAX(2), .RMW_EN(0), .MUT(0), .NATIVE_ROWS(1), .QPIPE(2)) ref_ (
        .rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(r_h_crn), .t_v(r_t_v), .t_d(r_t_d),
        .t_cr(t_cr), .clk_i(clk_i), .clk_i_bank({clk_i, clk_i}), .clk_i_out(clk_i), .ck(ck), .o_v(r_o_v), .o_we(r_o_we),
        .o_addr(r_o_addr), .o_d(r_o_d), .o_cr(o_cr), .i_rv(1'b0), .i_rd(256'd0), .fault(r_fault),
        .quiet_h(r_qh), .quiet_i(r_qi), .quiet_c(r_qc));

    // ---- compare (falling edges) ------------------------------------------------------------------------------------
    integer mis = 0, cmp_h = 0, cmp_i = 0, cmp_c = 0, ov_n = 0, tv_n = 0;
    task automatic miss(input string what);
        if (mis < 8) $display("QM_SRAM_EQUIV MISMATCH %s at %0t", what, $time);
        mis = mis + 1;
    endtask
    always @(negedge clk_h) if (rst_n) begin
        cmp_h = cmp_h + 1;
        if (h_crn !== r_h_crn) miss($sformatf("h_crn %0d/%0d", h_crn, r_h_crn));
        if (t_v !== r_t_v) miss("t_v");
        if (t_v && t_d !== r_t_d) miss("t_d");
        if (qh !== r_qh) miss("quiet_h");
        if (t_v) tv_n = tv_n + 1;
    end
    always @(negedge clk_i) if (rst_n) begin
        cmp_i = cmp_i + 1;
        if (qi !== r_qi) miss("quiet_i");
    end
    always @(negedge ck) if (rst_n) begin
        cmp_c = cmp_c + 1;
        if (o_v !== r_o_v) miss("o_v");
        if (o_v && (o_we !== r_o_we || o_addr !== r_o_addr || o_d !== r_o_d)) miss("o_we/o_addr/o_d");
        if (fault !== r_fault) miss("fault");
        if (qc !== r_qc) miss("quiet_c");
        if (o_v) ov_n = ov_n + 1;
    end

    // ---- host (clk_h), driven from the new DUT's credits (identical to the reference's while the miter holds) ------
    integer hcred = 1 << HFA, di = 0, pi = 0, pleft = 0, csr_done = 0, hup = 0, mark_sent = 0, dones = 0, fwords = 0;
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
                t_cr <= 1'b1;
                if (t_d[63:56] == 8'h01) dones <= dones + 1; else fwords <= fwords + 1;
            end
        end
    end

    // ---- die fabric (ck) ----------------------------------------------------------------------------------------------
    reg          fq_we [0:OCRED-1];
    reg [AW-1:0] fq_a  [0:OCRED-1];
    reg [255:0]  fq_d  [0:OCRED-1];
    integer fw = 0, fr = 0, ccyc = 0, errors = 0, oob = 0, sectors = 0, idle = 0, marks = 0, last_o = 0;
    reg [31:0] rnd_c;
    always @(posedge ck) begin
        ccyc <= ccyc + 1;
        rnd_c = $random(seed);
        o_cr <= 1'b0;
        if (o_v) begin
            fq_we[fw % OCRED] <= o_we; fq_a[fw % OCRED] <= o_addr; fq_d[fw % OCRED] <= o_d; fw <= fw + 1;
            if (fw - fr >= OCRED) oob <= oob + 1000;
            last_o <= ccyc;
        end
        if (fr != fw && (rnd_c % 100) >= mstall) begin
            if (fq_we[fr % OCRED] && fq_a[fr % OCRED] == 32'hFFFFFFFF) marks <= marks + 1;
            else if (!expm.exists(fq_a[fr % OCRED])) oob <= oob + 1;
            else if (fq_we[fr % OCRED]) begin hbm[fq_a[fr % OCRED]] = fq_d[fr % OCRED]; sectors <= sectors + 1; end
            fr <= fr + 1; o_cr <= 1'b1;
        end
        idle <= (host_done && dones >= nfence && marks >= 1 && fr == fw && !o_v) ? idle + 1 : 0;
        if (rst_n && (idle >= 400 || ccyc > maxcyc || ccyc > last_o + 200000)) begin
            foreach (expm[ea]) if (hbm[ea] !== expm[ea]) errors = errors + 1;
            if (mis == 0 && errors == 0 && oob == 0 && !fault && dones == nfence && sectors == nsector && marks == 1 && idle >= 400)
                $display("QM_SRAM_EQUIV PASS sectors=%0d dones=%0d/%0d o_words=%0d t_words=%0d cmp_h=%0d cmp_i=%0d cmp_c=%0d ck_cycles=%0d",
                         sectors, dones, nfence, ov_n, tv_n, cmp_h, cmp_i, cmp_c, ccyc);
            else
                $display("QM_SRAM_EQUIV FAIL mismatches=%0d errors=%0d oob=%0d fault=%0d dones=%0d/%0d sectors=%0d/%0d marks=%0d idle=%0d ck_cycles=%0d",
                         mis, errors, oob, fault, dones, nfence, sectors, nsector, marks, idle, ccyc);
            $finish;
        end
    end
endmodule
