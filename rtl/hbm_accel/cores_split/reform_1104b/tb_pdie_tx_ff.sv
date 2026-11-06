`timescale 1ns/1ps
module tb_pdie_tx_ff;
    parameter integer MUT=0;
    reg clk=0,rst=0;
    reg [511:0] tx=0;
    wire [543:0] a,b;
    wire fa,fb;
    ot_pdie_serdes_tx #(.ELA(2),.EFF(0)) u_a (.clk(clk),.rst(rst),.tx(tx),.pma_tx(a),.e_flt_o(fa));
    ot_pdie_serdes_tx #(.ELA(2),.EFF(1),.EMUT(MUT)) u_b (.clk(clk),.rst(rst),.tx(tx),.pma_tx(b),.e_flt_o(fb));
    always #1 clk=~clk;
    reg [543:0] aq;
    integer cyc=0,bad=0,cmp=0,k,seed=73;
    initial k=$urandom(seed);
    always @(negedge clk) begin
        cyc=cyc+1;
        rst=cyc>=5 && !(cyc>=1800 && cyc<1806);
        for(k=0;k<16;k=k+1) tx[k*32+:32]=$urandom;
    end
    always @(posedge clk) begin
        aq<=a;
        // PMA is unreset; allow its finite pipeline to drain around reset.
        if(cyc>40 && !(cyc>=1800 && cyc<1846)) begin
            cmp=cmp+1;
            if(b!==aq || fb!==fa) begin
                bad=bad+1;
                if(bad<=4) $display("ERR cyc=%0d data_xor=%h fault=%b/%b",cyc,b^aq,fb,fa);
            end
        end
        if(cyc>=4000) begin
            $display("TB_PDIE_TX_FF %s MUT=%0d mismatches=%0d compared_words=%0d extra_edges=1 fault_extra_edges=0",bad==0 && cmp>3000?"PASS":"FAIL",MUT,bad,cmp);
            if(bad!=0 || cmp<=3000) $fatal(1,"native PMA stream mismatch");
            $finish;
        end
    end
endmodule
