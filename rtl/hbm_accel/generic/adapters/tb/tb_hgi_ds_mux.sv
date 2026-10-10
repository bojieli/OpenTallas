`timescale 1ns/1ps
// hgi-adapters: the DS pass-through mux in front of a pin register is cycle-identical to the bare pin register when sel = 0,
// and carries the HGI bus when sel = 1 (random buses, 20,000 cycles each).  MUT_SEL: the mux selects the HGI bus in DS mode.
module tb_hgi_ds_mux;
    localparam integer W = 670;
    reg clk = 0; always #1 clk = ~clk;
    reg sel = 0; reg [W-1:0] lg, hg; wire [W-1:0] q; reg [W-1:0] pin_ref, pin_mux;
`ifdef MUT_SEL
    ot_hgi_ds_mux #(.W(W)) u (.sel(1'b1), .legacy(lg), .hgi(hg), .q(q));
`else
    ot_hgi_ds_mux #(.W(W)) u (.sel(sel), .legacy(lg), .hgi(hg), .q(q));
`endif
    integer i, k, errors = 0, seed = 1;
    always @(posedge clk) begin pin_mux <= q; pin_ref <= sel ? hg : lg; end
    initial begin
        for (k = 0; k < 2; k = k + 1) begin
            sel = k;
            for (i = 0; i < 20000; i = i + 1) begin
                @(negedge clk); lg = {21{$random(seed)}}; hg = {21{$random(seed)}};
                @(posedge clk); #0.1 if (pin_mux !== pin_ref) errors = errors + 1;
            end
        end
        if (errors == 0) $display("HGI_DS_MUX PASS"); else $display("HGI_DS_MUX FAIL errors=%0d", errors);
        $finish;
    end
endmodule
