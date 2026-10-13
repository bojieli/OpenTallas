`timescale 1ns/1ps
module tb_hgi_sfu_wm;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, begin_v=0;
    reg [3:0] tag=0;
    reg [2:0] base=0;
    reg [14:0] count=0;
    reg [7:0] done=0, issue=0;
    wire [19:0] wm; wire fault;
`ifndef MUT_WM
`define MUT_WM 0
`endif
    ot_hgi_sfu_wm #(.MUT_WM(`MUT_WM)) dut(clk,rst_n,begin_v,tag,base,count,done,issue,wm,fault);
    bit committed[0:63]; integer consumed, last_wm, errors=0;
    // Consumer may read every sector below the advertised prefix; stale data fails.
    always @(negedge clk) if (rst_n && !begin_v && wm[19]) begin
        if (wm[18:15] != tag || wm[14:0] < last_wm || wm[14:0] > count) errors++;
        for(integer k=consumed;k<int'(wm[14:0]);k++) if(!committed[k]) begin
            $display("STALE sector=%0d wm=%0d tag=%0d",k,wm[14:0],tag); errors++;
        end
        consumed=wm[14:0]; last_wm=wm[14:0];
    end
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        // Rotate the base across every lane, with unequal tail lane counts.
        for(integer r=0;r<8;r++) begin
            @(negedge clk); begin_v=1; tag=4'(r); base=3'(r); count=15'(25+r);
            consumed=0; last_wm=0; foreach(committed[k]) committed[k]=0;
            @(negedge clk); begin_v=0;
            // Issue a full lane wave, then stall its writes long enough that
            // an issue-counted watermark reaches the consumer before memory.
            for(integer first=0;first<int'(count);first+=8) begin
                for(integer k=first;k<first+8 && k<int'(count);k++) issue[(r+k)%8]=1;
                @(negedge clk); issue=0;
                repeat(9) @(negedge clk);
                // Complete in reverse lane order to exercise the min tree.
                for(integer k=first+7;k>=first;k--) if(k<int'(count)) begin
                    done[(r+k)%8]=1; committed[k]=1;
                    @(negedge clk); done=0;
                end
            end
            repeat(8) @(negedge clk);
            if(consumed!=count || fault) errors++;
        end
        if(errors) $fatal(1,"SFU_WM FAIL errors=%0d",errors);
        $display("SFU_WM PASS 8 rotated records, committed prefix exact"); $finish;
    end
endmodule
