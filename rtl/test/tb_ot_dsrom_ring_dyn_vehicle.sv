// tb_ot_dsrom_ring_dyn_vehicle: drive the ring-DYN route vehicle (full shape, NSLOT 1) with a list of positions and
// read back all 64 DYN rows through the 17 registered read ports; tools/mtp_ring_dyn_vehicle.py bench compares them
// with tools/v41_fullshape_isa.full_dyn.  Output: "DYNV pos=<p> tok=<t> idx=<i> val=<v>" per row, then "DYNV_END".
`timescale 1ns/1ps
module tb_ot_dsrom_ring_dyn_vehicle #(parameter integer RING = 1);   // RING 0 = the pre-V36 mutant
    localparam integer AW = 30, NW = 21, NRD = 17, RIW = 8;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg              cap = 0;
    reg [2:0]        ds = 0;
    reg [NW-1:0]     tok = 0, pos = 0;
    reg [NRD*3-1:0]  slot = 0;
    reg [NRD*RIW-1:0] idx = 0;
    wire [NRD*AW-1:0] val;
    ot_dsrom_ring_dyn_vehicle #(.FULL_SHAPE(1), .NSLOT(1), .ROLLBACK_RING_DYN(RING)) dut (
        .clk(clk), .rst_n(rst_n), .i_cap(cap), .i_ds(ds), .i_tok(tok), .i_pos(pos),
        .i_rd_slot(slot), .i_rd_idx(idx), .o_rd_val(val));
    integer np, k, g, i;
    reg [NW-1:0] plist [0:31];
    initial begin
        plist[0] = 0; plist[1] = 1; plist[2] = 2; plist[3] = 3; plist[4] = 4; plist[5] = 5; plist[6] = 6; plist[7] = 7;
        plist[8] = 8; plist[9] = 9; plist[10] = 10; plist[11] = 15; plist[12] = 16; plist[13] = 17; plist[14] = 31;
        plist[15] = 63; plist[16] = 126; plist[17] = 127; plist[18] = 128; plist[19] = 129; plist[20] = 511;
        plist[21] = 512; plist[22] = 1000; plist[23] = 2047; plist[24] = 4095; plist[25] = 16383; plist[26] = 16384;
        plist[27] = 16385; plist[28] = 65535; plist[29] = 100001; plist[30] = 262143; plist[31] = 1048573;
        np = 32;
        repeat (3) @(posedge clk);
        rst_n = 1;
        for (k = 0; k < np; k = k + 1) begin
            @(negedge clk); pos = plist[k]; tok = (k * 37 + 11) % 129280; ds = 0; cap = 1;
            @(negedge clk); cap = 0;                   // cap_q samples next edge; capture one edge later
            repeat (3) @(negedge clk);
            for (g = 0; g < 4; g = g + 1) begin       // 4 groups of 16 rows (port 16 idles on row 0)
                for (i = 0; i < NRD; i = i + 1) begin
                    slot[i * 3 +: 3] = 0;
                    idx[i * RIW +: RIW] = (i < 16) ? (g * 16 + i) : 0;
                end
                repeat (3) @(negedge clk);             // in flop -> read mux -> out flop
                for (i = 0; i < 16; i = i + 1)
                    $display("DYNV pos=%0d tok=%0d idx=%0d val=%0d", plist[k], tok, g * 16 + i, val[i * AW +: AW]);
            end
        end
        $display("DYNV_END");
        $finish;
    end
endmodule
