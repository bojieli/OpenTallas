// The 640-row store is checked at the original consumer capture edge.
module tb_svc_land_mem;
    reg clk = 0;
    always #5 clk = ~clk;
    reg [2:0] we = 0;
    reg [29:0] wa = 0;
    reg [767:0] wd = 0;
    reg [47:0] ra = 0;
    wire [1023:0] rd, mutant_rd;
    dsdv_svc_land_mem good (clk, we, wa, wd, ra, rd);
    dsdv_svc_land_mem #(.MUT(1)) mutant (clk, we, wa, wd, ra, mutant_rd);

    reg [255:0] ref_mem [0:639];
    reg [1023:0] expected;
    integer checks = 0, mutant_edges = 0, collisions = 0, triple_writes = 0, shared_bank_reads = 0;

    task automatic step(input integer n);
        integer a, base;
        @(negedge clk);
        // Sustain all three writers on one bank. A same-row case reverses
        // writer priority in the negative control.
        base = 4 * (n % 157) + n % 4;
        wa = {10'(base + 8), 10'(base + 4), 10'(base)};
        if (n % 7 == 0) begin
            wa = {3{10'(base)}};
            collisions++;
        end
        we = n % 5 == 0 ? 3'(n) : 3'b111;
        if (we == 3'b111)
            triple_writes++;
        for (integer w = 0; w < 3; w++)
            wd[256*w +: 256] = {8{32'(n * 67 + w * 257)}};
        // Reads 0/1 share a bank, and exercise old data on the write edge.
        // Also check fixed ports 2/3 and both ends of the legal address space.
        ra = {12'(base - (base % 4) + 3), 12'(base - (base % 4) + 2), 12'(base + 4), 12'(base)};
        if (n % 13 == 0)
            ra = {12'd639, 12'd638, 12'd640, 12'd0};
        if (ra[1:0] == ra[13:12])
            shared_bank_reads++;
        @(posedge clk);
        for (integer r = 0; r < 4; r++) begin
            a = 32'(ra[12*r +: 12]);
            expected[256*r +: 256] = (a < 640) ? ref_mem[a] : 256'd0;
        end
        for (integer w = 0; w < 3; w++) begin
            a = 32'(wa[10*w +: 10]);
            if (we[w] && a < 640)
                ref_mem[a] = wd[256*w +: 256];
        end
        #1;
        if (rd !== expected)
            $fatal(1, "landing data/edge mismatch n=%0d ra=%h", n, ra);
        checks += 4;
        if (mutant_rd !== expected)
            mutant_edges++;
    endtask

    initial begin
        for (integer a = 0; a < 640; a++)
            ref_mem[a] = '0;
        for (integer n = 0; n < 3000; n++)
            step(n);
        if (mutant_edges == 0 || shared_bank_reads < 2000 || triple_writes < 2000)
            $fatal(1, "missing priority mutant or same-bank traffic");
        $display("LAND_MEM PASS checks=%0d shared_bank_reads=%0d triple_writes=%0d collisions=%0d mutant_edges=%0d",
                 checks, shared_bank_reads, triple_writes, collisions, mutant_edges);
        $finish;
    end
endmodule
