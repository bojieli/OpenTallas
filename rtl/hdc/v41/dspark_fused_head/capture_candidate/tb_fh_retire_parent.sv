`timescale 1ns/1ps
module tb_fh_retire_parent;
    reg clk=0,rst_n=0,v=0,warm=0,sink_busy=0,ack_v=0;
    reg [5511:0] packet=0;
    reg [23:0] word=24'h125,ack_word=0;
    reg [15:0] mask=16'h20,ack_mask=0;
    reg [7:0] ack_id=0;
    reg [63:0] poison=0;
    reg [3:0] address_fault=0;
    reg arithmetic_fault=0;
    wire rv,rw,busy,wa,fault,debt;
    wire [5511:0] retired;
    wire [7:0] rid;
    wire [63:0] veto;
    wire [3:0] wveto;
    reg [5511:0] actual_memory=0;
    reg [7:0] committed_id;
    integer checks=0;
    ot_hdc_v41_fh_retire_parent #(.ENABLE(1)) dut
        (clk,rst_n,v,warm,packet,word,mask,poison,address_fault,arithmetic_fault,
         sink_busy,ack_v,ack_id,ack_word,ack_mask,rv,rw,retired,rid,veto,wveto,busy,wa,fault,debt);
    always #5 clk=~clk;
    task reset_owner;
        begin
            @(negedge clk);rst_n=0;v=0;warm=0;ack_v=0;sink_busy=0;
            @(negedge clk);rst_n=1;
        end
    endtask
    task issue_warm;
        begin
            @(negedge clk);packet={172{32'h89abcdef}};packet[0]=1;v=1;warm=1;
            @(posedge clk);#1;if(!debt||wa) $fatal(1,"emission cleared/unowned warm debt");
            @(negedge clk);v=0;warm=0;
            repeat(3) @(posedge clk);
            #1;if(!rv||!rw||retired!==packet||fault||veto||wveto)
                $fatal(1,"four-edge warm transaction changed");
            committed_id=rid;
            // Model a held, finite consumer: its write occurs after receiving
            // the complete retired tuple, and receipt is withheld afterward.
            @(negedge clk);sink_busy=1;
            repeat(2) @(posedge clk);
            #1;actual_memory=retired;
            checks=checks+1;
        end
    endtask
    task receipt(input integer wrong_identity);
        begin
            @(negedge clk);
            if(actual_memory!==packet) $fatal(1,"ACK before actual held memory write");
            ack_v=1;ack_id=committed_id^(wrong_identity==1?8'h1:8'h0);ack_word=word^(wrong_identity==2?24'h1:24'h0);ack_mask=mask^(wrong_identity==3?16'h1:16'h0);
            #1;if(wa===(wrong_identity!=0)) $fatal(1,"commit identity compare missing");
            @(posedge clk);#1;
            if(wrong_identity) begin
                if(!fault||!debt||wa) $fatal(1,"bad identity released quarantine");
            end else if(debt||fault) $fatal(1,"matching real commit did not clear debt");
            @(negedge clk);ack_v=0;sink_busy=0;
            checks=checks+1;
        end
    endtask
    initial begin
        reset_owner;
        // Masked/invalid input marker must not create or clear debt.
        @(negedge clk);warm=1;packet[0]=1;v=0;
        repeat(2) @(posedge clk);
        #1;if(debt||wa) $fatal(1,"invalid marker creates warm transaction");
        @(negedge clk);warm=0;
        issue_warm;
        repeat(7) begin @(posedge clk);#1;if(!debt||wa||!busy) $fatal(1,"held receipt loses debt/consumer busy");end
        receipt(0);
        issue_warm;
        receipt(1);
        repeat(6) begin @(posedge clk);#1;if(!debt||!fault||wa) $fatal(1,"quarantine did not persist");end
        // Even the correct identity cannot undo the sticky protocol failure.
        @(negedge clk);ack_v=1;ack_id=committed_id;
        @(posedge clk);#1;if(!debt||wa) $fatal(1,"late receipt relaxed original identity failure");
        // Every identity field is checked on held boundaries, one config.
        reset_owner;issue_warm;receipt(2);
        reset_owner;issue_warm;receipt(3);
        // A protection fault arriving while the actual commit is held must
        // quarantine debt even if the matching receipt arrives later.
        reset_owner;issue_warm;
        @(negedge clk);poison[56]=1;
        repeat(4) @(posedge clk);
        @(negedge clk);ack_v=1;ack_id=committed_id;ack_word=word;ack_mask=mask;
        @(posedge clk);#1;if(!fault||!debt||wa) $fatal(1,"protection fault lost warm debt");
        checks=checks+1;
        @(negedge clk);poison=0;
        reset_owner;
        if(debt||fault) $fatal(1,"reset did not flush owner state");
        // An old post-reset receipt with no owned transaction is rejected.
        @(negedge clk);ack_v=1;ack_word=word;ack_mask=mask;
        @(posedge clk);#1;if(!fault||wa) $fatal(1,"stale reset receipt accepted");
        reset_owner;
        $display("PASS G4W16 parent real-held-commit identity/debt/quarantine/reset invalid-marker checks=%0d",checks);
        $finish;
    end
endmodule
