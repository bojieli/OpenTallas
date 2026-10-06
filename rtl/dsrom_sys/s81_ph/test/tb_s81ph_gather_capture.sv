`timescale 1ns/1ps
// tb_s81ph_gather_capture (CLAUDE S81-PH): exact lockstep of the S81 die return chain dsfd_sp_gather ->
// dsfd_sp_capture (serial-domain VM writes) against the reference = 128 ot_v41_ret_root (D = QD = 128, the field's
// region roots) + ot_dsrom_rd64_vm_capture (ENABLE, CAPACITY 1, VM_AW 19, ALWAYS_ACCEPT; S81 profile quota), wired as
// rtl/dsrom_sys/s81_capture_parent/ot_v41_spine_w17w10.sv.  Same partials on the same stream cycles; compares every
// root's ordered (addr, data) VM write sequence, totals, final drained and fault; reports per-phase completion delay.
// +STIM=<file> (tools: gen_stim.py).  ck : ckv = 4 : 3 (1.2 / 0.9 GHz, related, as the die PLL).
module tb_s81ph_gather_capture;
    localparam integer NR = 128;
    reg ck = 0, ckv = 0;
    always #3 ck = ~ck;     // period 6
    always #4 ckv = ~ckv;   // period 8
    reg rst = 0, rsv = 0;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    // ---------------- stimulus registers (driven at negedge ck)
    reg [NR-1:0] s_v; reg [31:0] s_t [0:NR-1]; reg [31:0] s_d [0:NR-1]; reg [NR-1:0] s_e, s_b;
    // ---------------- reference
    wire [NR-1:0] rr_v, rr_e, rr_f;
    wire [NR*16-1:0] rr_row, rr_bf; wire [NR*3-1:0] rr_pos; wire [NR*32-1:0] rr_fp;
    reg rst_n_ref = 0;
    genvar g;
    generate for (g = 0; g < NR; g = g + 1) begin : g_ref
        ot_v41_ret_root #(.D(128), .QD(128)) u_root (.clk(ck), .rst_n(rst_n_ref), .i_v(s_v[g]), .i_t(s_t[g]), .i_d(s_d[g]),
            .i_e(s_e[g]), .r_v(rr_v[g]), .r_row(rr_row[16*g +: 16]), .r_pos(rr_pos[3*g +: 3]), .r_fp32(rr_fp[32*g +: 32]),
            .r_bf16(rr_bf[16*g +: 16]), .r_e(rr_e[g]), .fault(rr_f[g]));
    end endgenerate
    reg p_v = 0, rreq = 0;
    reg [46:0] p_id; reg [9:0] p_ph; reg [29:0] p_ob, p_ops; reg [2:0] p_np; reg [1:0] p_fmt; reg [15:0] p_rs, p_rows;
    reg p_lo, p_hi;
    wire [128*19-1:0] quota;
    ot_dsrom_s81_phase_capture_profile #(.ENABLE(1)) u_prof (.phase_rows(p_rows), .phase_np(p_np), .root_returns(quota));
    wire [NR-1:0] rv_valid; wire [NR*30-1:0] rv_addr; wire [NR*32-1:0] rv_data;
    wire r_ready, r_live, r_idle, r_drained, r_fault;
    ot_dsrom_rd64_vm_capture #(.ENABLE(1), .ROOTS(NR), .CAPACITY(1), .VM_AW(19), .VM_ALWAYS_ACCEPT(1)) u_rc (
        .clk(ck), .rst_n(rst_n_ref), .reset_request(rreq), .phase_valid(p_v), .phase_ready(r_ready),
        .phase_identity(p_id), .phase_id(p_ph), .phase_root_rows(quota), .phase_obase(p_ob), .phase_ops(p_ops),
        .phase_np(p_np), .phase_fmt(p_fmt), .phase_rsplit(p_rs), .phase_fp32_low(p_lo), .phase_fp32_high(p_hi),
        .r_valid(rr_v), .r_error(rr_e), .r_row(rr_row), .r_bf16(rr_bf), .r_pos(rr_pos), .r_fp32(rr_fp),
        .vm_valid(rv_valid), .vm_accept(rv_valid), .vm_addr(rv_addr), .vm_data(rv_data), .vm_row(), .vm_pos(),
        .held_identity(), .held_phase(), .phase_live(r_live), .phase_idle(r_idle), .phase_drained(r_drained),
        .fault(r_fault));
    wire ref_fault = r_fault | (|rr_f);
    // ---------------- DUT
    localparam integer NC [0:5] = '{10, 11, 11, 11, 11, 10};
    reg [760:0] tp [0:11];
    reg [511:0] f_vm = 0;
    wire [6946:0] tcap; wire [13375:0] tvm;
    dsfd_sp_gather u_g (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_vm(f_vm), .t_capture(tcap),
        .rW0(tp[0][691:0]), .rW1(tp[1][760:0]), .rW2(tp[2][760:0]), .rW3(tp[3][760:0]), .rW4(tp[4][760:0]), .rW5(tp[5][691:0]),
        .rE0(tp[6][691:0]), .rE1(tp[7][760:0]), .rE2(tp[8][760:0]), .rE3(tp[9][760:0]), .rE4(tp[10][760:0]), .rE5(tp[11][691:0]));
    dsfd_sp_capture u_c (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_gather(tcap), .t_vm(tvm));
    wire [63:0] dst = tvm[13312 +: 64];
    function automatic integer port_of(input integer r);
        integer h, t, b;
        begin h = r / 64; b = h * 64; port_of = -1;
            for (t = 0; t < 6; t = t + 1) begin if (port_of < 0 && r < b + NC[t]) port_of = 6 * h + t; b = b + NC[t]; end end
    endfunction
    function automatic integer lane_of(input integer r);
        integer h, t, b;
        begin h = r / 64; b = h * 64; lane_of = -1;
            for (t = 0; t < 6; t = t + 1) begin if (lane_of < 0 && r < b + NC[t]) lane_of = NC[t] - 1 - (r - b); b = b + NC[t]; end end
    endfunction
    integer pi, li, rr;
    always @* begin
        for (pi = 0; pi < 12; pi = pi + 1) begin
            tp[pi] = 761'd0;
            tp[pi][69 * NC[pi % 6] +: 2] = 2'b01;           // {fault 0, live 1}
        end
        for (rr = 0; rr < NR; rr = rr + 1) begin
            pi = port_of(rr); li = lane_of(rr);
            tp[pi][69 * li] = s_v[rr];
            tp[pi][69 * li + 1 +: 68] = {1'b0, s_b[rr], s_e[rr], s_d[rr], s_t[rr], s_v[rr]};
        end
    end
    // ---------------- write collection
    reg [50:0] refq [0:NR-1][$];
    reg [50:0] dutq [0:NR-1][$];
    integer k;
    always @(posedge ck) for (k = 0; k < NR; k = k + 1) if (rv_valid[k]) refq[k].push_back({rv_data[32*k +: 32], rv_addr[30*k +: 19]});
    always @(posedge ckv) for (k = 0; k < NR; k = k + 1) begin
        if (tvm[104*k]) dutq[k].push_back(tvm[104*k + 1 +: 51]);
        if (tvm[104*k + 52]) dutq[k].push_back(tvm[104*k + 53 +: 51]);
    end
    // ---------------- driver
    integer fd, rc, gap, root, e_, n_ph, worst, maxd, t_issue, t_ref, t_dut, timeouts;
    reg [8*8-1:0] cmd; reg [63:0] a0, a1, a2, a3, a4, a5, a6, a7, a8, a9;
    reg [NR-1:0] n_v; reg [31:0] n_t [0:NR-1]; reg [31:0] n_d [0:NR-1]; reg [NR-1:0] n_e;
    string stim;
    // called at a negedge of ck: drives the accumulated set for exactly one cycle, returns at the next negedge
    task automatic flush; begin
        for (k = 0; k < NR; k = k + 1) begin s_v[k] = n_v[k]; s_t[k] = n_t[k]; s_d[k] = n_d[k]; s_e[k] = n_e[k]; s_b[k] = $random; end
        n_v = 0; n_e = 0;
        @(negedge ck); s_v = 0;
    end endtask
    task automatic idle(input integer n); integer j; begin for (j = 0; j < n; j = j + 1) @(negedge ck); end endtask
    initial begin
        s_v = 0; s_e = 0; s_b = 0; n_v = 0; n_e = 0; n_ph = 0; maxd = 0; timeouts = 0;
        for (k = 0; k < NR; k = k + 1) begin s_t[k] = 0; s_d[k] = 0; end
        p_id = 0; p_ph = 0; p_ob = 0; p_ops = 0; p_np = 0; p_fmt = 0; p_rs = 0; p_rows = 0; p_lo = 0; p_hi = 0;
        if (!$value$plusargs("STIM=%s", stim)) $fatal(1, "+STIM");
        fd = $fopen(stim, "r");
        idle(10); rst = 1; rsv = 1; rst_n_ref = 1; idle(60);
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%s", cmd);
            if (rc != 1) break;
            if (cmd == "P") begin
                rc = $fscanf(fd, "%h %h %h %h %h %h %h %h %h %h", a0, a1, a2, a3, a4, a5, a6, a7, a8, a9);
                // wait both idle
                k = 0; while (!(r_idle && dst[1] && !dst[0]) && k < 20000) begin @(negedge ck); k = k + 1; end
                p_rows = a0; p_np = a1; p_ob = a2; p_ops = a3; p_fmt = a4; p_rs = a5; p_lo = a6; p_hi = a7; p_id = a8; p_ph = a9;
                #1 if (!r_ready) $display("WARN ref not ready at phase %0d", a9);
                p_v = 1; @(negedge ck); p_v = 0; t_issue = cyc;
                @(negedge ckv);
                f_vm = 0; f_vm[0] = 1; f_vm[2:1] = 0; f_vm[159:1] = {1'b0, p_rows, p_hi, p_lo, p_rs, p_fmt, p_np, p_ops, p_ob, p_ph, p_id, 2'b00};
                @(negedge ckv); f_vm[0] = 0;
                idle(30);
            end else if (cmd == "C") begin
                rc = $fscanf(fd, "%h %h %h %h %h", a0, a1, a2, a3, a4);
                if (a0 != 0) begin flush; if (a0 > 1) idle(a0 - 1); end
                root = a1; n_v[root] = 1; n_t[root] = a2; n_d[root] = a3; n_e[root] = a4;
            end else if (cmd == "E") begin
                flush;
                k = 0; while (!(r_drained || ref_fault) && k < 50000) begin @(negedge ck); k = k + 1; end
                t_ref = cyc;
                k = 0; while (!(dst[0] || dst[3]) && k < 50000) begin @(negedge ck); k = k + 1; end
                k = 0; while (!(dst[2] || dst[3]) && k < 50000) begin @(negedge ck); k = k + 1; end
                if (k >= 50000) timeouts = timeouts + 1;
                t_dut = cyc;
                $display("PHASE %0d: ref done %0d cycles after issue, dut +%0d cycles", n_ph, t_ref - t_issue, t_dut - t_ref);
                if (t_dut - t_ref > maxd) maxd = t_dut - t_ref;
                n_ph = n_ph + 1;
            end else if (cmd == "R") begin
                rc = $fscanf(fd, "%h", a0);
                rreq = a0[0];
                @(negedge ckv); f_vm = 0; f_vm[0] = 1; f_vm[2:1] = 2'd1; f_vm[159] = a0[0]; @(negedge ckv); f_vm[0] = 0;
                idle(40);
            end
        end
        idle(200);
        begin : cmp
            // ORDERED (default): every root's write sequence equal.  +UNORD (pipelined root, ot_s81ph_ret_root_p):
            // every root's writes equal as a multiset (rows of one root may complete in another order: VM state is
            // the same, addresses within a phase are distinct); counts of roots whose order differs are reported.
            // Fault runs (ref_fault): fail closed = the DUT faults too and makes no write the reference does not make.
            integer bad, tot, tr, td, reord, extra, j, hit;
            reg unord;
            unord = $test$plusargs("UNORD");
            bad = 0; tot = 0; reord = 0; extra = 0;
            for (k = 0; k < NR; k = k + 1) begin
                tr = refq[k].size(); td = dutq[k].size(); tot = tot + tr;
                if (ref_fault && unord) begin
                    for (rr = 0; rr < td; rr = rr + 1) begin
                        hit = 0; for (j = 0; j < tr; j = j + 1) if (refq[k][j] == dutq[k][rr]) hit = 1;
                        if (!hit) begin extra = extra + 1; bad = bad + 1; if (bad < 6) $display("MISMATCH root %0d: dut write %h not made by ref", k, dutq[k][rr]); end
                    end
                end else if (tr != td) begin bad = bad + 1; if (bad < 6) $display("MISMATCH root %0d: ref %0d writes, dut %0d", k, tr, td); end
                else begin
                    for (rr = 0; rr < tr; rr = rr + 1) if (refq[k][rr] != dutq[k][rr]) begin
                        if (!unord) begin bad = bad + 1; if (bad < 6) $display("MISMATCH root %0d write %0d: ref %h dut %h", k, rr, refq[k][rr], dutq[k][rr]); end
                        else reord = reord + 1;
                        break; end
                    if (unord) begin
                        refq[k].sort(); dutq[k].sort();
                        for (rr = 0; rr < tr; rr = rr + 1) if (refq[k][rr] != dutq[k][rr]) begin
                            bad = bad + 1; if (bad < 6) $display("MISMATCH root %0d sorted write %0d: ref %h dut %h", k, rr, refq[k][rr], dutq[k][rr]); break; end
                    end
                end
            end
            if (unord) $display("UNORD reordered_roots=%0d fault_run_dut_writes_not_in_ref=%0d", reord, extra);
            $display("SUMMARY phases=%0d writes=%0d ref_fault=%0d dut_fault=%0d ref_drained=%0d dut_drained=%0d max_extra_cycles=%0d timeouts=%0d mismatching_roots=%0d",
                     n_ph, tot, ref_fault, dst[3], r_drained, dst[2], maxd, timeouts, bad);
            if (bad == 0 && ref_fault == dst[3] && timeouts == 0 && (ref_fault || r_drained == dst[2])) $display("RESULT PASS");
            else $display("RESULT FAIL");
        end
        $finish;
    end
endmodule
