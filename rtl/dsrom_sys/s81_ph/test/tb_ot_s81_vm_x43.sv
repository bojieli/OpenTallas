`timescale 1ps/1ps
// tb_ot_s81_vm_x43 (claude S81 VM owner r9, 2026-10-14): exact bench of the fixed-phase 3:4 stream -> serial transfer.
// Clocks from one epoch: serial 1112 ps, stream 834 ps (3 x 1112 = 4 x 834).  Every stream sample index n = 0 / 2 / 3
// presents a word (random valid, counting data); n = 1 presents none.  Every serial edge is checked: the word sampled
// at stream edge n of epoch e must be on o_v / o_d after serial edge 2 (n = 0) of epoch e, edge 0 (n = 2) or 1 (n = 3)
// of epoch e + 1.  +mode 0 aligned (PASS, no fault); 1 stream reset one stream cycle late; 2 serial reset one serial
// cycle late (alignment fault required); 3 a valid word on sample index 1 (schedule fault required).
module tb_ot_s81_vm_x43;
    localparam integer W = 64;
    reg s_ck = 0, t_ck = 0, s_rn = 0, t_rn = 0;
    always #556 s_ck = ~s_ck;
    always #417 t_ck = ~t_ck;
    reg t_v = 0; reg [W-1:0] t_d = 0; wire o_v; wire [W-1:0] o_d; wire fault;
    ot_s81_vm_x43 #(.W(W)) u (.t_ck(t_ck), .t_rst_n(t_rn), .s_v(t_v), .s_d(t_d), .s_ck(s_ck), .s_rst_n(s_rn),
        .o_v(o_v), .o_d(o_d), .fault(fault));
    integer mode = 0, seed = 1, bad = 0, words = 0, got = 0, sk = 0, tk = 0, i;
    reg ev [0:4095]; reg [W-1:0] ed [0:4095];        // expected word per serial edge index
    initial for (i = 0; i < 4096; i = i + 1) ev[i] = 0;
    localparam integer E0 = 4;
    always @(posedge t_ck) if (t_rn) begin : tdrive integer n, e, se;
        n = tk % 4; e = tk / 4;                        // this edge samples the word presented now
        se = (n == 0) ? 3 * e + 2 : (n == 2) ? 3 * (e + 1) : (n == 3) ? 3 * (e + 1) + 1 : -1;
        if (se >= 0) begin ev[se] = t_v; ed[se] = t_d; if (t_v) words = words + 1; end
        tk = tk + 1;
        #10 t_v = ((tk % 4) == 1) ? (mode == 3 && tk > 100 && tk < 110) : $random(seed); t_d = t_d + 1;
    end
    always @(posedge s_ck) if (s_rn) begin
        #20;
        if (sk > 8 && mode == 0) begin
            if (o_v !== ev[sk] || (o_v && o_d !== ed[sk])) begin bad = bad + 1; if (bad < 5) $display("MISMATCH sk %0d got %b %h exp %b %h", sk, o_v, o_d, ev[sk], ed[sk]); end
            if (o_v) got = got + 1;
        end
        sk = sk + 1;
    end
    initial begin
        if (!$value$plusargs("mode=%d", mode)) mode = 0;
        #(3336 * E0 - 100);
        s_rn = (mode == 2) ? 0 : 1; t_rn = (mode == 1) ? 0 : 1;
        if (mode == 1) begin #(834); t_rn = 1; end
        if (mode == 2) begin #(1112); s_rn = 1; end
        #(3336 * 900);
        if (mode == 0) begin
            if (fault) begin bad = bad + 1; $display("UNEXPECTED FAULT"); end
            $display("TB_X43 RESULT mode 0 words %0d got %0d bad %0d", words, got, bad);
            $display("TB_X43 %s mode 0", (bad == 0 && got > 1000) ? "PASS" : "FAIL");
        end else
            $display("TB_X43 %s mode %0d (fault %b)", fault ? "PASS" : "FAIL", mode, fault);
        $finish;
    end
endmodule
