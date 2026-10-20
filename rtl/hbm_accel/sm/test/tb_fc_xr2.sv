// HF-5a bench: ot_hbm_accel_smh_fc_xr2 is exactly fc_xr delayed by one more cycle on xo / lo / fo (2 cycles from the
// pins), with the valid bits reset.  Random stimulus every cycle; the reference is a 2-deep history of the inputs.
`timescale 1ns/1ps
module tb_fc_xr2;
    localparam integer TAGW = 16, LW = 554 + TAGW, N = 4000;
    reg clk = 0, rst_a = 0;
    reg  [2068:0] xi; reg [LW-1:0] li; reg [2:0] fi;
    wire [2068:0] xo; wire [LW-1:0] lo; wire [2:0] fo;
    ot_hbm_accel_smh_fc_xr2 #(.TAGW(TAGW)) dut (.clk(clk), .rst_a(rst_a), .xi(xi), .xo(xo), .li(li), .lo(lo), .fi(fi), .fo(fo));
    reg [2068:0] hx [0:1]; reg [LW-1:0] hl [0:1]; reg [2:0] hf [0:1];
    integer cyc = 0, bad = 0, chk = 0, rbad = 0, k;
    task rnd; begin
        for (k = 0; k < 2069; k = k + 32) xi[k +: 32] = $urandom;
        for (k = 0; k < LW; k = k + 32) li[k +: 32] = $urandom;
        fi = $urandom;
    end endtask
    always #1 clk = ~clk;
    initial begin
        rnd;
        repeat (4) @(posedge clk);
        #0.1 if (xo[2068] !== 1'b0 || lo[LW-1 -: 3] !== 3'b0 || fo !== 3'b0) rbad = rbad + 1;  // valids reset
        rst_a = 1;
        repeat (N) begin
            @(posedge clk); #0.1;
            cyc = cyc + 1;
            if (cyc > 8) begin
                chk = chk + 1;
                if (xo !== hx[1] || lo !== hl[1] || fo !== hf[1]) begin
                    bad = bad + 1;
                    if (bad < 4) $display("MISMATCH cyc %0d xo %0d lo %0d fo %0d", cyc, xo !== hx[1], lo !== hl[1], fo !== hf[1]);
                end
            end
            hx[1] = hx[0]; hl[1] = hl[0]; hf[1] = hf[0];
            rnd;
            hx[0] = xi; hl[0] = li; hf[0] = fi;
        end
        if (bad == 0 && rbad == 0 && chk > 0) $display("FCXR2 PASS checked=%0d", chk);
        else $display("FCXR2 FAIL mismatches=%0d reset_bad=%0d checked=%0d", bad, rbad, chk);
        $finish;
    end
endmodule
