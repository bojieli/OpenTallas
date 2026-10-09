`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Control-sequencing bench of the full-shape Qwen3-8B ROM package control plane (stream qwen-system 2026-10-08).
// DUT: ot_qfd_sysctl (die 0: host_if FMT 1, csr, rst_seq, pkgctl, prompt buffer) + ot_qfd_dctl on each of the 4 dies,
// joined by the package control channel (die 0 through a 1-edge local relay, dies 1..3 through CL-edge pipes each way,
// `CL).  Outside the DUT: the host (register driver + host memory / DMA slave, FMT 1 rings), link training / HBM boot
// responders, and per die a SEQUENCER MODEL that answers each stage's h_start with s_done after a stage time and, at the
// head stage, the scenario's argmax.
// Checks against tools/qwen_system/ctl_golden.py (+SCEN=<scen_*.hex>):
//   every h_start of every die == the golden stage trace (stage order E, L0..L35, H; program, KV layer, next-layer
//   notice, constant-ROM stage, code / scale bases; the step's token and position), every completion the host reads ==
//   the golden completion stream (kind, status, position, 18-bit token, tokens generated), no fault (or, with +FAULT_*,
//   the fail-closed completion and the named FAULT_STATUS source).
// Measures the argmax -> next-token turnaround: from the last die's head-stage done to each die's next E h_start.
// +MEAS: stage times of the P8191 full token (L0 6,044, L1..35 5,282, H 2,998; E 7) instead of short random ones.
// Prints "CTL_RESULT pass=.. steps=.. trace_events=.. trace_bad=.. cq=.. cq_bad=.. turn_min/max=.. ..".
// ---------------------------------------------------------------------------------------------------------------------
`include "stab.svh"
`ifndef PROMPT_SRAM
`define PROMPT_SRAM 0
`endif
`ifndef PB_VALID_ONLY
`define PB_VALID_ONLY 1
`endif
`ifndef PROMPT_POISON
`define PROMPT_POISON 0
`endif
module tb_qfd_ctl_stn_pb2;
    localparam integer D = 4, NW = 18, AW = 24, NS = 38, EW = 2 + 6 + 2*24, NL = 6;
    localparam integer CLAT = `CL;
    reg clk = 0;
    always #0.4166 clk = ~clk;
    reg por_n = 0;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    localparam [NS*EW-1:0] STAB = `QFD_STAB;

    // ------------------------------------------------------------------ DUT: die 0 control master
    reg  s_awvalid = 0, s_wvalid = 0, s_bready = 1, s_arvalid = 0, s_rready = 1;
    reg  [12:0] s_awaddr = 0, s_araddr = 0;
    reg  [31:0] s_wdata = 0;
    wire s_awready, s_wready, s_bvalid, s_arready, s_rvalid;
    wire [31:0] s_rdata;
    wire m_arvalid, m_rready, m_awvalid, m_wvalid, m_wlast, m_bready, irq;
    reg  m_arready = 0, m_rvalid = 0, m_awready = 0, m_wready = 0, m_bvalid = 0;
    wire [63:0] m_araddr, m_awaddr, m_wdata;
    reg  [63:0] m_rdata = 0;
    wire [7:0] m_wstrb, m_arlen, m_awlen;
    wire [2:0] m_arsize, m_awsize;
    reg  [NL-1:0] link_up = 0;
    reg  [D-1:0] boot_done = 0, boot_ok = 0;
    wire host_rst_n, link_rst_n, hbm_rst_n, boot_go, die_rst_n, sys_ready;
    wire c_start; wire [NW-1:0] c_token, c_pos; wire [AW-1:0] c_kv_base; wire [1:0] c_gen;
    wire [D-1:0] c_done, c_drained, c_fault; wire [D*2-1:0] c_done_gen; wire [D*NW-1:0] c_ntok;
    wire [D*32-1:0] c_nval; wire [D*4-1:0] c_fvec;
    wire [31:0] fault_src;
    // Model arbitrary unwritten silicon cells with a deterministic UE in every token slot.
    // Physical mapping: column=data_bit*2+column_select, row=logical_address>>1.
    generate if (`PROMPT_SRAM != 0 && `PROMPT_POISON != 0) begin:g_poison_prompt
        integer rr, ll, cc;
        initial begin
            #0.001;
            for(rr=0;rr<514;rr=rr+1) begin
                dut.u_core.g_pb_sram.u_pb.u_sram.arr[rr]=0;
                for(ll=0;ll<8;ll=ll+1) for(cc=0;cc<4;cc=cc+1)
                    dut.u_core.g_pb_sram.u_pb.u_sram.arr[rr][ll*64+cc]=1'b1;
            end
        end
    end endgenerate
    ot_qfd_sysctl_stn_pb2 #(.PROMPT_READ_STATION(1), .BOUNDARY_STATIONS(1),.PROMPT_VALID_ONLY(`PB_VALID_ONLY), .PROMPT_SRAM(`PROMPT_SRAM), .D(D), .NW(NW), .AW(AW), .NL(NL), .T_LINK(5000), .T_HBM(5000)) dut (
        .clk(clk), .por_n(por_n),
        .s_awvalid(s_awvalid), .s_awready(s_awready), .s_awaddr(s_awaddr),
        .s_wvalid(s_wvalid), .s_wready(s_wready), .s_wdata(s_wdata), .s_wstrb(4'hF),
        .s_bvalid(s_bvalid), .s_bready(s_bready), .s_bresp(),
        .s_arvalid(s_arvalid), .s_arready(s_arready), .s_araddr(s_araddr),
        .s_rvalid(s_rvalid), .s_rready(s_rready), .s_rdata(s_rdata), .s_rresp(),
        .m_arvalid(m_arvalid), .m_arready(m_arready), .m_araddr(m_araddr), .m_arlen(m_arlen), .m_arsize(m_arsize),
        .m_rvalid(m_rvalid), .m_rready(m_rready), .m_rdata(m_rdata), .m_rresp(2'b00), .m_rlast(1'b1),
        .m_awvalid(m_awvalid), .m_awready(m_awready), .m_awaddr(m_awaddr), .m_awlen(m_awlen), .m_awsize(m_awsize),
        .m_wvalid(m_wvalid), .m_wready(m_wready), .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_wlast(m_wlast),
        .m_bvalid(m_bvalid), .m_bready(m_bready), .m_bresp(2'b00), .irq(irq),
        .link_up(link_up), .boot_done(boot_done), .boot_ok(boot_ok),
        .host_rst_n(host_rst_n), .link_rst_n(link_rst_n), .hbm_rst_n(hbm_rst_n), .boot_go(boot_go),
        .die_rst_n(die_rst_n), .sys_ready(sys_ready),
        .c_start(c_start), .c_token(c_token), .c_pos(c_pos), .c_kv_base(c_kv_base), .c_gen(c_gen),
        .c_done(c_done), .c_done_gen(c_done_gen), .c_next_token(c_ntok), .c_next_val(c_nval),
        .c_drained(c_drained), .c_fault(c_fault), .c_fault_vec(c_fvec), .crom_fault(1'b0), .fault_src(fault_src));

    // link training / HBM boot responders (the real blocks' handshakes)
    always @(posedge clk) begin
        if (!link_rst_n) link_up <= 0; else if (cyc % 37 == 0) link_up <= {link_up[NL-2:0], 1'b1};
        if (!hbm_rst_n) begin boot_done <= 0; boot_ok <= 0; end
        else if (boot_go) begin boot_done <= {D{1'b1}}; boot_ok <= {D{1'b1}}; end
    end

    // ------------------------------------------------------------------ scenario
    integer sc_plen, sc_max, sc_eos, sc_eos0, sc_eos1, sc_tag, sc_salt;
    reg [NW-1:0] prompt [0:8191];
    integer st_pos [0:8191], st_tok [0:8191], st_out [0:8191];
    integer cq_kind [0:8191], cq_st [0:8191], cq_pos [0:8191], cq_tok [0:8191], cq_ng [0:8191];
    integer n_p = 0, n_s = 0, n_c = 0;
    integer fault_die = -1, fault_step = -1, fault_stage = -1, fault_kind = 0, dis_step = -1, meas = 0;
    reg [8*512-1:0] scen;
    initial begin : load
        integer fd, rc, a0, a1, a2, a3, a4, a5, a6;
        reg [7:0] c;
        if (!$value$plusargs("SCEN=%s", scen)) begin $display("need +SCEN"); $finish; end
        if ($value$plusargs("FAULT_DIE=%d", fault_die)) ;
        if ($value$plusargs("FAULT_STEP=%d", fault_step)) ;
        if ($value$plusargs("FAULT_STAGE=%d", fault_stage)) ;
        if ($value$plusargs("FAULT_KIND=%d", fault_kind)) ;   // 1 sequencer 2 core 3 collective 4 hang (watchdog)
        if ($value$plusargs("DISAGREE_STEP=%d", dis_step)) ;
        if ($test$plusargs("MEAS")) meas = 1;
        fd = $fopen(scen, "r");
        if (fd == 0) begin $display("cannot open scenario"); $finish; end
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%c", c);
            case (c)
                "R": rc = $fscanf(fd, " %h %h %h %h %h %h %h\n", sc_plen, sc_max, sc_eos, sc_eos0, sc_eos1, sc_tag, sc_salt);
                "P": begin rc = $fscanf(fd, " %h\n", a0); prompt[n_p] = a0; n_p = n_p + 1; end
                "S": begin rc = $fscanf(fd, " %h %h %h\n", a0, a1, a2); st_pos[n_s] = a0; st_tok[n_s] = a1;
                           st_out[n_s] = a2; n_s = n_s + 1; end
                "C": begin rc = $fscanf(fd, " %h %h %h %h %h\n", a0, a1, a2, a3, a4); cq_kind[n_c] = a0; cq_st[n_c] = a1;
                           cq_pos[n_c] = a2; cq_tok[n_c] = a3; cq_ng[n_c] = a4; n_c = n_c + 1; end
                default: ;
            endcase
        end
        $display("SCEN %0s plen=%0d max=%0d steps=%0d completions=%0d", scen, sc_plen, sc_max, n_s, n_c);
    end

    // ------------------------------------------------------------------ dies: control channel + stepper + sequencer model
    localparam integer DNW = 1 + NW + NW + AW + 2;                   // start, token, pos, kv_base, gen
    localparam integer UPW = 1 + 2 + NW + 32 + 1 + 1 + 4;             // done, gen, token, logit, drained, fault, fvec
    integer trace_ev = 0, trace_bad = 0;
    integer h_done_t [0:D-1];
    integer last_h_done = 0, turn_min = 1 << 30, turn_max = 0, turn_sum = 0, turn_n = 0;
    integer step_t0 = 0, step_cycles_last = 0;
    genvar d;
    generate for (d = 0; d < D; d = d + 1) begin : g_die
        localparam integer LAT = (d == 0) ? 1 : CLAT;
        // control channel, both ways (CTRL class of the die-to-die link; die 0: a local relay)
        reg [DNW-1:0] dn_p [0:LAT-1];
        reg [UPW-1:0] up_p [0:LAT-1];
        wire [UPW-1:0] up_in;
        integer k;
        always @(posedge clk) begin
            dn_p[0] <= {c_start, c_token, c_pos, c_kv_base, c_gen};
            up_p[0] <= up_in;
            for (k = 1; k < LAT; k = k + 1) begin dn_p[k] <= dn_p[k-1]; up_p[k] <= up_p[k-1]; end
        end
        wire           r_start; wire [NW-1:0] r_tok, r_pos; wire [AW-1:0] r_kvb; wire [1:0] r_gen;
        assign {r_start, r_tok, r_pos, r_kvb, r_gen} = die_rst_n ? dn_p[LAT-1] : {DNW{1'b0}};
        assign {c_done[d], c_done_gen[d*2 +: 2], c_ntok[d*NW +: NW], c_nval[d*32 +: 32], c_drained[d], c_fault[d],
                c_fvec[d*4 +: 4]} = up_p[LAT-1];
        // stage stepper
        wire h_start; wire [NW-1:0] tp_token, tp_pos; wire [5:0] stage, st_layer, st_next, st_crom; wire [1:0] st_prog;
        wire [AW-1:0] st_code, st_scale;
        wire dd, ddr, dfl; wire [1:0] dgen; wire [NW-1:0] dtok; wire [31:0] dval, dcyc; wire [3:0] dfc;
        reg  s_done = 1'b1, s_fault = 0, core_fault = 0, coll_fault = 0, kv_drained = 1'b1;
        reg  [NW-1:0] seq_ntok = 0; reg [31:0] seq_nval = 0;
        ot_qfd_dctl #(.NW(NW), .AW(AW), .NS(NS), .WDOG(`WDOG), .STAB(STAB)) u_dctl (
            .clk(clk), .rst_n(die_rst_n),
            .d_start(r_start), .d_token(r_tok), .d_pos(r_pos), .d_gen(r_gen),
            .d_done(dd), .d_done_gen(dgen), .d_next_token(dtok), .d_next_val(dval), .d_drained(ddr), .d_fault(dfl),
            .d_fault_code(dfc), .d_cycles(dcyc),
            .h_start(h_start), .tp_token(tp_token), .tp_pos(tp_pos), .stage(stage), .st_prog(st_prog),
            .st_layer(st_layer), .st_next_layer(st_next), .st_crom(st_crom), .st_code(st_code), .st_scale(st_scale),
            .s_done(s_done), .seq_ntok(seq_ntok), .seq_nval(seq_nval), .s_fault(s_fault), .core_fault(core_fault),
            .coll_fault(coll_fault), .kv_write_drained(kv_drained));
        assign up_in = {dd, dgen, dtok, dval, ddr, dfl, 1'b0, 1'b0, 1'b0, dfl};
        // sequencer model + trace check
        integer step = -1, k_st = 0, left = 0, cur_stage = 0, drain_left = -1, hang = 0;
        reg [EW-1:0] e, en;
        always @(posedge clk) begin
            if (h_start) begin
                if (stage == 0) step = step + 1;
                cur_stage = stage;
                e = STAB[stage * EW +: EW];
                en = (stage + 1 < NS) ? STAB[(stage + 1) * EW +: EW] : {2'd0, 6'd63, 48'd0};
                trace_ev = trace_ev + 1;
                if (stage != k_st || st_prog != e[EW-1 -: 2] || st_layer != e[48 +: 6] || st_next != en[48 +: 6] ||
                    st_crom != ((e[EW-1 -: 2] == 2) ? 6'd36 : e[48 +: 6]) || st_code != e[24 +: 24] ||
                    st_scale != e[0 +: 24] || step >= n_s || tp_pos != st_pos[step] || tp_token != st_tok[step]) begin
                    trace_bad = trace_bad + 1;
                    if (trace_bad < 6) $display("TRACE_BAD die%0d step%0d stage %0d (exp %0d) prog %0d layer %0d next %0d crom %0d code %0d scale %0d token %0d pos %0d (exp token %0d pos %0d)",
                        d, step, stage, k_st, st_prog, st_layer, st_next, st_crom, st_code, st_scale, tp_token, tp_pos,
                        st_tok[step], st_pos[step]);
                end
                k_st = (k_st + 1) % NS;
                if (stage == 0) begin
                    kv_drained <= 1'b0;
                    if (d == 0) begin
                        if (step > 0) step_cycles_last = cyc - step_t0;
                        step_t0 = cyc;
                    end
                    if (step > 0) begin : turn
                        integer tt;
                        tt = cyc - last_h_done;
                        if (tt < turn_min) turn_min = tt;
                        if (tt > turn_max) turn_max = tt;
                        turn_sum = turn_sum + tt; turn_n = turn_n + 1;
                    end
                end
                s_done <= 1'b0;
                left = meas ? ((stage == 0) ? 7 : (stage == 1) ? 6044 : (stage == NS - 1) ? 2998 : 5282)
                            : 2 + ($urandom % 24);
                hang = (fault_kind == 4 && d == fault_die && step == fault_step && stage == fault_stage);
            end else if (!s_done && !hang && !s_fault && !core_fault && !coll_fault) begin
                if (d == fault_die && step == fault_step && cur_stage == fault_stage && fault_kind >= 1 && fault_kind <= 3
                    && left == 1) begin
                    if (fault_kind == 1) s_fault <= 1'b1; else if (fault_kind == 2) core_fault <= 1'b1; else coll_fault <= 1'b1;
                end else if (left <= 1) begin
                    s_done <= 1'b1;
                    if (cur_stage == NS - 1) begin
                        seq_ntok <= NW'(st_out[step] + ((d == 3 && step == dis_step) ? 1 : 0));
                        seq_nval <= 32'h4228_0000 + st_pos[step];
                        h_done_t[d] = cyc;
                        if (d == D - 1 || 1) begin : lh
                            integer j, mx;
                            mx = 0;
                            for (j = 0; j < D; j = j + 1) if (h_done_t[j] > mx) mx = h_done_t[j];
                            last_h_done = mx;
                        end
                        drain_left = 3;
                    end
                end else left = left - 1;
            end
            if (drain_left == 0) kv_drained <= 1'b1;
            if (drain_left >= 0) drain_left = drain_left - 1;
        end
    end endgenerate

    // ------------------------------------------------------------------ host memory and DMA slave
    reg [63:0] hmem [0:16383];
    reg [63:0] rd_addr;
    always @(posedge clk) begin
        m_arready <= 1'b0; m_rvalid <= 1'b0; m_awready <= 1'b0; m_wready <= 1'b0; m_bvalid <= 1'b0;
        if (m_arvalid && !m_arready && !m_rvalid) begin m_arready <= 1'b1; rd_addr <= m_araddr; end
        if (m_arready) begin m_rvalid <= 1'b1; m_rdata <= hmem[rd_addr[16:3]]; end
        if (m_awvalid && m_wvalid && !m_awready && !m_bvalid) begin
            m_awready <= 1'b1; m_wready <= 1'b1;
            for (integer b = 0; b < 8; b = b + 1) if (m_wstrb[b]) hmem[m_awaddr[16:3]][8*b +: 8] <= m_wdata[8*b +: 8];
        end
        if (m_awready) m_bvalid <= 1'b1;
    end

    // ------------------------------------------------------------------ host driver (FMT 1)
    localparam integer SQ = 32'h1000, CQ = 32'h2000, MSI = 32'h4000, PR = 32'h8000;
    localparam integer CQ_LOG = 4;
    integer h_st = 0, h_pc = 0;
    reg [31:0] rd_val, fault_status_rd = 0;
    reg op_busy = 0, op_wr = 0;
    integer cq_i = 0, cq_seen = 0, cq_ok = 0, cq_bad = 0, done_run = 0, f_entries = 0, f_ok = 0, f_step;
    reg cq_ph = 1'b1;
    reg [44:0] cfg [0:12];
    initial begin
        cfg[0]  = {13'h1014, 32'hFFFF_FFFF}; cfg[1] = {13'h0010, SQ}; cfg[2] = {13'h0014, 32'd0};
        cfg[3]  = {13'h0018, 32'd3}; cfg[4] = {13'h0024, CQ}; cfg[5] = {13'h0028, 32'd0}; cfg[6] = {13'h002C, CQ_LOG};
        cfg[7]  = {13'h003C, 32'd3}; cfg[8] = {13'h0040, MSI}; cfg[9] = {13'h0044, 32'd0}; cfg[10] = {13'h0048, 32'hC0DE};
        cfg[11] = {13'h004C, 32'd1}; cfg[12] = {13'h0008, 32'd1};
    end
    task automatic axil_write(input [12:0] a, input [31:0] dd);
        begin s_awaddr <= a; s_wdata <= dd; s_awvalid <= 1'b1; s_wvalid <= 1'b1; op_busy <= 1'b1; op_wr <= 1'b1; end
    endtask
    task automatic axil_read(input [12:0] a);
        begin s_araddr <= a; s_arvalid <= 1'b1; op_busy <= 1'b1; op_wr <= 1'b0; end
    endtask
    reg [63:0] w0, w1;
    integer tok_got, i;
    always @(posedge clk) begin
        if (cyc == 10) por_n <= 1'b1;
        if (s_awvalid && s_awready) begin s_awvalid <= 1'b0; s_wvalid <= 1'b0; end
        if (op_busy && op_wr && s_bvalid) op_busy <= 1'b0;
        if (s_arvalid && s_arready) s_arvalid <= 1'b0;
        if (op_busy && !op_wr && s_rvalid) begin op_busy <= 1'b0; rd_val <= s_rdata; end
        if (!op_busy && !(s_awvalid || s_arvalid) && por_n) case (h_st)
            0: begin axil_read(13'h1004); h_st <= 1; end
            1: if (rd_val[0]) begin h_pc <= 0; h_st <= 2; $display("BOOT sys_ready cycle %0d", cyc); end
               else if (rd_val[1]) begin $display("BOOT_FAULT %08x", rd_val); h_st <= 30; end
               else h_st <= 0;
            2: begin axil_write(cfg[h_pc][44:32], cfg[h_pc][31:0]); if (h_pc == 12) h_st <= 3; else h_pc <= h_pc + 1; end
            3: begin
                for (i = 0; i < (sc_plen + 1) / 2; i = i + 1)
                    hmem[(PR >> 3) + i] = {32'(prompt[2*i + 1]), 32'(prompt[2*i])};
                hmem[(SQ >> 3) + 0] = {sc_max[15:0], sc_plen[15:0], sc_tag[15:0], 8'(sc_eos ? 3 : 1), 8'h01};
                hmem[(SQ >> 3) + 1] = PR;
                hmem[(SQ >> 3) + 2] = 64'd0;
                hmem[(SQ >> 3) + 3] = {sc_eos1[31:0], sc_eos0[31:0]};
                axil_write(13'h001C, 32'd1);
                h_st <= 4;
            end
            4: if (irq) h_st <= 5;
            5: begin
                w0 = hmem[(CQ >> 3) + 2*cq_i]; w1 = hmem[(CQ >> 3) + 2*cq_i + 1];
                if (w0[0] == cq_ph) begin
                    tok_got = {w1[63:48], w0[63:48]};
                    f_step = (dis_step >= 0) ? dis_step : fault_step;
                    if (w0[7:4] == 4'd7) begin
                        // a fail-closed completion: must be the injected step's
                        f_entries = f_entries + 1;
                        if ((fault_die >= 0 || dis_step >= 0) && w0[47:32] == st_pos[f_step][15:0]) f_ok = 1;
                        $display("CQ fault completion pos %0d status %0d", w0[47:32], w0[7:4]);
                    end else if (cq_ok >= n_c || w0[2:1] != cq_kind[cq_ok][1:0] || w0[7:4] != cq_st[cq_ok][3:0] ||
                        (w0[2:1] != 3 && (w0[47:32] != cq_pos[cq_ok][15:0] || tok_got != cq_tok[cq_ok] ||
                                          w1[47:32] != cq_ng[cq_ok][15:0])) || w0[31:16] != sc_tag[15:0]) begin
                        cq_bad = cq_bad + 1;
                        if (cq_bad < 6) $display("CQ_BAD #%0d kind %0d st %0d pos %0d tok %0d ngen %0d | exp kind %0d st %0d pos %0d tok %0d ngen %0d",
                            cq_ok, w0[2:1], w0[7:4], w0[47:32], tok_got, w1[47:32], cq_kind[cq_ok], cq_st[cq_ok],
                            cq_pos[cq_ok], cq_tok[cq_ok], cq_ng[cq_ok]);
                    end else cq_ok = cq_ok + 1;
                    if (w0[2:1] == 2 || w0[2:1] == 3) done_run = 1;
                    cq_seen = cq_seen + 1;
                    if (cq_i == (1 << CQ_LOG) - 1) cq_ph <= ~cq_ph;
                    cq_i <= (cq_i + 1) % (1 << CQ_LOG);
                end else h_st <= 6;
            end
            6: begin axil_write(13'h0030, cq_i); h_st <= 7; end
            7: begin axil_write(13'h0038, 32'd3); h_st <= 8; end
            8: h_st <= done_run ? 10 : 9;
            9: h_st <= irq ? 5 : 9;
            10: begin axil_read(13'h1010); h_st <= 11; end
            11: begin fault_status_rd <= rd_val; h_st <= 20; end
            20: begin : fin
                reg pass;
                reg [31:0] want;
                if (fault_die >= 0 || dis_step >= 0) begin
                    // fail closed: the completions before the injected step exact, one fault completion at that step,
                    // the named FAULT_STATUS sources latched
                    want = (dis_step >= 0) ? 32'h0001_0000 : (32'h0010_0000 | (32'h1 << (4 * fault_die)));
                    pass = cq_bad == 0 && f_entries == 1 && f_ok && ((fault_status_rd & want) == want);
                end else
                    pass = cq_bad == 0 && cq_ok == n_c && f_entries == 0 && trace_bad == 0 && fault_status_rd == 0;
                $display("CTL_RESULT pass=%0d steps=%0d trace_events=%0d trace_bad=%0d cq=%0d/%0d cq_bad=%0d fault_cq=%0d fault_status=%08x turn_min=%0d turn_max=%0d turn_avg=%0d step_cycles=%0d CL=%0d cycles=%0d",
                    pass, g_die[0].step + 1, trace_ev, trace_bad, cq_ok, n_c, cq_bad, f_entries, fault_status_rd, turn_min,
                    turn_max, turn_n ? turn_sum / turn_n : 0, step_cycles_last, CLAT, cyc);
                $finish;
            end
            30: begin $display("CTL_RESULT pass=0 boot fault"); $finish; end
            default: ;
        endcase
        if (cyc > 400000000) begin $display("CTL_RESULT pass=0 timeout h_st=%0d cq=%0d", h_st, cq_seen); $finish; end
    end
endmodule
