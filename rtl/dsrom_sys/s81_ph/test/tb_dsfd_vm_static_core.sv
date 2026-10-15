`timescale 1ns/1ps
// tb_dsfd_vm_static_core (claude S81 VM owner r8, 2026-10-14): exact production-shape bench of the static S81 VM core
// (128 real SRAM macro models, real relays / FSR / return store / write dispatch / storage / engine 12 / landing).
// The bench is the compiler: it emits a fixed calendar (pin cycle of every request) and the expected answer of every
// cycle; data values are declared external stimuli (row, word, version), never produced inside the DUT by the bench.
//   W  all 16384 rows written once (SU 16 + HC 8 + collective 4 sources an edge, distinct banks, lane 0) under an
//      engine ARM (slot 0, rows 0..1023, client SU) and a CHECK at its exact first legal pin; every commit observed on
//      its real bank port at ONE constant latency K after its source pin; c_done exactly 6 after each command pin;
//      t_inp_su rises at the fixed edge after the CHECK.
//   L  lanes 1 / 2: three sources to one bank on one edge, the next on that bank 3 edges later: commits at K + lane.
//   M  static LARM: selector rows (group 5) and scan-service row pairs (group 0) land at base + OFF + STRIDE * k.
//   R  random SU / HC native reads (fixed slots, SU1 relocation, distinct banks) + PQ 4-row x reads, every edge for
//      +reads edges: every returned row compared word-by-word at the ONE constant latency 11 edges (pin -> output reg).
//   +mode 0 base (expect no fault); 1 four sources on one bank (lane >= 3); 2 drain collision; 3 PQ misaligned;
//   4 P2RD native op; 5 duplicate read bank (FSR); 6 MIX and SU on one logical port -- each must raise ITS fault source.
module tb_dsfd_vm_static_core;
    // landing commit age (edges from the row's pin edge): 2 with the native pin stage (dsfd_vm_static_landing PINREG=1, F8
    // 2026-10-15), 1 for the r1 PINREG=0 reference.  The compiler's LARM row-commit constant follows the same value.
`ifdef OT_VM_LANDING_PINREG0
    localparam integer LAND_AGE = 1;
`else
    localparam integer LAND_AGE = 2;
`endif
`ifdef OT_VM_NATIVE_READ_L16
    localparam integer READ_PIPE=4;     // + pin-registered rsched / return lanes (L16)
`elsif OT_VM_NATIVE_READ_PINREG
    localparam integer READ_PIPE=2;
`elsif OT_VM_NATIVE_READ
    localparam integer READ_PIPE=1;
`else
    localparam integer READ_PIPE=0;
`endif
`ifdef OT_VM_NATIVE_CAP
    localparam integer CAP_PIPE=1;
