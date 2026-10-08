`timescale 1ns/1ps
module tb_window_column_split;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [31:0] row_we=0;
    reg [255:0] write_data=0;
    reg read_v=0;
    reg [4:0] read_addr=0;
    wire [255:0] q256, qsplit;
    ot_dsrom_window_column_256_split split128(clk,rst_n,row_we,write_data,read_v,read_addr,qsplit);
    wire [127:0] q128;
    ot_dsrom_window_column #(.WIDTH(256)) dut256(clk,rst_n,row_we,write_data,read_v,read_addr,q256);
    ot_dsrom_window_column #(.WIDTH(128)) dut128(clk,rst_n,row_we,write_data[127:0],read_v,read_addr,q128);
    reg [255:0] reference [0:31];
    reg [255:0] captured, expected;
    reg valid=0;
    integer checks=0, collisions=0;
    reg [31:0] rng=32'h19572ae1;
    integer mutation=0;
    always @(negedge rst_n) valid=0;
    always @(posedge clk) begin
        if(rst_n && valid) expected=captured;
        valid=rst_n && read_v;
        if(read_v) begin
            captured=reference[read_addr];
            if(row_we[read_addr]) collisions=collisions+1;
        end
        for(integer i=0;i<32;i=i+1)
            if(row_we[i]) reference[i]=write_data;
        #1;
        if(qsplit !== (expected ^ (mutation && checks>100 ? 256'd1 : 256'd0)) || q256 !== expected || q128 !== expected[127:0])
            $fatal(1,"column mismatch check=%0d actual=%h expected=%h", checks,q256,expected);
        checks=checks+1;
    end
    task tick;
        begin
            @(negedge clk);
            rng=rng^(rng<<13); rng=rng^(rng>>17); rng=rng^(rng<<5);
            write_data={rng,~rng,rng+32'd1,rng-32'd1,rng^32'habcdef21,rng<<7,rng>>3,rng};
        end
    endtask
    initial begin
        mutation=$test$plusargs("mutant");
        repeat(2) tick(); rst_n=1;
        // Initialize every physical row and then read all addresses.
        for(integer i=0;i<32;i=i+1) begin row_we=32'b1<<i; tick(); end
        row_we=0; read_v=1;
        for(integer i=0;i<32;i=i+1) begin read_addr=5'(i); tick(); end
        // Same-row read/write, bubbles, multi-row writes, and payload retention.
        for(integer i=0;i<1500;i=i+1) begin
            read_addr=rng[4:0]; read_v=rng[5];
            row_we=rng[6] ? 32'b1<<read_addr : rng;
            if(i==700) rst_n=0;
            if(i==703) rst_n=1;
            tick();
        end
        row_we=0; read_v=0; repeat(3) tick();
        if(collisions<100 || checks<1500) $fatal(1,"coverage missing");
        $display("PASS column split width128+256+2x128 checks=%0d read_write_collisions=%0d added_cycles=0",checks,collisions);
        $finish;
    end
endmodule
