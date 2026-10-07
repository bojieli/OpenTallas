`timescale 1ns/1ps
module tb_core_replay;
    import ot_gpu_w6_secded_pkg::*;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,return_valid=0;
    reg [9215:0] return_code=0;
    reg [15:0] return_tag=0;
    reg [6:0] return_addr=0;
    wire core_valid,corrected,fault;
    wire [8191:0] core_data;
    wire [15:0] core_tag;
    wire [6:0] core_addr;
    integer cycle=0,issued=0,received=0,row_id=0;
    integer queued_row[0:127],queued_cycle[0:127];
    reg [15:0] queued_tag[0:127];
    reg [6:0] queued_addr[0:127];
    reg inject_single=0;
    reg queued_correction[0:127];
    ot_dsrom_softmax_core_replay dut(.*);
    function automatic [63:0] payload(input integer row,input integer lane);
        payload=64'h9e3779b97f4a7c15*(64'(row*128+lane)+1);
    endfunction
    always @(posedge clk)begin
        cycle<=cycle+1;
        if(!rst_n)begin issued<=0;received<=0;end
        else begin
            if(return_valid)begin
                queued_row[issued]<=row_id;queued_cycle[issued]<=cycle;
                queued_tag[issued]<=return_tag;queued_addr[issued]<=return_addr;
                queued_correction[issued]<=inject_single;issued<=issued+1;
            end
            if(core_valid)begin
                if(fault || received>=issued || cycle-queued_cycle[received]!=3)$fatal(1,"LATENCY_OR_IDENTITY");
                if(core_tag!==queued_tag[received] || core_addr!==queued_addr[received] || corrected!==queued_correction[received])$fatal(1,"METADATA_ALIGNMENT");
                for(integer lane=0;lane<128;lane=lane+1)
                    if(core_data[64*lane +:64]!==payload(queued_row[received],lane))$fatal(1,"CORE_PAYLOAD row=%0d lane=%0d",queued_row[received],lane);
                received<=received+1;
            end
        end
    end
    task automatic reset;
        @(negedge clk);rst_n=0;return_valid=0;
        repeat(2)@(negedge clk);rst_n=1;
        @(posedge clk);#1;if(fault||core_valid)$fatal(1,"RESET");
    endtask
    task automatic burst(input integer first_row,input integer count,input integer base_addr,input [15:0] tag);
        for(integer row=0;row<count;row=row+1)begin
            @(negedge clk);row_id=first_row+row;return_valid=1;
            return_tag=tag;return_addr=7'(base_addr+row);
            for(integer lane=0;lane<128;lane=lane+1)return_code[72*lane +:72]=encode64(payload(row_id,lane));
            inject_single=(row%7==0);
            if(inject_single)return_code=return_code^(9216'b1<<(72*(row%128)+row%72));
        end
        @(negedge clk);return_valid=0;
        repeat(4)@(negedge clk);
        if(fault||received!=issued)$fatal(1,"BURST_DRAIN");
    endtask
    initial begin
        reset();burst(0,40,0,16'h1200);burst(40,32,40,16'h1200);burst(72,8,0,16'h1201);
        if(received!=80)$fatal(1,"FULL_SHAPE_COUNT");
        $display("BURST_PASS vectors=%0d payload_bytes=%0d II=1 return_to_consume_edges=3",received,received*1024);
        @(negedge clk);return_valid=1;inject_single=0;row_id=80;return_tag=16'h1202;return_addr=0;
        for(integer lane=0;lane<128;lane=lane+1)return_code[72*lane +:72]=encode64(payload(row_id,lane));
        return_code=return_code^(9216'b1<<(72*127+2))^(9216'b1<<(72*127+3));
        @(negedge clk);return_valid=0;
        repeat(5)@(negedge clk);
        if(!fault||core_valid||received!=80)$fatal(1,"UE_NOT_ABORTED");
        reset();
        @(negedge clk);return_valid=1;row_id=0;inject_single=0;
        for(integer lane=0;lane<128;lane=lane+1)return_code[72*lane +:72]=encode64(payload(row_id,lane));
        @(posedge clk);#1;reset();
        repeat(4)@(negedge clk);if(core_valid||received!=0)$fatal(1,"STALE_AFTER_RESET");
        burst(0,1,0,16'h1203);
        force dut.identity1_n=23'd0;#1;if(!fault)$fatal(1,"IDENTITY_UPSET_ESCAPED");
        @(posedge clk);#1;release dut.identity1_n;
        $display("PASS full8192-bit II1 score40/PV32/score8 bursts, single-bit correction, UE/reset/identity negatives");
        $finish;
    end
endmodule
