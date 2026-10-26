`timescale 1ns/1ps
// q13 r5 leaf 1: the hardened top ot_qwen_tile_rpair (its own two macros) against the benched row logic
// ot_qwen_rpair_logic (the module tb_qwen_me_partition_w12 RPH=1 proves exact against the flat tile pipeline) with the
// same behavioural macros outside it: r_q equal on every edge.  MUT=1: the reference is the boundary mutant (MUT5,
// relay word one edge late) -> FAIL.  Macro model: registered read, output held without ce (as the tile benches).
module ot_rom_4096x266_m8 #(parameter integer SALT = 0) (input wire clk, input wire ce_in, input wire [11:0] addr_in,
                                                          output reg [265:0] rd_out);
    integer k;
    reg [287:0] w;
    always @(posedge clk) if (ce_in) begin
        for (k = 0; k < 9; k = k + 1) w[k*32 +: 32] = ({20'd0, addr_in} + 32'd1 + SALT) * 32'h9E3779B1 + k * 32'h85EBCA6B + (addr_in << (k % 7));
        rd_out <= w[265:0];
    end
    initial rd_out = 266'd0;
endmodule
module tb_qwen_tile_rpair;
    parameter integer MUT = 0, N = 20000, SEED = 1;
    reg clk = 0, rst_n = 0, ce_d = 0, any_d = 0; reg [11:0] ad_d = 0;
    wire [1023:0] q_dut, q_ref; wire [25:0] rq; wire [265:0] r0, r1;
    always #1 clk = ~clk;
    ot_qwen_tile_rpair dut (.clk(clk), .rst_n(rst_n), .ce_d(ce_d), .any_d(any_d), .ad_d(ad_d), .r_q(q_dut));
    defparam dut.u_rom1.SALT = 7;
    ot_qwen_rpair_logic #(.PWB(256), .ROM_CAP2(1), .ROM_CAPX(2), .MUT5(MUT)) u_ref (.clk(clk), .rst_n(rst_n), .ce_d(ce_d),
        .any_d(any_d), .ad_d(ad_d), .req_m(rq), .rd({r1[255:0], r0[255:0]}), .r_q(q_ref));
    ot_rom_4096x266_m8 #(.SALT(0)) m0 (.clk(clk), .ce_in(rq[12]), .addr_in(rq[11:0]), .rd_out(r0));
    ot_rom_4096x266_m8 #(.SALT(7)) m1 (.clk(clk), .ce_in(rq[25]), .addr_in(rq[24:13]), .rd_out(r1));
    integer i, s, cmp = 0, nz = 0, r;
    initial begin
        s = SEED;
        repeat (4) @(posedge clk); rst_n <= 1;
        for (i = 0; i < N; i = i + 1) begin
            @(posedge clk);
            r = $random(s);
            any_d <= (r[2:0] != 0);                    // some row of the tile reads
            ce_d  <= (r[2:0] != 0) && (r[4:3] != 0);   // this row is the one (or another row is)
            ad_d  <= r[16:5];
            if (i % 4999 == 4998) rst_n <= 0; else if (!rst_n && i > 4) rst_n <= 1;
            if (i > 12) begin
                if (q_dut !== q_ref) begin $display("FAIL cycle %0d r_q mismatch", i); $finish; end
                cmp = cmp + 1; if (|q_dut) nz = nz + 1;
            end
        end
        if (nz < N / 8) begin $display("FAIL vacuous: %0d nonzero words", nz); $finish; end
        $display("PASS %0d cycles compared, %0d nonzero relay words", cmp, nz); $finish;
    end
endmodule
