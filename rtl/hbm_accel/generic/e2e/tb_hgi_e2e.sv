`timescale 1ns/1ps
// hgi-e2e (2026-10-09): DIE-LEVEL harness of the generic HBM die (r25 / R25G with HGI-1): one layer of a real program
// through the die's command path, unit by unit real RTL where it exists, a labelled replay STUB where it does not.
//
//   host AXI-lite -> ot_hgi_loader_cp (CFG window: the full 64-word model descriptor + CFG_COMMIT; doorbell;
//   completion FIFO) -> loader link -> ot_hgi_cp_die (ot_hgi_cp = config path + v1.0 sequencer; record-ring fetch on
//   loader memory lane 1; VM packet reads; per-unit dispatch credits; coll / quant / idx record buses; ux_* ports)
//   -> unit slots:
//     REAL_DMA    ot_hgi_dma_record (LEGACY 0) + ot_hgi_dma_mover (kport lane -> HBM model, VM packet client)
//     REAL_QUANT  unit-4 QDQ ops -> ot_hgi_quant_unit (record -> transport -> VM packet client); other unit-4 ops
//                 (ROW_NORM / HC_PRE_NORM / HC_POST / SOFTMAX: the FUSED front, not on main) -> stub
//     REAL_IDX    ot_hgi_idx_unit on the die idx record bus (native selector peers tied: no IDX.INDEX on these layers)
//     everything else: STUB (labelled): accepts the record, holds it for the simulator's unit cost, then applies the
//                 simulator's golden writes of that record (replay: a stub computes nothing).
//   Memories are MODELS (hgi_e2e_dpi.cpp): VM (packet clients with in-order responses after VLAT cycles, up to 4
//   outstanding as the HGI VM fast path) and HBM (sparse sectors; record fetch and kport lanes after FLAT / KLAT).
// Checks (hgi_e2e_dpi.cpp): every CP dispatch == the golden record (unit, header, effective base / n of every
// operand); every REAL unit's retire: its golden VM / HBM writes present bit for bit, no stray writes; at the end the
// whole VM == the golden final VM and every golden HBM write range == golden; the completion token == golden.
// DIE GAP used by the harness: the ux_* ports of ot_hgi_cp_die carry valid / ready / done / fault but no record
// payload; the harness taps the sequencer's dispatch registers (cpd.u_cp.d_*) for ux units (a die-level bus is owed).
module tb_hgi_e2e;
    parameter integer REAL_DMA = 0, REAL_QUANT = 0, REAL_IDX = 0, REAL_SU = 0, REAL_SFU = 0;
    parameter integer SU_N = 16, SU_M = 8;
    parameter integer FLAT = 40, KLAT = 40, VLAT = 6;
    import "DPI-C" function int e2e_init(input string d, input string outp);
    import "DPI-C" function void e2e_vm_sector(input int unit, input int sec, input bit we, input bit [255:0] wd,
                                               input bit [31:0] mask, output bit [255:0] rd);
    import "DPI-C" function void e2e_hbm_sector(input longint addr, input bit we, input bit [255:0] wd,
                                                input bit [31:0] strb, output bit [255:0] rd);
    import "DPI-C" function int e2e_dispatch(input int unit, input bit [127:0] hdr, input bit [1791:0] desc,
                                             input bit [146:0] n, input longint cyc);
    import "DPI-C" function int e2e_cost(input int k);
    import "DPI-C" function void e2e_stub_retire(input int k, input longint cyc);
    import "DPI-C" function int e2e_real_retire(input int k, input longint cyc);
    import "DPI-C" function int e2e_finish(input longint cyc, input int token, input int status);

    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    longint cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg [8*512-1:0] dir, outp;
    reg [31:0] host [0:79];        // md words 0..63, token 64, pos 65, expected token 66, rank 67, ncol 68
    // ---------------------------------------------------------------- host AXI-lite + loader + CP die
    reg s_awvalid = 0, s_wvalid = 0, s_bready = 1, s_arvalid = 0, s_rready = 1; reg [11:0] s_awaddr = 0, s_araddr = 0;
    reg [31:0] s_wdata = 0; wire s_awready, s_wready, s_bvalid, s_arready, s_rvalid; wire [31:0] s_rdata;
    wire c_awvalid, c_wvalid, c_arvalid, c_bready, c_rready; wire [11:0] c_awaddr, c_araddr; wire [31:0] c_wdata; wire [3:0] c_wstrb;
    wire [418:0] lcp; wire [221:0] cplk; wire m_req_v; wire [36:0] m_req_addr; reg m_req_rdy = 0, m_rsp_v = 0; reg [255:0] m_rsp_data = 0;
    wire lfault;
    ot_hgi_loader_cp ldr (.clk(clk), .rst_n(rst_n), .s_awvalid(s_awvalid), .s_awready(s_awready), .s_awaddr(s_awaddr),
        .s_wvalid(s_wvalid), .s_wready(s_wready), .s_wdata(s_wdata), .s_wstrb(4'hf), .s_bvalid(s_bvalid), .s_bready(s_bready),
        .s_arvalid(s_arvalid), .s_arready(s_arready), .s_araddr(s_araddr), .s_rvalid(s_rvalid), .s_rready(s_rready),
        .s_rdata(s_rdata), .c_awvalid(c_awvalid), .c_awready(1'b0), .c_awaddr(c_awaddr), .c_wvalid(c_wvalid), .c_wready(1'b0),
        .c_wdata(c_wdata), .c_wstrb(c_wstrb), .c_bvalid(1'b0), .c_bready(c_bready), .c_arvalid(c_arvalid), .c_arready(1'b0),
        .c_araddr(c_araddr), .c_rvalid(1'b0), .c_rready(c_rready), .c_rdata(32'd0), .lcp(lcp), .cpl(cplk),
        .m_req_v(m_req_v), .m_req_rdy(m_req_rdy), .m_req_addr(m_req_addr), .m_rsp_v(m_rsp_v), .m_rsp_data(m_rsp_data),
        .fault(lfault));
    wire [337:0] cp_vmq; wire [273:0] cp_vmr;
    wire [967:0] coll_rec; wire [682:0] quant_rec; wire [1818:0] idx_rec; wire [39:0] cfg_bus;
    reg  [2:0] coll_ret, quant_ret, idx_ret;
    wire [15:0] ux_v; reg [15:0] ux_rdy, ux_done, ux_fault;
    ot_hgi_cp_die #(.USE_MACRO(0)) cpd (.clk(clk), .rst_n(rst_n), .lcp(lcp), .cpl(cplk), .vmq(cp_vmq), .vmr(cp_vmr),
        .vmstat(19'd0), .coll_rec(coll_rec), .coll_ret(coll_ret), .quant_rec(quant_rec), .quant_ret(quant_ret),
        .idx_rec(idx_rec), .idx_ret(idx_ret), .cfg_bus(cfg_bus), .ux_v(ux_v), .ux_rdy(ux_rdy), .ux_done(ux_done),
        .ux_fault(ux_fault), .wr_quiet(1'b1));
    hgi_e2e_vmc #(.UNIT(0), .LAT(VLAT)) vm_cp (.clk(clk), .rst_n(rst_n), .q(cp_vmq), .r(cp_vmr));
    // the sequencer's dispatch (the record payload of the ux units: die gap, see header)
    wire [15:0]   s_uv = cpd.u_cp.u_v;
    wire [15:0]   s_ur = cpd.u_rdy;
    wire [127:0]  d_hdr = cpd.u_cp.d_hdr;
    wire [1791:0] d_desc = cpd.u_cp.d_desc;
    wire [146:0]  d_n = cpd.u_cp.d_n;
    wire [20:0]   d_pos1 = cpd.u_cp.d_pos1;
    // ---------------------------------------------------------------- record-ring fetch (loader memory lane 1): HBM model
    integer fd = 0; reg fpend = 0; reg [36:0] fa;
    always @(posedge clk) begin
        m_rsp_v <= 1'b0;
        m_req_rdy <= !fpend;
        if (rst_n && m_req_v && m_req_rdy && !fpend) begin fpend = 1; fa = m_req_addr; fd = FLAT; end
        else if (fpend) begin
            if (fd > 1) fd = fd - 1;
            else begin : frsp
                bit [255:0] rd;
                e2e_hbm_sector({27'd0, fa}, 1'b0, 256'd0, 32'd0, rd);
                m_rsp_v <= 1'b1; m_rsp_data <= rd; fpend = 0;
            end
        end
    end
    // ---------------------------------------------------------------- unit slots
    localparam [15:0] REALM = (REAL_DMA ? 16'h0100 : 16'h0) | (REAL_IDX ? 16'h0200 : 16'h0) |
                              (REAL_SU ? 16'h0004 : 16'h0) | (REAL_SFU ? 16'h0008 : 16'h0);
    localparam [15:0] REAL_UX = REALM & ~16'h0250;            // real units on ux_* ports
    wire [15:0] r_rdy, r_done, r_fault;                       // their handshakes
    assign r_rdy[1:0] = 2'b0; assign r_done[1:0] = 2'b0; assign r_fault[1:0] = 2'b0;
    assign r_rdy[7:4] = 4'b0; assign r_done[7:4] = 4'b0; assign r_fault[7:4] = 4'b0;
    assign r_rdy[15:9] = 7'b0; assign r_done[15:9] = 7'b0; assign r_fault[15:9] = 7'b0;
    // SU (unit 2) / SFU (unit 3): adapter + the reference vec unit on the VM model (hgi_e2e_slots.sv)
    generate if (REAL_SU) begin : g_su
        hgi_e2e_su_slot #(.UNIT(2), .GLU(0), .N(SU_N), .M(SU_M)) u_s (.clk(clk), .rst_n(rst_n), .rec_v(ux_v[2]),
            .rec_rdy(r_rdy[2]), .rec_hdr(d_hdr), .rec_sut(cpd.u_cp.d_sut), .rec_desc(d_desc), .rec_n_a(d_n[0 +: 21]),
            .rec_done(r_done[2]), .rec_fault(r_fault[2]));
    end else begin : g_su_stub
        assign r_rdy[2] = 1'b0; assign r_done[2] = 1'b0; assign r_fault[2] = 1'b0;
    end endgenerate
    generate if (REAL_SFU) begin : g_sfu
        hgi_e2e_su_slot #(.UNIT(3), .GLU(1), .N(SU_N), .M(SU_M)) u_s (.clk(clk), .rst_n(rst_n), .rec_v(ux_v[3]),
            .rec_rdy(r_rdy[3]), .rec_hdr(d_hdr), .rec_sut(cpd.u_cp.d_sut), .rec_desc(d_desc), .rec_n_a(d_n[0 +: 21]),
            .rec_done(r_done[3]), .rec_fault(r_fault[3]));
    end else begin : g_sfu_stub
        assign r_rdy[3] = 1'b0; assign r_done[3] = 1'b0; assign r_fault[3] = 1'b0;
    end endgenerate
    // DMA (unit 8)
    wire dma_rdy, dma_done, dma_fault;
    assign r_rdy[8] = dma_rdy; assign r_done[8] = dma_done; assign r_fault[8] = dma_fault;
    generate if (REAL_DMA) begin : g_dma
        wire mv_v, mv_rdy, mv_done, mv_fault, fence_v, fence_rdy, fence_done; wire [226:0] mv;
        ot_hgi_dma_record #(.LEGACY(0)) u_rec (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(ux_v[8]), .rec_rdy(dma_rdy),
            .rec_hdr(d_hdr), .rec_a(d_desc[0 +: 256]), .rec_o(d_desc[4*256 +: 256]), .rec_n_a(d_n[0 +: 21]),
            .rec_n_o(d_n[4*21 +: 21]), .rec_pos1(d_pos1), .rec_done(dma_done), .rec_fault(dma_fault), .halted(),
            .lg_mv_v(1'b0), .lg_mv_rdy(), .lg_mv(227'd0), .lg_fence_v(1'b0), .lg_fence_rdy(),
            .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done), .mv_fault(mv_fault),
            .fence_v(fence_v), .fence_rdy(fence_rdy), .fence_done(fence_done));
        wire k_req_v, k_req_we, k_rsp_rdy, k_rsp_v, k_rsp_we, k_req_rdy; wire [36:0] k_addr; wire [255:0] k_wd, k_rd;
        wire [31:0] k_ws; wire [15:0] k_tag; wire [337:0] vq; wire [273:0] vr;
        ot_hgi_dma_mover u_mv (.clk(clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done),
            .mv_fault(mv_fault), .fence_v(fence_v), .fence_rdy(fence_rdy), .fence_done(fence_done),
            .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_addr), .k_req_wdata(k_wd),
            .k_req_wstrb(k_ws), .k_req_tag(k_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we),
            .k_rsp_data(k_rd), .k_fault(1'b0), .vmq(vq), .vmr(vr));
        hgi_e2e_kport #(.LAT(KLAT)) u_kp (.clk(clk), .rst_n(rst_n), .req_v(k_req_v), .req_rdy(k_req_rdy), .req_we(k_req_we),
            .req_addr(k_addr), .req_wd(k_wd), .req_ws(k_ws), .rsp_v(k_rsp_v), .rsp_we(k_rsp_we), .rsp_d(k_rd));
        hgi_e2e_vmc #(.UNIT(8), .LAT(VLAT)) u_vm (.clk(clk), .rst_n(rst_n), .q(vq), .r(vr));
    end else begin : g_dma_stub
        assign dma_rdy = 1'b0; assign dma_done = 1'b0; assign dma_fault = 1'b0;
    end endgenerate
    // QUANT (unit 4, QDQ ops) behind the harness's unit-4 split
    reg  [682:0] q_rec;                 // to the real quant unit
    wire [2:0]   q_ret;
    generate if (REAL_QUANT) begin : g_quant
        wire [337:0] vq; wire [273:0] vr;
        ot_hgi_quant_unit u_q (.clk(clk), .rst_n(rst_n), .rec(q_rec), .ret(q_ret), .vmq(vq), .vmr(vr));
        hgi_e2e_vmc #(.UNIT(4), .LAT(VLAT)) u_vm (.clk(clk), .rst_n(rst_n), .q(vq), .r(vr));
    end else begin : g_quant_stub
        assign q_ret = 3'b001;
    end endgenerate
    // IDX (unit 9)
    wire [2:0] i_ret;
    generate if (REAL_IDX) begin : g_idx
        wire [337:0] vq; wire [273:0] vr;
        ot_hgi_idx_unit u_i (.clk(clk), .rst_n(rst_n), .rec(idx_rec), .ret(i_ret), .vmq(vq), .vmr(vr),
            .sel_fs(), .sel_qb(), .sel_qbr(1'b0), .sel_kin(), .sel_to(612'd0), .sel_toc(), .sel_co(72'd0), .sel_coc(),
            .sel_ev(2'd0));
        hgi_e2e_vmc #(.UNIT(9), .LAT(VLAT)) u_vm (.clk(clk), .rst_n(rst_n), .q(vq), .r(vr));
    end else begin : g_idx_stub
        assign i_ret = 3'b001;
    end endgenerate
    // ---------------------------------------------------------------- dispatch monitor + stub engine + retire checks
    integer kq [0:15][0:7]; integer kh [0:15]; integer kt [0:15];
    integer sbusy [0:15]; integer scnt [0:15]; integer sk [0:15];
    reg [15:0] s_done;                  // stub done pulses (ux units)
    reg s4_done, s6_done, s9_done;      // stub done pulses on the record-bus units
    reg q_inflight;                     // unit-4 record went to the real quant unit
    integer errs = 0, real_recs = 0, real_bad = 0, faults = 0;
    function automatic integer is_real(input integer u, input integer quant_now);
        is_real = (u == 8 && REAL_DMA != 0) || (u == 9 && REAL_IDX != 0) || (u == 4 && quant_now != 0);
    endfunction
    task automatic kpush(input integer u, input integer k); begin kq[u][kt[u] % 8] = k; kt[u] = kt[u] + 1; end endtask
    function automatic integer kpop(input integer u);
        begin if (kh[u] == kt[u]) kpop = -1; else begin kpop = kq[u][kh[u] % 8]; kh[u] = kh[u] + 1; end end
    endfunction
    always @* begin
        ux_rdy = 16'd0;
        for (integer u = 1; u < 16; u = u + 1) ux_rdy[u] = REAL_UX[u] ? r_rdy[u] : (sbusy[u] == 0);
        ux_done = (s_done & ~REAL_UX) | (r_done & REAL_UX); ux_fault = r_fault & REAL_UX;
        coll_ret = {1'b0, s6_done, 1'b1};
        quant_ret = {q_ret[2], q_ret[1] | s4_done, 1'b1};
        idx_ret = REAL_IDX ? i_ret : {1'b0, s9_done, 1'b1};
    end
    integer u, k, m;
    always @(posedge clk) begin
        if (!rst_n) begin
            for (u = 0; u < 16; u = u + 1) begin kh[u] = 0; kt[u] = 0; sbusy[u] = 0; scnt[u] = 0; sk[u] = -1; end
            s_done <= 16'd0; s4_done <= 1'b0; s6_done <= 1'b0; s9_done <= 1'b0; q_rec <= 683'd0; q_inflight = 0;
        end else begin
            s_done <= 16'd0; s4_done <= 1'b0; s6_done <= 1'b0; s9_done <= 1'b0; q_rec[0] <= 1'b0;
            // stubs count down and retire (golden writes applied at retire)
            for (u = 1; u < 16; u = u + 1) if (sbusy[u] != 0) begin
                scnt[u] = scnt[u] - 1;
                if (scnt[u] <= 0) begin
                    e2e_stub_retire(sk[u], cyc); sbusy[u] = 0;
                    if (u == 4) s4_done <= 1'b1; else if (u == 6) s6_done <= 1'b1; else if (u == 9) s9_done <= 1'b1;
                    else s_done[u] <= 1'b1;
                end
            end
            // real units retire: check the record's golden writes
            for (u = 1; u < 16; u = u + 1) if (REAL_UX[u] && (r_done[u] || r_fault[u])) begin
                k = kpop(u); m = e2e_real_retire(k, cyc); real_recs = real_recs + 1;
                if (m != 0 || r_fault[u]) begin real_bad = real_bad + 1; $display("E2E REAL unit %0d record %0d: %0d mismatches fault %0d", u, k, m, r_fault[u]); end
            end
            if (REAL_IDX && (i_ret[1] || i_ret[2])) begin
                k = kpop(9); m = e2e_real_retire(k, cyc); real_recs = real_recs + 1;
                if (m != 0 || i_ret[2]) begin real_bad = real_bad + 1; $display("E2E REAL IDX record %0d: %0d mismatches fault %0d", k, m, i_ret[2]); end
            end
            if (REAL_QUANT && (q_ret[1] || q_ret[2])) begin
                k = kpop(4); m = e2e_real_retire(k, cyc); real_recs = real_recs + 1; q_inflight = 0;
                if (m != 0 || q_ret[2]) begin real_bad = real_bad + 1; $display("E2E REAL QUANT record %0d: %0d mismatches fault %0d", k, m, q_ret[2]); end
            end
            // record-bus units (4 coll 6 idx 9): a valid edge starts the slot
            if (coll_rec[0]) begin k = kpop(6); sbusy[6] = 1; sk[6] = k; scnt[6] = e2e_cost(k); end
            if (idx_rec[0] && !REAL_IDX) begin k = kpop(9); sbusy[9] = 1; sk[9] = k; scnt[9] = e2e_cost(k); end
            if (quant_rec[0]) begin
                if (REAL_QUANT && quant_rec[1 + 118 +: 6] >= 6'd4) begin q_rec <= quant_rec; q_inflight = 1; end
                else begin k = kpop(4); sbusy[4] = 1; sk[4] = k; scnt[4] = e2e_cost(k); end
            end
            // the CP's dispatch
            if (|(s_uv & s_ur)) begin
                u = 0; for (integer j = 0; j < 16; j = j + 1) if (s_uv[j] & s_ur[j]) u = j;
                k = e2e_dispatch(u, d_hdr, d_desc, d_n, cyc);
                if (u == 4 || u == 6 || u == 9 || (REALM[u])) kpush(u, k);
                else begin sbusy[u] = 1; sk[u] = k; scnt[u] = e2e_cost(k); end
            end
        end
    end
    // ---------------------------------------------------------------- host
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
    longint t_db, t_cpl;
    always @(posedge clk) if (rst_n && cpd.u_cp.cpl_v && t_cpl == 0) t_cpl = cyc;
    integer w, n_rec, c_tok, c_st, c_cyc, fin, cfgfix;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = "vec";
        if (!$value$plusargs("OUT=%s", outp)) outp = "e2e_records.txt";
        $readmemh({dir, "/host.mem"}, host);
        n_rec = e2e_init(dir, outp);
        if (n_rec <= 0) $fatal(1, "E2E init failed");
        t_cpl = 0;
        repeat (3) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
        axw(12'hC14, host[67]);
        for (w = 0; w < 31; w = w + 1) begin axw(12'hD00 + 8 * w, host[2 * w]); axw(12'hD04 + 8 * w, host[2 * w + 1]); end
        // DIE FINDING (hgi-e2e F1): the CFG window cannot stage MD words 62-63: pair 31 IS the CFG_COMMIT address
        // (ot_hgi_cp: c_wr excludes the commit), so the CRC word 63 is never written and every real descriptor fails
        // E_CRC (the CP then keeps the reset image_base 0 and fetches 4,096 CTL.NOP sectors of empty HBM before reaching
        // the image).  +CFGFIX=1 (default) deposits words 62-63 into the staging buffer as the commit's data would if
        // c_wr included the commit (the proposed one-line fix); +CFGFIX=0 measures the RTL as is.
        if (!$value$plusargs("CFGFIX=%d", cfgfix)) cfgfix = 1;
        if (cfgfix != 0) begin cpd.u_cp.u_cfg.buf_[62] = host[62]; cpd.u_cp.u_cfg.buf_[63] = host[63]; end
        axw(12'hD00 + 8 * 31, host[62]); axw(12'hD04 + 8 * 31, host[63]);
        repeat (4) @(negedge clk);
        w = 0; while ((cpd.u_cp.u_cfg.st_hold || !cpd.u_cp.cfg_loaded) && w < 4000) begin @(negedge clk); w = w + 1; end
        repeat (3) @(negedge clk);
        axr(12'hC24);
        $display("E2E CFG status err %0d loaded %0d", rd[3:1], rd[0]);
        if (rd[3:1] != 0 || !rd[0]) begin errs = errs + 1; end
        axw(12'hC00, host[64]); axw(12'hC04, host[65]); axw(12'hC08, 32'h0E2E); axw(12'hC0C, {20'd0, host[68][3:0], 8'h01});
        t_db = cyc;
        axw(12'hC10, 1);
        w = 0; rd = 0;
        while (rd[10:8] == 0 && w < 2000000) begin axr(12'hC20); w = w + 1; end
        if (rd[10:8] == 0) begin
            $display("E2E FAIL: no completion (timeout)"); errs = errs + 1; c_tok = -1; c_st = 15; c_cyc = 0;
        end else begin
            axr(12'hC40); c_tok = rd[17:0]; axr(12'hC4C); c_st = rd[7:4]; axr(12'hC50); c_cyc = rd;
        end
        repeat (20) @(negedge clk);
        fin = e2e_finish(t_cpl - t_db, c_tok, c_st);
        $display("E2E completion token %0d (golden %0d) status %0d cp_cycles %0d doorbell->completion %0d", c_tok, host[66], c_st, c_cyc, t_cpl - t_db);
        $display("E2E real-unit records %0d, mismatching %0d", real_recs, real_bad);
        if (c_tok != host[66] || c_st != 0) errs = errs + 1;
        if (fin == 0 && errs == 0 && real_bad == 0) $display("HGI_E2E PASS");
        else $display("HGI_E2E FAIL (finish %0d, errors %0d, real mismatching %0d)", fin, errs, real_bad);
        $finish;
    end
endmodule

// VM packet client on the VM model: request {v, we, byte addr 32, wdata 256, byte mask 32, tag 16}; the access lands at
// acceptance; the response {v, tag, we echo, rdata} after LAT cycles, in request order (HGI VM fast path).
module hgi_e2e_vmc #(parameter integer UNIT = 0, parameter integer LAT = 6) (
    input wire clk, input wire rst_n, input wire [337:0] q, output reg [273:0] r);
    import "DPI-C" function void e2e_vm_sector(input int unit, input int sec, input bit we, input bit [255:0] wd,
                                               input bit [31:0] mask, output bit [255:0] rd);
    reg [272:0] rq [0:15]; longint due [0:15]; integer h = 0, t = 0; longint c = 0;
    always @(posedge clk) begin
        c <= c + 1;
        r[273] <= 1'b0;
        if (rst_n && q[337]) begin : acc
            bit [255:0] rd;
            e2e_vm_sector(UNIT, int'(q[335:304] >> 5), q[336], q[303:48], q[47:16], rd);
            rq[t % 16] = {q[15:0], q[336], rd}; due[t % 16] = c + LAT; t = t + 1;
        end
        if (h < t && due[h % 16] <= c) begin r <= {1'b1, rq[h % 16]}; h = h + 1; end
    end
endmodule

// kport lane on the HBM model: one transaction outstanding, the response LAT cycles after acceptance.
module hgi_e2e_kport #(parameter integer LAT = 40) (
    input wire clk, input wire rst_n, input wire req_v, output reg req_rdy, input wire req_we, input wire [36:0] req_addr,
    input wire [255:0] req_wd, input wire [31:0] req_ws, output reg rsp_v, output reg rsp_we, output reg [255:0] rsp_d);
    import "DPI-C" function void e2e_hbm_sector(input longint addr, input bit we, input bit [255:0] wd,
                                                input bit [31:0] strb, output bit [255:0] rd);
    reg pend = 0; integer cnt = 0; reg we_q; reg [255:0] d_q;
    always @(posedge clk) begin
        rsp_v <= 1'b0;
        req_rdy <= rst_n && !pend;
        if (rst_n && req_v && req_rdy && !pend) begin : acc
            bit [255:0] rd;
            e2e_hbm_sector({27'd0, req_addr}, req_we, req_wd, req_ws, rd);
            pend = 1; cnt = LAT; we_q = req_we; d_q = rd; req_rdy <= 1'b0;
        end else if (pend) begin
            if (cnt > 1) cnt = cnt - 1;
            else begin rsp_v <= 1'b1; rsp_we <= we_q; rsp_d <= d_q; pend = 0; end
        end
    end
endmodule
