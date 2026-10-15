`timescale 1ps/1ps
// Exact scheduled component composition of the die-name VM master using 128 real SRAM models.
// The bench supplies external boundary stimuli and expected answers; all DUT computation,
// capture assembly, fixed-phase transfers and memory services instantiate actual RTL.
// Epoch: 4 x 834 ps stream edges = 3 x 1112 ps serial edges. Both resets release
// before a common rising edge, which is index zero in both domains.
// Base calendar: SU writes; four direct collective row-write tuples with sparse masks;
// 32 source-row reads (L12); selector/collector/scan landing transfers; qSW/gather
// STREAM commands; 64 WFC writes + START doorbell and 32 read pairs (serial L15);
// capture all128roots (3 full rounds +40 elements), then every landed row read back.
// Every command completes at its pin edge +6. Checks cover every output valid edge
// and numerical payload when valid; HC/PQ/MIX full traffic is the companion core gate.
// Fault witnesses: 1 invalid STREAM dest, 2 gather phase mismatch, 3 scan status,
// 4 unsupported LARM7, 5 aux lane collision, 6 WFC range, 7 WFC pair lane,
// 8 capture alignment. Each requires its named sticky fault AND top-level c_st[0].
module tb_dsfd_sp_vm_static;
`ifdef OT_VM_NATIVE_READ_L16
    localparam integer READ_PIPE=4;     // + pin-registered rsched / return lanes (L16)
`elsif OT_VM_NATIVE_READ_PINREG
    localparam integer READ_PIPE=2;
`elsif OT_VM_NATIVE_READ
    localparam integer READ_PIPE=1;
`else
    localparam integer READ_PIPE=0;
`endif
`ifdef OT_VM_NATIVE_CAP_PINREG
    localparam integer CAP_PIPE=2;
`elsif OT_VM_NATIVE_CAP
    localparam integer CAP_PIPE=1;
