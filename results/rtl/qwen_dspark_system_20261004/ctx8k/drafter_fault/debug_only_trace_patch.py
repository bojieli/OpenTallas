from pathlib import Path
p=Path("rtl/hdc/ot_qwen_w12_matvec.sv"); s=p.read_text()
anchor="    assign t_fault = fault;\n"
assert s.count(anchor)==1
s=s.replace(anchor, anchor+"""    // DEBUG ONLY (not committed): which fault source rises
    integer mf_n = 0;
    always @(posedge clk) if (rst_n && mf_n < 6) begin : g_mftrace
        integer q;
        for (q = 0; q < G; q = q + 1) if (|lfault[q*W +: W]) begin $display("MEFAULT part=%0d lanes grp=%0d mask=%h", PART, q, lfault[q*W +: W]); mf_n = mf_n + 1; end
        if (|tfault) begin $display("MEFAULT part=%0d tree=%b", PART, tfault); mf_n = mf_n + 1; end
        if (|scale_faults) begin $display("MEFAULT part=%0d scale=%h", PART, scale_faults); mf_n = mf_n + 1; end
        if (split_fault) begin $display("MEFAULT part=%0d split", PART); mf_n = mf_n + 1; end
        if (PART == 2 && t_fault_in) begin $display("MEFAULT part=2 t_fault_in"); mf_n = mf_n + 1; end
    end
""")
a2="                assign lfault[LI] = f0 | f1;\n"
assert s.count(a2)==1
s=s.replace(a2, a2+"""                integer lf_n = 0;
                always @(posedge clk) if (rst_n && (f0 || f1) && lf_n < 2) begin
                    $display("MEFAULT lane g=%0d l=%0d mul=%0d add=%0d prod=%h acc=%h w=%h x=%h", g, gl, f0, f1, prod, acc_in, s3_w[32*LI +: 32], s3_x[32*g +: 32]);
                    lf_n = lf_n + 1;
                end
""")
p.write_text(s)
t=Path("rtl/hdc/ot_qwen_rom_tile_w12.sv"); s=t.read_text()
i=s.index("endmodule", s.index("module ot_qwen_rom_tile_w12"))
s=s[:i]+"""    // DEBUG ONLY: tile id of a fault
    reg mf_d = 1'b0;
    always @(posedge clk) begin mf_d <= fault; if (fault && !mf_d) $display("MEFAULT tile=%0d", tile_id); end
"""+s[i:]
t.write_text(s)
print("patched")
