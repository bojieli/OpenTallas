`timescale 1ns/1ps
// Check of rtl/hdc/v41x/ot_dsrom_su_spsqrt.sv against tools/hdc_golden_v41 sqrt(softplus(x)) vectors
// (tools/dsrom_su_routeract.py).
//
// +IN=<file>   one hex word a line, LANES words a beat (lane 0 first)
// +EXP=<file>  the expected r words, same layout
// +SEG=<n>     beats per segment (a die's rows): span = first beat of segment 0 accepted -> its last beat out
// +BUBBLE=<p>  percent of cycles the driver withholds a beat; +SEED=<n>
// Reports latency (accept -> out edges, must be constant), span0, errors, faults.
module tb_dsrom_su_spsqrt
`ifdef VERILATOR
    (input wire clk)
`endif
    ;
`ifndef VERILATOR
    reg clk = 1'b0;
    always #0.5 clk = !clk;
`endif
    parameter integer LANES = 24;
    parameter integer IMPL = 0;
    parameter integer IN_STAGES = 2;
    parameter integer OUT_STAGES = 2;
    localparam integer MAXB = 1 << 20;

    reg                 rst_n = 1'b0;
    reg                 in_valid = 1'b0;
    reg [LANES*32-1:0]  in_x = 0;
    wire                out_valid, out_fault;
    wire [LANES*32-1:0] out_r;
    ot_dsrom_su_spsqrt #(.LANES(LANES), .IMPL(IMPL), .IN_STAGES(IN_STAGES), .OUT_STAGES(OUT_STAGES)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_x(in_x), .out_valid(out_valid), .out_r(out_r),
        .out_fault(out_fault));

    integer fin, fexp, rc, l, seg = 1, bubble = 0;
    reg [31:0] rng = 32'h2545F491, w;
    reg [8*512-1:0] fname;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction
    reg have = 1'b0, drv_done = 1'b0;
    reg [LANES*32-1:0] b_x, e_r;
    task automatic fetch;
        begin
            have = 1'b1;
            for (l = 0; l < LANES; l = l + 1) begin
                rc = $fscanf(fin, "%h\n", w);
                if (rc != 1) have = 1'b0;
                b_x[32*l +: 32] = w;
            end
        end
    endtask
    initial begin
        if (!$value$plusargs("IN=%s", fname)) begin $display("need +IN"); $finish; end
        fin = $fopen(fname, "r");
        if (!$value$plusargs("EXP=%s", fname)) begin $display("need +EXP"); $finish; end
        fexp = $fopen(fname, "r");
        if (!$value$plusargs("SEG=%d", seg)) seg = 1;
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 0;
        if ($value$plusargs("SEED=%d", rc)) rng = rng ^ rc;
        fetch;
    end

    integer cyc = 0, nin = 0, nout = 0, errors = 0, faults = 0, lat_min = 1 << 30, lat_max = -1, span0 = -1;
    integer last_out = 0;
    integer acc [0:MAXB-1];
    reg show;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (rst_n) begin
            if (in_valid) begin acc[nin] = cyc; nin = nin + 1; fetch; end
            rng = xs(rng);
            show = have && (rng % 100) >= bubble;
            in_valid <= show;
            in_x <= b_x;
            if (!have) drv_done <= 1'b1;
        end
    end
    integer s;
    always @(posedge clk) begin
        if (rst_n && out_valid) begin
            last_out = cyc;
            if (cyc - 1 - acc[nout] < lat_min) lat_min = cyc - 1 - acc[nout];
            if (cyc - 1 - acc[nout] > lat_max) lat_max = cyc - 1 - acc[nout];
            if (nout == seg - 1) span0 = cyc - acc[0];
            if (out_fault) faults = faults + 1;
            for (s = 0; s < LANES; s = s + 1) begin
                rc = $fscanf(fexp, "%h\n", w);
                if (out_r[32*s +: 32] !== w) begin
                    if (errors < 20) $display("MISMATCH beat=%0d lane=%0d got %h expect %h", nout, s, out_r[32*s +: 32], w);
                    errors = errors + 1;
                end
            end
            nout = nout + 1;
        end
        if (drv_done && cyc > last_out + 600 && cyc > 64) begin
            $display("SPSQRT LANES=%0d IMPL=%0d beats_in=%0d beats_out=%0d errors=%0d faults=%0d lat_min=%0d lat_max=%0d span0=%0d cycles=%0d",
                     LANES, IMPL, nin, nout, errors, faults, lat_min, lat_max, span0, cyc);
            if (errors == 0 && faults == 0 && nout == nin && nin > 0 && lat_min == lat_max) $display("PASS");
            else $display("FAIL");
            $finish;
        end
        if (cyc > 50000000) begin $display("TIMEOUT"); $finish; end
    end
endmodule
