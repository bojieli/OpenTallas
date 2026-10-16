`timescale 1ns/1ps
module tb_hbm_sm_pv_publish;
    parameter integer MUT=0;
    reg clk=0,rst_n=0,ev=0,pub_start=0;
    reg [511:0] sum=0;
    reg [15:0] tag_d=0;
    reg [2:0] pub_slot=0;
    reg fold_start=0; reg [2:0] fold_a=0, fold_b=0;
    wire pv_v,pub_v,fault;
    wire [511:0] pv_y;
    wire [15:0] pv_tag,pub_tag;
    wire [31:0] pub_data;
    wire [3:0] pub_word;
    wire [2:0] pub_out_slot;
    always #0.5 clk=~clk;
    ot_hbm_sm_pv_merge #(.PUBLISH(1),.MUT(MUT)) u_dut(.*);
    function automatic [31:0] word(input integer slot,input integer lane);
        word=32'h40000000+32'((slot*16+lane)*8192);
    endfunction
    integer cyc=0,nodes=0,seen=0,first_request=-1,previous_output=-1;
    reg check_enable=1;
    always @(posedge clk)begin
        cyc=cyc+1;
        if(pub_start && first_request<0)first_request=cyc;
        #0.01;
        if(rst_n && check_enable)begin
            if(fault)$fatal(1,"unexpected merge/publication fault");
            if(pv_v)nodes=nodes+1;
            if(pub_v)begin
                if(pub_out_slot !== 3'(seen/16) || pub_word !== 4'(seen%16) ||
                   pub_tag[2:0] !== 3'(seen/16) || pub_data !== word(seen/16,seen%16))
                    $fatal(1,"publication data/tag/order mismatch word=%0d",seen);
                if(seen==0 && cyc-first_request!=2)$fatal(1,"first scalar must arrive2edges after request");
                if(seen>0 && cyc!=previous_output+1)$fatal(1,"unexpected publication bubble");
                previous_output=cyc;seen=seen+1;
            end
        end
    end
    integer s,l,t,c;
    initial begin
        repeat(4)@(negedge clk);rst_n=1;
        repeat(4)@(negedge clk);
        // Four canonical chunks per slot exercise real carries and the flush.
        // Each chunk is exactly one quarter of the expected final word.
        for(c=0;c<4;c=c+1)begin
            for(s=0;s<8;s=s+1)begin
                @(negedge clk);ev=1;tag_d={1'b1,(c==0),(c==3),10'd0,3'(s)};
                for(l=0;l<16;l=l+1)sum[32*l+:32]=word(s,l)-32'h01000000;
            end
            @(negedge clk);ev=0;
            repeat(55)@(negedge clk);
        end
        wait(nodes==8);
        @(negedge clk);
        for(t=0;t<128;t=t+1)begin
            @(negedge clk);pub_start=(t%16==0);pub_slot=3'(t/16);
        end
        @(negedge clk);pub_start=0;
        repeat(5)@(negedge clk);
        if(seen!=128 || nodes!=8)$fatal(1,"count mismatch nodes=%0d words=%0d",nodes,seen);
        $display("PASS shared real64x512 stack publication128words, fixed2edge first scalar, no bubbles");
        check_enable=0;
        // An event colliding with a publication request must fault, without
        // moving the compiler's request to some later available cycle.
        @(negedge clk);ev=1;pub_start=1;pub_slot=0;tag_d=16'he000;
        @(negedge clk);ev=0;pub_start=0;
        repeat(3)@(negedge clk);
        if(!fault)$fatal(1,"publication/merge port collision did not fault");
        $display("PASS conflicting compiled merge/publication slot fails closed");
        $finish;
    end
    initial begin #5000;$fatal(1,"timeout");end
endmodule
