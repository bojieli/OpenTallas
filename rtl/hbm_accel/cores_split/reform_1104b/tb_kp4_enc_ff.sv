`timescale 1ns/1ps
// Native LA2 stream refinement: FF=1 must add precisely one output edge.
// MUT 1 corrupts transmitted parity; MUT 2 corrupts a registered matrix
// partial; MUT 3 shifts parity-load control. Every comparison is a full word.
module tb_kp4_enc_ff;
    parameter integer MUT = 0;
    reg clk=0, rst_n=0, tx_v=0;
    reg [511:0] tx_d=0;
    wire rv,dv,rf,df;
    wire [543:0] rd,dd;
    ot_s81_kp4_enc_la #(.MUT(0),.LA(2),.FF(0)) u_ref
        (.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(rv),.p_d(rd),.fault(rf));
    ot_s81_kp4_enc_la #(.MUT(MUT),.LA(2),.FF(1)) u_dut
        (.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(dv),.p_d(dd),.fault(df));
    always #1 clk=~clk;
    reg rv_q=0;
    reg [543:0] rd_q=0;
    integer cyc=0, bad=0, cmp=0, par=0, frame_word=0, epochs=0;
    integer ncyc=4000, stall=-1, reset_at=-1, seed=1, k, warm=0;
    reg was_valid=0;
    initial begin
        if (!$value$plusargs("NCYC=%d",ncyc)) ncyc=4000;
        if (!$value$plusargs("STALL=%d",stall)) stall=-1;
        if (!$value$plusargs("RESET_AT=%d",reset_at)) reset_at=-1;
        if (!$value$plusargs("SEED=%d",seed)) seed=1;
        k=$urandom(seed);
    end
    // Drive on falling edges so comparison observes stable registered outputs.
    always @(negedge clk) begin
        cyc=cyc+1;
        rst_n=(cyc>=5) && !(reset_at>=0 && cyc>=reset_at && cyc<reset_at+6);
        tx_v=rst_n && cyc>=13 && !(reset_at>=0 && cyc<reset_at+18 && cyc>=reset_at)
             && cyc!=stall && cyc!=stall+1;
        for(k=0;k<16;k=k+1) tx_d[32*k+:32]=$urandom;
    end
    always @(posedge clk) begin
        if (!rst_n) begin
            warm=0; was_valid=0; frame_word=0;
        end else begin
            warm=warm+1;
            if(warm>8) begin
                if(dv!==rv_q || (rv_q && dd!==rd_q) || df!==rf) begin
                    bad=bad+1;
                    if(bad<=5) $display("ERR cyc=%0d valid=%b/%b fault=%b/%b data_xor=%h",cyc,dv,rv_q,df,rf,dd^rd_q);
                end
                if(rv_q) begin
                    cmp=cmp+1;
                    if(!was_valid) begin epochs=epochs+1; frame_word=0; end
                    if(frame_word==9) par=par+1;
                    frame_word=(frame_word==9)?0:frame_word+1;
                end
                was_valid=rv_q;
            end
        end
        rd_q<=rd; rv_q<=rv;
        if(cyc>=ncyc) begin
            $display("TB_KP4_ENC_FF %s MUT=%0d mismatches=%0d compared_words=%0d parity_words=%0d epochs=%0d extra_edges=1 fault_extra_edges=0",(bad==0 && cmp>100 && par>10)?"PASS":"FAIL",MUT,bad,cmp,par,epochs);
            if(bad!=0 || cmp<=100 || par<=10) $fatal(1,"stream refinement failed");
            $finish;
        end
    end
endmodule
