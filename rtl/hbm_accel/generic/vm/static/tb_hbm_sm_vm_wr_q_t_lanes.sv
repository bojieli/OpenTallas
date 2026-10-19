`timescale 1ns/1ps
`default_nettype none
// Bench (H-NETLIST/smvm 2026-10-16): ot_hbm_sm_vm_wr_q + 8 real ot_vms_bank_static (NW shape RG/WG: wq0 = LG, wq1 = SM
// writer, wq2 idle) with the bench acting as the compiler: it derives every writer emission cycle from the fixed timing
// contract (wq slot 0 at rv+3, serial P-cycle server per SM, DEPTH rows) and programmes the VM calendar wslot from it;
// an LG competitor writes the SAME banks on every cycle the calendar leaves free.  SM result streams follow the SM's
// retire pattern (SUB=4 rows back to back, then a K-dependent gap; SM k staggered by its hop).  After the run every
// touched bank row is read back through rq group 0 and compared bit-exact to an independent address/value model.
// PASS needs: 0 mismatches, no bank schedule/decode fault, no writer fault.  -DMUT=1 (wrong row) / -DMUT=2 (late
// phase) must FAIL.
// H-SM 2026-10-16 (_t): the HARDENED wrapper ot_hbm_sm_vm_wr_q_t_faces4 (folded MODE 1 command calendar, TGT_PIN strap 160).
// The writer descriptors are NOT driven by the bench: the bench installs them as command-calendar entries {cmd, at}
// through the real host ingress (AXI-lite F20..F30), launches, and aligns its SM-result frame to cycle 0 = the collar
// cycle C_launch + 2 + LEAD.  -DMUT=3 (quad strap ignored) and -DMUT=4 (calendar fires one edge late) must FAIL too.
// H-WRQ 2026-10-17 (_t_lanes): the lane-root master ot_hbm_sm_vm_wr_q_t_lanes (one clock root per SM lane, per-SM ports).
// -DLANE_CLOCK_MUT=k+1 stops lane k's clock (clk_l<k>): that SM's results must be lost -> FAIL, so every lane root is real.
`ifndef LANE_CLOCK_MUT
`define LANE_CLOCK_MUT 0
`endif
module tb_hbm_sm_vm_wr_q_t_lanes;
`ifndef MUT
`define MUT 0
`endif
`ifndef VM_LAT
`define VM_LAT 0
`endif
`ifndef NAT2_MUT
`define NAT2_MUT 0
`endif
    localparam integer Q = 2, NCYC = 6000, G_SM = 1, G_LG = 0;
    reg clk = 0, rst_n = 0;
    wire [7:0] clk_l;
    genvar lc;
    generate for (lc = 0; lc < 8; lc = lc + 1) begin : g_lc
        assign clk_l[lc] = (`LANE_CLOCK_MUT == lc + 1) ? 1'b0 : clk;
    end endgenerate
    always #1 clk = ~clk;
    localparam integer LEAD = 8;
    reg [7:0] rv, smf; reg [95:0] rrow; reg [2047:0] rdata;
    wire [2247:0] wq_sm; wire wfault, w_active, w_cfgd;
    // ---- host ingress (as tb_static_cmd_target)
    reg awv = 0, wv = 0, arv = 0, rr = 1, br = 1; reg [11:0] awa = 0, ara = 0; reg [31:0] wd = 0;
    wire awr, wr, bv, arr, rvl; wire [1:0] bresp; wire [31:0] rdat;
    wire cfg_v, desc_v, launch_v, ing_fault; wire [7:0] cfg_target; wire [11:0] cfg_addr, desc_base; wire [255:0] cfg_data;
    wire [12:0] desc_limit; wire [15:0] desc_loops;
    ot_hbm_host_static_ingress #(.TARGET_MASK(256'd1<<160)) ing(
        .clk(clk), .rst_n(rst_n), .s_awvalid(awv), .s_awready(awr), .s_awaddr(awa), .s_wvalid(wv), .s_wready(wr),
        .s_wdata(wd), .s_wstrb(4'hf), .s_bvalid(bv), .s_bready(br), .s_bresp(bresp), .s_arvalid(arv), .s_arready(arr),
        .s_araddr(ara), .s_rvalid(rvl), .s_rready(rr), .s_rdata(rdat), .block_ready(1'b1), .program_active(w_active),
        .program_fault(1'b0), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .fault(ing_fault));
    ot_hbm_sm_vm_wr_q_t_lanes #(.DEPTH(4), .MUT(`MUT)) dut(.clk(clk), .clk_cal(clk), .rst_n(rst_n), .tgt(8'd160), .quad(2'(Q)),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v),
        .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .clk_l0(clk_l[0]), .rv_s0(rv[0]), .smf_s0(smf[0]), .sms_s0(1'b0), .rrow_s0(rrow[0+:12]), .rdata_s0(rdata[0+:256]), .wq_s0(wq_sm[0+:281]),
        .clk_l1(clk_l[1]), .rv_s1(rv[1]), .smf_s1(smf[1]), .sms_s1(1'b0), .rrow_s1(rrow[12+:12]), .rdata_s1(rdata[256+:256]), .wq_s1(wq_sm[281+:281]),
        .clk_l2(clk_l[2]), .rv_s2(rv[2]), .smf_s2(smf[2]), .sms_s2(1'b0), .rrow_s2(rrow[24+:12]), .rdata_s2(rdata[512+:256]), .wq_s2(wq_sm[562+:281]),
        .clk_l3(clk_l[3]), .rv_s3(rv[3]), .smf_s3(smf[3]), .sms_s3(1'b0), .rrow_s3(rrow[36+:12]), .rdata_s3(rdata[768+:256]), .wq_s3(wq_sm[843+:281]),
        .clk_l4(clk_l[4]), .rv_s4(rv[4]), .smf_s4(smf[4]), .sms_s4(1'b0), .rrow_s4(rrow[48+:12]), .rdata_s4(rdata[1024+:256]), .wq_s4(wq_sm[1124+:281]),
        .clk_l5(clk_l[5]), .rv_s5(rv[5]), .smf_s5(smf[5]), .sms_s5(1'b0), .rrow_s5(rrow[60+:12]), .rdata_s5(rdata[1280+:256]), .wq_s5(wq_sm[1405+:281]),
        .clk_l6(clk_l[6]), .rv_s6(rv[6]), .smf_s6(smf[6]), .sms_s6(1'b0), .rrow_s6(rrow[72+:12]), .rdata_s6(rdata[1536+:256]), .wq_s6(wq_sm[1686+:281]),
        .clk_l7(clk_l[7]), .rv_s7(rv[7]), .smf_s7(smf[7]), .sms_s7(1'b0), .rrow_s7(rrow[84+:12]), .rdata_s7(rdata[1792+:256]), .wq_s7(wq_sm[1967+:281]),
        .configured(w_cfgd), .fault(wfault), .active(w_active));
    integer axerr = 0;
    task automatic axw(input [11:0] a, input [31:0] d);
        reg ad, dd;
        begin
            ad = 0; dd = 0; @(negedge clk); awv = 1; awa = a; wv = 1; wd = d;
            while (!(ad && dd)) begin
                begin : HS reg ha, hw; ha = awv && awr; hw = wv && wr;
                @(posedge clk); #0.01; if (ha) begin ad = 1; awv = 0; end if (hw) begin dd = 1; wv = 0; end end
                @(negedge clk);
            end
            while (!bv) @(posedge clk);
            if (bresp != 0) begin $display("ERROR bresp %0d at %h data %h", bresp, a, d); axerr = axerr + 1; end
            @(posedge clk);
        end
    endtask
    task automatic hrow(input [7:0] t, input [11:0] addr, input [255:0] data);
        begin
            axw(12'hf20, {12'd0, addr, t});
            for (integer q = 0; q < 8; q = q + 1) axw(12'hf24, data[q*32 +: 32]);
        end
    endtask
    task automatic hdesc(input [7:0] t, input [11:0] b_, input [12:0] lim, input [15:0] loops);
        begin axw(12'hf20, {12'd0, 12'd0, t}); axw(12'hf28, {7'd0, lim, b_}); axw(12'hf2c, {16'd0, loops}); end
    endtask
    reg [31:0] C_launch; reg launched = 0;
    always @(posedge clk) if (rst_n && launch_v && !launched) begin launched <= 1; C_launch <= dut.u_tgt.cycle; end
    // banks
    reg [7:0] wslot_v, rslot_v; reg [2:0] wslot [0:7]; reg [0:0] rslot [0:7];
    reg [280:0] lgq [0:7]; reg [16:0] rqb [0:7];
    wire [256:0] rrb [0:7]; wire [17:0] bst [0:7]; wire [2:0] wqd [0:7];
    genvar b;
    generate for (b = 0; b < 8; b = b + 1) begin : g_b
        wire [275:0] eg; wire [265:0] pr; wire dd, kd, xd, x2d;
        // VM_LAT=1 (H-SM 2026-10-16, nat2 VM bank masters): one pin-register edge on EVERY bank input (slots, rq, wq),
        // as the nat2 bank views; the writer RTL and the compiler slot cycles are unchanged (slot and data move together).
        // NAT2_MUT=1: only the SM writer's wq is delayed (slot not) -> must FAIL.
        wire b_rsv, b_wsv; wire [0:0] b_rs; wire [2:0] b_ws; wire [16:0] b_rq; wire [280:0] b_wsm, b_wlg;
        if (`VM_LAT == 1) begin : g_nat2
            reg r_rsv, r_wsv; reg [0:0] r_rs; reg [2:0] r_ws; reg [16:0] r_rq; reg [280:0] r_wsm, r_wlg;
            always @(posedge clk) begin r_rsv <= rslot_v[b]; r_wsv <= wslot_v[b]; r_rs <= rslot[b]; r_ws <= wslot[b];
                r_rq <= rqb[b]; r_wsm <= wq_sm[b*281 +: 281]; r_wlg <= lgq[b]; end
            assign b_rsv = r_rsv; assign b_wsv = (`NAT2_MUT == 1) ? wslot_v[b] : r_wsv; assign b_rs = r_rs;
            assign b_ws = (`NAT2_MUT == 1) ? wslot[b] : r_ws; assign b_rq = r_rq; assign b_wsm = r_wsm;
            assign b_wlg = (`NAT2_MUT == 1) ? lgq[b] : r_wlg;
        end else begin : g_nat0
            assign b_rsv = rslot_v[b]; assign b_wsv = wslot_v[b]; assign b_rs = rslot[b]; assign b_ws = wslot[b];
            assign b_rq = rqb[b]; assign b_wsm = wq_sm[b*281 +: 281]; assign b_wlg = lgq[b];
        end
        ot_vms_bank_static #(.RG(1), .WG(3)) u_bank(.clk(clk), .rst_n(rst_n), .bid(3'(b)), .sid(2'(Q)),
            .rslot_v(b_rsv), .rslot(b_rs), .wslot_v(b_wsv), .wslot(b_ws),
            .rq(b_rq), .rr(rrb[b]), .wq({281'd0, b_wsm, b_wlg}), .wq_done(wqd[b]),
            .dq(281'd0), .dq_done(dd), .kq(281'd0), .kq_done(kd), .xq(276'd0), .xq_done(xd), .xq2(276'd0), .xq2_done(x2d),
            .eg(eg), .pq(285'd0), .pr(pr), .status(bst[b]));
    end endgenerate
    // ---------------- golden model ----------------
    reg [31:0] gold [0:7][0:2047][0:7];   // bank, row11 {mirror,row10}, word
    reg        gset [0:7][0:2047];
    function automatic [31:0] to_bf16(input [31:0] x, input en);
        reg [31:0] r;
        begin
            if (!en) to_bf16 = x;
            else if (&x[30:23] && |x[22:0]) to_bf16 = {x[31:16] | 16'h0040, 16'h0000};
            else begin r = x + 32'h0000_7FFF + x[16]; to_bf16 = {r[31:16], 16'h0000}; end
        end
    endfunction
    // ---------------- schedule (the compiler) ----------------
    reg [7:0] ev_rv [0:NCYC-1];
    reg [11:0] ev_row [0:NCYC-1][0:7];
    reg [255:0] ev_dat [0:NCYC-1][0:7];
    reg ev_cmd [0:NCYC-1]; reg [25:0] ev_cmdw [0:NCYC-1];
    reg [7:0] slot_sm [0:NCYC-1];        // bank k reserved for the SM writer at cycle c
    integer freec [0:7];
    integer c, k, i, p, op, nrows, gap, t, st, lastemit, mism, nwr, nlg, seed;
    reg [9:0] base, stride; reg [3:0] P; reg fmt, mir; reg [31:0] w; reg [10:0] row;
    initial begin
        seed = 7;
        for (c = 0; c < NCYC; c = c + 1) begin ev_rv[c] = 0; ev_cmd[c] = 0; slot_sm[c] = 0; end
        for (k = 0; k < 8; k = k + 1) for (i = 0; i < 2048; i = i + 1) gset[k][i] = 0;
        for (k = 0; k < 8; k = k + 1) freec[k] = 0;
        t = 20; lastemit = 0;
        for (op = 0; op < 5; op = op + 1) begin
            case (op)
                0: begin P = 1; fmt = 0; mir = 0; base = 10'd0;   stride = 10'd0;  end
                1: begin P = 4; fmt = 1; mir = 0; base = 10'd64;  stride = 10'd8;  end
                2: begin P = 2; fmt = 0; mir = 1; base = 10'd200; stride = 10'd3;  end
                3: begin P = 8; fmt = 1; mir = 0; base = 10'd300; stride = 10'd16; end
                4: begin P = 3; fmt = 0; mir = 0; base = 10'd700; stride = 10'd40; end
            endcase
            c = lastemit + 3; if (c < t) c = t;                // descriptor only while the writer is idle
            ev_cmd[c] = 1; ev_cmdw[c] = {fmt, mir, P, stride, base};
            t = c + 1;   // tight (_t): the first rv one frame after its descriptor, so a late calendar fire (MUT 4) faults
            nrows = (op == 0) ? 24 : 16;
            for (k = 0; k < 8; k = k + 1) begin
                st = t + k;                                    // hop stagger of SM k
                for (i = 0; i < nrows; i = i + 1) begin
                    // SUB=4 retire burst, then a K-dependent gap (at least the P-cycle service of 4 rows)
                    if (i > 0 && i % 4 == 0) begin gap = 4 * P + 1 + ($urandom(seed) % 9); st = st + gap; end
                    else if (i > 0) st = st + 1;
                    ev_rv[st][k] = 1;
                    ev_row[st][k] = (i < 8) ? 12'(i) : 12'(40 + i);   // rows 0..7 and 48..; exercises r[11:3]
                    for (p = 0; p < 8; p = p + 1) begin
                        w = $urandom(seed);
                        if (i == 3 && p == 0) w = 32'h7F80_0001;        // NaN (quiet on BF16)
                        if (i == 5 && p == 1) w = 32'h3F80_8000;        // RNE tie
                        ev_dat[st][k][32*p +: 32] = w;
                    end
                    // timing contract: slot 0 at rv+3, serial server per SM
                    begin : srv
                        integer s0, e; s0 = st + 3; if (freec[k] > s0) s0 = freec[k];
                        for (p = 0; p < P; p = p + 1) begin
                            e = s0 + p; slot_sm[e][k] = 1;
                            row = {mir, 10'(base + p * stride + ev_row[st][k][11:3])};
                            gold[k][row][ev_row[st][k][2:0]] = to_bf16(ev_dat[st][k][32*p +: 32], fmt);
                            gset[k][row] = 1;
                            if (e > lastemit) lastemit = e;
                        end
                        freec[k] = s0 + P;
                    end
                end
            end
            t = lastemit + 1;
        end
        $display("schedule: last SM-writer emission at cycle %0d", lastemit);
    end
    // ---------------- drive ----------------
    integer cyc; reg [9:0] lgrow; reg [2:0] lgw; reg [31:0] lgv;
    integer rbk, rrw, phase_rd;
    reg [10:0] rd_row [0:7][0:9]; integer rdc [0:7];
    initial begin
        rv = 0; smf = 0; rrow = 0; rdata = 0; wslot_v = 0; rslot_v = 0; mism = 0; nwr = 0; nlg = 0;
        for (k = 0; k < 8; k = k + 1) begin lgq[k] = 0; rqb[k] = 0; wslot[k] = 0; rslot[k] = 0; end
        repeat (4) @(posedge clk); rst_n = 1; repeat (5) @(posedge clk);
        // install the writer descriptors as command-calendar entries {cmd26, at32} (at = the bench frame cycle)
        begin : INST
            integer ne; ne = 0;
            for (c = 0; c < NCYC; c = c + 1) if (ev_cmd[c]) begin hrow(8'd160, 12'h800 + 12'(ne), {198'd0, ev_cmdw[c], 32'(c)}); ne = ne + 1; end
            hdesc(8'd160, 12'd0, 13'(ne), 16'd1);
            repeat (10) @(posedge clk);
            if (!w_cfgd || wfault || ing_fault || axerr != 0) begin mism = mism + 1; $display("ERROR install: cfgd %0d fault %0d ingress %0d axi %0d", w_cfgd, wfault, ing_fault, axerr); end
            axw(12'hf30, 32'd1);
            // frame cycle 0 = the period whose collar cycle is C_launch + 2 + LEAD (an entry with at = c fires in frame c)
            while (!launched) @(posedge clk);
            @(negedge clk); while (dut.u_tgt.cycle != C_launch + 2 + LEAD - 1) @(negedge clk);
        end
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            @(negedge clk);
            rv = ev_rv[cyc];
            for (k = 0; k < 8; k = k + 1) begin
                rrow[12*k +: 12] = ev_row[cyc][k]; rdata[256*k +: 256] = ev_dat[cyc][k];
                lgq[k] = 0; wslot_v[k] = 0; wslot[k] = 0;
                if (slot_sm[cyc][k]) begin wslot_v[k] = 1; wslot[k] = 3'(G_SM); nwr = nwr + 1; end
                else if (cyc > 10 && cyc < lastemit && ($urandom(seed) % 3) == 0) begin
                    // LG competitor on the free calendar cycles, own rows 960..1023 of the same banks
                    lgrow = 10'(960 + ($urandom(seed) % 64)); lgw = 3'($urandom(seed)); lgv = $urandom(seed);
                    lgq[k] = {1'b1, 1'b0, 2'(Q), lgrow, 3'(k), {8{lgv}}, 8'd1 << lgw};
                    wslot_v[k] = 1; wslot[k] = 3'(G_LG);
                    gold[k][{1'b0, lgrow}][lgw] = lgv; gset[k][{1'b0, lgrow}] = 1; nlg = nlg + 1;
                end
            end
        end
        // read back every touched row through read group 0
        repeat (8) @(negedge clk);
        for (k = 0; k < 8; k = k + 1) wslot_v[k] = 0;
        for (i = 0; i < 2048 + 8; i = i + 1) begin
            @(negedge clk);
            for (k = 0; k < 8; k = k + 1) begin
                rslot_v[k] = 0; rqb[k] = 0;
                if (i < 2048 && gset[k][i]) begin
                    rslot_v[k] = 1; rslot[k] = 0;
                    rqb[k] = {1'b1, i[10], i[10] ? 2'b00 : 2'(Q), i[9:0], 3'(k)};
                end
            end
        end
        repeat (10) @(negedge clk);
        for (k = 0; k < 8; k = k + 1) if (bst[k][17]) begin mism = mism + 1; $display("bank %0d FAULT (schedule/decode)", k); end
        if (wfault || ing_fault || axerr != 0) begin mism = mism + 1; $display("writer/collar FAULT %0d ingress %0d axi %0d", wfault, ing_fault, axerr); end
        // status path: an SM fault pulse must reach the sticky writer fault in 2 edges
        @(negedge clk); smf = 8'h08; @(negedge clk); smf = 0; repeat (3) @(negedge clk);
        if (!wfault) begin mism = mism + 1; $display("SM fault did not reach the writer fault"); end
        $display("SM writes %0d, LG writes %0d, rows checked %0d", nwr, nlg, nchk);
        for (k = 0; k < 8; k = k + 1) for (i = 0; i < 2048; i = i + 1) if (gset[k][i]) nexp = nexp + 1;
        if (nchk != nexp) begin mism = mism + 1; $display("rows checked %0d != touched %0d", nchk, nexp); end
        if (mism == 0 && nchk > 0) $display("TB_HBM_SM_VM_WR_Q_T PASS MUT=%0d", `MUT);
        else $display("TB_HBM_SM_VM_WR_Q_T FAIL MUT=%0d mismatches+faults=%0d", `MUT, mism);
        $finish;
    end
    // response checker: rr arrives 6 edges after the request is presented (bank header)
    reg [10:0] pipe_row [0:7][0:15]; reg pipe_v [0:7][0:15];
    integer nchk = 0, nexp = 0, j;
    always @(posedge clk) begin
        for (k = 0; k < 8; k = k + 1) begin
            for (j = 15; j > 0; j = j - 1) begin pipe_v[k][j] <= pipe_v[k][j-1]; pipe_row[k][j] <= pipe_row[k][j-1]; end
            pipe_v[k][0] <= rst_n && rslot_v[k] && rqb[k][16];
            pipe_row[k][0] <= {rqb[k][15], rqb[k][12:3]};
        end
    end
    always @(negedge clk) if (rst_n) begin
        for (k = 0; k < 8; k = k + 1) if (rrb[k][256]) begin
            if (!pipe_v[k][6+`VM_LAT]) begin mism = mism + 1; $display("bank %0d unexpected response", k); end
            else begin
                nchk = nchk + 1;
                for (j = 0; j < 8; j = j + 1)
                    if (rrb[k][32*j +: 32] !== gold[k][pipe_row[k][6+`VM_LAT]][j] && !(gold[k][pipe_row[k][6+`VM_LAT]][j] === 32'bx && rrb[k][32*j +: 32] == 0)) begin
                        if (mism < 10) $display("MISMATCH bank %0d row %0d word %0d: got %h want %h", k, pipe_row[k][6+`VM_LAT], j,
                            rrb[k][32*j +: 32], gold[k][pipe_row[k][6+`VM_LAT]][j]);
                        mism = mism + 1;
                    end
            end
        end
    end
endmodule
`default_nettype wire
