`timescale 1ns/1ps
module tb_hdc_v41x_idx_stack_major_ingest;
    localparam IW=30, KW=544;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, cmd_v=0, i_valid=0;
    reg [1:0] cmd_stack=0;
    reg [IW-1:0] cmd_first_local=0, cmd_count=0, cmd_nkeys=0;
    reg [15:0] i_kv=0;
    reg [16*KW-1:0] i_key=0;
    reg [3:0] lane_ready=4'hf;
    wire i_ready, fault;
    wire [3:0] lane_valid;
    wire [15:0] lane_kv;
    wire [16*KW-1:0] lane_key;
    wire [4*IW-1:0] lane_first_local;
    wire [7:0] lane_stack;
    wire [IW-1:0] quarter_size;
    integer beats=0, checked=0;
    ot_hdc_v41x_idx_stack_major_ingest #(.IW(IW),.KW(KW)) dut (.*);

    task automatic run_stack(input integer n, input integer stack_id,
                             input integer first_local, input integer count);
        integer off, rem, take, idx, qs, q;
        begin
            @(negedge clk);
            cmd_v=1; cmd_stack=stack_id; cmd_first_local=first_local; cmd_count=count; cmd_nkeys=n;
            @(negedge clk);cmd_v=0;
            qs=(n>>5)<<3;
            for(off=0;off<count;off=off+take) begin
                rem=count-off;take=rem>16 ? 16 : rem;
                i_valid=1;i_kv=(1<<take)-1;
                for(integer k=0;k<16;k=k+1)
                    i_key[KW*k +: KW]=KW'(first_local+off+k);
                lane_ready=4'b1011;
                #1;
                if(i_ready || lane_valid!=0) $fatal(1,"non-atomic four-lane stall");
                @(negedge clk);
                lane_ready=4'hf;
                #1;
                if(!i_ready || lane_valid!=4'hf || lane_kv!=i_kv || lane_key!=i_key)
                    $fatal(1,"lane transfer mismatch");
                for(integer k=0;k<take;k=k+1) begin
                    idx=64*((first_local+off+k)>>4)+16*stack_id+((first_local+off+k)&15);
                    q=(qs==0) ? 3 : (idx<qs ? 0 : (idx<2*qs ? 1 : (idx<3*qs ? 2 : 3)));
                    if(lane_first_local[IW*(k/4) +: IW]+(k%4)!==
                       IW'(first_local+off+k) ||
                       lane_stack[2*(k/4) +: 2]!==2'(stack_id) ||
                       quarter_size!==IW'(qs) || idx>=n)
                        $fatal(1,"rank metadata mismatch local=%0d stack=%0d",
                               first_local+off+k,stack_id);
                    checked++;
                end
                beats++;
                @(posedge clk);#1;i_valid=0;
                @(negedge clk);
            end
            i_valid=0;i_kv=0;
            @(negedge clk);
            if(fault) $fatal(1,"unexpected range fault");
        end
    endtask

    initial begin
        repeat(3) @(negedge clk);rst_n=1;
        // Reduced nonuniform last quarter: the final 16 keys are on stack 0.
        for(integer s=0;s<4;s=s+1) run_stack(1040,s,0,s==0 ? 272 : 256);
        // Shipped per-die 1M context: 262144 keys, 65536 per stack.
        for(integer s=0;s<4;s=s+1) run_stack(262144,s,0,65536);
        $display("PASS stack-major ingest beats=%0d keys=%0d",beats,checked);
        $finish;
    end
endmodule
