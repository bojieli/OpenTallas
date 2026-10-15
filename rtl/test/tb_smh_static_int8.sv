module tb_smh_static_int8;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [1098:0] source=0;
    wire [1098:0] result;
    ot_smh_static_int8 dut(clk,rst_n,source,result);
    reg [1098:0] expected [0:8200];
    integer c,lane,word_index=0,checks=0;
    reg [7:0] code;
    reg [1023:0] lo,hi;
    reg [9:0] tag;
    // Independent integer normalization reference; every signed byte is exact.
    function automatic [15:0] golden(input [7:0] x);
        integer signed_value, mag, exponent, fraction, shift;
        begin
            signed_value = x < 128 ? x : x-256;
            mag = signed_value < 0 ? -signed_value : signed_value;
            if (mag==0) golden=0;
            else begin
                if (mag>=128) shift=7;
                else if (mag>=64) shift=6;
                else if (mag>=32) shift=5;
                else if (mag>=16) shift=4;
                else if (mag>=8) shift=3;
                else if (mag>=4) shift=2;
                else if (mag>=2) shift=1;
                else shift=0;
                exponent=127+shift;
                fraction=(mag*128/(1<<shift))-128;
                golden=((signed_value<0)<<15) | (exponent<<7) | fraction;
            end
        end
    endfunction
    initial begin
        for(c=0;c<=8200;c=c+1) expected[c]=0;
        repeat(2) @(negedge clk);
        rst_n=1;
        for(c=0;c<8196;c=c+1) begin
            source=0;
            if(c<8192 && c%2==0 && c%22!=0) begin
                // Deliberately repeat tags and wrap them independently of data.
                tag=(word_index/3)%1024;
                source[1098]=1;
                source[1097:1088]=tag;
                source[1087:1024]=64'h0123456789abcdef;
                for(lane=0;lane<128;lane=lane+1) begin
                    code=(word_index*73+lane*17)%256;
                    source[8*lane+:8]=code;
                    if(lane<64) lo[16*lane+:16]=golden(code);
                    else hi[16*(lane-64)+:16]=golden(code);
                end
                expected[c+1]={1'b1,tag,64'd0,lo};
                expected[c+2]={1'b1,tag,64'd0,hi};
                word_index=word_index+1;
            end
`ifdef OT_STATIC_INT8_MUT_CALENDAR
            if(c==3) source[1098]=1;
`endif
            @(posedge clk); #1;
            if(result[1098] !== expected[c][1098])
                $fatal(1,"valid edge %0d got %b expected %b",c,result[1098],expected[c][1098]);
            if(expected[c][1098]) begin
                if(result !== expected[c]) $fatal(1,"payload/tag edge %0d",c);
                checks=checks+1;
            end
            @(negedge clk);
        end
        if(checks!=2*word_index || word_index<3700) $fatal(1,"count");
        // Reset must flush a pending high half and the classified low half.
        source[1098]=1;
        @(posedge clk); #1;
        @(negedge clk); rst_n=0; source=0;
        @(posedge clk); #1;
        if(result[1098]!==0) $fatal(1,"reset did not flush");
        @(negedge clk); rst_n=1;
        repeat(3) begin @(posedge clk); #1; if(result[1098]!==0) $fatal(1,"stale after reset"); end
        $display("PASS actual static INT8: %0d packed lines, %0d full1099bit outputs, II2 input/II1 output, bubbles/repeated tags/reset",word_index,checks);
        $finish;
    end
endmodule
