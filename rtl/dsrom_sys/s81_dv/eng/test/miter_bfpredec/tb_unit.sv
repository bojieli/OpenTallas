`timescale 1ns/1ps
// PATH-S81/ENG3 10-25: exhaustive equivalence of the split decode (ot_s81eng_rr_bfpre -> ot_s81eng_rr_bfpost_byte, both
// bytes) against the unchanged ot_s81eng_rr_bfraw_byte over all 65,536 {code, scale} pairs.  BFP_MUT: MUT 1 pre-decode.
module tb;
`ifdef BFP_MUT
    localparam integer PM = 1;
`else
    localparam integer PM = 0;
`endif
    reg ck = 0; reg [7:0] code = 0, scale = 0, sc_q = 0;
    wire [19:0] pd; wire [7:0] lo, hi, lo_r, hi_r;
    ot_s81eng_rr_bfpre #(.MUT(PM)) u_p (.ck(ck), .code(code), .q(pd));
    ot_s81eng_rr_bfpost_byte #(.LO(0)) u_l (.pd(pd), .scale(sc_q), .q(lo));
    ot_s81eng_rr_bfpost_byte #(.LO(8)) u_h (.pd(pd), .scale(sc_q), .q(hi));
    reg [7:0] code_q = 0;
    ot_s81eng_rr_bfraw_byte_ref #(.LO(0)) r_l (.code(code_q), .scale(sc_q), .q(lo_r));
    ot_s81eng_rr_bfraw_byte_ref #(.LO(8)) r_h (.code(code_q), .scale(sc_q), .q(hi_r));
    integer i, mis = 0, nsub = 0, novf = 0, nnan = 0;
    initial begin
        for (i = 0; i < 65536; i = i + 1) begin
            code = i[7:0]; scale = i[15:8];
            #1 ck = 1; code_q = code; sc_q = scale; #1 ck = 0; #1;
            if ({hi, lo} !== {hi_r, lo_r}) begin
                if (mis < 5) $display("MISMATCH code=%h scale=%h new=%h ref=%h", code, scale, {hi, lo}, {hi_r, lo_r});
                mis = mis + 1;
            end
            if (hi_r[6:0] == 7'd0 && lo_r[7] == 1'b0 && lo_r != 0) nsub = nsub + 1;
            if ({hi_r[6:0], lo_r[7]} == 8'hFF && lo_r[6:0] == 0) novf = novf + 1;
            if ({hi_r[6:0], lo_r} == 15'h7FC0) nnan = nnan + 1;
        end
        $display("ENG3_UNIT_MITER %s pairs=65536 mismatches=%0d subnormal_out=%0d inf_out=%0d nan_out=%0d",
                 (mis == 0) ? "PASS" : "FAIL", mis, nsub, novf, nnan);
        $finish;
    end
endmodule
