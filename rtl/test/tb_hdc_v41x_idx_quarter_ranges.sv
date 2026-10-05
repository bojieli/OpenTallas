`timescale 1ns/1ps
module tb_hdc_v41x_idx_quarter_ranges;
    reg [29:0] n;
    wire [16*30-1:0] first,count;
    wire [16*20-1:0] base;
    wire [16*10-1:0] skip;
    ot_hdc_v41x_idx_quarter_ranges dut (
        .i_nkeys(n),.i_base_block(20'd1088),
        .o_first_local(first),.o_count(count),.o_base_block(base),.o_skip(skip));
    integer fd,got;
    reg [1023:0] path;
    initial begin
        if(!$value$plusargs("vectors=%s",path)) $fatal(1,"missing vectors");
        fd=$fopen(path,"r");
        if(fd==0) $fatal(1,"open vectors failed");
        while(!$feof(fd)) begin
            got=$fscanf(fd,"%d\n",n);
            if(got==1) begin
                #1;
                for(integer i=0;i<16;i=i+1)
                    $display("R %0d %0d %0d %0d %0d %0d",n,i,
                             first[i*30 +:30],count[i*30 +:30],
                             base[i*20 +:20],skip[i*10 +:10]);
            end
        end
        $fclose(fd);$finish;
    end
endmodule
