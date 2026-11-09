`timescale 1ns/1ps
module tb_sm_local_ctrl;
    parameter integer MUT=0;
    reg clk=0, rst=0, d=0, v=0;
    always #1 clk=~clk;
    reg old_r0, old_r1, new_r0;
    always @(posedge clk or negedge rst)
        if(!rst)begin old_r0<=0;old_r1<=0;new_r0<=0;end
        else begin old_r0<=1;old_r1<=old_r0;new_r0<=1;end
    wire[5:0] rn;
    genvar g;
    generate for(g=0;g<6;g=g+1)begin:R
        ot_svc_sm_keep_bit u(.clk(clk),.rst_n(rst),.d(new_r0),.q(rn[g]));
    end endgenerate
    reg old_pending, data_prev, data_old;
    always @(posedge clk or negedge old_r1)
        if(!old_r1)old_pending<=0;else old_pending<=v;
    always @(posedge clk)begin data_prev<=d;data_old<=data_prev;end
    wire[4:0] pending_copy, data_copy;
    generate for(g=0;g<5;g=g+1)begin:C
        ot_svc_sm_keep_bit p(.clk(clk),.rst_n(rn[0]),.d(v),.q(pending_copy[g]));
        ot_svc_sm_keep_bit #(.RESET(0))q(.clk(clk),.rst_n(rst),
            .d((MUT!=0&&g==3)?~data_prev:data_prev),.q(data_copy[g]));
    end endgenerate
    integer checks=0,errors=0,seed=1108,i;
    always @(negedge clk)begin
        for(integer k=0;k<6;k++)begin if(rn[k]!==old_r1)errors++;checks++;end
        for(integer k=0;k<5;k++)begin
            if(pending_copy[k]!==old_pending)errors++;
            if(data_copy[k]!==data_old)errors++;
            checks+=2;
        end
    end
    initial begin
        seed=$urandom(seed);
        for(i=0;i<2000;i++)begin
            #0.37; rst=(i%73>3);d=1'($urandom);v=1'($urandom);
            #0.63;
        end
        #3;
        if(errors)$fatal(1,"LOCAL_CTRL FAIL checks%0d errors%0d MUT%0d",checks,errors,MUT);
        $display("LOCAL_CTRL PASS checks%0d MUT%0d",checks,MUT);$finish;
    end
endmodule