`else
    localparam integer CAP_PIPE=0;
`endif

    reg ck = 1'b0; reg rss = 1'b0;
    always #0.4167 ck = ~ck;
    reg  [84:0] c_cmd = 0; wire [8:0] c_done; wire [1:0] c_st; wire t_inp_su, t_inp_hc;
    reg  [15:0] su_rqv = 0; reg [223:0] su_rq = 0; wire [15:0] su_rsv; wire [8191:0] su_rs;
    reg  [15:0] su_wqv = 0; reg [223:0] su_wq = 0; reg [255:0] su_wqm = 0; reg [8191:0] su_wqd = 0;
    reg  [1:0] hc_rqv = 0; reg [27:0] hc_rq = 0; wire [1:0] hc_rsv; wire [1023:0] hc_rs;
    reg  [7:0] hc_wqv = 0; reg [111:0] hc_wq = 0; reg [127:0] hc_wqm = 0; reg [4095:0] hc_wqd = 0;
    reg  [19:0] pqx = 0; wire [2048:0] pq_o; reg [14:0] crq = 0; wire [512:0] crs;
    reg  [3:0] l_v = 0; reg [2047:0] l_d = 0; reg [2203:0] cvm = 0;
    reg  [19:0] mx_rqv = 0; reg [279:0] mx_rq = 0; wire [19:0] mx_rsv; wire [10239:0] mx_rs;
    reg  [3:0] mx_wqv = 0; reg [55:0] mx_wq = 0; reg [63:0] mx_wqm = 0; reg [2047:0] mx_wqd = 0;
    // Compatibility stimulus adapter for the core's explicit auxiliary and row-write ports.
    wire [7:0] xv; wire [4095:0] xd;
    reg [1:0] crlane [0:12+READ_PIPE]; integer ci;
    always @(posedge ck) begin
        crlane[0] <= crq[2:1];
        for (ci = 1; ci < 13+READ_PIPE; ci = ci + 1) crlane[ci] <= crlane[ci-1];
    end
    assign crs = {xd[512*crlane[12+READ_PIPE] +: 512], xv[crlane[12+READ_PIPE]]};
    wire [31:0] clt; wire [3:0] clv; wire [55:0] clr; wire [63:0] clm; wire [2047:0] cld;
    genvar cl;
    generate for (cl = 0; cl < 4; cl = cl + 1) begin
        assign clv[cl] = cvm[551*cl];
        assign clt[8*cl +: 8] = cvm[551*cl+543 +: 8];
        assign clr[14*cl +: 14] = cvm[551*cl+1 +: 14];
        assign clm[16*cl +: 16] = cvm[551*cl+15 +: 16];
        assign cld[512*cl +: 512] = cvm[551*cl+31 +: 512];
    end endgenerate
    wire vm_fault;
    dsfd_vm_static_core #(.READ_PIPE(READ_PIPE)) dut (.cks(ck), .rss(rss),
        .ck_read_data({64{ck}}), .ck_read_valid({8{ck}}), .rst_read_data_n({64{rss}}), .rst_read_valid_n({8{rss}}),
        .ck_rsched(ck), .ck_seq(ck), .ck_landing(ck),
        .ck_mem_fsr({16{ck}}), .ck_mem_return({4{ck}}), .ck_mem_bank({128{ck}}),
        .ck_mem_wcapture({128{ck}}), .ck_mem_wscatter({16{ck}}),
        .ck_mem_relay_req({48{ck}}), .ck_mem_relay_rsp({48{ck}}),
        .ck_write_control(ck), .ck_write_header(ck), .ck_write_payload({4{ck}}),
        .ck_write_dispatch({16{ck}}), .ck_write_stage({128{ck}}),
        .rst_rsched_n(rss), .rst_seq_n(rss), .rst_landing_n(rss),
        .rst_mem_fsr_n({16{rss}}), .rst_mem_return_n({4{rss}}), .rst_mem_bank_n({128{rss}}),
        .rst_mem_wcapture_n({128{rss}}), .rst_mem_wscatter_n({16{rss}}), .rst_mem_relay_n({48{rss}}),
        .rst_write_control_n(rss), .rst_write_header_n(rss), .rst_write_payload_n({4{rss}}),
        .rst_write_dispatch_n({16{rss}}), .rst_write_stage_n({128{rss}}), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .t_inp_su(t_inp_su),
        .t_inp_hc(t_inp_hc), .f_su_rqv(su_rqv), .f_su_rq(su_rq), .t_su_rsv(su_rsv), .t_su_rs(su_rs), .f_su_wqv(su_wqv),
        .f_su_wq(su_wq), .f_su_wqm(su_wqm), .f_su_wqd(su_wqd), .f_hc_rqv(hc_rqv), .f_hc_rq(hc_rq), .t_hc_rsv(hc_rsv),
        .t_hc_rs(hc_rs), .f_hc_wqv(hc_wqv), .f_hc_wq(hc_wq), .f_hc_wqm(hc_wqm), .f_hc_wqd(hc_wqd), .f_pqx(pqx), .t_pqx(pq_o), .x_av({4'd0, (crq[0] ? (4'b1 << crq[2:1]) : 4'd0)}), .x_ar({56'd0, {4{crq[14:1]}}}), .x_rv(xv), .x_rd(xd), .nf_v(), .nf_d(),
        .f_mx_rqv(mx_rqv), .f_mx_rq(mx_rq), .t_mx_rsv(mx_rsv), .t_mx_rs(mx_rs),
        .f_mx_wqv(mx_wqv), .f_mx_wq(mx_wq), .f_mx_wqm(mx_wqm), .f_mx_wqd(mx_wqd),
        .l_v(l_v), .l_d(l_d), .cp_v(16'd0), .cp_row(224'd0), .cp_m(256'd0), .cp_d(8192'd0), .cl_t(clt), .cl_v(clv), .cl_row(clr), .cl_m(clm), .cl_d(cld), .wf_v(1'b0), .wf_row(14'd0), .wf_d(512'd0), .x_al(3'd0), .x_hdr(9'd0), .edge_f(3'd0), .vm_fault(vm_fault));

    localparam integer RL = 12+READ_PIPE, DL = 7;      // Exact elapsed edges from command/read sampling to output.
    integer cy = 0, bad = 0, mode = 0, seed = 1, nreads = 4000, K = -1, commits = 0, reads = 0, rows_checked = 0;
    integer dones = 0, pqreads = 0, cmds = 0, mxreads = 0, mxwrites = 0, fault_seen = 0;
    reg [7:0] ver [0:16383];                 // stimulus version of each row (value function input)
    integer exp_c [0:16383]; reg [3:0] exp_sl [0:16383]; reg [15:0] exp_m [0:16383];
    function [31:0] value(input integer row, input integer word, input integer v);
        value = 32'(row * 773 + word * 127 + v * 40503 + 19);
    endfunction
    function [511:0] rowdata(input integer row, input integer v); integer w;
        for (w = 0; w < 16; w = w + 1) rowdata[32*w +: 32] = value(row, w, v);
    endfunction
    function [4:0] bank_of(input [13:0] r); bank_of = r[4:0] ^ {r[7:5], 2'b00}; endfunction
    integer rnd;
    function integer urand(input integer n); begin rnd = $random(seed); urand = (rnd < 0 ? -rnd : rnd) % n; end endfunction

    // expected per-cycle answers
    localparam integer MAXC = 40000;
    reg [8:0] dn_exp [0:MAXC-1];
    reg [17:0] rv_exp [0:MAXC-1]; reg [251:0] rr_exp [0:MAXC-1]; reg pq_exp [0:MAXC-1]; reg [13:0] pq_row [0:MAXC-1]; reg cr_exp [0:MAXC-1]; reg [13:0] cr_row [0:MAXC-1]; reg [19:0] mx_exp [0:MAXC-1]; reg [279:0] mx_row [0:MAXC-1];
    integer i;
    initial for (i = 0; i < MAXC; i = i + 1) begin dn_exp[i] = 0; rv_exp[i] = 0; pq_exp[i] = 0; cr_exp[i] = 0; mx_exp[i] = 0; end

    // ---------------------------------------------------------------- per-cycle checks (negedge, before driving)
    always @(negedge ck) if (rss) begin : chk integer p, s, b, q; reg [13:0] row; reg [8:0] a;
        // engine done
        if (c_done !== dn_exp[cy]) begin bad = bad + 1; if (bad < 10) $display("DONE MISMATCH cy %0d got %h exp %h", cy, c_done, dn_exp[cy]); end
        if (c_done[8]) dones = dones + 1;
        // commits: every observed commit on its real bank port at its expected cycle with its expected mask
        for (p = 0; p < 128; p = p + 1) if (dut.cm_v[p]) begin
            s = p / 32; b = p % 32; a = dut.cm_a[9*p +: 9];
            row = {a, 5'(b) ^ {a[2:0], 2'b00}};
            if (K < 0 && exp_c[row] >= 0) K = cy - exp_c[row];
            if (exp_c[row] < 0 || cy - exp_c[row] != K || exp_sl[row][s] || dut.cm_m[4*p +: 4] !== exp_m[row][4*s +: 4]) begin
                bad = bad + 1; if (bad < 10) $display("COMMIT MISMATCH cy %0d row %0d slice %0d exp_c %0d K %0d", cy, row, s, exp_c[row], K);
            end
            exp_sl[row][s] = 1'b1; commits = commits + 1;
        end
        // native reads
        for (q = 0; q < 18; q = q + 1) begin
            if ((q < 16 ? su_rsv[q] : hc_rsv[q-16]) !== rv_exp[cy][q]) begin
                bad = bad + 1; if (bad < 10) $display("RSV MISMATCH cy %0d port %0d", cy, q); end
            if (rv_exp[cy][q]) begin
                row = rr_exp[cy][14*q +: 14];
                if ((q < 16 ? su_rs[512*q +: 512] : hc_rs[512*(q-16) +: 512]) !== rowdata(row, ver[row])) begin
                    bad = bad + 1; if (bad < 10) $display("READ DATA MISMATCH cy %0d port %0d row %0d", cy, q, row); end
                rows_checked = rows_checked + 1;
            end
        end
        if (mx_rsv !== mx_exp[cy]) begin bad = bad + 1; if (bad < 10) $display("MX RSV MISMATCH cy %0d got %h exp %h", cy, mx_rsv, mx_exp[cy]); end
        for (q = 0; q < 20; q = q + 1) if (mx_exp[cy][q]) begin
            row = mx_row[cy][14*q +: 14];
            if (mx_rs[512*q +: 512] !== rowdata(row, ver[row])) begin bad = bad + 1; if (bad < 10) $display("MX DATA MISMATCH cy %0d lane %0d row %0d ver %0d wr_cy %0d got %h exp %h", cy, q, row, ver[row], wr_cy[row], mx_rs[512*q +: 32], rowdata(row, ver[row]) & 32'hffffffff); end
            rows_checked = rows_checked + 1;
        end
        if (vm_fault && !fault_seen) begin fault_seen = 1;
            $display("FIRST FAULT cy %0d: wsched own %b dflt %h sflt %h | mem %h | land %b pq %b out %b op %b rsched %b | seq flt %b",
                cy, dut.u_ws.own, dut.u_ws.dflt, dut.u_ws.sflt, dut.m_flt, dut.l_flt, dut.u_seq.pq_bad, dut.u_seq.o_bad, dut.u_seq.op_bad,
                dut.r_flt, dut.u_seq.u_seq.flt); end
        if (crs[0] !== cr_exp[cy]) begin bad = bad + 1; if (bad < 10) $display("CRS MISMATCH cy %0d", cy); end
        if (cr_exp[cy]) begin
            if (crs[512:1] !== rowdata(cr_row[cy], ver[cr_row[cy]])) begin bad = bad + 1; if (bad < 10) $display("CRS DATA MISMATCH cy %0d", cy); end
            rows_checked = rows_checked + 1;
        end
        if (pq_o[0] !== pq_exp[cy]) begin bad = bad + 1; if (bad < 10) $display("PQ RV MISMATCH cy %0d", cy); end
        if (pq_exp[cy]) begin
            for (q = 0; q < 4; q = q + 1)
                if (pq_o[1 + 512*q +: 512] !== rowdata(pq_row[cy] + q, ver[pq_row[cy] + q])) begin
                    bad = bad + 1; if (bad < 10) $display("PQ DATA MISMATCH cy %0d row %0d", cy, pq_row[cy] + q); end
            rows_checked = rows_checked + 4;
        end
    end

    // ---------------------------------------------------------------- calendar helpers (drive at negedge cy)
    task step; begin
        @(negedge ck); #0.01; cy = cy + 1;
        c_cmd = 0; su_rqv = 0; hc_rqv = 0; su_wqv = 0; hc_wqv = 0; pqx = 0; l_v = 0; cvm = 0; crq = 0; mx_rqv = 0; mx_wqv = 0;
    end endtask
    task cmd(input [23:0] arg); begin
        c_cmd = {1'b1, 1'b0, 10'd0, 21'd0, 21'(cmds), arg, 7'(cmds % 128)};
        dn_exp[cy + DL] = {1'b1, 1'b0, 7'(cmds % 128)}; cmds = cmds + 1;
    end endtask
    // write source n (0..15 SU, 16..23 HC, 24..27 collective) of row r, version v, full mask, lane l
    task wsrc(input integer n, input integer r, input integer v, input integer l); begin
        ver[r] = v[7:0]; exp_c[r] = cy + l; exp_sl[r] = 4'd0; exp_m[r] = 16'hffff;
        if (n < 16) begin su_wqv[n] = 1; su_wq[14*n +: 14] = r; su_wqm[16*n +: 16] = 16'hffff; su_wqd[512*n +: 512] = rowdata(r, v); end
        else if (n < 24) begin hc_wqv[n-16] = 1; hc_wq[14*(n-16) +: 14] = r; hc_wqm[16*(n-16) +: 16] = 16'hffff; hc_wqd[512*(n-16) +: 512] = rowdata(r, v); end
        else begin cvm[551*(n-24)] = 1; cvm[551*(n-24) + 1 +: 14] = r; cvm[551*(n-24) + 15 +: 16] = 16'hffff;
            cvm[551*(n-24) + 31 +: 512] = rowdata(r, v); cvm[551*(n-24) + 543 +: 8] = 8'(n); end
    end endtask

    integer e, n, r, k, p, rowp, chk_pin, base; integer wr_cy [0:16383]; integer rd_cy [0:16383];
    reg [31:0] bk_used;
    initial begin
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("reads=%d", nreads)) nreads = 4000;
        for (i = 0; i < 16384; i = i + 1) begin wr_cy[i] = -100; rd_cy[i] = -100; ver[i] = 0; exp_c[i] = -1; exp_sl[i] = 0; exp_m[i] = 0; end
        repeat (3) @(negedge ck); rss = 1'b1; repeat (4) step;
        if (mode == 0) begin
            // ---------------- W: ARM slot 0 (rows 0..1023, client SU: arg {code 0, client 0, base16 0, nrows-1 1023})
            step; cmd({3'd0, 1'b0, 10'd0, 10'd1023});
            step; step;
            for (e = 0; e < 512; e = e + 1) begin            // block e (rows 32e .. 32e + 31: 32 distinct banks)
                step; for (n = 0; n < 28; n = n + 1) wsrc(n, 32 * e + n, 1, 0);
                step; for (n = 0; n < 4; n = n + 1) wsrc(n, 32 * e + 28 + n, 1, 0);
            end
            // CHECK of slot 0 after every row 0..1023 commit was observed (they end at W edge 64; CHECK after edge 1024 + 40)
            repeat (40) step;
            if (K < 0) begin bad = bad + 1; $display("NO COMMIT OBSERVED"); end
            step; cmd({3'd0, 1'b0, 10'h3FF, 10'h3FF}); chk_pin = cy;
            repeat (12) step;
            if (!t_inp_su || c_st[0]) begin bad = bad + 1; $display("CHECK did not verify: inp %b st %b", t_inp_su, c_st); end
            // ---------------- L: lanes 1 / 2 (three sources -> one bank), next use of the bank 3 edges later
            for (k = 0; k < 8; k = k + 1) begin
                step;
                // rows with the same bank: r, r + 32 (row[7:5] changes -> bank changes!) -> use r and r + 256 (row[7:5] equal)
                r = 512 + 32 * k;
                wsrc(0, r, 2, 0); wsrc(1, r + 256, 2, 1); wsrc(2, r + 512, 2, 2);
                step; step; step;
            end
            // ---------------- M: static LARM
            step; cmd({3'd6, 4'd5, 3'd0, 14'd3000});            // selector lane -> rows 3000..
            step; cmd({3'd6, 4'd0, 3'd0, 14'd5000});            // scan service -> rows 5000/5001, 5002/5003 ..
            repeat (6) step;
            for (k = 0; k < 8; k = k + 1) begin
                step;                                   // selector row k (even edges), scan pair k (odd edges)
                l_v[2] = 1; l_d[1024 +: 512] = rowdata(3000 + k, 3); ver[3000 + k] = 3; exp_c[3000 + k] = cy + LAND_AGE; exp_sl[3000 + k] = 0; exp_m[3000 + k] = 16'hffff;
                step;
                if (k < 4) begin
                    l_v[0] = 1; l_v[1] = 1; l_d[0 +: 512] = rowdata(5000 + 2 * k, 3); l_d[512 +: 512] = rowdata(5001 + 2 * k, 3);
                    ver[5000 + 2 * k] = 3; ver[5001 + 2 * k] = 3;
                    exp_c[5000 + 2 * k] = cy + LAND_AGE; exp_c[5001 + 2 * k] = cy + LAND_AGE; exp_sl[5000 + 2 * k] = 0; exp_sl[5001 + 2 * k] = 0;
                    exp_m[5000 + 2 * k] = 16'hffff; exp_m[5001 + 2 * k] = 16'hffff;
                end
            end
            repeat (40) step;
            // ---------------- R: random native + PQ reads
            for (e = 0; e < nreads; e = e + 1) begin
                step; bk_used = 0;
                if (e % 8 == 3) begin                    // MIX read edge: lanes as the MIX4 layout (row[1:0] = lane ^ beat)
                    for (n = 0; n < 20; n = n + 1) if (urand(5) != 0) begin
                        for (k = 0; k < 40; k = k + 1) begin
                            r = urand(16384); r = {r[13:2], 2'(n % 4) ^ 2'(e / 8)};
                            if (!bk_used[bank_of(r)] && cy - wr_cy[r] > 40) k = 99;
                        end
                        if (k >= 99) begin
                            bk_used[bank_of(r)] = 1;
                            mx_rqv[n] = 1; mx_rq[14*n +: 14] = r; rd_cy[r] = cy;
                            mx_exp[cy + RL][n] = 1; mx_row[cy + RL][14*n +: 14] = r; mxreads = mxreads + 1;
                        end
                    end
                end
                else if (e % 8 == 4) begin                    // MIX writes: 4 rows of 4 distinct banks, new version
                    base = 32 * urand(512);
                    for (n = 0; n < 4; n = n + 1) begin
                        r = base + 8 * n + urand(8); while (cy - wr_cy[r] <= 40 || cy - rd_cy[r] <= 20) r = base + 8 * n + urand(8); wr_cy[r] = cy;
                        ver[r] = ver[r] + 1; exp_c[r] = cy; exp_sl[r] = 0; exp_m[r] = 16'hffff;
                        mx_wqv[n] = 1; mx_wq[14*n +: 14] = r; mx_wqm[16*n +: 16] = 16'hffff; mx_wqd[512*n +: 512] = rowdata(r, ver[r]);
                        mxwrites = mxwrites + 1;
                    end
                end else begin
                rowp = 4 * urand(4096);
                if (urand(3) == 0 && cy - wr_cy[rowp] > 40 && cy - wr_cy[rowp+1] > 40 && cy - wr_cy[rowp+2] > 40 && cy - wr_cy[rowp+3] > 40) begin           // PQ: rows 4m .. 4m + 3 (banks distinct)
                    pqx = 20'd1; pqx[19:1] = 19'(rowp * 16); for (k = 0; k < 4; k = k + 1) rd_cy[rowp + k] = cy;
                    for (k = 0; k < 4; k = k + 1) bk_used[bank_of(rowp + k)] = 1;
                    pq_exp[cy + RL] = 1; pq_row[cy + RL] = rowp; pqreads = pqreads + 1;
                end
                if (urand(2) == 0) begin           // collective source row (aux 4 + low2)
                    for (k = 0; k < 20; k = k + 1) begin r = urand(16384); if (!bk_used[bank_of(r)] && cy - wr_cy[r] > 40) k = 99; end
                    if (k >= 99) begin bk_used[bank_of(r)] = 1; crq = {14'(r), 1'b1}; rd_cy[r] = cy; cr_exp[cy + RL] = 1; cr_row[cy + RL] = r; reads = reads + 1; end
                end
                for (p = 0; p < 18; p = p + 1) if (urand(4) != 0) begin
                    // low2: SU p>=2 -> p % 4; SU0 / SU1 free; HC -> distinct low2
                    for (k = 0; k < 20; k = k + 1) begin
                        r = urand(16384);
                        if (p >= 2 && p < 16) r = {r[13:2], 2'(p % 4)};
                        if (p == 17 && hc_rqv[0]) r = {r[13:2], 2'(hc_rq[1:0] + 1)};
                        if (p == 1 && su_rqv[0]) r = {r[13:2], su_rq[1:0]};   // forces the SU1 relocation 4 + low2
                        if (!bk_used[bank_of(r)] && cy - wr_cy[r] > 40) k = 99;
                    end
                    if (k >= 99) begin
                        // SU1 relocated to slot 4 + low2 collides with SU 4..7 fixed slots: keep those idle then
                        if (p >= 4 && p < 8 && su_rqv[1] && su_rq[15:14] == 2'(p - 4)) ;
                        else begin
                            bk_used[bank_of(r)] = 1;
                            if (p < 16) begin su_rqv[p] = 1; su_rq[14*p +: 14] = r; end
                            else begin hc_rqv[p-16] = 1; hc_rq[14*(p-16) +: 14] = r; end
                            rv_exp[cy + RL][p] = 1; rr_exp[cy + RL][14*p +: 14] = r; reads = reads + 1; rd_cy[r] = cy;
                        end
                    end
                end
                // SU1 at the same low2 as SU0 relocates to slot 4 + low2: SU 4 + low2 must be idle (fixed-slot rule)
                if (su_rqv[0] && su_rqv[1] && su_rq[1:0] == su_rq[15:14] && su_rqv[4 + su_rq[1:0]]) begin
                    su_rqv[4 + su_rq[1:0]] = 0; rv_exp[cy + RL][4 + su_rq[1:0]] = 0; reads = reads - 1;
                end
                // SU1 at low2 2/3 with SU2/SU3 valid also relocates
                if (su_rqv[1] && ((su_rq[15:14] == 2'd2 && su_rqv[2]) || (su_rq[15:14] == 2'd3 && su_rqv[3])) && su_rqv[4 + su_rq[15:14]]) begin
                    su_rqv[4 + su_rq[15:14]] = 0; rv_exp[cy + RL][4 + su_rq[15:14]] = 0; reads = reads - 1;
                end
                // SU0 shares slots 0..3 with SU2 / SU3 (fixed slots 2 / 3): drop SU0 if it would collide
                if (su_rqv[0] && ((su_rq[1:0] == 2'd2 && su_rqv[2]) || (su_rq[1:0] == 2'd3 && su_rqv[3]))) begin
                    su_rqv[0] = 0; rv_exp[cy + RL][0] = 0; reads = reads - 1;
                end
            end
                end
            repeat (30) step;
        end else begin
            // ---------------- fault witnesses
            step;
            case (mode)
                1: begin wsrc(0, 64, 1, 0); wsrc(1, 64 + 256, 1, 1); wsrc(2, 64 + 512, 1, 2); wsrc(3, 64 + 768, 1, 3); end
                2: begin wsrc(0, 64, 1, 0); wsrc(1, 64 + 256, 1, 1); step; wsrc(0, 64 + 512, 1, 0); end
                3: pqx = {19'(16 * 4 + 16), 1'b1};
                4: cmd({3'd6, 4'd7, 17'd0});
                6: begin mx_rqv[0] = 1; mx_rq[0 +: 14] = 14'd64; su_rqv[0] = 1; su_rq[0 +: 14] = 14'd128; end
                5: begin su_rqv[2] = 1; su_rq[28 +: 14] = 14'd2; su_rqv[6] = 1; su_rq[84 +: 14] = 14'd258; end
                default: ;
            endcase
            repeat (30) step;
            // the witness must raise ITS fault source (and reach vm_fault / c_st[0])
            case (mode)
                1: chk_pin = dut.u_ws.own[0] && !dut.u_ws.own[1];
                2: chk_pin = dut.u_ws.own[1] && !dut.u_ws.own[0];
                3: chk_pin = dut.u_seq.pq_bad;
                4: chk_pin = dut.u_seq.op_bad;
                5: chk_pin = dut.m_flt[0] && !dut.w_flt;
                6: chk_pin = dut.r_flt;
                default: chk_pin = 0;
            endcase
            bad = (!vm_fault || !c_st[0] || !chk_pin) ? 1 : 0;
            $display("TB_VMCORE FAULT mode %0d vm_fault %b c_st %b own_source %0d", mode, vm_fault, c_st, chk_pin);
            $display("TB_VMCORE %s mode %0d", bad == 0 ? "PASS" : "FAIL", mode);
            $finish;
        end
        // The simulator schedules $finish for the end of this time step. A fault
        // witness must not fall through into the base-calendar count checks.
        if (mode == 0) begin
        if (mode == 0 && (vm_fault || c_st[0])) begin bad = bad + 1;
            $display("UNEXPECTED FAULT vm_fault %b c_st %b: wsched own %b dflt %h sflt %h | mem %h | land %b pq %b out %b op %b rsched %b | seq flt %b",
                vm_fault, c_st, dut.u_ws.own, dut.u_ws.dflt, dut.u_ws.sflt, dut.m_flt, dut.l_flt, dut.u_seq.pq_bad, dut.u_seq.o_bad, dut.u_seq.op_bad,
                dut.r_flt, dut.u_seq.u_seq.flt); end
        $display("TB_VMCORE RESULT mode %0d cycles %0d commits %0d K %0d reads %0d pq %0d mix_reads %0d mix_writes %0d rows_checked %0d dones %0d cmds %0d bad %0d",
                 mode, cy, commits, K, reads, pqreads, mxreads, mxwrites, rows_checked, dones, cmds, bad);
        if (commits != 4 * (16384 + 24 + 16 + mxwrites)) begin bad = bad + 1; $display("COMMIT COUNT %0d", commits); end
        $display("TB_VMCORE %s mode %0d", bad == 0 ? "PASS" : "FAIL", mode);
        $finish;
        end
    end
endmodule
