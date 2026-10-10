// hgi-takeover 2026-10-09: the hbm-forks sequencer vectors (tools/hgi_seq_vectors.py) run through the DIE binding of the
// command processor: ot_hgi_loader_cp (host AXI-lite window: CFG window + CFG_COMMIT, doorbell, completion FIFO, CF-0
// read-back) <-> loader link <-> ot_hgi_cp_die (ot_hgi_cp + doorbell / completion / fetch stations, VM packet read
// client, per-unit dispatch credits and the coll / quant record buses).  The record ring is served on the loader's
// memory lane 1 (m_req / m_rsp), VM reads by a packet-protocol model.  Every dispatch is checked against the vectors
// exactly as tb_hgi_seq does; coll (6) and quant (4) dispatches are also checked on their die record buses.
module tb_hgi_cp_die_seq;
    parameter integer MUT = 0;
`include "hgi_seq_sizes.svh"
`include "hgi_seq_sizes_conf.svh"
    localparam integer NCASE = SEQ_NCASE, NEXP = SEQ_NEXP, NW = SEQ_NW;
    localparam integer PAGE = 32'h10;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg [7:0] rank;
    // host AXI-lite
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
    wire [337:0] vmq; reg [273:0] vmr = 0; wire [967:0] coll_rec; wire [682:0] quant_rec; wire [1818:0] idx_rec; reg [2:0] idx_ret = 3'b001; wire [39:0] cfg_bus;
    wire [690:0] am_rec; reg [2:0] am_ret = 3'b001;
    wire [938:0] sm_rec, hc_rec; wire [2197:0] su_rec; wire [1173:0] sfu_rec; wire [1471:0] att_rec; wire [703:0] dma_rec;
    reg [2:0] sm_ret = 3'b001, su_ret = 3'b001, sfu_ret = 3'b001, att_ret = 3'b001, dma_ret = 3'b001, hc_ret = 3'b001;
    wire [15:0] ux_v; reg [15:0] ux_rdy = 0, ux_done = 0, ux_fault = 0; reg [2:0] coll_ret = 3'b001, quant_ret = 3'b001;
    ot_hgi_cp_die #(.USE_MACRO(0), .MUT(MUT)) cpd (.clk(clk), .rst_n(rst_n), .lcp(lcp), .cpl(cplk), .vmq(vmq), .vmr(vmr),
        .vmstat(19'd0), .coll_rec(coll_rec), .coll_ret(coll_ret), .quant_rec(quant_rec), .quant_ret(quant_ret), .idx_rec(idx_rec), .idx_ret(idx_ret),
        .am_rec(am_rec), .am_ret(am_ret),
        .sm_rec(sm_rec), .sm_ret(sm_ret), .su_rec(su_rec), .su_ret(su_ret), .sfu_rec(sfu_rec), .sfu_ret(sfu_ret),
        .att_rec(att_rec), .att_ret(att_ret), .dma_rec(dma_rec), .dma_ret(dma_ret), .hc_rec(hc_rec), .hc_ret(hc_ret), .cfg_bus(cfg_bus), .ux_v(ux_v), .ux_rdy(ux_rdy), .ux_done(ux_done), .ux_fault(ux_fault), .wr_quiet(1'b1));
    // the sequencer-side view the vector checks use
    wire [15:0] u_v = cpd.u_cp.u_v; wire [15:0] u_rdy = cpd.u_rdy; wire [127:0] d_hdr = cpd.u_cp.d_hdr;
    wire [255:0] d_sut = cpd.u_cp.d_sut; wire [1791:0] d_desc = cpd.u_cp.d_desc; wire [146:0] d_n = cpd.u_cp.d_n;
    wire [20:0] d_pos1 = cpd.u_cp.d_pos1, d_pslot1 = cpd.u_cp.d_pslot1; wire [15:0] d_L = cpd.u_cp.d_L, d_L1 = cpd.u_cp.d_L1;
    wire busy = cpd.u_cp.u_seq.busy;
    reg [15:0] u_done = 0, u_fault = 0;
    always @* begin
        ux_done = u_done & ~16'h07FE; ux_fault = u_fault & ~16'h07FE;
        am_ret = {u_fault[7], u_done[7], 1'b1};
        sm_ret = {u_fault[1], u_done[1], 1'b1}; su_ret = {u_fault[2], u_done[2], 1'b1}; sfu_ret = {u_fault[3], u_done[3], 1'b1};
        att_ret = {u_fault[5], u_done[5], 1'b1}; dma_ret = {u_fault[8], u_done[8], 1'b1}; hc_ret = {u_fault[10], u_done[10], 1'b1};
        coll_ret = {u_fault[6], u_done[6], 1'b1}; quant_ret = {u_fault[4], u_done[4], 1'b1}; idx_ret = {u_fault[9], u_done[9], 1'b1};
    end
    reg [63:0] tks [0:NCASE*16-1];
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
    task automatic cfg_pair(input [4:0] pr, input [31:0] lo, input [31:0] hi);
        begin axw(12'hD00 + 8 * pr, lo); axw(12'hD04 + 8 * pr, hi); end
    endtask
    task automatic cfg_load(input [31:0] voc, input [31:0] ctx, input [31:0] grp, input [31:0] entry);
        integer w; begin
            cfg_pair(5'd20, voc, ctx); cfg_pair(5'd23, grp, 0); cfg_pair(5'd28, entry, 0); cfg_pair(5'd30, PAGE, 1);
            cfg_pair(5'd31, 0, 0); repeat (4) @(negedge clk);
            w = 0; while ((cpd.u_cp.u_cfg.st_hold || !cpd.u_cp.cfg_loaded) && w < 2000) begin @(negedge clk); w = w + 1; end
            repeat (3) @(negedge clk);
            axr(12'hC24); if (rd[3:1] != 0 || !rd[0]) begin $display("FAIL cfg load err %0d loaded %0d", rd[3:1], rd[0]); fails = fails + 1; end
            axr(12'hC28); if (rd !== voc) begin $display("FAIL cfg read-back vocab %h", rd); fails = fails + 1; end
            axr(12'hC2C); if (rd !== ctx) begin $display("FAIL cfg read-back ctx %h", rd); fails = fails + 1; end
        end
    endtask
    reg [127:0] img [0:NW-1];
    reg [95:0] vmi [0:CONF_NVMI-1];
    reg [255:0] ex [0:NEXP-1];
    reg [31:0] cfg [0:NCASE*12-1];
    reg [95:0] vmw [0:4095];
    reg [63:0] vm0 [0:SEQ_NVM0-1];
    integer nvmw = 0;
    initial begin
`ifdef SEQ_CONF
        $readmemh("hgi_seq_image_conf.mem", img);
        $readmemh("hgi_seq_expect_conf.mem", ex); $readmemh("hgi_seq_cfg_conf.mem", cfg);
        for (nvmw = 0; nvmw < 4096; nvmw = nvmw + 1) vmw[nvmw] = {96{1'b1}};
        $readmemh("hgi_seq_vmi_conf.mem", vmi);
        for (nvmw = 0; nvmw < NCASE*16; nvmw = nvmw + 1) tks[nvmw] = 0;
`elsif SEQ_STALE
        $readmemh("hgi_seq_image.mem", img);
        $readmemh("hgi_seq_expect_stale.mem", ex); $readmemh("hgi_seq_cfg_stale.mem", cfg); $readmemh("hgi_seq_toks_stale.mem", tks);
        for (nvmw = 0; nvmw < 4096; nvmw = nvmw + 1) vmw[nvmw] = {96{1'b1}};
        $readmemh("hgi_seq_vmw_stale.mem", vmw);
`else
        $readmemh("hgi_seq_image.mem", img);
        $readmemh("hgi_seq_expect.mem", ex); $readmemh("hgi_seq_cfg.mem", cfg); $readmemh("hgi_seq_toks.mem", tks);
        for (nvmw = 0; nvmw < 4096; nvmw = nvmw + 1) vmw[nvmw] = {96{1'b1}};
        $readmemh("hgi_seq_vmw.mem", vmw);
`endif
        $readmemh("hgi_seq_vm0.mem", vm0);
    end
    // ---- HBM: the image at byte PAGE*4096 (word w at +16 w); in-order sector responses after 2..8 cycles
    localparam [39:0] IMG = PAGE * 4096;
    function automatic [127:0] word_at(input [39:0] a);
        reg signed [41:0] w; begin w = ($signed({2'b0, a}) - $signed({2'b0, IMG})) / 16;
            word_at = (w >= 0 && w < NW) ? img[w] : 128'hDEAD; end
    endfunction
    // F5: the memory lane accepts back-to-back requests and answers IN ORDER after FLAT cycles (+0..3 jitter, never
    // before its predecessor); a request accepted while 48 are in flight is a violation
    integer FLAT = 40; integer mq_t [0:255]; reg [36:0] mq_a [0:255]; integer mq_h = 0, mq_n = 0, tnow = 0, tlast = 0, maxf = 0;
    initial if (!$value$plusargs("FLAT=%d", FLAT)) FLAT = 40;
    always @(posedge clk) begin
        tnow = tnow + 1;
        m_req_rdy <= ($urandom % 4) != 0; m_rsp_v <= 1'b0;
        if (mq_n > 0 && mq_t[mq_h % 256] <= tnow) begin
            m_rsp_v <= 1'b1; m_rsp_data <= {word_at({3'd0, mq_a[mq_h % 256]} + 16), word_at({3'd0, mq_a[mq_h % 256]})};
            mq_h = mq_h + 1; mq_n = mq_n - 1;
        end
        if (m_req_v && m_req_rdy) begin
            if (mq_n >= 48) $fatal(1, "more than 48 ring sectors in flight");
            tlast = (tnow + FLAT + ($urandom % 4) > tlast + 1) ? tnow + FLAT + ($urandom % 4) : tlast + 1;
            mq_a[(mq_h + mq_n) % 256] = m_req_addr; mq_t[(mq_h + mq_n) % 256] = tlast; mq_n = mq_n + 1;
            if (mq_n > maxf) maxf = mq_n;
        end
    end
    // ---- VM: the bench's memory; a unit's writes land at its RETIRE (vmw: dispatch index -> addr, value)
    reg [31:0] vm [0:262143];
    integer vdl = 0; reg vpend = 0; reg [14:0] vsec; integer q2;
    always @(posedge clk) begin
        vmr[273] <= 1'b0;
        if (vmq[337] && !vpend) begin vpend = 1; vsec = vmq[323:309]; vdl = 1 + $urandom % 4; end
        else if (vpend) begin
            vdl = vdl - 1;
            if (vdl == 0) begin
                vmr[273] <= 1'b1; vmr[272:257] <= vmq[15:0]; vmr[256] <= 1'b0;
                for (q2 = 0; q2 < 8; q2 = q2 + 1) vmr[q2*32 +: 32] <= vm[{vsec, 3'(q2)}];
                vpend = 0;
            end
        end
    end
    // ---- units: accept, check, retire after a delay
    integer outst [0:15]; integer pend [0:15][0:31]; integer pdi [0:15][0:31]; integer pn [0:15];
    integer ei = 0, nd = 0, fails = 0, w, k, uu, j, fault_at = -1;
    reg [3:0] cu;
    task automatic retire_writes(input integer di);
        integer q; begin
            for (q = 0; q < 4096; q = q + 1)
                if (vmw[q][95:64] == di) vm[vmw[q][49:32]] = vmw[q][31:0];
        end
    endtask
    always @(posedge clk) begin
        ux_rdy <= $urandom; u_done <= 0; u_fault <= 0;
        for (uu = 1; uu < 16; uu = uu + 1) begin
            for (k = 0; k < pn[uu]; k = k + 1) pend[uu][k] = pend[uu][k] - 1;
            if (pn[uu] > 0 && pend[uu][0] <= 0) begin
                u_done[uu] <= 1'b1; outst[uu] = outst[uu] - 1;
                retire_writes(pdi[uu][0]);
                for (k = 0; k < 31; k = k + 1) begin pend[uu][k] = pend[uu][k + 1]; pdi[uu][k] = pdi[uu][k + 1]; end
                pn[uu] = pn[uu] - 1;
            end
        end
        if (|(u_v & u_rdy)) begin
            cu = d_hdr[127:124];
            if (u_v !== (16'd1 << cu)) begin $display("FAIL dispatch port %h for unit %0d", u_v, cu); fails = fails + 1; end
            for (w = 1; w < 16; w = w + 1) if (d_hdr[102 + w] && outst[w] != 0) begin
                $display("FAIL wait rule: unit %0d dispatched while unit %0d has %0d outstanding", cu, w, outst[w]); fails = fails + 1; end
            if (ei + 11 > NEXP) begin $display("FAIL extra dispatch %0d", nd); fails = fails + 1; end
            else begin
                if (ex[ei][3:0] !== cu || ex[ei][19:4] !== d_L || ex[ei][35:20] !== d_L1 || ex[ei][56:36] !== d_pos1 ||
                    ex[ei][77:57] !== d_pslot1 || ex[ei + 1][127:0] !== d_hdr || ex[ei + 2] !== d_sut ||
                    ex[ei + 10][146:0] !== d_n) begin
                    $display("FAIL dispatch %0d unit %0d/%0d L %0d/%0d L1 %0d/%0d pos1 %0d pslot1 %0d hdr %b sut %b n %b",
                        nd, cu, ex[ei][3:0], d_L, ex[ei][19:4], d_L1, ex[ei][35:20], d_pos1 === ex[ei][56:36],
                        d_pslot1 === ex[ei][77:57], ex[ei+1][127:0] === d_hdr, ex[ei+2] === d_sut, ex[ei+10][146:0] === d_n);
                    fails = fails + 1;
                end
                for (j = 0; j < 7; j = j + 1) if (ex[ei + 3 + j] !== d_desc[j*256 +: 256]) begin
                    $display("FAIL dispatch %0d unit %0d descriptor %0d: base %h/%h n %h/%h", nd, cu, j,
                             d_desc[j*256 + 8 +: 40], ex[ei + 3 + j][47:8], d_desc[j*256 + 48 +: 20], ex[ei + 3 + j][67:48]);
                    fails = fails + 1;
                end
            end
            if (cu == 6) begin exp_coll = {rank, d_n[6*21 +: 21], d_n[4*21 +: 21], d_n[0 +: 21], d_desc[6*256 +: 256], d_desc[4*256 +: 256], d_desc[0 +: 256], d_hdr, 1'b1}; check_coll = 1; end
            begin : xr
                reg [20:0] nA_, nB_, nC_, nO_; reg [255:0] A_, B_, C_, D_, O_, R_, I_;
                nA_ = d_n[0 +: 21]; nB_ = d_n[21 +: 21]; nC_ = d_n[42 +: 21]; nO_ = d_n[4*21 +: 21];
                A_ = d_desc[0 +: 256]; B_ = d_desc[256 +: 256]; C_ = d_desc[512 +: 256]; D_ = d_desc[768 +: 256];
                O_ = d_desc[1024 +: 256]; R_ = d_desc[1280 +: 256]; I_ = d_desc[1536 +: 256];
                if (cu == 1) exp_x = {nB_, nA_, O_, B_, A_, d_hdr, 1'b1};
                if (cu == 2) exp_x = {nA_, I_, R_, O_, D_, C_, B_, A_, d_sut, d_hdr, 1'b1};
                if (cu == 3) exp_x = {nA_, O_, C_, B_, A_, d_hdr, 1'b1};
                if (cu == 5) exp_x = {d_pos1, nC_, nB_, O_, C_, B_, A_, d_sut, d_hdr, 1'b1};
                if (cu == 8) exp_x = {d_pos1, nO_, nA_, O_, A_, d_hdr, 1'b1};
                if (cu == 10) exp_x = {nO_, nA_, O_, B_, A_, d_hdr, 1'b1};
                if (cu == 1 || cu == 2 || cu == 3 || cu == 5 || cu == 8 || cu == 10) begin chk_u = cu; check_x = 1; end
            end
            if (cu == 7) begin exp_am = {rank, d_n[4*21 +: 21], d_n[0 +: 21], d_desc[4*256 +: 256], d_desc[0 +: 256], d_hdr, 1'b1}; check_am = 1; end
            if (cu == 4) begin exp_quant = {d_n[4*21 +: 21], d_n[0 +: 21], d_desc[4*256 +: 256], d_desc[0 +: 256], d_hdr, 1'b1}; check_quant = 1; end
            ei = ei + 11;
            outst[cu] = outst[cu] + 1;
            pend[cu][pn[cu]] = (cu == 9 || cu == 7) ? 40 + $urandom % 21 : $urandom % 21; pdi[cu][pn[cu]] = nd;
            pn[cu] = pn[cu] + 1;
            if (nd == fault_at) u_fault[cu] <= 1'b1;
            nd = nd + 1;
        end
    end
    reg check_coll = 0, check_quant = 0, check_am = 0; reg [967:0] exp_coll; reg [682:0] exp_quant; reg [690:0] exp_am;
    integer n_am = 0, n_x = 0; reg check_x = 0; reg [3:0] chk_u; reg [2197:0] exp_x;
    reg [2197:0] got_x; reg got_v; reg [3:0] got_u;
    always @(negedge clk) begin
        if (coll_rec[0]) begin if (!check_coll || coll_rec !== exp_coll) begin $display("FAIL coll record bus"); fails = fails + 1; end check_coll = 0; end
        got_v = 1'b0; got_x = 0;
        if (sm_rec[0]) begin got_v = 1; got_u = 1; got_x = sm_rec; end
        if (su_rec[0]) begin got_v = 1; got_u = 2; got_x = su_rec; end
        if (sfu_rec[0]) begin got_v = 1; got_u = 3; got_x = sfu_rec; end
        if (att_rec[0]) begin got_v = 1; got_u = 5; got_x = att_rec; end
        if (dma_rec[0]) begin got_v = 1; got_u = 8; got_x = dma_rec; end
        if (hc_rec[0]) begin got_v = 1; got_u = 10; got_x = hc_rec; end
        if (got_v) begin
            if (!check_x || got_u != chk_u || got_x !== exp_x) begin $display("FAIL unit %0d record bus", got_u); fails = fails + 1; end
            check_x = 0; n_x = n_x + 1;
        end
        if (am_rec[0]) begin if (!check_am || am_rec !== exp_am) begin $display("FAIL argmax record bus"); fails = fails + 1; end check_am = 0; n_am = n_am + 1; end
        if (quant_rec[0]) begin if (!check_quant || quant_rec !== exp_quant) begin $display("FAIL quant record bus"); fails = fails + 1; end check_quant = 0; end
    end
    integer c, n0, t, a, nbeat, tbad; reg [17:0] c_tok; reg [3:0] c_st; reg c_tx; reg [19:0] c_pos;
    initial begin
        for (k = 0; k < 16; k = k + 1) begin outst[k] = 0; pn[k] = 0; end
        for (a = 0; a < 262144; a = a + 1) vm[a] = 0;
        rank = 0;
        repeat (3) @(posedge clk); rst_n = 1; @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            for (a = 0; a < SEQ_NVM0; a = a + 1) vm[vm0[a][49:32]] = vm0[a][31:0];
            for (a = 0; a < 16; a = a + 1) vm[32'hF000 + a] = 0;
            for (a = 0; a < 16; a = a + 1) vm[32'hF010 + a] = 0;
            vm[32'hF000] = 3; vm[32'hF100] = 1 << 21;
`ifdef SEQ_CONF
            for (a = 0; a < 262144; a = a + 1) vm[a] = 0;
            for (a = 0; a < CONF_NVMI; a = a + 1) if (vmi[a][95:64] == c) vm[vmi[a][49:32]] = vmi[a][31:0];
`endif
            rank = cfg[c*12 + 3]; axw(12'hC14, rank);
            cfg_load(cfg[c*12 + 4], cfg[c*12 + 5], (cfg[c*12 + 4] == 129280) ? 96 : 4, cfg[c*12 + 0]);
            fault_at = (cfg[c*12 + 9] == 32'hFFFF) ? -1 : cfg[c*12 + 10] + cfg[c*12 + 9];
            n0 = nd; ei = cfg[c*12 + 10] * 11;
            if (nd != cfg[c*12 + 10]) begin $display("FAIL case %0d starts at dispatch %0d, expected %0d", c, nd, cfg[c*12 + 10]);
                fails = fails + 1; nd = cfg[c*12 + 10]; n0 = nd; end
            axw(12'hC00, cfg[c*12 + 1]); axw(12'hC04, cfg[c*12 + 2]); axw(12'hC08, 32'h1234); axw(12'hC0C, {20'd0, cfg[c*12 + 11][11:8], 8'h05});   // ncol, entry 0, gen 5
            axw(12'hC10, 1);
            // completions through the host window: CTL.TOKX beats (0xC4C bit 8) {token, pos + i - 1, status 0}, then END
            nbeat = 0; tbad = 0; c_tx = 1;
            while (c_tx) begin
                t = 0; rd = 0; while (rd[10:8] == 0 && t < 400000) begin axr(12'hC20); t = t + 1; end
                if (rd[10:8] == 0) begin c_tx = 0; c_st = 4'hE; end
                else begin
                    axr(12'hC40); c_tok = rd[17:0]; axr(12'hC44); c_pos = rd[19:0]; axr(12'hC4C); c_st = rd[7:4]; c_tx = rd[8];
                    axr(12'hC50);
                    if (c_tx) begin
                        if (nbeat >= 16 || c_tok !== tks[c*16 + nbeat][49:32] || c_pos !== tks[c*16 + nbeat][19:0] || c_st !== 0) tbad = 1;
                        nbeat = nbeat + 1;
                    end
                end
            end
            if (c_st == 4'hE) begin $display("FAIL case %0d: no completion (dispatches %0d)", c, nd - n0); fails = fails + 1; end
            else if (c_tok !== cfg[c*12 + 7][17:0] || c_st !== cfg[c*12 + 8][3:0] || nd - n0 !== cfg[c*12 + 6]) begin
                $display("FAIL case %0d: token %0d/%0d status %0d/%0d dispatches %0d/%0d", c, c_tok, cfg[c*12 + 7],
                         c_st, cfg[c*12 + 8], nd - n0, cfg[c*12 + 6]); fails = fails + 1;
            end else if (tbad || nbeat !== cfg[c*12 + 11][4:0]) begin
                $display("FAIL case %0d: TOKX beats %0d/%0d or token/pos", c, nbeat, cfg[c*12 + 11][4:0]); fails = fails + 1;
            end else $display("SEQ-DIE case %0d: %0d dispatches, token %0d status %0d tokx %0d", c, nd - n0, c_tok, c_st, nbeat);
            t = 0; while (busy && t < 2000) begin @(negedge clk); t = t + 1; end
            nd = cfg[c*12 + 10] + cfg[c*12 + 6];
        end
        if (fails == 0) $display("HGI_SEQ_DIE PASS cases=%0d dispatches=%0d argmax_records=%0d other_unit_records=%0d max_fetch_inflight=%0d", NCASE, nd, n_am, n_x, maxf);
        else $display("HGI_SEQ_DIE FAIL %0d", fails);
        $finish;
    end
endmodule
