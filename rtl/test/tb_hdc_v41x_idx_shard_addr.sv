`timescale 1ns/1ps
module tb_hdc_v41x_idx_shard_addr;
    reg [29:0] nkeys,beat;
    reg [1:0] quarter;
    reg [3:0] lane;
    reg [27:0] base_sec;
    wire present;
    wire [29:0] global_key,local_key;
    wire [1:0] stack;
    wire [27:0] scale_sec,code_sec;
    wire [2:0] scale_slot;
    ot_hdc_v41x_idx_shard_addr dut (
        .i_nkeys(nkeys),.i_beat(beat),.i_quarter(quarter),.i_lane(lane),
        .i_base_sec(base_sec),.o_present(present),.o_global(global_key),
        .o_stack(stack),.o_local(local_key),.o_scale_sec(scale_sec),
        .o_scale_slot(scale_slot),.o_code_sec(code_sec));
    integer fd,got;
    reg [1023:0] path;
    initial begin
        if (!$value$plusargs("vectors=%s",path)) $fatal(1,"missing vectors");
        fd=$fopen(path,"r");
        if (fd==0) $fatal(1,"open vectors failed");
        while (!$feof(fd)) begin
            got=$fscanf(fd,"%d %d %d %d %d\n",nkeys,beat,quarter,lane,base_sec);
            if (got==5) begin
                #1;
                $display("A %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",
                         nkeys,beat,quarter,lane,present,global_key,stack,
                         local_key,scale_sec,scale_slot,code_sec);
            end
        end
        $fclose(fd);
        $finish;
    end
endmodule
