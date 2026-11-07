`timescale 1ns/1ps
module tb_serdes_col_tx_pin;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0, tx_v = 0;
    reg [511:0] tx_d;
    wire gv, dv, mv, gf, df, mf;
    wire [543:0] gd, dd, md;
    ot_s81_kp4_enc gold (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d),
        .p_v(gv), .p_d(gd), .fault(gf));
    ot_s81_serdes_col_tx_pin #(.N(3)) dut (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d),
        .p_v(dv), .p_d(dd), .fault(df));
    // Seeded fault: bypass one requested pin stage. A merely self-consistent
    // delayed-data test must fail to accept this shorter calendar.
    ot_s81_serdes_col_tx_pin #(.N(2)) mutant (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d),
        .p_v(mv), .p_d(md), .fault(mf));
    wire [544:0] gold_l, dut_l, mut_l;
    ot_pl_pad #(.W(545), .N(2)) gold_pad (.ck(clk), .d({gv,gd}), .q(gold_l));
    ot_pl_pad #(.W(545), .N(7)) dut_pad (.ck(clk), .d({dv,dd}), .q(dut_l));
    ot_pl_pad #(.W(545), .N(7)) mut_pad (.ck(clk), .d({mv,md}), .q(mut_l));
    reg [544:0] expect_l [0:7];
    reg expect_f [0:2];
    integer cycle, j, k, errors = 0, mutant_errors = 0, checked = 0;
    reg [31:0] rng = 32'h6ac3d52f;
    function automatic [31:0] step(input [31:0] x);
        reg [31:0] y;
        begin y=x^(x<<13); y=y^(y>>17); step=y^(y<<5); end
    endfunction
    initial begin
        tx_d = 0;
        for (cycle=0; cycle<2200; cycle=cycle+1) begin
            @(negedge clk);
            // Includes a 64-edge warm reset after the stream is live, and
            // deliberate valid gaps that exercise the encoder's sticky fault.
            rst_n = !((cycle<70) || (cycle>=1100 && cycle<1164));
            rng=step(rng);
            tx_v = rst_n && (rng[7:0] != 8'h7c);
            for (k=0;k<16;k=k+1) begin rng=step(rng); tx_d[32*k+:32]=rng; end
            @(posedge clk);
            #1;
            if (cycle>100) begin
                checked=checked+1;
                if (dut_l !== expect_l[7] || df !== expect_f[2]) begin
                    errors=errors+1;
                    if (errors<5) $display("ERR cycle=%0d data=%0d fault=%0d",cycle,dut_l!==expect_l[7],df!==expect_f[2]);
                end
                if (mut_l !== expect_l[7] || mf !== expect_f[2]) mutant_errors=mutant_errors+1;
            end
            for (j=7;j>0;j=j-1) expect_l[j]=expect_l[j-1];
            expect_l[0]=gold_l;
            for (j=2;j>0;j=j-1) expect_f[j]=expect_f[j-1];
            expect_f[0]=gf;
        end
        $display("TX_PIN_RESULT checked=%0d errors=%0d mutant_errors=%0d PIN_TX_ADDED=8 RESET_RELEASE_ADDED=3",checked,errors,mutant_errors);
        if (errors || !mutant_errors) $fatal(1,"TX PIN lockstep/mutant failed");
        $finish;
    end
endmodule
