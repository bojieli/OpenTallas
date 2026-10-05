`timescale 1ns/1ps
module tb_hdc_chunk8_stack;
    localparam integer IL = 8;
    localparam integer MAXT = 16384;
    localparam integer MAXJ = 1024;
    reg clk = 0;
    always #0.5 clk = ~clk;
    reg rst_n = 0, in_v = 0, in_first = 0, in_last = 0, in_fault = 0;
    reg [2:0] in_slot = 0;
    reg [31:0] in_term = 0;
    wire in_ready, out_v, out_fault;
    wire [31:0] out_acc;
    wire [15:0] out_bf16;
    ot_hdc_chunk8_stack #(.IL(IL), .MAX_BLOCKS(192)) dut (
        .clk(clk), .rst_n(rst_n), .in_v(in_v), .in_ready(in_ready),
        .in_first(in_first), .in_last(in_last), .in_slot(in_slot),
        .in_term(in_term), .in_fault(in_fault), .out_v(out_v),
        .out_acc(out_acc), .out_bf16(out_bf16), .out_fault(out_fault));
    reg [31:0] terms [0:MAXT-1];
    reg [63:0] jobs [0:MAXJ-1]; // start[63:32], count[31:16], reserved[15:0]
    reg [47:0] expected [0:MAXJ-1];
    integer nt, nj, i, cycle = 0, issued = 0, checked = 0, failures = 0;
    integer active [0:IL-1], row [0:IL-1], pos [0:IL-1], fifo [0:MAXJ-1];
    integer last_cycle [0:MAXJ-1], latency = -1;
    integer fw = 0, fr = 0, s, b, quiet = 0;
    initial begin
        if (!$value$plusargs("NTERM=%d", nt)) $fatal(1,"NTERM missing");
        if (!$value$plusargs("NJOB=%d", nj)) $fatal(1,"NJOB missing");
        $readmemh("terms.mem",terms,0,nt-1);
        $readmemh("jobs.mem",jobs,0,nj-1);
        $readmemh("expect.mem",expected,0,nj-1);
        for (i=0;i<IL;i=i+1) active[i]=0;
    end
    always @(negedge clk) begin
        cycle = cycle + 1;
        if (cycle == 4) rst_n = 1;
        in_v = 0; in_first = 0; in_last = 0; in_fault = 0;
        in_slot = cycle % IL;
        #0.01; // let the combinational ready compare see the new slot
        if (rst_n) begin
            s = in_slot;
            if (!active[s] && issued < nj) begin
                active[s] = 1;
                row[s] = issued;
                pos[s] = 0;
                issued = issued + 1;
            end
            if (active[s]) begin
                if (!in_ready) begin
                    if (failures < 12) $display("BACKPRESSURE slot=%0d cycle=%0d",s,cycle);
                    failures = failures + 1;
                end else begin
                    b = jobs[row[s]][63:32] + pos[s];
                    in_v = 1;
                    in_first = (pos[s] == 0);
                    in_last = (pos[s] + 1 == jobs[row[s]][31:16]);
                    in_term = terms[b];
                    pos[s] = pos[s] + 1;
                    if (in_last) begin
                        fifo[fw] = row[s]; last_cycle[fw] = cycle; fw = fw + 1;
                        active[s] = 0;
                    end
                end
            end
            if (out_v) begin
                if (fr == fw) begin $display("EXTRA OUTPUT"); failures = failures + 1; end
                else begin
                    i = fifo[fr];
                    if (latency < 0) latency = cycle - last_cycle[fr];
                    else if (cycle - last_cycle[fr] != latency) begin
                        if (failures < 12) $display("VARIABLE LATENCY row=%0d got=%0d expected=%0d",
                            i, cycle - last_cycle[fr], latency);
                        failures = failures + 1;
                    end
                    fr = fr + 1;
                    if (out_fault || out_acc !== expected[i][47:16] || out_bf16 !== expected[i][15:0]) begin
                        if (failures < 12)
                            $display("MISMATCH row=%0d got=%h/%h fault=%b expected=%h/%h",
                                i,out_acc,out_bf16,out_fault,expected[i][47:16],expected[i][15:0]);
                        failures = failures + 1;
                    end
                    checked = checked + 1;
                end
            end
            if (checked == nj) quiet = quiet + 1;
            if (quiet == 5 || cycle > 80*(nt+nj)) begin
                $display("CHUNK8 rows=%0d checked=%0d errors=%0d latency=%0d cycles=%0d",
                    nj,checked,failures,latency,cycle);
                if (checked != nj || failures != 0) $fatal(1,"FAIL");
                $display("PASS"); $finish;
            end
        end
    end
endmodule
