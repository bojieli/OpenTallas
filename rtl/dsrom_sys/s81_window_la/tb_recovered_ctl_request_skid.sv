`timescale 1ns/1ps
// Minimum production mechanism for the recovered MARGIN2 late-payload mutant.
// MW = HAW30 + LEN4 + TAG16 + WE1 + DATA256 + STRB32 = 339 bits.
module tb_recovered_ctl_request_skid;
    localparam integer W=339;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, in_v=0, out_ready=0;
    reg [W-1:0] in_d=0;
    wire in_ready, out_v;
    wire [W-1:0] out_d;
    ot_dsrom_window_skid #(.W(W), .ZERO_IDLE(1), .PTR(1)) dut
        (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_ready(in_ready),
         .in_d(in_d), .out_v(out_v), .out_ready(out_ready), .out_d(out_d));
    reg [W-1:0] expected [0:2047];
    integer sent=0, received=0, stalls=0, simultaneous=0;
    reg [31:0] rng=32'h5a177903;
    always @(posedge clk) begin
        if(rst_n) begin
            if(out_v && out_ready) begin
                if(received>=sent || out_d !== expected[received])
                    $fatal(1,"REQUEST_PAYLOAD_MISMATCH transaction=%0d actual=%h expected=%h",received,out_d,expected[received]);
                received=received+1;
            end
            if(in_v && in_ready) begin
                expected[sent]=in_d;
                sent=sent+1;
            end
            if(out_v && !out_ready) stalls=stalls+1;
            if(in_v && in_ready && out_v && out_ready) simultaneous=simultaneous+1;
        end
    end
    initial begin
        repeat(3) @(negedge clk);
        rst_n=1;
        for(integer cycle=0;cycle<1200;cycle=cycle+1) begin
            @(negedge clk);
            rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5);
            // Keep an unaccepted offer stable; otherwise generate a new request.
            if(!in_v || in_ready) begin
                in_v=(cycle%7!=0);
                in_d={rng[18:0],{10{rng}}};
            end
            out_ready=(cycle%5!=0 && cycle%5!=1);
        end
        // Finish any outstanding offer before draining the two physical slots.
        out_ready=1;
        while(in_v && !in_ready) @(negedge clk);
        @(negedge clk); in_v=0;
        repeat(4) @(negedge clk);
        if(sent!=received || received<300 || stalls<100 || simultaneous<100)
            $fatal(1,"COVERAGE_OR_DRAIN sent=%0d received=%0d stalls=%0d simultaneous=%0d",sent,received,stalls,simultaneous);
        $display("PASS REQUEST_SKID width=%0d sent=%0d received=%0d stalls=%0d simultaneous=%0d",W,sent,received,stalls,simultaneous);
        $finish;
    end
endmodule
