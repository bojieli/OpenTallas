// DIE-QC-59P: load probe of the QC programme ROM images through the unchanged ROM models (+OT_ROM_DIR).
// Reads every word of sys_face_cfg (4096x72) and words 0..4095 of calendar_m0 / table_s0_m0 (4096x266) and prints them.
`timescale 1ns/1ps
module tb_qc_prog_rom_probe;
    reg clk = 0; reg [11:0] a = 0; integer i, fo;
    wire [71:0] q_sf; wire [265:0] q_c0, q_c1, q_t0;
    ot_rom_4096x72_m8  #(.INSTANCE("sys_face_cfg")) u_sf (.clk(clk), .ce_in(1'b1), .addr_in(a), .rd_out(q_sf));
    ot_rom_4096x266_m8 #(.INSTANCE("calendar_m0"))  u_c0 (.clk(clk), .ce_in(1'b1), .addr_in(a), .rd_out(q_c0));
    ot_rom_4096x266_m8 #(.INSTANCE("calendar_m1"))  u_c1 (.clk(clk), .ce_in(1'b1), .addr_in(a), .rd_out(q_c1));
    ot_rom_4096x266_m8 #(.INSTANCE("table_s0_m0"))  u_t0 (.clk(clk), .ce_in(1'b1), .addr_in(a), .rd_out(q_t0));
    qc_prog_rom_guard u_guard ();
    initial begin
        fo = $fopen("probe_words.txt", "w");
        #2;
        for (i = 0; i < 4096; i = i + 1) begin
            a = i[11:0]; #1 clk = 1; #1 clk = 0;
            $fwrite(fo, "%0d %018h %067h %067h %067h\n", i, q_sf, q_c0, q_c1, q_t0);
        end
        $fclose(fo); $display("PROBE_DONE 4096"); $finish;
    end
endmodule
