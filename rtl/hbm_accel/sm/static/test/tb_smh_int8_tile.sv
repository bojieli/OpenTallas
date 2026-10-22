`timescale 1ns/1ps
// LH-SMATT/INT8 10-19: lockstep bench ot_smh_int8_tile (SAFE hard tile) vs ot_smh_static_int8 (the merged smh_attn
// ENABLE_INT8 glue, main 61fd7503e), both behind the exact smh_attn merge mux
//   f_packet = conv_valid ? conv : (mark ? 0 : packet)
// on a random legal static calendar (packed lines >= 2 edges apart, raw packets never on a converted beat), all 256
// code values, with reset bursts.  Compares f_packet (1099 b) every cycle and every o_sel copy against o_v.
module tb_smh_int8_tile;
    parameter integer CYCLES = 20000;
    parameter integer SEED = 1;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg mark;
    reg [1098:0] packet;
    wire [1098:0] ref_out;
    ot_smh_static_int8 u_ref (.clk(clk), .rst_n(rst_n), .packet_in({packet[1098] & mark, packet[1097:0]}), .packet_out(ref_out));
    wire o_v; wire [9:0] o_tag; wire [1023:0] o_data; wire [34:0] o_sel;
    ot_smh_int8_tile u_dut (.clk(clk), .rst_n(rst_n), .i_v(packet[1098] & mark), .i_tag(packet[1097:1088]),
        .i_codes(packet[1023:0]), .o_v(o_v), .o_tag(o_tag), .o_data(o_data), .o_sel(o_sel));
    wire [1098:0] f_ref = ref_out[1098] ? ref_out : (mark ? 1099'd0 : packet);
    wire [1098:0] conv = {o_v, o_tag, 64'd0, o_data};
    wire [1098:0] raw  = mark ? 1099'd0 : packet;
    reg  [1098:0] f_new;
    integer b;
    always @* for (b = 0; b < 1099; b = b + 1) f_new[b] = o_sel[b / 32] ? conv[b] : raw[b];
    integer seed, cyc, checked, mism, beats, lines, last_line, k, r, warm;
    initial begin
        seed = SEED; checked = 0; mism = 0; beats = 0; lines = 0; last_line = -10; warm = 0;
        mark = 0; packet = 0;
        repeat (3) @(posedge clk);
        #0.2 rst_n = 1;
        for (cyc = 0; cyc < CYCLES; cyc = cyc + 1) begin
            @(negedge clk);
            // reset burst every ~4000 cycles (asserted 3 cycles)
            if (cyc % 4000 == 3997) begin rst_n = 0; last_line = cyc + 3; end
            if (cyc % 4000 == 0 && cyc > 0) rst_n = 1;
            r = $urandom(seed) % 8; seed = seed + 1;
            mark = 0; packet = 0;
            for (k = 0; k < 35; k = k + 1) packet[32*k +: 32] = $urandom;
            packet[1098] = 0;
            if (rst_n && r < 4 && cyc - last_line >= 2) begin          // packed INT8 line
                mark = 1; packet[1098] = 1; last_line = cyc; lines = lines + 1;
            end else if (rst_n && r < 6 && cyc - last_line != 2 && cyc - last_line != 3) begin
                packet[1098] = 1;                                     // raw (BF16 / DS) packet on a free slot
            end else if (r == 6) begin
                mark = 0;                                             // idle with random payload
            end
        end
        $display("I8T %s checked=%0d beats=%0d lines=%0d mismatches=%0d", (mism == 0 && beats > 0) ? "PASS" : "FAIL",
                 checked, beats, lines, mism);
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        checked <= checked + 1;
        if (ref_out[1098]) beats <= beats + 1;
        if (f_new !== f_ref || o_v !== ref_out[1098] || o_sel !== {35{o_v}}) begin
            mism <= mism + 1;
            if (mism < 5) $display("I8T MISMATCH t=%0t ref_v=%b o_v=%b tag %h/%h data[31:0] %h/%h", $time, ref_out[1098], o_v,
                                   ref_out[1097:1088], o_tag, f_ref[31:0], f_new[31:0]);
        end
    end
endmodule
