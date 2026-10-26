`timescale 1ns/1ps
module tb_hbm_sm_attn_pstore;
    parameter integer MUT=0;
    reg clk=0,rst_n=0,clear_v=0,xw_en=0,read_v=0;
    reg [6:0] xw_addr=0,xw_grp=0,read_addr=0;
    reg [2047:0] xw_data=0;
    wire p_v,fault;
    wire [127:0] p_data;
    always #0.5 clk=~clk;
    ot_hbm_sm_attn_pstore #(.MUT(MUT)) u_dut(.*);
    function automatic [127:0] image(input [6:0] addr);
        integer c;
        begin
            for(c=0;c<8;c=c+1)image[16*c+:16]=16'h3f80+16'(8*addr+c);
        end
    endfunction
    reg [2:0] vq=0;
    reg [6:0] aq0=0,aq1=0,aq2=0;
    integer seen=0;
    reg check_enable=1;
    always @(posedge clk)begin
        if(!rst_n)begin vq=0;aq0=0;aq1=0;aq2=0;end
        else begin vq={vq[1:0],read_v};aq2=aq1;aq1=aq0;aq0=read_addr;end
        #0.01;
        if(rst_n && check_enable)begin
            if(p_v !== vq[2])$fatal(1,"fixed read visibility mismatch");
            if(p_v)begin
                if(p_data !== image(aq2))$fatal(1,"probability column/row mismatch row=%0d",aq2);
                seen=seen+1;
            end
        end
    end
    integer i;
    initial begin
        repeat(4)@(negedge clk);rst_n=1;
        @(negedge clk);clear_v=1;
        @(negedge clk);clear_v=0;
        for(i=0;i<128;i=i+1)begin
            @(negedge clk);xw_en=1;xw_grp=127;xw_addr=i[6:0];xw_data={1920'd0,image(i[6:0])};
        end
        @(negedge clk);xw_en=0;
        repeat(3)@(negedge clk);
        for(i=0;i<128;i=i+1)begin
            @(negedge clk);read_v=1;read_addr=i[6:0];
        end
        @(negedge clk);read_v=0;
        repeat(4)@(negedge clk);
        if(seen!=128 || fault)$fatal(1,"positive fail seen=%0d fault=%0d",seen,fault);
        $display("PASS compact probability store128rows x8columns, fixed2edge reads");
        check_enable=0;
        @(negedge clk);clear_v=1;
        @(negedge clk);clear_v=0;
        @(negedge clk);read_v=1;read_addr=7;
        @(negedge clk);read_v=0;
        repeat(4)@(negedge clk);
        if(!fault)$fatal(1,"stale epoch read failed to fault");
        $display("PASS missing current-epoch load faults without changing read timeline");
        $finish;
    end
endmodule
