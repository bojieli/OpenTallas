// The four slot-shaped station cells (rtl/physical/ot_qwen_die_station_slots.sv), one per run (-D CELL_CST_S |
// CELL_CST_N | CELL_CHEAD_W | CELL_CHEAD_E): on random words and random readies every data output equals the input
// word one cycle later (bit-exact, all 508 bits, every output face), and the upstream ready equals the AND of the
// downstream readies two cycles later.  The DUT is driven through its OWN port names, so a wrong face mapping (a
// station wired against its flow) fails.  With -D OT_QFD_STATION_MUT the cell inverts one data bit: must FAIL.
`timescale 1ns/1ps
module tb_qwen_die_station_slots;
    parameter integer N = 20000;
    localparam integer DW = 508;
    reg ck = 0, rst_n = 0, r0 = 0, r1 = 0, r2 = 0;
    reg  [DW-1:0] in_d = 0;
    wire [DW-1:0] o0, o1, o2;
    wire in_r;
`ifdef CELL_CST_S
    localparam integer NO = 2;
    qfd_cst_s u (.ck(ck), .rst_n(rst_n), .a_d(in_d), .a_r(in_r), .b_d(o0), .b_r(r0), .tap_d(o1), .tap_r(r1));
    assign o2 = o0;
`elsif CELL_CST_N
    localparam integer NO = 2;
    qfd_cst_n u (.ck(ck), .rst_n(rst_n), .b_d(in_d), .b_r(in_r), .a_d(o0), .a_r(r0), .tap_d(o1), .tap_r(r1));
    assign o2 = o0;
`elsif CELL_CHEAD_W
    localparam integer NO = 3;
    qfd_chead_w u (.ck(ck), .rst_n(rst_n), .e_d(in_d), .e_r(in_r), .w_d(o0), .w_r(r0), .n_d(o1), .n_r(r1), .s_d(o2), .s_r(r2));
`else
    localparam integer NO = 3;
    qfd_chead_e u (.ck(ck), .rst_n(rst_n), .w_d(in_d), .w_r(in_r), .e_d(o0), .e_r(r0), .n_d(o1), .n_r(r1), .s_d(o2), .s_r(r2));
`endif
    always #1 ck = ~ck;
    reg rq [0:3];
    integer i, k, bad = 0, seed = 7, nrdy = 0;
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 7;
        repeat (3) @(posedge ck); rst_n = 1;
        for (i = 0; i < N; i = i + 1) begin
            @(negedge ck);
            // outputs now hold what the last posedge captured: the stimulus driven one iteration ago
            if (i > 4) begin
                if (o0 !== in_d || o1 !== in_d || o2 !== in_d) bad = bad + 1;
                if (in_r !== rq[1]) bad = bad + 1;
                if (in_r === 1'b1) nrdy = nrdy + 1;
            end
            for (k = 0; k < DW; k = k + 32) in_d[k +: 32] = $random(seed);
            rq[3] = rq[2]; rq[2] = rq[1]; rq[1] = rq[0];
            r0 = $random(seed); r1 = $random(seed); r2 = (NO == 3) ? $random(seed) : 1'b1;
            rq[0] = r0 & r1 & r2;
        end
        // the ready path must have been exercised both ways (not a stuck value)
        if (nrdy == 0 || nrdy >= N - 5) bad = bad + 1;
        if (bad == 0) $display("PASS station_slots %m: %0d cycles, %0d ready, %0d outputs x %0d bits exact", N, nrdy, NO, DW);
        else $display("FAIL station_slots %m: %0d mismatches", bad);
        $finish;
    end
endmodule
