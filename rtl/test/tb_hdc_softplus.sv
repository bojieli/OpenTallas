`timescale 1ns/1ps
// Streams golden vectors ("x softplus sqrt(softplus) fault", hex; see
// tools/rtl_hdc_v41_engram_campaign.py) through ot_hdc_softplus with random
// input bubbles and checks both results and the fault flag, in order, bit for
// bit.  A vector whose golden result is not finite expects fault with +0
// outputs.  Clocked from outside (Verilator harness) or by the HDC_SELF_CLOCK
// wrapper (Icarus).
module tb_hdc_softplus (input wire clk);
    localparam integer MAXV = 1 << 16;
    reg [31:0] vx [0:MAXV-1];
    reg [31:0] vs [0:MAXV-1];
    reg [31:0] vr [0:MAXV-1];
    reg        vf [0:MAXV-1];
    integer nvec = 0, fd, rc;
    reg [31:0] a0, a1, a2, a3;

    reg rst_n = 1'b0;
    reg v = 1'b0;
    reg [31:0] x = 0;
    wire [31:0] sp, r;
    wire vo, fault;
    ot_hdc_softplus dut (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .sp(sp), .r(r), .vo(vo), .fault(fault));

    initial begin : load
        reg [8*512-1:0] path;
        if (!$value$plusargs("VEC=%s", path)) path = "softplus_vectors.txt";
        fd = $fopen(path, "r");
        if (fd == 0) begin $display("cannot open vectors"); $finish; end
        rc = 4;
        while (rc == 4 && nvec < MAXV) begin
            rc = $fscanf(fd, "%h %h %h %h", a0, a1, a2, a3);
            if (rc == 4) begin
                vx[nvec] = a0; vs[nvec] = a1; vr[nvec] = a2; vf[nvec] = a3[0];
                nvec = nvec + 1;
            end
        end
        $fclose(fd);
    end

    integer cyc = 0, sent = 0, got = 0, errors = 0, faults = 0, idle = 0;
    reg [31:0] seed = 32'h5EED_0F41;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        seed = seed ^ (seed << 13); seed = seed ^ (seed >> 17); seed = seed ^ (seed << 5);
        if (rst_n && sent < nvec && seed[2:0] != 3'd0) begin
            v <= 1'b1; x <= vx[sent];
            sent <= sent + 1;
        end else begin
            v <= 1'b0; x <= seed;                     // idle inputs are noise
        end
        if (rst_n && vo) begin
            if (got >= nvec || sp !== vs[got] || r !== vr[got] || fault !== vf[got]) begin
                if (errors < 10)
                    $display("MISMATCH idx=%0d x=%h got sp=%h r=%h f=%b expect sp=%h r=%h f=%b", got,
                             vx[got], sp, r, fault, vs[got], vr[got], vf[got]);
                errors = errors + 1;
            end
            if (fault) faults = faults + 1;
            got = got + 1;
        end else if (rst_n && fault) begin
            $display("FAULT without a result at cycle %0d", cyc);
            errors = errors + 1;
        end
        idle = (rst_n && sent >= nvec) ? idle + 1 : 0;
        if (idle > 300 || cyc > 4 * MAXV + 1000) begin
            $display("SOFTPLUS vectors=%0d checked=%0d errors=%0d faults=%0d cycles=%0d", nvec, got, errors,
                     faults, cyc);
            if (errors == 0 && got == nvec && nvec > 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule

`ifdef HDC_SELF_CLOCK
module tb_hdc_softplus_clk;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    tb_hdc_softplus u (.clk(clk));
endmodule
`endif
