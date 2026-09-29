`timescale 1ns/1ps
module tb_hdc_v41x_idx_score_slice;
    parameter integer NK=1;
    localparam NB=4, IW=30;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,ql_v=0,i_valid=0,i_last=0,o_ready=0;
    reg [7:0] ql_head=0;
    reg [NB*128-1:0] ql_codes=0;
    reg [NB*8-1:0] ql_sc=0;
    reg [15:0] ql_w=0;
    reg [IW-1:0] i_first_index=0;
    reg [NK-1:0] i_kv=0,i_ref=0,i_keep=0;
    reg [NK*NB*136-1:0] i_key=0;
    wire i_ready,o_valid,o_last,ql_ready;
    wire [NK-1:0] o_kv,o_fault;
    wire [NK*16-1:0] o_score;
    wire [NK*IW-1:0] o_index;
    integer sent=0,got=0,cycle=0,stalls=0,first_out=-1,nostall;
    ot_hdc_v41x_idx_score_slice #(.NK(NK),.NB(NB),.IW(IW),.MD(64)) dut(.*);
    initial begin
        nostall=$test$plusargs("NOSTALL");
        repeat(4) @(negedge clk);rst_n=1;
        for(integer h=0;h<32;h=h+1) begin
            ql_v=1;ql_head=h;ql_codes={128{4'h2}};
            ql_sc=32'h7f7f7f7f;ql_w=16'h3f80;
            @(negedge clk);
        end
        ql_v=0;repeat(5) @(negedge clk);
        for(cycle=0;cycle<1000 && got<128;cycle=cycle+1) begin
            i_valid=sent<128;
            i_last=sent==127;
            i_first_index=100+sent*NK;
            i_kv={NK{1'b1}};
            i_ref=(sent==17) ? {{(NK-1){1'b0}},1'b1} : {NK{1'b0}};
            i_keep=(sent==31) ? {{(NK-1){1'b1}},1'b0} : {NK{1'b1}};
            for(integer lane=0;lane<NK;lane=lane+1) begin
                i_key[(lane*NB*136)+:NB*136]={32'h7f7f7f7f,{512{1'b0}}};
                if(sent[0]) i_key[(lane*NB*136)+:512]={128{4'h2}};
            end
            o_ready=nostall ? 1'b1 : (!(cycle>=55 && cycle<115) && cycle%11!=0);
            #1;
            if(i_valid && !i_ready) stalls++;
            @(posedge clk);
            if(i_valid && i_ready) sent++;
            if(o_valid && o_ready) begin
                if(first_out<0) first_out=cycle;
                if(o_last!==(got==127)) $fatal(1,"last beat %0d",got);
                for(integer lane=0;lane<NK;lane=lane+1) begin
                    if(o_index[IW*lane +: IW]!==IW'(100+got*NK+lane) ||
                       !o_kv[lane] || o_fault[lane]!==((got==17)&&(lane==0)) ||
                       o_score[16*lane +: 16]!==
                           ((lane==0 && got==17) ? 16'h0000 :
                            ((lane==0 && got==31) ? 16'hff80 :
                             (got[0] ? 16'h4580 : 16'h0000))))
                        $fatal(1,"score beat=%0d lane=%0d idx=%0d score=%h fault=%b",
                               got,lane,o_index[IW*lane +: IW],o_score[16*lane +: 16],o_fault[lane]);
                end
                got++;
            end
            @(negedge clk);
        end
        if(sent!=128 || got!=128 || (nostall && stalls!=0) || (!nostall && stalls==0))
            $fatal(1,"incomplete sent=%0d got=%0d stalls=%0d",sent,got,stalls);
        $display("PASS score slice sent=%0d got=%0d first_output_cycle=%0d total_cycles=%0d input_stalls=%0d",sent,got,first_out,cycle,stalls);
        $finish;
    end
endmodule
