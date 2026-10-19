`timescale 1ns/1ps
// Cycle exact source-partition regression, independent local and recovered roots.
// Both endpoints receive the same reference transmitter; the receive side is
// exercised by valid complete FEC frames, not idle-only random PMA samples.
module tb_s81_serdes_partition;
    parameter integer MUT = 0;
    reg clk=0, rck=0, rst=0;
    always #0.41667 clk=~clk;
    always #0.41669 rck=~rck;
    reg [511:0] tx=0;
    wire [511:0] a_rx,b_rx;
    wire [1:0] a_st,b_st;
    wire [543:0] a_p,b_p;
    wire a_ck,b_ck;
    ot_pdie_serdes_before_split ref_i (.clk(clk),.rst(rst),.tx(tx),.rx(a_rx),.st(a_st),
        .pma_tx(a_p),.pma_tck(a_ck),.pma_rx(a_p),.pma_rck(rck));
    ot_pdie_serdes #(.EMUT(MUT)) dut_i (.clk(clk),.rst(rst),.tx(tx),.rx(b_rx),.st(b_st),
        .pma_tx(b_p),.pma_tck(b_ck),.pma_rx(a_p),.pma_rck(rck));
    integer bad=0, checks=0, live=0, nonidle=0;
    always @(negedge clk) begin
        if (rst) begin
            checks=checks+1;
            if ({a_rx,a_st,a_p,a_ck} !== {b_rx,b_st,b_p,b_ck}) begin
                bad=bad+1;
                if (bad<4) $display("ERR partition cycle=%0d",checks);
            end
            if(a_st[1]) live=live+1;
            if (a_rx!=512'd2) nonidle=nonidle+1;
        end
        tx={16{$urandom}};
        tx[1:0]=2'b01;
    end
    initial begin
        repeat (16) @(negedge clk); rst=1;
        repeat (2000) @(negedge clk);
        rst=0;
        repeat (16) @(negedge clk); rst=1;
        repeat (2000) @(negedge clk);
        $display("TB_S81_SERDES_PARTITION checks=%0d live=%0d nonidle=%0d mismatch=%0d MUT=%0d",checks,live,nonidle,bad,MUT);
        if (bad || checks<3900 || live<3000 || nonidle<3000) $display("TB_S81_SERDES_PARTITION FAIL");
        else $display("TB_S81_SERDES_PARTITION PASS");
        $finish;
    end
endmodule
