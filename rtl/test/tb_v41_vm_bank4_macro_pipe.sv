`timescale 1ns/1ps
module tb_v41_vm_bank4_macro_pipe;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0,rd_v=0;
    reg [14:0] rd_base_word=0;
    wire rd_out_v;
    wire [1:0] rd_out_rot;
    wire [2047:0] rd_out_bank_words;
    wire rd_fault,wr_fault,rw_collision_fault;
    reg [3:0] wr_v=0;
    reg [59:0] wr_word_addr=0;
    reg [2047:0] wr_word_data=0;
    ot_v41_vm_bank4_macro_pipe #(.DEPTH_GROUPS(3)) dut (.*);

    function automatic [511:0] pattern(input integer word_addr);
        integer e;
        begin
            pattern=0;
            for (e=0;e<16;e=e+1)
                pattern[e*32 +:32] = 32'h3f000000 ^ (word_addr<<9) ^ e;
        end
    endfunction
    task automatic check_beat(input integer base, input integer beat);
        integer b,delta,a;
        begin
            if (!rd_out_v) $fatal(1,"missing beat base=%0d beat=%0d",base,beat);
            if (rd_out_rot !== base[1:0])
                $fatal(1,"rotation mismatch base=%0d got=%0d",base,rd_out_rot);
            for (b=0;b<4;b=b+1) begin
                delta=(b-(base&3)+4)&3;
                a=base+4*beat+delta;
                if (rd_out_bank_words[b*512 +:512] !== pattern(a))
                    $fatal(1,"bank %0d base=%0d beat=%0d word=%0d mismatch",b,base,beat,a);
            end
        end
    endtask
    task automatic write_region(input integer base);
        integer beat,b,delta,a;
        begin
            for (beat=0;beat<8;beat=beat+1) begin
                @(negedge clk);
                wr_v=4'hf;
                for (b=0;b<4;b=b+1) begin
                    delta=(b-(base&3)+4)&3;
                    a=base+4*beat+delta;
                    wr_word_addr[b*15 +:15]=a;
                    wr_word_data[b*512 +:512]=pattern(a);
                end
                @(posedge clk); #1;
                if (wr_fault || rw_collision_fault) $fatal(1,"write fault");
            end
            @(negedge clk);
            wr_v=0;
            repeat (3) @(posedge clk);
        end
    endtask
    task automatic read_region(input integer base);
        integer beat;
        begin
            for (beat=0;beat<8;beat=beat+1) begin
                @(negedge clk);
                rd_v=1;
                rd_base_word=base+4*beat;
                #1;
                if (rd_fault) $fatal(1,"read fault at %0d",rd_base_word);
                @(posedge clk);
                #1;
                if (beat>=4) check_beat(base,beat-4);
            end
            @(negedge clk); rd_v=0;
            for (integer drain=4;drain<8;drain=drain+1) begin
                @(posedge clk); #1;
                check_beat(base,drain);
            end
        end
    endtask

    initial begin
        repeat (2) @(posedge clk);
        @(negedge clk); rst_n=1;
        // Checkpoint ACC element base 74272 = logical 512-bit word 4642,
        // requiring rotation 2 and depth group 2.
        write_region(4642);
        read_region(4642);
        // Span the 512-row boundary between depth groups 0 and 1.
        write_region(2047);
        read_region(2047);
        write_region(0);
        read_region(0);
        @(negedge clk); wr_v=4'b0001; wr_word_addr[14:0]=15'd1;
        @(posedge clk); #1;
        if (!wr_fault) $fatal(1,"missing wrong-bank write fault");
        @(negedge clk); wr_v=4'b0001; wr_word_addr[14:0]=15'd0;
        rd_v=1; rd_base_word=0;
        @(posedge clk); #1;
        if (!rw_collision_fault) $fatal(1,"missing same-word read/write collision");
        @(negedge clk); wr_v=0; rd_v=0;
        @(negedge clk); rd_v=1; rd_base_word=6143;
        @(posedge clk); #1;
        if (!rd_fault) $fatal(1,"missing out-of-range fault");
        $display("PASS bank4 pipelined 3-group slice: 24 beats, 96 words, rotations 2/3/0, depth carry, range/bank/collision checks");
        $finish;
    end
endmodule
