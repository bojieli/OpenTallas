// QC-GLUE OBS-STAGE: gold = single selected flop + 512-bit mux (the original provider tail); gate = 32 keep_hierarchy copies.
module embed_sel_gold(input wire ck, en, d, input wire [511:0] a, b, output wire [511:0] y);
    reg selected; always @(posedge ck) if (en) selected <= d;
    assign y = selected ? a : b;
endmodule
module embed_sel_gate(input wire ck, en, d, input wire [511:0] a, b, output wire [511:0] y);
    genvar gi;
    for (gi = 0; gi < 32; gi = gi + 1) begin : g_selc
        qfd_embed_rope_mux #(.W(16), .ID(gi)) u_m (.ck(ck), .en(en), .d(d), .a(a[gi*16 +: 16]), .b(b[gi*16 +: 16]), .y(y[gi*16 +: 16]));
    end
endmodule
