// S81-LEAF-SWR: the leaf's vsw -> vs return station (ot_s81sl_leaf u_cst_swr = ot_s81sl_cst #(.W(64), .V(2), .D(CS_SWR_D)))
// at depth D against a reference shift of SHIFT clocks.  SHIFT == D must PASS; SHIFT != D must FAIL (control).
// Checked every clock after reset: q (sw_ri data) and qv ({sw_vi, sw_fi}) both equal their inputs SHIFT clocks earlier,
// so valid, fault and data stay on one edge; qv is 0 while the reset is held (D > 0).
`timescale 1ns/1ps
`ifndef D
 `define D 1
`endif
`ifndef SHIFT
 `define SHIFT `D
`endif
`ifndef NCYC
 `define NCYC 4000
`endif
module tb_cst_swr;
    localparam integer D = `D, SHIFT = `SHIFT, H = 8;
    reg clk = 1'b0, rst_n = 1'b0;
    reg [63:0] d = 64'd0; reg [1:0] dv = 2'd0;
    wire [63:0] q; wire [1:0] qv;
    ot_s81sl_cst #(.W(64), .V(2), .D(D)) dut (.clk(clk), .rst_n(rst_n), .d(d), .dv(dv), .q(q), .qv(qv));
    reg [63:0] hd [0:H-1]; reg [1:0] hv [0:H-1];
    integer i, n = 0, errs = 0, rst_errs = 0, valids = 0, seed = 32'h5a81_0520;
    wire [63:0] ed = (SHIFT == 0) ? d : hd[SHIFT - 1];
    wire [1:0]  ev = (SHIFT == 0) ? dv : hv[SHIFT - 1];
    always #5 clk = ~clk;
    initial begin
        for (i = 0; i < H; i = i + 1) begin hd[i] = 64'd0; hv[i] = 2'd0; end
        // reset held with valids driven: a D > 0 station must hold qv at 0
        repeat (4) begin
            @(negedge clk); d = {$random(seed), $random(seed)}; dv = 2'b11;
            @(posedge clk); #1; if (D > 0 && qv !== 2'b00) rst_errs = rst_errs + 1;
        end
        @(negedge clk); dv = 2'b00; rst_n = 1'b1;
        repeat (`NCYC) begin
            @(negedge clk);
            d = {$random(seed), $random(seed)}; dv = $random(seed);
            #1;
            if (n >= H) begin
                if (q !== ed || qv !== ev) errs = errs + 1;
                if (qv != 2'b00) valids = valids + 1;
            end
            @(posedge clk);
            for (i = H - 1; i > 0; i = i - 1) begin hd[i] = hd[i - 1]; hv[i] = hv[i - 1]; end
            hd[0] = d; hv[0] = dv;
            n = n + 1;
        end
        $display("CST_SWR_RESULT %s D %0d shift %0d checked %0d valids %0d errors %0d reset_errors %0d",
                 (errs == 0 && rst_errs == 0) ? "PASS" : "FAIL", D, SHIFT, n - H, valids, errs, rst_errs);
        $finish;
    end
endmodule
