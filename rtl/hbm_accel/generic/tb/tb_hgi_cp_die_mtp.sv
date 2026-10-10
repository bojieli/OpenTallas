`timescale 1ns/1ps
// hgi-1010 2026-10-10: the MTP backend translator inside the CP die (ot_hgi_cp_die MTP=1; decision 3 of 10-09, stage B)
// with G23 kernel entries and G26 per-layer bodies, through the host CFG window (ot_hgi_loader_cp) and the record ring
// on the loader's memory lane.  Native DSpark operations enter on x_cmd (the MX1 collar's backend side); every kernel
// launch must run the body the expansion names: a body is one CTL.END returning 1000 + id (id = kind, or 100 * kind + L'
// for kinds 3 / 7 / 8), so each translator-owned completion is checked against (kind, L') of its own doorbell, computed
// here independently from the operation (the legacy expansion's L of the column's swapin).  Head kinds 4 / 10 must
// raise x_am with that token; no translator completion may reach the host completion FIFO; a host AR doorbell after
// the MTP job completes normally (token 999).  MUT 2 (G26 offset dropped) must FAIL.
// Vectors: python3 tools/hgi_mtp_cpdie_vectors.py
module tb_hgi_cp_die_mtp;
    parameter integer MUT = 0;
`include "hgi_mtp_cpdie_sizes.svh"
    localparam integer PAGE = 32'h10;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg s_awvalid = 0, s_wvalid = 0, s_bready = 1, s_arvalid = 0, s_rready = 1; reg [11:0] s_awaddr = 0, s_araddr = 0;
    reg [31:0] s_wdata = 0; wire s_awready, s_wready, s_bvalid, s_arready, s_rvalid; wire [31:0] s_rdata;
    wire c_awvalid, c_wvalid, c_arvalid, c_bready, c_rready; wire [11:0] c_awaddr, c_araddr; wire [31:0] c_wdata; wire [3:0] c_wstrb;
    wire [418:0] lcp; wire [221:0] cplk; wire m_req_v; wire [36:0] m_req_addr; reg m_req_rdy = 0, m_rsp_v = 0; reg [255:0] m_rsp_data;
    wire lfault;
    ot_hgi_loader_cp ldr (.clk(clk), .rst_n(rst_n), .s_awvalid(s_awvalid), .s_awready(s_awready), .s_awaddr(s_awaddr),
        .s_wvalid(s_wvalid), .s_wready(s_wready), .s_wdata(s_wdata), .s_wstrb(4'hf), .s_bvalid(s_bvalid), .s_bready(s_bready),
        .s_arvalid(s_arvalid), .s_arready(s_arready), .s_araddr(s_araddr), .s_rvalid(s_rvalid), .s_rready(s_rready),
        .s_rdata(s_rdata), .c_awvalid(c_awvalid), .c_awready(1'b0), .c_awaddr(c_awaddr), .c_wvalid(c_wvalid), .c_wready(1'b0),
        .c_wdata(c_wdata), .c_wstrb(c_wstrb), .c_bvalid(1'b0), .c_bready(c_bready), .c_arvalid(c_arvalid), .c_arready(1'b0),
        .c_araddr(c_araddr), .c_rvalid(1'b0), .c_rready(c_rready), .c_rdata(32'd0), .lcp(lcp), .cpl(cplk),
        .m_req_v(m_req_v), .m_req_rdy(m_req_rdy), .m_req_addr(m_req_addr), .m_rsp_v(m_rsp_v), .m_rsp_data(m_rsp_data),
        .fault(lfault));
    wire [337:0] vmq; reg [273:0] vmr = 0; wire [39:0] cfg_bus; wire [15:0] ux_v;
    // native operation side
    reg xcv = 0; reg [200:0] xc = 0; wire xcr, xcpl_v, xcpl_f, xam_v, xdr; wire [16:0] xam; wire [31:0] xj, xs; wire [3:0] xg;
    ot_hgi_cp_die #(.USE_MACRO(0), .MUT(MUT), .MTP(1)) cpd (.clk(clk), .rst_n(rst_n), .lcp(lcp), .cpl(cplk), .vmq(vmq), .vmr(vmr),
        .vmstat(19'd0), .coll_rec(), .coll_ret(3'b001), .quant_rec(), .quant_ret(3'b001), .idx_rec(), .idx_ret(3'b001),
        .am_rec(), .am_ret(3'b001), .sm_rec(), .sm_ret(3'b001), .su_rec(), .su_ret(3'b001), .sfu_rec(), .sfu_ret(3'b001),
        .att_rec(), .att_ret(3'b001), .dma_rec(), .dma_ret(3'b001), .hc_rec(), .hc_ret(3'b001), .cfg_bus(cfg_bus),
        .ux_v(ux_v), .ux_rdy(16'd0), .ux_done(16'd0), .ux_fault(16'd0), .wr_quiet(1'b1),
        .x_cmd_v(xcv), .x_cmd_ready(xcr), .x_cmd(xc), .x_cmd_job(32'h12345678), .x_cmd_gen(4'hb), .x_cmd_seq(32'd5),
        .x_cpl_v(xcpl_v), .x_cpl_ready(1'b1), .x_cpl_job(xj), .x_cpl_gen(xg), .x_cpl_seq(xs), .x_cpl_fault(xcpl_f),
        .x_am_v(xam_v), .x_am_idx(xam), .x_drained_ready(xdr), .x_ext_fault(1'b0), .x_noise(17'd129279));
    // ---- HBM image + in-order memory lane
    reg [127:0] img [0:MTPV_NW-1]; reg [31:0] md [0:63]; reg [63:0] vm0 [0:MTPV_NVM-1];
    initial begin $readmemh("hgi_mtp_cpdie_image.mem", img); $readmemh("hgi_mtp_cpdie_md.mem", md); $readmemh("hgi_mtp_cpdie_vm0.mem", vm0); end
    localparam [39:0] IMG = PAGE * 4096;
    function automatic [127:0] word_at(input [39:0] a);
        reg signed [41:0] w; begin w = ($signed({2'b0, a}) - $signed({2'b0, IMG})) / 16;
            word_at = (w >= 0 && w < MTPV_NW) ? img[w] : 128'd0; end
    endfunction
    integer mq_t [0:255]; reg [36:0] mq_a [0:255]; integer mq_h = 0, mq_n = 0, tnow = 0, tlast = 0;
    always @(posedge clk) begin
        tnow = tnow + 1; m_req_rdy <= ($urandom % 4) != 0; m_rsp_v <= 1'b0;
        if (mq_n > 0 && mq_t[mq_h % 256] <= tnow) begin
            m_rsp_v <= 1'b1; m_rsp_data <= {word_at({3'd0, mq_a[mq_h % 256]} + 16), word_at({3'd0, mq_a[mq_h % 256]})};
            mq_h = mq_h + 1; mq_n = mq_n - 1;
        end
        if (m_req_v && m_req_rdy) begin
            tlast = (tnow + 40 + ($urandom % 4) > tlast + 1) ? tnow + 40 + ($urandom % 4) : tlast + 1;
            mq_a[(mq_h + mq_n) % 256] = m_req_addr; mq_t[(mq_h + mq_n) % 256] = tlast; mq_n = mq_n + 1;
        end
    end
    // ---- VM packet model
    reg [31:0] vm [0:262143]; integer vdl = 0; reg vpend = 0; reg [14:0] vsec; integer q2;
    always @(posedge clk) begin
        vmr[273] <= 1'b0;
        if (vmq[337] && !vpend) begin vpend = 1; vsec = vmq[323:309]; vdl = 1 + $urandom % 4; end
        else if (vpend) begin vdl = vdl - 1;
            if (vdl == 0) begin vmr[273] <= 1'b1; vmr[272:257] <= vmq[15:0]; vmr[256] <= 1'b0;
                for (q2 = 0; q2 < 8; q2 = q2 + 1) vmr[q2*32 +: 32] <= vm[{vsec, 3'(q2)}]; vpend = 0; end
        end
    end
    // ---- host AXI-lite
    task automatic axw(input [11:0] a, input [31:0] d);
        begin @(negedge clk); s_awvalid = 1; s_wvalid = 1; s_awaddr = a; s_wdata = d;
            @(posedge clk); while (!(s_awready && s_wready)) @(posedge clk); @(negedge clk); s_awvalid = 0; s_wvalid = 0;
            while (!s_bvalid) @(negedge clk); end
    endtask
    reg [31:0] rd;
    task automatic axr(input [11:0] a);
        begin @(negedge clk); s_arvalid = 1; s_araddr = a; @(posedge clk); while (!s_arready) @(posedge clk);
            @(negedge clk); s_arvalid = 0; while (!s_rvalid) @(negedge clk); rd = s_rdata; end
    endtask
    // ---- the operations (DS shapes) and the independent expectation of every launch's body
    localparam integer NOPS = 9;
    reg [200:0] ops [0:NOPS-1];
    function automatic [200:0] mk(input [3:0] op, input [7:0] idx, input [3:0] nc, input [31:0] pos, input [16:0] t1);
        reg [200:0] c; integer j;
        begin c = 0; c[3:0] = op; c[11:4] = idx; c[15:12] = nc; c[47:16] = pos; c[64:48] = t1;
            for (j = 0; j < 8; j = j + 1) c[65 + 17*j +: 17] = 17'(1000 + 37 * j + pos); mk = c; end
    endfunction
    initial begin
        ops[0] = mk(0, 0, 3, 100, 7);  ops[1] = mk(0, 5, 2, 200, 9);  ops[2] = mk(0, 39, 1, 300, 11);
        ops[3] = mk(1, 0, 2, 400, 13); ops[4] = mk(2, 0, 2, 500, 15); ops[5] = mk(3, 0, 5, 600, 17);
        ops[6] = mk(3, 2, 5, 700, 19); ops[7] = mk(4, 0, 5, 800, 21); ops[8] = mk(5, 3, 1, 900, 23);
    end
    // expected (kind, L') per launch, from the operation alone (v41_dspark expand: swapin L / 40 + st precedes the body)
    integer exp_kind [0:1023]; integer exp_l [0:1023]; integer nexp = 0;
    task automatic expect_op(input [200:0] c);
        integer op, idx, nc, col, st; begin
            op = c[3:0]; idx = c[11:4]; nc = c[15:12];
            case (op)
                0: for (col = 0; col < nc; col = col + 1) begin
                       exp_kind[nexp] = 0; nexp = nexp + 1;
                       if (idx == 0) begin exp_kind[nexp] = 2; nexp = nexp + 1; end
                       exp_kind[nexp] = 3; exp_l[nexp] = idx; nexp = nexp + 1;
                       exp_kind[nexp] = 1; nexp = nexp + 1; end
                1: for (col = 0; col < nc; col = col + 1) begin exp_kind[nexp] = 0; exp_kind[nexp + 1] = 4; nexp = nexp + 2; end
                2: for (col = 0; col < nc; col = col + 1) begin exp_kind[nexp] = 5; nexp = nexp + 1; end
                3: begin
                       for (col = 0; col < 5; col = col + 1) begin
                           exp_kind[nexp] = 0; nexp = nexp + 1;
                           if (idx == 0) begin exp_kind[nexp] = 6; nexp = nexp + 1; end
                           exp_kind[nexp] = 7; exp_l[nexp] = idx; nexp = nexp + 1;
                           exp_kind[nexp] = 1; nexp = nexp + 1; end
                       for (col = 0; col < 5; col = col + 1) begin
                           exp_kind[nexp] = 0; exp_kind[nexp + 1] = 8; exp_l[nexp + 1] = idx; exp_kind[nexp + 2] = 1; nexp = nexp + 3; end
                   end
                4: for (col = 0; col < 5; col = col + 1) begin exp_kind[nexp] = 0; exp_kind[nexp + 1] = 9; nexp = nexp + 2; end
                5: begin exp_kind[nexp] = 10; nexp = nexp + 1; end
            endcase
        end
    endtask
    // ---- checks on every translator-owned completion
    integer ncpl = 0, nam = 0, nres = 0, errs = 0, hostc = 0;
    reg [17:0] last_tok;
    always @(posedge clk) if (rst_n) begin
        if (cpd.cpl_v && cpd.x_run) begin
            begin : chk
                integer id;
                id = (exp_kind[ncpl] == 3 || exp_kind[ncpl] == 7 || exp_kind[ncpl] == 8) ? 100 * exp_kind[ncpl] + exp_l[ncpl] : exp_kind[ncpl];
                if (ncpl >= nexp || cpd.cpl_token !== 18'(1000 + id) || cpd.cpl_status !== 4'd0) begin
                    if (errs < 6) $display("FAIL launch %0d: token %0d status %0d, expected body kind %0d L' %0d (token %0d)",
                                           ncpl, cpd.cpl_token, cpd.cpl_status, exp_kind[ncpl], exp_l[ncpl], 1000 + id);
                    errs = errs + 1;
                end
                if (exp_kind[ncpl] == 4 || exp_kind[ncpl] == 10) begin nres = nres + 1; last_tok = cpd.cpl_token; end
            end
            ncpl = ncpl + 1;
        end
        if (cpd.cpl[1] && cpd.x_run) begin $display("FAIL a translator completion reached the host"); errs = errs + 1; end
        if (xam_v) begin nam = nam + 1; if ({1'b0, xam} !== last_tok) begin $display("FAIL am %0d vs %0d", xam, last_tok); errs = errs + 1; end end
    end
    integer i, t, a;
    initial begin
        for (a = 0; a < 262144; a = a + 1) vm[a] = 0;
        repeat (3) @(negedge clk);
        for (a = 0; a < MTPV_NVM; a = a + 1) vm[vm0[a][49:32]] = vm0[a][31:0];
        rst_n = 1; repeat (4) @(negedge clk);
        axw(12'hC14, 0);
        for (a = 0; a < 32; a = a + 1) begin axw(12'hD00 + 8 * a, md[2*a]); axw(12'hD04 + 8 * a, md[2*a + 1]); end
        t = 0; repeat (4) @(negedge clk);
        while ((cpd.u_cp.u_cfg.st_hold || !cpd.u_cp.cfg_loaded) && t < 4000) begin @(negedge clk); t = t + 1; end
        repeat (3) @(negedge clk);
        axr(12'hC24); if (rd[3:1] != 0 || !rd[0]) begin $display("FAIL cfg load err %0d loaded %0d", rd[3:1], rd[0]); errs = errs + 1; end
        for (i = 0; i < NOPS; i = i + 1) begin
            expect_op(ops[i]);
            xc = ops[i]; xcv = 1; while (!xcr) @(negedge clk); @(negedge clk); xcv = 0;
            t = 0; while (!xcpl_v && t < 400000) begin @(negedge clk); t = t + 1; end
            if (!xcpl_v || xcpl_f || xj != 32'h12345678 || xs != 32'd5) begin $display("FAIL operation %0d (fault %0d)", i, xcpl_f); errs = errs + 1; end
            repeat (3) @(negedge clk);
        end
        if (ncpl != nexp) begin $display("FAIL launches %0d expected %0d", ncpl, nexp); errs = errs + 1; end
        if (nam != nres) begin $display("FAIL am %0d results %0d", nam, nres); errs = errs + 1; end
        // the host path after the MTP job: an AR doorbell (entry 0) completes with the AR body's token
        axw(12'hC00, 5); axw(12'hC04, 77); axw(12'hC08, 32'h4321); axw(12'hC0C, {20'd0, 4'd1, 8'h05}); axw(12'hC10, 1);
        t = 0; rd = 0; while (rd[10:8] == 0 && t < 40000) begin axr(12'hC20); t = t + 1; end
        if (rd[10:8] == 0) begin $display("FAIL host doorbell: no completion"); errs = errs + 1; end
        else begin axr(12'hC40); if (rd[17:0] !== 18'd999) begin $display("FAIL host token %0d", rd[17:0]); errs = errs + 1; end
                   axr(12'hC4C); if (rd[7:4] !== 0) begin $display("FAIL host status %0d", rd[7:4]); errs = errs + 1; end
                   axr(12'hC50); end
        if (errs == 0) $display("PASS HGI_CP_DIE_MTP ops=%0d launches=%0d results=%0d am=%0d (G26 KS %0d) + host AR", NOPS, ncpl, nres, nam, MTPV_KS);
        else $display("FATAL HGI_CP_DIE_MTP errors=%0d", errs);
        $finish;
    end
    initial begin #4000000; $display("FATAL HGI_CP_DIE_MTP watchdog (launches %0d of %0d)", ncpl, nexp); $finish; end
endmodule
