`timescale 1ns/1ps
module tb_serial_row;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,wr_valid=0,mem_w_ready=0,rd_valid=0,out_ready=0;
    reg [1023:0] wr_data=0;
    reg [2:0] wr_beat=0;
    reg [6:0] wr_addr=0,rd_addr=0;
    reg [15:0] wr_tag=0,rd_tag=0;
    wire wr_ready,mem_w_valid,rd_ready,mem_r_en,out_valid,out_corrected,fault;
    wire [6:0] mem_w_addr,mem_r_addr;
    wire [15:0] mem_r_tag;
    wire [9215:0] mem_w_code;
    reg mem_return_valid=0;
    reg [15:0] mem_return_tag=0;
    reg [9215:0] mem_return_code=0,read_mask=0;
    reg corrupt_return_tag=0;
    wire [1023:0] out_data;
    wire [2:0] out_beat;
    wire [15:0] out_tag;
    reg [9215:0] memory[0:127];
    integer cycle=0,writes=0,checks=0,last_write_cycle=0;
    reg held_valid=0;
    reg [1043:0] held_output;
    ot_dsrom_softmax_serial_row dut(.*);
    always @(posedge clk)begin
        cycle<=cycle+1;
        mem_return_valid<=rst_n&&mem_r_en;
        if(mem_w_valid&&mem_w_ready)begin memory[mem_w_addr]<=mem_w_code;writes<=writes+1;last_write_cycle<=cycle;end
        if(mem_r_en)begin mem_return_code<=memory[mem_r_addr]^read_mask;mem_return_tag<=mem_r_tag^{15'd0,corrupt_return_tag};end
        if(!rst_n)held_valid<=0;
        else begin
            if(held_valid && !fault && (!out_valid || {out_corrected,out_tag,out_beat,out_data}!==held_output))$fatal(1,"STALL_OUTPUT_CHANGED");
            held_valid<=out_valid&&!out_ready&&!fault;
            if(out_valid&&!out_ready)held_output<={out_corrected,out_tag,out_beat,out_data};
        end
    end
    function automatic [1023:0] payload(input integer row_id,input integer beat_id);
        for(integer i=0;i<32;i=i+1)
            payload[32*i +:32]=32'h9e3779b9*(32'(row_id*256+beat_id*32+i)+1);
    endfunction
    task automatic reset;
        @(negedge clk);rst_n=0;wr_valid=0;rd_valid=0;out_ready=0;mem_w_ready=0;read_mask=0;corrupt_return_tag=0;
        repeat(2)@(negedge clk);rst_n=1;
        @(posedge clk);#1;if(fault||!wr_ready||!rd_ready)$fatal(1,"RESET");
    endtask
    task automatic write_row(input integer row_id);
        integer last_input,old_writes;
        reg [9215:0] held;
        old_writes=writes;
        mem_w_ready=(row_id==0);
        for(integer beat=0;beat<8;beat=beat+1)begin
            @(negedge clk);wr_valid=1;wr_beat=3'(beat);wr_addr=7'(row_id);wr_tag=16'(row_id+100);wr_data=payload(row_id,beat);
            if(!wr_ready)$fatal(1,"WR_BACKPRESSURE_BEFORE_FULL");
            @(posedge clk);last_input=cycle;#1;if(fault)$fatal(1,"WRITE_FAULT");
        end
        @(negedge clk);wr_valid=0;wr_addr=127;wr_tag=16'hffff;
        @(posedge clk);#1;
        if(!mem_w_valid||wr_ready)$fatal(1,"ROW_COMMIT_BOUNDARY");
        held=mem_w_code;
        if(row_id!=0)begin
            repeat(17)begin @(posedge clk);#1;if(!mem_w_valid||mem_w_code!==held||fault)$fatal(1,"WRITE_HOLD_CHANGED");end
            @(negedge clk);mem_w_ready=1;
        end
        @(posedge clk);#1;if(writes!=old_writes+1)$fatal(1,"MACRO_WRITE_COUNT");
        if(row_id==0 && last_write_cycle-last_input!=2)$fatal(1,"UNPRICED_WRITE_LATENCY");
        @(negedge clk);mem_w_ready=0;
        checks=checks+1;
    endtask
    task automatic read_row(input integer row_id,input integer stall,input integer corrected_expected);
        integer count,steps,request_cycle,first_take,last_take,corrected_count;
        @(negedge clk);rd_addr=7'(row_id);rd_tag=16'(row_id+200);rd_valid=1;out_ready=0;
        if(!rd_ready)$fatal(1,"RD_NOT_READY");
        @(posedge clk);request_cycle=cycle;
        @(negedge clk);rd_valid=0;rd_addr=127;rd_tag=16'hffff;
        count=0;steps=0;corrected_count=0;first_take=0;last_take=0;
        while(count<8 && steps<100)begin
            out_ready=!stall || (steps%5!=0);
            @(posedge clk);
            if(fault)$fatal(1,"READ_FAULT");
            if(out_valid&&out_ready)begin
                if(out_beat!=count||out_tag!=row_id+200||out_data!==payload(row_id,count))$fatal(1,"PAYLOAD_OR_IDENTITY row=%0d beat=%0d",row_id,count);
                if(count==0)first_take=cycle-request_cycle;
                last_take=cycle-request_cycle;corrected_count=corrected_count+out_corrected;
                count=count+1;checks=checks+1;
            end
            @(negedge clk);steps=steps+1;
        end
        out_ready=0;
        if(count!=8||corrected_count!=corrected_expected)$fatal(1,"DRAIN_OR_CORRECTION_COUNT");
        if(!stall && (first_take!=6||last_take!=34))$fatal(1,"UNPRICED_LATENCY first=%0d last=%0d",first_take,last_take);
        $display("READ row=%0d stall=%0d first=%0d last=%0d corrected=%0d",row_id,stall,first_take,last_take,corrected_count);
    endtask
    initial begin
        reset();
        for(integer row_id=0;row_id<4;row_id=row_id+1)begin
            write_row(row_id);read_row(row_id,0,0);
            read_mask=9216'b1<<(1152*3+72*2+10);read_row(row_id,1,1);read_mask=0;
        end
        // Double-bit corruption in one SECDED word must suppress payload.
        read_mask=(9216'b1<<2)|(9216'b1<<3);
        @(negedge clk);rd_valid=1;rd_addr=0;rd_tag=300;out_ready=1;
        @(posedge clk);@(negedge clk);rd_valid=0;
        repeat(6)begin @(posedge clk);if(out_valid)$fatal(1,"UNCORRECTABLE_EMITTED");end
        #1;if(!fault)$fatal(1,"UNCORRECTABLE_ESCAPED");checks=checks+1;
        reset();
        @(negedge clk);wr_valid=1;wr_beat=1;wr_addr=0;wr_tag=1;
        @(posedge clk);#1;if(!fault)$fatal(1,"BAD_BEAT_ESCAPED");checks=checks+1;
        reset();corrupt_return_tag=1;
        @(negedge clk);rd_valid=1;rd_addr=0;rd_tag=300;
        @(posedge clk);@(negedge clk);rd_valid=0;
        repeat(3)@(posedge clk);#1;if(!fault)$fatal(1,"BAD_RETURN_TAG_ESCAPED");checks=checks+1;
        reset();force dut.wc=4'd1;#1;if(!fault)$fatal(1,"COUNTER_UPSET_ESCAPED");
        @(posedge clk);#1;release dut.wc;checks=checks+1;
        $display("PASS checks=%0d protected8beat rows, single-bit correction, UE suppression, stalls, tags/counters; first6 last34 edges",checks);
        $finish;
    end
endmodule
