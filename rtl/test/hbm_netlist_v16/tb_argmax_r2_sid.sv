`timescale 1ns/1ps
`default_nettype none
// HBM-BIND B2 (lane hbm-bind-idx 2026-10-24): ot_hbm_argmax_static_sw_vm_r2 SID strap lockstep bench.
//   S 0: DUT at the default strap vs REF = the UNCHANGED as-built r18h5 master (source d34578d6f, renamed *_ref).
//   S 3: DUT #(.SID(3)) (the B2 NE-served engine) vs REF3 = the as-built text with its literal 'sid = 2'd0' set to 2'd3.
//   DIE 1: TP 192, VMX 89, ACK 52 (the r18h5 hb_argmax instance); DIE 0: TP 192 and the module defaults.
//   SIDMUT (define): the DUT is built with SID 0 against REF3 (the as-built SW strap left on a B2 die) -> must FAIL.
// Every output (vm_rq, cq, cq_seq, busy, done, fault, nan_flag) compared EVERY edge (!==). Stimulus: go every ~150 edges
// (also while busy), descriptors with VM / STREAM mode, mirror, a / o sectors = the strap (60 %), 0 (20 %) or random,
// n 1..40, o_is 0..15 (some crossing a sector), random die_id / imm_a; random vm_rr (lane valids + data) and hub acks
// every edge.
module tb_argmax_r2_sid;
`ifndef S
`define S 0
`endif
`ifndef DIE
`define DIE 0
`endif
`ifndef NCYC
`define NCYC 60000
`endif
    localparam integer VMX = `DIE ? 89 : 5, ACK = `DIE ? 52 : 13;
    localparam [1:0] SID = `S;
`ifdef SIDMUT
    localparam [1:0] DSID = 2'd0;
`else
    localparam [1:0] DSID = SID;
`endif
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg [7:0] die_id = 0; reg go = 0, mode = 0, a_mirror = 0; reg [17:0] imm_a = 0, a_base = 0, n = 0, o_base = 0; reg [15:0] o_is = 0;
    reg [263:0] vm_rr = 0; reg [273:0] cr = 0;
    wire [135:0] q0, q1; wire [337:0] c0, c1; wire [1:0] s0, s1; wire b0, b1, d0, d1, f0, f1, n0, n1;
`define APORTS .clk(clk), .rst_n(rst_n), .die_id(die_id), .go(go), .mode(mode), .imm_a(imm_a), .a_mirror(a_mirror), .a_base(a_base), \
        .n(n), .o_base(o_base), .o_is(o_is), .vm_rr(vm_rr), .cr(cr)
    generate if (`S == 0) begin : g_r0
        ot_hbm_argmax_static_sw_vm_r2_ref #(.TP(192), .VMX(VMX), .ACK(ACK)) ref_(`APORTS, .vm_rq(q0), .cq(c0), .cq_seq(s0),
            .busy(b0), .done(d0), .fault(f0), .nan_flag(n0));
    end else begin : g_r3
        ot_hbm_argmax_static_sw_vm_r2_ref3 #(.TP(192), .VMX(VMX), .ACK(ACK)) ref_(`APORTS, .vm_rq(q0), .cq(c0), .cq_seq(s0),
            .busy(b0), .done(d0), .fault(f0), .nan_flag(n0));
    end endgenerate
    ot_hbm_argmax_static_sw_vm_r2 #(.TP(192), .VMX(VMX), .ACK(ACK), .SID(DSID)) dut(`APORTS, .vm_rq(q1), .cq(c1), .cq_seq(s1),
        .busy(b1), .done(d1), .fault(f1), .nan_flag(n1));
    function automatic [1:0] pick(input integer r); pick = (r < 60) ? SID : (r < 80) ? 2'd0 : 2'($urandom); endfunction
    integer cyc = 0, chk = 0, errs = 0, ngo = 0, nbusy = 0, ndone = 0, nfault = 0, ncq = 0, w;
    always @(negedge clk) begin
        cyc = cyc + 1; go = 0;
        if (cyc == 10) rst_n = 1;
        if (rst_n && $urandom % 150 == 0) begin
            go = 1; ngo = ngo + 1; mode = ($urandom % 10 == 0); a_mirror = ($urandom % 5 == 0);
            a_base = {a_mirror ? 2'd0 : pick($urandom % 100), 16'($urandom % 60000)}; n = 18'(1 + $urandom % 40);
            o_base = {pick($urandom % 100), 16'(($urandom % 8 == 0) ? 16'hfff8 + $urandom % 8 : $urandom % 60000)};
            o_is = 16'($urandom % 16); imm_a = ($urandom % 50 == 0) ? 18'h3ffff : 18'($urandom % 40); die_id = $urandom;
        end
        for (w = 0; w < 8; w = w + 1) vm_rr[32*w +: 32] = $urandom;
        vm_rr[263:256] = ($urandom % 2) ? 8'(1 << ($urandom % 8)) : 8'($urandom);
        for (w = 0; w < 8; w = w + 1) cr[32*w +: 32] = $urandom;
        cr[273:256] = $urandom;
        if (cyc == `NCYC) begin
            $display("ARGMAX_R2_SID S=%0d DIE=%0d DSID=%0d checks=%0d go=%0d busy_edges=%0d done=%0d fault=%0d cq_v=%0d errors=%0d",
                `S, `DIE, DSID, chk, ngo, nbusy, ndone, nfault, ncq, errs);
            $display("ARGMAX_R2_SID %s checks=%0d errors=%0d", (errs == 0 && chk > 0 && ndone + nfault > 0) ? "PASS" : "FAIL", chk, errs);
            $finish;
        end
    end
    always @(posedge clk) if (rst_n) begin
        chk = chk + 1; if (b0) nbusy = nbusy + 1; if (d0) ndone = ndone + 1; if (f0) nfault = nfault + 1; if (c0[337]) ncq = ncq + 1;
        if ({q0, c0, s0, b0, d0, f0, n0} !== {q1, c1, s1, b1, d1, f1, n1}) begin
            errs = errs + 1;
            if (errs <= 5) $display("MISMATCH cyc=%0d rq %b cq %b seq %b busy %b/%b done %b/%b fault %b/%b nan %b/%b", cyc,
                q0 !== q1, c0 !== c1, s0 !== s1, b0, b1, d0, d1, f0, f1, n0, n1);
        end
    end
endmodule
`default_nettype wire
