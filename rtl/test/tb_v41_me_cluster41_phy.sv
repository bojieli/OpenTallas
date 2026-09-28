`timescale 1ns/1ps
module tb_v41_me_cluster41_phy;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, pre_v=0;
    reg [1:0] pre_p=0, rd_rot=2;
    reg [12:0] pre_e=0;
    reg [2047:0] pre_fp32=0;
    reg [7:0] rq_v=0;
    reg [8*14-1:0] rq_q=0;
    reg [8*4-1:0] rq_plg=0;
    reg [40:0] consumer_take={41{1'b1}};
    wire pre_fault,pre_saturated;
    wire [40:0] consumer_valid;
    wire [41*32-1:0] consumer_digest;
    ot_v41_me_cluster41_phy dut (.*);

    reg [2047:0] expected;
    reg [31:0] expected_digest;
    reg [40:0] seen_valid=0;
    reg [31:0] observed_digest [0:40];
    integer i,p,j,k,t,logical_lane;
    always @(posedge clk) if (rst_n)
        for (integer c=0;c<41;c=c+1)
            if (consumer_valid[c]) begin
                seen_valid[c] <= 1'b1;
                observed_digest[c] <= consumer_digest[c*32 +:32];
            end
    task automatic preload(input integer pos);
        begin
            @(negedge clk);
            pre_v=1;
            pre_p=pos[1:0];
            pre_e=0;
            for (integer a=0;a<64;a=a+1) begin
                // ACC base mod64=32: physical quarters 2,3,0,1.
                logical_lane=(a+32)%64;
                pre_fp32[a*32 +:32]=(pos==0 ? 32'h3f800000 : 32'h40000000)
                                     | (logical_lane<<16);
            end
            @(negedge clk);
            pre_v=0;
            repeat (3) @(posedge clk);
        end
    endtask

    initial begin
        for (i=0;i<8;i=i+1) rq_plg[i*4 +:4]=4'd3;
        repeat (2) @(posedge clk);
        @(negedge clk); rst_n=1;
        preload(0);
        preload(1);
        @(negedge clk); rq_v=8'hff;
        @(negedge clk); rq_v=0;
        repeat (4) @(posedge clk);
        #1;
        if (pre_fault || pre_saturated) $fatal(1,"unexpected BF16 preload fault/saturation");
        expected=0;
        for (i=0;i<64;i=i+1) begin
            expected[(i*2+0)*16 +:16]=16'h3f80+i;
            expected[(i*2+1)*16 +:16]=16'h4000+i;
        end
        expected_digest=0;
        for (k=0;k<32;k=k+1)
            for (t=0;t<64;t=t+1)
                expected_digest[k]=expected_digest[k]^expected[k+32*t];
        for (j=0;j<41;j=j+1) begin
            if (!seen_valid[j]) $fatal(1,"consumer %0d missing beat",j);
            if (observed_digest[j] !== expected_digest)
                $fatal(1,"consumer %0d digest mismatch got=%h expected=%h",j,
                       observed_digest[j],expected_digest);
        end
        if (dut.g_consumer[0].operand_q !== expected)
            $fatal(1,"consumer 0 full operand mismatch");
        if (dut.g_consumer[40].operand_q !== expected)
            $fatal(1,"consumer 40 full operand mismatch");
        $display("PASS 41 consumers; bank-major rotation 2; digest=%h",expected_digest);
        $finish;
    end
endmodule
