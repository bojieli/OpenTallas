`timescale 1ns/1ps
// QC-CBGLUE-1116: cycle equivalence of ot_qfd_xcst_rep vs ot_qfd_xcst (b_d, tap_d) under random corridor words.
module tb_qfd_xcst_rep_eq;
    localparam integer AW=24, NW=18, IBW=3*NW+13*AW+13, CW=1+IBW+128+8;
    reg ck=0, rst_n=0; reg [2:0] sidx; reg [CW-1:0] a_d;
    wire [CW-1:0] b0, b1; wire [IBW+128:0] t0, t1; wire ar;
    ot_qfd_xcst     #(.AW(AW),.NW(NW),.XOFF(3)) u0 (.ck(ck),.rst_n(rst_n),.sidx(sidx),.a_d(a_d),.a_r(ar),.b_d(b0),.b_r(1'b1),.tap_d(t0));
    ot_qfd_xcst_rep #(.AW(AW),.NW(NW),.XOFF(3)) u1 (.ck(ck),.rst_n(rst_n),.sidx(sidx),.a_d(a_d),.b_d(b1),.tap_d(t1));
    always #1 ck = ~ck;
    integer n, err=0, cyc, w;
    initial begin
        sidx = 3'd5; a_d = 0;
        repeat (3) @(posedge ck); #0.1 rst_n = 1;
        for (cyc = 0; cyc < 200000; cyc = cyc + 1) begin
            @(negedge ck);
            for (w = 0; w < CW; w = w + 32) a_d[w +: 32] = $random;
            a_d[0] = ($random % 13) == 0;                       // GO now and then
            if ($random % 3 == 0) a_d[1+IBW+128 +: 4] = {1'b1, sidx};   // tag_a hits
            if ($random % 3 == 0) a_d[1+IBW+128+4 +: 4] = {1'b1, sidx}; // tag_b hits
            if (cyc % 5000 == 4999) sidx = $random;
            if (cyc == 100000) begin rst_n = 0; @(negedge ck); rst_n = 1; end
            @(posedge ck); #0.1;
            if (cyc > 4 && (b0 !== b1 || t0 !== t1)) begin
                err = err + 1;
                if (err < 5) $display("MISMATCH cyc %0d tap %0d b %0d", cyc, t0 !== t1, b0 !== b1);
            end
        end
        if (err) $display("XCST_EQ FAIL %0d", err); else $display("XCST_EQ PASS 200000 cycles");
        $finish;
    end
endmodule
