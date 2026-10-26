`timescale 1ps/1ps
// tb_ot_s81_vm_x34 (claude S81 VM owner r8, 2026-10-14): exact bench of the fixed-phase 3:4 serial -> stream transfer.
// Clocks from one epoch: serial 1112 ps, stream 834 ps (3 x 1112 = 4 x 834 = 3336 ps).  Every serial cycle presents a
// word (random valid, counting data).  Every stream edge is checked: the word sampled at serial edge k of epoch n must
// be on o_v / o_d after stream edge 2 + k of epoch n, nothing on stream edge 1.  +mode 0 aligned (must PASS, no fault);
// +mode 1 stream reset released one stream cycle late (must raise the alignment fault); +mode 2 one serial cycle late.
module tb_ot_s81_vm_x34;
    localparam integer W = 64;
    parameter integer NAT = 0;   // NAT=1: captured stream side, every word one stream edge later (claude F2 1015)
    parameter integer BAL = 0;   // BAL=1: core/output flops behind a 4th register-enabled ICG (S-ELEM-A 1015)
    reg s_ck = 0, t_ck = 0, s_rn = 0, t_rn = 0;
    always #556 s_ck = ~s_ck;
    always #417 t_ck = ~t_ck;
    reg s_v = 0; reg [W-1:0] s_d = 0; wire o_v; wire [W-1:0] o_d; wire fault;
    ot_s81_vm_x34 #(.W(W), .NAT(NAT), .BAL(BAL)) u (.s_ck(s_ck), .s_rst_n(s_rn), .s_v(s_v), .s_d(s_d), .t_ck(t_ck), .t_rst_n(t_rn),
        .o_v(o_v), .o_d(o_d), .fault(fault));
    integer mode = 0, seed = 1, bad = 0, words = 0, got = 0, sk = 0, tk = 0, i;
    reg ev [0:4095]; reg [W-1:0] ed [0:4095];        // expected word for stream edge index
    initial for (i = 0; i < 4096; i = i + 1) ev[i] = 0;
    // serial edge index sk (0 = epoch 0 edge 0 at t = 3336 * E0), stream edge index tk likewise
    localparam integer E0 = 4;                         // reset released before epoch 4
    always @(posedge s_ck) if (s_rn) begin : sdrive integer kk, nn;
        // the word presented now (sampled at serial edge sk) -> stream edge 4 n + 2 + k (k = sk mod 3, n = sk / 3)
        kk = sk % 3; nn = sk / 3;
        ev[4 * nn + 2 + kk + NAT] = s_v; ed[4 * nn + 2 + kk + NAT] = s_d; if (s_v) words = words + 1;
        sk = sk + 1;
        #10 s_v = $random(seed); s_d = s_d + 1;
    end
    always @(posedge t_ck) if (t_rn) begin
        #20;  // after the edge: registered outputs settled
        if (tk > 8 && mode == 0) begin
            if (o_v !== ev[tk] || (o_v && o_d !== ed[tk])) begin bad = bad + 1; if (bad < 5) $display("MISMATCH tk %0d got %b %h exp %b %h", tk, o_v, o_d, ev[tk], ed[tk]); end
            if (o_v) got = got + 1;
        end
        tk = tk + 1;
    end
    initial begin
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        // release just before the epoch-E0 edges (both clocks rise together at multiples of 3336 ps)
        #(3336 * E0 - 100);
        s_rn = (mode == 2) ? 0 : 1; t_rn = (mode == 1) ? 0 : 1;
        if (mode == 1) begin #(834); t_rn = 1; end
        if (mode == 2) begin #(1112); s_rn = 1; end
        #(3336 * 900);
        if (mode == 0) begin
            if (fault) begin bad = bad + 1; $display("UNEXPECTED FAULT"); end
            $display("TB_X34 RESULT mode 0 words %0d got %0d bad %0d", words, got, bad);
            $display("TB_X34 %s mode 0", (bad == 0 && got > 1000) ? "PASS" : "FAIL");
        end else
            $display("TB_X34 %s mode %0d (alignment fault %b)", fault ? "PASS" : "FAIL", mode, fault);
        $finish;
    end
endmodule