`else
    localparam integer CAP_PIPE=0;
`endif

    reg s_ck = 1, t_ck = 1, rst = 1, rss = 1;
    reg bench_active = 0;
    always #556 s_ck = ~s_ck;
    always #417 t_ck = ~t_ck;
    // ---------------------------------------------------------------- DUT
    reg  [84:0] c_cmd = 0; wire [8:0] c_done; wire [1:0] c_st; wire t_inp_su, t_inp_hc;
    reg  [15:0] su_rqv = 0; reg [223:0] su_rq = 0; wire [15:0] su_rsv; wire [8191:0] su_rs;
    reg  [15:0] su_wqv = 0; reg [223:0] su_wq = 0; reg [255:0] su_wqm = 0; reg [8191:0] su_wqd = 0;
    wire [1:0] hc_rsv; wire [1023:0] hc_rs; wire [2048:0] pq_o;
    reg  [13375:0] fcap = 0; reg [559:0] fwfc = 0; wire [1028:0] twfc;
    reg [2203:0] fcol = 0; reg [14:0] crq = 0; wire [512:0] crs;
    reg [514:0] sel = 0, col = 0; reg [1026:0] asw = 0;
    wire [511:0] tgat; reg [10:0] xgo = 0; wire [512:0] qsw; reg [2:0] qsws = 3'b011;
    dsfd_sp_vm #(.CAP_PIPE(CAP_PIPE), .READ_PIPE(READ_PIPE)) dut (
        .ck_read_data_t({64{t_ck}}), .ck_read_valid_t({8{t_ck}}), .rss_read_data_t({64{rss}}), .rss_read_valid_t({8{rss}}),
        .ck_core_t(t_ck), .ck_rsched_t(t_ck), .ck_seq_t(t_ck), .ck_landing_t(t_ck),
        .ck_mem_fsr_t({16{t_ck}}), .ck_mem_return_t({16{t_ck}}), .ck_mem_bank_t({128{t_ck}}),
        .ck_mem_wcapture_t({128{t_ck}}), .ck_mem_wscatter_t({16{t_ck}}),
        .ck_mem_relay_req_t({48{t_ck}}), .ck_mem_relay_rsp_t({48{t_ck}}),
        .ck_write_control_t(t_ck), .ck_write_header_t(t_ck), .ck_write_payload_t({4{t_ck}}),
        .ck_write_dispatch_t({16{t_ck}}), .ck_write_stage_t({128{t_ck}}),
        .ck_landing_x34_s({3{s_ck}}), .ck_landing_x34_t({3{t_ck}}),
        .rss_core_t(rss), .rss_rsched_t(rss), .rss_seq_t(rss), .rss_landing_t(rss),
        .rss_mem_fsr_t({16{rss}}), .rss_mem_return_t({4{rss}}), .rss_mem_bank_t({128{rss}}),
        .rss_mem_wcapture_t({128{rss}}), .rss_mem_wscatter_t({16{rss}}), .rss_mem_relay_t({48{rss}}),
        .rss_write_control_t(rss), .rss_write_header_t(rss), .rss_write_payload_t({4{rss}}),
        .rss_write_dispatch_t({16{rss}}), .rss_write_stage_t({128{rss}}),
        .rst_landing_x34_s({3{rst}}), .rss_landing_x34_t({3{rss}}),
        .ck_cap_control_s(s_ck), .rst_cap_control_s(rst), .ck_cap_lane_s({16{s_ck}}),
        .ck_cap_x34_s({16{s_ck}}), .ck_cap_x34_t({16{t_ck}}), .rst_cap_x34_s({16{rst}}), .rss_cap_x34_t({16{rss}}),
        .ck_wfc_control_s(s_ck), .ck_wfc_control_t(t_ck), .ck_wfc_x34_s(s_ck), .ck_wfc_x34_t(t_ck), .ck_wfc_x43_s(s_ck), .ck_wfc_x43_t(t_ck),
        .rst_wfc_control_s(rst), .rss_wfc_control_t(rss), .rst_wfc_x34_s(rst), .rss_wfc_x34_t(rss), .rst_wfc_x43_s(rst), .rss_wfc_x43_t(rss),
        .ck_xio_control_s(s_ck), .ck_xio_control_t(t_ck), .ck_xio_x43_s({2{s_ck}}), .ck_xio_x43_t({2{t_ck}}),
        .rst_xio_control_s(rst), .rss_xio_control_t(rss), .rst_xio_x43_s({2{rst}}), .rss_xio_x43_t({2{rss}}), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
        .t_inp_su(t_inp_su), .t_inp_hc(t_inp_hc),
        .f_su_rqv(su_rqv), .f_su_rq(su_rq), .t_su_rsv(su_rsv), .t_su_rs(su_rs),
        .f_su_wqv(su_wqv), .f_su_wq(su_wq), .f_su_wqm(su_wqm), .f_su_wqd(su_wqd),
        .f_hc_rqv(2'd0), .f_hc_rq(28'd0), .t_hc_rsv(hc_rsv), .t_hc_rs(hc_rs),
        .f_hc_wqv(8'd0), .f_hc_wq(112'd0), .f_hc_wqm(128'd0), .f_hc_wqd(4096'd0),
        .f_pqx(20'd0), .t_pqx(pq_o), .sel(sel), .col(col), .aSW(asw),
        .f_capture(fcap), .f_wfc(fwfc), .t_wfc(twfc), .f_collective(fcol), .f_crq(crq), .t_crs(crs),
        .t_gather(tgat), .f_xgo(xgo), .qSW(qsw), .qSWs(qsws));
    // ---------------------------------------------------------------- bench state
    integer mode = 0, seed = 1, bad = 0, tk = -1, sk = -1, i;
    integer n_rec = 0, n_q = 0, n_g = 0, n_w = 0, n_su = 0, n_done = 0, n_cl = 0;
    localparam integer MT = 6000, MS = 4500;
    function [31:0] value(input integer row, input integer word, input integer v);
        value = 32'(row * 773 + word * 127 + v * 40503 + 19);
    endfunction
    function [511:0] rowdata(input integer row, input integer v); integer w;
        for (w = 0; w < 16; w = w + 1) rowdata[32*w +: 32] = value(row, w, v);
    endfunction
    integer rnd;
    function integer urand(input integer n); begin rnd = $random(seed); urand = (rnd < 0 ? -rnd : rnd) % n; end endfunction
    reg [511:0] mem [0:16383]; reg memv [0:16383];
    initial for (i = 0; i < 16384; i = i + 1) memv[i] = 0;
    // expected outputs
    reg [512:0] e_tc [0:MT-1];  reg [8:0] e_dn [0:MT-1]; integer e_su_row [0:MT-1];
    reg [512:0] e_q [0:MS-1];   reg [511:0] e_g [0:MS-1]; reg [1025:0] e_w [0:MS-1];
    initial for (i = 0; i < MT; i = i + 1) begin e_tc[i] = 0; e_dn[i] = 0; e_su_row[i] = -1; end
    initial for (i = 0; i < MS; i = i + 1) begin e_q[i] = 0; e_g[i] = 0; e_w[i] = 0; end
    function integer x43_serial(input integer s);  // stream sample edge s -> serial edge of the x43 output register
        integer n, e; begin n = s % 4; e = s / 4;
            x43_serial = (n == 0) ? 3 * e + 2 : (n == 2) ? 3 * (e + 1) : (n == 3) ? 3 * (e + 1) + 1 : -1; end
    endfunction
    // engine command: drive for sample edge E (the caller is right after edge E-1)
    function [84:0] mkcmd(input [2:0] code, input [20:0] op, input [6:0] row);
        mkcmd = {1'b1, 1'b0, 10'd37, 21'd5000 + 21'(row), 21'd77, code, op, row};
    endfunction
    integer cmd_row = 0;
    task issue(input [2:0] code, input [20:0] op);
        begin c_cmd = mkcmd(code, op, 7'(cmd_row)); e_dn[tk + 1 + 7] = {1'b1, 1'b0, 7'(cmd_row)}; cmd_row = cmd_row + 1; end
    endtask
    task stream(input integer dest, input integer base, input integer n);
        integer k, I, E; reg [511:0] d;
        begin
            E = tk + 1;
            issue(3'd4, {1'b0, 1'(dest), 14'(base), 5'(n - 1)});
            I = E + 3;
            for (k = 0; k < n; k = k + 1) begin
                while (I % 4 == ((2-READ_PIPE)%4+4)%4) I = I + 1;
                d = mem[base + k];
                if (dest == 0) e_q[x43_serial(I + 15+READ_PIPE)] = {d, 1'b1};
                else e_g[x43_serial(I + 15+READ_PIPE)] = {d[510:0], 1'b1};
                I = I + 1;
            end
        end
    endtask
    // ---------------------------------------------------------------- stream program
    integer cl_next = 2048, cl_beats = 0, gph = 0, xgo_at [0:7], cap_on = 0;
    reg [9:0] gphase [0:3];
    always @(posedge t_ck) if (rss && bench_active) begin : prog integer k, r, b; reg [3:0] m; reg [2047:0] dd;
        tk = tk + 1;
        #10;
        c_cmd = 0; su_wqv = 0; su_rqv = 0; fcol = 0; crq = 0; xgo = 0;
        // S: SU writes 1024..1279, 16 an edge (distinct banks), then the gather phase-word rows
        if (tk >= 10 && tk < 26) begin
            for (k = 0; k < 16; k = k + 1) begin
                r = 1024 + 16 * (tk - 10) + k;
                su_wqv[k] = 1'b1; su_wq[14*k +: 14] = 14'(r); su_wqm[16*k +: 16] = 16'hffff; su_wqd[512*k +: 512] = rowdata(r, 0);
                mem[r] = rowdata(r, 0); memv[r] = 1;
            end
        end
        // Seed the complete capture destination, so partial writes must preserve untouched words.
        if (tk >= 150 && tk < 154) begin
            for (k = 0; k < 16; k = k + 1) begin
                r = 6144 + 16 * (tk - 150) + k;
                su_wqv[k] = 1'b1; su_wq[14*k +: 14] = 14'(r); su_wqm[16*k +: 16] = 16'hffff; su_wqd[512*k +: 512] = rowdata(r, 9);
                mem[r] = rowdata(r, 9); memv[r] = 1;
            end
        end
        if (tk == 30) for (k = 0; k < 4; k = k + 1) begin
            r = 3000 + k; gphase[k] = 10'(100 + 7 * k);
            dd[511:0] = rowdata(r, 1); dd[1:0] = 2'd0; dd[58:49] = gphase[k];
            su_wqv[k] = 1'b1; su_wq[14*k +: 14] = 14'(r); su_wqm[16*k +: 16] = 16'hffff; su_wqd[512*k +: 512] = dd[511:0];
            mem[r] = dd[511:0]; memv[r] = 1;
        end
        // Four direct compiler-addressed row tuples. Sparse masks exercise every physical source.
        if (tk >= 50 && tk < 90) begin
            m = 4'(1 + urand(15)); if (tk == 50) m = 4'b1010;
            for (k = 0; k < 4; k = k + 1) if (m[k]) begin
                r = 2048 + 4 * (tk - 50) + k;
                fcol[551*k +: 551] = {8'd0, rowdata(r, 2), 16'hffff, 14'(r), 1'b1};
                mem[r] = rowdata(r, 2); memv[r] = 1; n_cl = n_cl + 1;
            end
        end
        if (tk >= 300 && tk < 332) begin
            r = 1024 + tk - 300; crq = {14'(r), 1'b1};
            e_tc[tk + 1 + 12+READ_PIPE] = {mem[r], 1'b1};
        end
        // Invalid STREAM destination is a schedule-fault witness.
        if (mode == 1 && tk == 360) issue(3'd4, {2'd2, 14'd1024, 5'd0});
        // Unsupported collective LARM7 must fault rather than silently preserve credits.
        if (mode == 4 && tk == 380) issue(3'd6, {4'd7, 17'd0});
        if (tk == 100) issue(3'd6, {4'd5, 3'd0, 14'd7000});
        if (tk == 110) issue(3'd6, {4'd6, 3'd0, 14'd7200});
        if (tk == 120) issue(3'd6, {4'd0, 3'd0, 14'd7400});
        // Q / G streams
        if (tk == 420) stream(0, 1088, 20);
        if (mode == 3 && tk >= 420 && tk < 470) qsws = 3'b010; else qsws = 3'b011;
        if (tk == 480) stream(1, 3000, 4);
        if (mode == 5 && tk == 520) begin                                  // two units, same lane, same edge
            stream(0, 1100, 2);
        end
        // READ_PIPE 2 blocks issue phase 0 instead of 1, which shifts Q's rows one edge: G then starts on Q's lane.
        if (mode == 5 && tk == 521) stream(1, (READ_PIPE == 2) ? 1100 : 1101, 2);
        // gather go: the bench (gather) pulses xgo for each posted phase, in order, ~60 edges after the post
        if (tk >= 560 && tk < 564) begin xgo = {1'b1, gphase[tk - 560]}; if (mode == 2 && tk == 562) xgo[0] = ~xgo[0]; end
        // R: SU read-back of the collective landing rows (one a stream edge, port 4 + row[1:0])
        if (tk >= 600 && tk < 600 + 160) begin
            r = 2048 + (tk - 600);
            if (memv[r]) begin
                su_rqv[4 + r % 4] = 1'b1; su_rq[14*(4 + r % 4) +: 14] = 14'(r); e_su_row[tk + 1 + 12+READ_PIPE] = r;
            end
        end
        if (tk >= 2100 && tk < 2116) begin
            k = tk - 2100;
            r = (k < 4) ? 7000 + k : (k < 8) ? 7200 + k - 4 : 7400 + k - 8;
            su_rqv[4 + r % 4] = 1'b1; su_rq[14*(4 + r % 4) +: 14] = 14'(r); e_su_row[tk + 1 + 12+READ_PIPE] = r;
        end
        // R: SU read-back of the WFC rows and the capture rows (after both landed)
        if (tk >= 1800 && tk < 1800 + 64) begin
            r = 4096 + (tk - 1800);
            su_rqv[4 + r % 4] = 1'b1; su_rq[14*(4 + r % 4) +: 14] = 14'(r); e_su_row[tk + 1 + 12+READ_PIPE] = r;
        end
        if (tk >= 1900 && tk < 1900 + 64) begin
            r = 6144 + (tk - 1900);
            if (memv[r]) begin su_rqv[4 + r % 4] = 1'b1; su_rq[14*(4 + r % 4) +: 14] = 14'(r); e_su_row[tk + 1 + 12+READ_PIPE] = r; end
        end
    end
    // ---------------------------------------------------------------- serial program (WFC kit, capture)
    integer wfc_w = 0, wfc_r = 0;
    always @(posedge s_ck) if (rst && bench_active) begin : sprog integer r, k, j, el, w; reg [50:0] e;
        sk = sk + 1;
        #10;
        fwfc = 0; fcap = 0; sel = 0; col = 0; asw = 0;
        // W: 64 writes rows 4096.. (one a serial cycle) + the START doorbell, then 32 read pairs
        if (sk >= 60 && sk < 124) begin
            r = 4096 + (sk - 60);
            fwfc[0] = 1'b1; fwfc[527:513] = 15'(r); fwfc[512:1] = rowdata(r, 4); mem[r] = rowdata(r, 4); memv[r] = 1;
            if (mode == 6 && sk == 70) fwfc[527:513] = 15'h5000;
        end
        if (sk == 124) begin fwfc[0] = 1'b1; fwfc[527:513] = 15'h7fff; fwfc[512:1] = 512'h5eed; end
        if (sk >= 200 && sk < 232) begin
            r = 4096 + 2 * (sk - 200);
            fwfc[528] = 1'b1; fwfc[543:529] = 15'(r); fwfc[558:544] = 15'(r + 1); fwfc[559] = 1'b1;
            if (mode == 7 && sk == 210) fwfc[558:544] = 15'(r + 4);
            e_w[sk + 1 + 15+3*((READ_PIPE+3)/4)] = {1'b1, mem[r + 1], 1'b1, mem[r]};
        end
        if (sk >= 130 && sk < 134) begin
            r = 7000 + sk - 130; sel = {1'b0, 1'b1, rowdata(r, 6), 1'b1}; mem[r] = rowdata(r, 6); memv[r] = 1;
        end
        if (sk >= 140 && sk < 144) begin
            r = 7200 + sk - 140; col = {1'b0, 1'b1, rowdata(r, 7), 1'b1}; mem[r] = rowdata(r, 7); memv[r] = 1;
        end
        if (sk >= 150 && sk < 154) begin
            r = 7400 + 2 * (sk - 150); asw = {1'b0, 1'b1, rowdata(r + 1, 8), rowdata(r, 8), 1'b1};
            mem[r] = rowdata(r, 8); mem[r + 1] = rowdata(r + 1, 8); memv[r] = 1; memv[r + 1] = 1;
        end
        // K: capture phase through f_capture: obase word 98304 (row 6144), 3 full rounds + 40 elements, every root
        // two elements a serial cycle (row0 then row1), status live / drained
        if (sk >= 300 && sk < 304) begin
            for (r = 0; r < 128; r = r + 1) for (k = 0; k < 2; k = k + 1) begin
                el = 256 * (sk - 300) + 2 * r + k;             // element index (round sk-300, root r, slot k)
                if (sk - 300 < 3 || el - 256 * 3 < 40) begin
                    w = 98304 + el;
                    e = {value(w / 16, w % 16, 5), 19'(w)};
                    if (mode == 8 && r == 5 && k == 1 && sk == 301) e[3] = ~e[3];
                    fcap[104 * r + 52 * k] = 1'b1; fcap[104 * r + 52 * k + 1 +: 51] = e;
                    if (!memv[w / 16]) mem[w / 16] = 0;
                    mem[w / 16][32 * (w % 16) +: 32] = value(w / 16, w % 16, 5); memv[w / 16] = 1;
                end
            end
        end
        fcap[13312] = (sk >= 299 && sk < 306);              // live
        fcap[13314] = (sk >= 310 && sk < 320);              // drained
    end
    // ---------------------------------------------------------------- checks
    integer done_seen = 0, fault_at = -1;
    always @(posedge t_ck) if (rss && bench_active) begin : tchk integer p, r;
        #20;
        if (tk >= 0 && tk < MT) begin
            if (c_done !== e_dn[tk]) begin bad = bad + 1; if (bad < 12) $display("DONE MISMATCH tk %0d got %h exp %h", tk, c_done, e_dn[tk]); end
            if (c_done[8]) n_done = n_done + 1;
            if (mode == 0 && (crs[0] !== e_tc[tk][0] || (crs[0] && crs !== e_tc[tk]))) begin bad = bad + 1; if (bad < 12) $display("T_COLLECTIVE MISMATCH tk %0d got v%b t%0d exp v%b t%0d", tk, crs[0], crs[2:1], e_tc[tk][0], e_tc[tk][2:1]); end
            if (crs[0]) n_rec = n_rec + 1;
            r = e_su_row[tk];
            for (p = 0; p < 16; p = p + 1) if (su_rsv[p] !== (r >= 0 && p == 4 + r % 4)) begin bad = bad + 1; if (bad < 12) $display("SU RSV MISMATCH tk %0d port %0d", tk, p); end
            if (r >= 0 && mode != 1 && mode != 8) begin
                n_su = n_su + 1;
                if (su_rs[512 * (4 + r % 4) +: 512] !== mem[r]) begin bad = bad + 1; if (bad < 12) $display("SU DATA MISMATCH tk %0d row %0d", tk, r); end
            end
        end
        if (hc_rsv !== 0 || pq_o[0] !== 0) begin bad = bad + 1; if (bad < 12) $display("UNEXPECTED IDLE RETURN tk %0d", tk); end
        if (c_st[0] && fault_at < 0) fault_at = tk;
    end
    always @(posedge s_ck) if (rst && bench_active) begin : schk
        #20;
        if (sk >= 0 && sk < MS) begin
            if (mode == 0 && (qsw[0] !== e_q[sk][0] || (qsw[0] && qsw !== e_q[sk]))) begin bad = bad + 1; if (bad < 12) $display("QSW MISMATCH sk %0d got v%b exp v%b", sk, qsw[0], e_q[sk][0]); end
            if (qsw[0]) n_q = n_q + 1;
            if (mode == 0 && (tgat[0] !== e_g[sk][0] || (tgat[0] && tgat !== e_g[sk]))) begin bad = bad + 1; if (bad < 12) $display("T_GATHER MISMATCH sk %0d got v%b exp v%b", sk, tgat[0], e_g[sk][0]); end
            if (tgat[0]) n_g = n_g + 1;
            if (mode == 0 && twfc[1027:2] !== e_w[sk]) begin bad = bad + 1; if (bad < 12) $display("T_SRQ MISMATCH sk %0d got v%b%b exp v%b%b", sk, twfc[1027], twfc[514], e_w[sk][1025], e_w[sk][512]); end
            if (twfc[514]) n_w = n_w + 1;
            if (sk > 4 && (twfc[0] !== 1'b1 || twfc[1] !== 1'b1)) begin bad = bad + 1; if (bad < 12) $display("WFC GRANT LOW sk %0d", sk); end
        end
    end
    // ---------------------------------------------------------------- run
    initial begin
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        // Exercise a real reset edge after the native BAL clock gate has opened.
        // A time-zero low reset alone leaves the gated core without a clock or
        // falling reset edge in a two-state simulator. Keep the release epoch.
        #3337; rst = 0; rss = 0;
        #(3336 * 3 - 101); rst = 1; rss = 1; bench_active = 1;
        #(3336 * 600);
        if (mode == 0) begin
            if (c_st[0] || twfc[1028]) begin bad = bad + 1; $display("UNEXPECTED FAULT c_st %b t_err %b xio %b wfc %b cap %b", c_st, twfc[1028], dut.xio_f, dut.u_wfc.fault, dut.u_cap.fault); end
            $display("TB_SPVM RESULT mode 0 records %0d qSW %0d gather %0d wfc_rd %0d su_rd %0d cl_rows %0d dones %0d bad %0d",
                     n_rec, n_q, n_g, n_w, n_su, n_cl, n_done, bad);
            $display("TB_SPVM %s mode 0", (bad == 0 && n_rec == 32 && n_q == 20 && n_g == 4 && n_w == 32 && n_su == n_cl + 144 && n_done == 5) ? "PASS" : "FAIL");
        end else begin : fw reg ok;
            ok = 1'b0;
            case (mode)
                1: ok = dut.u_xio.f_iss[2];
                2: ok = dut.u_xio.f9;
                3: ok = dut.u_xio.f_s[0];
                4: ok = dut.u_xio.f_iss[2];
                5: ok = dut.u_xio.f_iss[1];
                6: ok = dut.u_wfc.err && twfc[1028];
                7: ok = dut.u_wfc.err && twfc[1028];
                8: ok = |dut.u_cap.lf;
                default: ok = 1'b0;
            endcase
            $display("TB_SPVM %s mode %0d (witness %b, c_st %b at tk %0d)", (ok && c_st[0]) ? "PASS" : "FAIL", mode, ok, c_st, fault_at);
        end
        $finish;
    end
endmodule
