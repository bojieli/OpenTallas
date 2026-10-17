`timescale 1ps/1ps
// tb_dsfd_capt_x8_x43 (claude S-VM-CAPT-X8, 2026-10-16): the static capture data half (dsfd_capt_x8_data_e = leaves
// dsfd_capt_x8x_t_e + dsfd_capt_x8x_s_e) against the old dynamic one (dsfd_capt_x8_data: 8 x dsfd_capt_row_local, hold
// queue + ot_ratio_cdc_fifo) on the SAME f_w stimulus.  Clocks from one epoch: stream 834 ps, serial 1112 ps
// (4 x 834 = 3 x 1112), released per the startup contract (both resets just before epoch edge 0).
// Stimulus per row: full-rate bursts (a word on every stream edge), random density, sparse, idle.
// Checks per row: NEW output word sequence == input sequence (content + order, nothing dropped or duplicated) ==
// OLD output sequence; NEW latency (input sample edge -> t_vm serial edge) is a constant per sample index n; reports
// both latency distributions per n.  No fault in mode 0.
// +mode=1: rsv released one serial cycle late; +mode=2: rst released one stream cycle late; +mode=3: rsv one epoch
// late.  Modes 1..3 require t_ho (sticky slip fault).
module tb_dsfd_capt_x8_x43;
    reg ck = 0, ckv = 0, rst = 0, rsv = 0;
    always #417 ck = ~ck;
    always #556 ckv = ~ckv;
    reg [415:0] f_w = 0;
    wire [831:0] vm_n, vm_o; wire ho_n, ho_o;
    dsfd_capt_x8_data_e u_new (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_w(f_w), .t_vm(vm_n), .t_ho(ho_n));
    dsfd_capt_x8_data   u_old (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_w(f_w), .t_vm(vm_o), .t_ho(ho_o));
    integer mode = 0, seed = 7, tk = -1, i, r, n, bad = 0, words = 0;
    integer live = 0;                                   // stream edges since the first counted edge
    // per row queues: input (word, time, index), new output, old output
    reg [50:0] iq [0:7][$]; time it [0:7][$]; integer ix [0:7][$];
    reg [50:0] nq [0:7][$]; time nt [0:7][$];
    reg [50:0] oq [0:7][$]; time ot [0:7][$];
    time lmin_n [0:3], lmax_n [0:3], lmin_o [0:3], lmax_o [0:3];
    initial for (i = 0; i < 4; i = i + 1) begin lmin_n[i] = 1e9; lmax_n[i] = 0; lmin_o[i] = 1e9; lmax_o[i] = 0; end
    reg [50:0] cnt [0:7];
    initial for (i = 0; i < 8; i = i + 1) cnt[i] = 51'(i) << 40;
    integer phase_kind = 0; reg v; time ln, lo;
    // stream driver: the word presented now is sampled at the NEXT posedge ck
    always @(posedge ck) begin
        if (rst) begin
            tk = tk + 1;                                 // tk = index of this edge since release
            for (r = 0; r < 8; r = r + 1) if (f_w[52 * r]) begin
                iq[r].push_back(f_w[52 * r + 1 +: 51]); it[r].push_back($time); ix[r].push_back((tk - 4) & 3); words = words + 1;
            end
        end
        #10;
        phase_kind = (tk / 200) % 4;                     // 0 full rate, 1 random 50 %, 2 sparse 10 %, 3 random 80 %
        for (r = 0; r < 8; r = r + 1) begin
            v = (tk > 40 && tk < 4400) && (phase_kind == 0 ? 1'b1 : phase_kind == 1 ? ($random(seed) & 1) :
                 phase_kind == 2 ? (($random(seed) % 10) == 0) : (($random(seed) % 5) != 0));
            f_w[52 * r] = v;
            f_w[52 * r + 1 +: 51] = v ? cnt[r] : 51'($random(seed));
            if (v) cnt[r] = cnt[r] + 1;
        end
    end
    always @(posedge ckv) if (rsv) begin
        #20;
        for (r = 0; r < 8; r = r + 1) begin
            if (vm_n[104 * r])      begin nq[r].push_back(vm_n[104 * r + 1 +: 51]);  nt[r].push_back($time - 20); end
            if (vm_n[104 * r + 52]) begin nq[r].push_back(vm_n[104 * r + 53 +: 51]); nt[r].push_back($time - 20); end
            if (vm_o[104 * r])      begin oq[r].push_back(vm_o[104 * r + 1 +: 51]);  ot[r].push_back($time - 20); end
            if (vm_o[104 * r + 52]) begin oq[r].push_back(vm_o[104 * r + 53 +: 51]); ot[r].push_back($time - 20); end
        end
    end
    initial begin
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        #(3336 * 4 - 100);
        rst = (mode == 2) ? 0 : 1; rsv = (mode == 1 || mode == 3) ? 0 : 1;
        if (mode == 1) begin #(1112); rsv = 1; end
        if (mode == 2) begin #(834); rst = 1; end
        if (mode == 3) begin #(3336); rsv = 1; end
        #(834 * 4600);
        if (mode != 0) begin
            $display("TB_CAPX43 %s mode %0d (t_ho %b)", ho_n ? "PASS" : "FAIL", mode, ho_n);
        end else begin
        for (r = 0; r < 8; r = r + 1) begin
            if (nq[r].size() != iq[r].size() || oq[r].size() != iq[r].size()) begin
                bad = bad + 1; $display("COUNT row %0d in %0d new %0d old %0d", r, iq[r].size(), nq[r].size(), oq[r].size());
            end else for (i = 0; i < iq[r].size(); i = i + 1) begin
                n = ix[r][i];
                if (nq[r][i] !== iq[r][i] || oq[r][i] !== iq[r][i]) begin
                    bad = bad + 1; if (bad < 6) $display("WORD row %0d #%0d in %h new %h old %h", r, i, iq[r][i], nq[r][i], oq[r][i]);
                end
                ln = nt[r][i] - it[r][i]; lo = ot[r][i] - it[r][i];
                if (ln < lmin_n[n]) lmin_n[n] = ln; if (ln > lmax_n[n]) lmax_n[n] = ln;
                if (lo < lmin_o[n]) lmin_o[n] = lo; if (lo > lmax_o[n]) lmax_o[n] = lo;
            end
        end
        for (n = 0; n < 4; n = n + 1) begin
            $display("LAT n=%0d new %0d..%0d ps  old %0d..%0d ps", n, lmin_n[n], lmax_n[n], lmin_o[n], lmax_o[n]);
            if (lmin_n[n] != lmax_n[n]) begin bad = bad + 1; $display("NEW latency not fixed at n=%0d", n); end
        end
        if (ho_n) begin bad = bad + 1; $display("UNEXPECTED t_ho"); end
        $display("TB_CAPX43 RESULT mode 0 words %0d bad %0d old_hovf %b", words, bad, ho_o);
        $display("TB_CAPX43 %s mode 0", (bad == 0 && words > 20000) ? "PASS" : "FAIL");
        end
        $finish;
    end
endmodule
