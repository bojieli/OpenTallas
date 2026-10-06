`timescale 1ns/1ps
module tb_dsrom_reindex_counter_split;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [31:0] accept[0:127];
    reg [1:0] fc[0:127];
    reg [63:0] beat[0:7];
    wire [19:0] count[0:127];
    reg [4:0] reference[0:511];
    reg [31:0] rng=32'h194aa70b;
    integer comparisons=0,aliases=0;
    integer mutation=0;
    generate for(genvar s=0;s<128;s=s+1) begin:g_slot
        ot_dsrom_reindex_counter_slot dut(clk,rst_n,accept[s],fc[s],beat[s/16],count[s]);
    end endgenerate
    integer p,e,c;
    reg [3:0] next_bits;
    // The original global array and PC-major loop, including last-assignment
    // priority and old-value NBA semantics for aliased accepted responses.
    always @(posedge clk) begin
        if(!rst_n) begin
            for(p=0;p<512;p=p+1) reference[p]<=0;
        end else begin
            for(p=0;p<32;p=p+1) for(e=0;e<128;e=e+1) if(accept[e][p]) begin
                c=(p^fc[e])&3;
                next_bits=reference[e*4+c][3:0] | (4'b0001<<beat[e/16][p*2+:2]);
                reference[e*4+c]<=(&next_bits)?5'd0:{^next_bits,next_bits};
            end
        end
        #1;
        for(integer s=0;s<128;s=s+1) for(integer k=0;k<4;k=k+1) begin
            if(count[s][5*k+:5] !== (reference[4*s+k] ^ (mutation && comparisons>1000 ? 5'd1 : 5'd0)))
                $fatal(1,"counter split mismatch slot=%0d counter=%0d check=%0d",s,k,comparisons);
            comparisons=comparisons+1;
        end
    end
    task randomize_inputs;
        begin
            @(negedge clk);
            for(integer g=0;g<8;g=g+1) begin
                rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
                beat[g]={rng,~rng};
            end
            for(integer s=0;s<128;s=s+1) begin
                rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
                fc[s]=rng[1:0];accept[s]=rng;
                if((rng&32'h11111111)!=0 && (rng&32'h11111111)!=(rng&-rng)) aliases=aliases+1;
            end
        end
    endtask
    initial begin
        mutation=$test$plusargs("mutant");
        for(integer s=0;s<128;s=s+1)begin accept[s]=0;fc[s]=0;end
        for(integer g=0;g<8;g=g+1)beat[g]=0;
        repeat(2) randomize_inputs();rst_n=1;
        repeat(500) randomize_inputs();
        rst_n=0;repeat(2)randomize_inputs();rst_n=1;
        repeat(500) randomize_inputs();
        if(aliases<1000) $fatal(1,"priority collision coverage missing");
        $display("PASS full128slots512counters checks=%0d aliases=%0d added_cycles=0",comparisons,aliases);
        $finish;
    end
endmodule
