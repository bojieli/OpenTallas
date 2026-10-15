`timescale 1ps/1ps
// tb_dsfd_vm_static_cap (claude S81 VM owner r9, 2026-10-14): exact bench of the static capture face of the S81 VM
// (dsfd_vm_static_cap: pin register, 16 static lanes, 16 fixed-phase 3:4 transfers) at production shape (128 roots,
// f_capture 13,376 b).  The bench is the field: phases of N elements at obase (multiple of 256 words), element e at
// word obase + e from root (e mod 256) / 2, each root emitting its elements in order, 0..2 a serial cycle (row0 port
// first), roots throttled to stay within SKEW rounds of the slowest root of their lane (the compiled skew bound).
// Status: live while the phase runs, drained after its last element.  CHECKS every stream edge of all 16 sources:
//   * every full row is written exactly once, word-exact (16 words), on the ONE fixed edge: last element at the pin
//     on serial edge P -> stream edge of serial edge P + 2 through the 3:4 slot (x34: serial edge 3n + k -> stream 4n+2+k);
//   * every partial (last-round) row is written once with exactly its words (mask) after the drained event;
//   * nothing else is written; no fault.
// +mode 0 base; fault witnesses (the named fault must be raised): 1 alias (one root held back E rounds), 2 alignment,
// 3 range, 4 duplicate word, 5 capture status fault.  Mutant OT_VM_CAPL_MUT_WORD must FAIL mode 0.
module tb_dsfd_vm_static_cap;
    reg s_ck = 0, t_ck = 0, rst = 0, rss = 0;
    always #556 s_ck = ~s_ck;
    always #417 t_ck = ~t_ck;
    reg [13375:0] fc = 0;
    wire [15:0] w_v; wire [223:0] w_row; wire [255:0] w_m; wire [8191:0] w_d; wire fault;
    dsfd_vm_static_cap #(.E(8), .CAP_PIPE(1)) dut (.ck_control_s(s_ck), .rst_control_s(rst), .ck_lane_s({16{s_ck}}), .ck_x34_s({16{s_ck}}), .rst_x34_s({16{rst}}), .ck_x34_t({16{t_ck}}), .rss_x34_t({16{rss}}), .f_capture(fc),
        .w_v(w_v), .w_row(w_row), .w_m(w_m), .w_d(w_d), .fault(fault));
    integer mode = 0, seed = 1, bad = 0, sk = 0, tk = 0, rows_full = 0, rows_part = 0, got = 0, i, nph = 14, SKEW = 5;
    localparam integer MAXR = 16384;
    reg [15:0] exp_m [0:MAXR-1]; integer exp_t [0:MAXR-1]; reg seen [0:MAXR-1]; reg [15:0] cnt_m [0:MAXR-1];
    initial for (i = 0; i < MAXR; i = i + 1) begin exp_m[i] = 0; exp_t[i] = -1; seen[i] = 0; cnt_m[i] = 0; end
    function [31:0] val(input integer w); val = 32'(w * 2654435761 + 12345); endfunction
    integer rnd;
    function integer urand(input integer n); begin rnd = $random(seed); urand = (rnd < 0 ? -rnd : rnd) % n; end endfunction
    // per-root progress in the current phase
    integer nxt [0:127];                  // index of the root's next element (0, 1, 2, ... in the root's own order)
    integer N, obase;                     // phase length (elements), base word
    function integer root_count(input integer r);  // elements of root r in [0, N)
        integer full, rem; begin full = N / 256; rem = N % 256;
            root_count = 2 * full + ((rem > 2 * r + 1) ? 2 : (rem > 2 * r) ? 1 : 0); end
    endfunction
    function integer elem_of(input integer r, input integer k);  // word offset of the root's k-th element
        elem_of = 256 * (k / 2) + 2 * r + (k % 2);
    endfunction
    // stream-edge expectation: a row completed by the element presented before serial edge P is on the source
    // outputs after stream edge 4 n + 2 + k with 3 n + k = P + 2
    function integer t_of(input integer p); integer q; begin q = p + 3; t_of = 4 * (q / 3) + 2 + (q % 3); end endfunction
    // ---- field drive (serial)
    reg phase_live = 0, phase_drn = 0;
    integer ph = 0, wait_c = 0, slow, lane_min [0:15];
    always @(posedge s_ck) if (rst) begin : field integer r, g, k, nemit, w, row, ksl; reg [50:0] el;
        sk = sk + 1;
        #10;
        fc = 0;
        fc[13312] = phase_live; fc[13314] = phase_drn; fc[13315] = (mode == 5 && ph == 2);
        if (phase_live) begin
            for (g = 0; g < 16; g = g + 1) begin lane_min[g] = 1 << 30;
                for (r = 8 * g; r < 8 * g + 8; r = r + 1) if (nxt[r] < root_count(r) && nxt[r] / 2 < lane_min[g]) lane_min[g] = nxt[r] / 2; end
            for (r = 0; r < 128; r = r + 1) begin
                nemit = urand(3);
                if (mode == 1 && ph == 1 && r == 9 && nxt[r] < 2) nemit = (sk % 40 == 0) ? 1 : 0;   // root 9 held back
                for (k = 0; k < 2; k = k + 1) if (k < nemit && nxt[r] < root_count(r) &&
                        (nxt[r] / 2 < lane_min[r / 8] + SKEW || (mode == 1 && ph == 1))) begin
                    w = obase + elem_of(r, nxt[r]);
                    el = {val(w), 19'(w)};
                    if (mode == 2 && ph == 1 && r == 20 && nxt[r] == 3) el[1] = ~el[1];
                    if (mode == 3 && ph == 1 && r == 21 && nxt[r] == 3) el[18] = 1'b1;
                    fc[104 * r + 52 * k] = 1'b1; fc[104 * r + 52 * k + 1 +: 51] = el;
                    row = w / 16;
                    cnt_m[row][w % 16] = 1'b1;
                    if (cnt_m[row] == 16'hffff) exp_t[row] = t_of(sk); if (r < 8 && cnt_m[row] == 16'hffff && ph == 0) $display("TRACE DRIVE time=%0t Pdrive=%0d row=%0d",$time,sk,row);       // the row's last element: this pin edge sk
                    nxt[r] = nxt[r] + 1;
                    if (mode == 4 && ph == 1 && r == 30 && nxt[r] == 3) begin  // duplicate: re-send element 2 next cycle
                        nxt[r] = 2; cnt_m[row][w % 16] = 1'b0; exp_t[row] = -1; mode = 104;
                    end
                end
            end
            // phase end
            k = 1; for (r = 0; r < 128; r = r + 1) if (nxt[r] < root_count(r)) k = 0;
            if (k) begin phase_live = 0; wait_c = 3; end
        end else if (wait_c > 0) begin
            wait_c = wait_c - 1; if (wait_c == 0) begin phase_drn = 1; wait_c = -20; end
        end else if (wait_c < 0) begin
            wait_c = wait_c + 1; if (wait_c == -10) phase_drn = 0;
            if (wait_c == 0) begin                                   // next phase
                ph = ph + 1;
                if (ph < nph) begin
                    N = 256 * (2 + urand(10)) + ((ph % 2) ? urand(256) : 0);
                    obase = 256 * (ph * 12);
                    for (r = 0; r < 128; r = r + 1) nxt[r] = 0;
                    for (row = obase / 16; row < (obase + N + 15) / 16; row = row + 1) begin exp_m[row] = 0; end
                    for (w = obase; w < obase + N; w = w + 1) exp_m[w / 16][w % 16] = 1'b1;
                    phase_live = 1;
                end
            end
        end
    end
    // ---- checks (stream)
    always @(posedge t_ck) if (rss) begin : chk integer g, row, ww;
        tk = tk + 1;
        #20;
        for (g = 0; g < 16; g = g + 1) if (w_v[g]) begin
            row = w_row[14 * g +: 14]; got = got + 1;
            if (row % 16 != g || seen[row] || w_m[16 * g +: 16] !== exp_m[row]) begin
                bad = bad + 1; if (bad < 8) $display("ROW MISMATCH tk %0d lane %0d row %0d mask %h exp %h seen %0d", tk, g, row, w_m[16*g +: 16], exp_m[row], seen[row]);
            end
            for (ww = 0; ww < 16; ww = ww + 1) if (w_m[16 * g + ww] && w_d[512 * g + 32 * ww +: 32] !== val(16 * row + ww)) begin
                bad = bad + 1; if (bad < 8) $display("DATA MISMATCH row %0d word %0d", row, ww); end
            if (exp_m[row] == 16'hffff) begin
                rows_full = rows_full + 1;
                if (tk != exp_t[row] + 1) begin bad = bad + 1; if (bad < 8) $display("TIME MISMATCH row %0d tk %0d exp %0d", row, tk, exp_t[row] + 1); end
            end else rows_part = rows_part + 1;
            seen[row] = 1;
        end
    end
    initial begin : main integer r, row, w, miss;
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        for (r = 0; r < 128; r = r + 1) nxt[r] = 0;
        ph = 0; N = 256 * 5 + 77; obase = 0;
        for (w = obase; w < obase + N; w = w + 1) exp_m[w / 16][w % 16] = 1'b1;
        #(3336 * 4 - 100); rst = 1; rss = 1;
        #(3336 * 3); phase_live = 1;
        wait (ph >= nph || $time > 3336 * 20000);
        #(3336 * 20);
        miss = 0; for (row = 0; row < MAXR; row = row + 1) if (exp_m[row] != 0 && !seen[row]) miss = miss + 1;
        if (mode == 0) begin
            if (fault) begin bad = bad + 1; $display("UNEXPECTED FAULT lanes %h", dut.lf); end
            $display("TB_VMCAP RESULT mode 0 phases %0d rows full %0d partial %0d missing %0d bad %0d", ph, rows_full, rows_part, miss, bad);
            $display("TB_VMCAP %s mode 0", (bad == 0 && miss == 0 && rows_full > 1000 && rows_part >= 6) ? "PASS" : "FAIL");
        end else begin : fw reg ok; integer g;
            ok = 1'b0;
            for (g = 0; g < 16; g = g + 1) begin
                if (mode == 1 && dut.lf[5 * g + 2]) ok = 1'b1;
                if (mode == 2 && dut.lf[5 * g + 1]) ok = 1'b1;
                if (mode == 3 && dut.lf[5 * g + 0]) ok = 1'b1;
                if (mode == 104 && dut.lf[5 * g + 3]) ok = 1'b1;
            end
            if (mode == 5 && dut.s_flt) ok = 1'b1;
            $display("TB_VMCAP %s mode %0d (fault %b lanes %h)", ok ? "PASS" : "FAIL", mode == 104 ? 4 : mode, fault, dut.lf);
        end
        $finish;
    end

 always @(posedge s_ck) if (rst) begin : trace_s
 integer r; reg [50:0] el;
 for(r=0;r<8;r=r+1) begin
 if(fc[104*r]) begin el=fc[104*r+1+:51]; if(el[17:4]<256) $display("TRACE SAMPLE time=%0t row=%0d word=%0d",$time,el[17:4],el[3:0]); end
 if(fc[104*r+52]) begin el=fc[104*r+53+:51]; if(el[17:4]<256) $display("TRACE SAMPLE time=%0t row=%0d word=%0d",$time,el[17:4],el[3:0]); end
 end
 if(dut.lane[0].ov && dut.lane[0].om==16'hffff && dut.lane[0].orow<256)
 $display("TRACE BANK_WRITE time=%0t row=%0d bank=%0d",$time,dut.lane[0].orow,(dut.lane[0].u_x.sp==2 ? 0 : dut.lane[0].u_x.sp+1));
 #1;if(dut.lane[0].ov && dut.lane[0].om==16'hffff && dut.lane[0].orow<256)
 $display("TRACE LEAF_POST time=%0t row=%0d sk=%0d",$time,dut.lane[0].orow,sk);
 end
 always @(posedge t_ck) if(rss)begin
 #1;if(w_v[0] && w_m[15:0]==16'hffff && w_row[13:0]<256)
 $display("TRACE STREAM_POST time=%0t row=%0d tk=%0d",$time,w_row[13:0],tk);
 end

endmodule
