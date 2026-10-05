`timescale 1ns/1ps
module tb_fh_sram_return;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [3:0] rd_en=0,wr_en=0;
    reg [95:0] rd_addr=0,wr_addr=0;
    reg [63:0] wr_mask=0;
    reg [2047:0] wr_data=0;
    wire [2047:0] rd_data;
    wire [63:0] rd_valid,corrected,poisoned,wr_committed;
    wire fault;
    ot_hdc_v41_fh_sram_return dut(.*);
    function automatic [31:0] value(input integer row,input integer bank);
        value=32'h3f000000 ^ (row<<7) ^ bank;
    endfunction
    integer r,b,g,accepted=0,released=0,writes=0,ces=0;
    reg check_stream=0,warm=0;
    reg [3:0] ev0=0,ev1=0,ev2=0;
    reg [8:0] er0[0:3],er1[0:3],er2[0:3];
    always @(posedge clk) begin
        if(!rst_n) begin ev0<=0;ev1<=0;ev2<=0;end
        else begin
            ev0<=rd_en;ev1<=ev0;ev2<=ev1;
            for(integer q=0;q<4;q=q+1) begin
                er0[q]<=rd_addr[24*q+:24]>>2;er1[q]<=er0[q];er2[q]<=er1[q];
            end
        end
    end
    always @(negedge clk) if(rst_n) begin
        for(integer q=0;q<64;q=q+1) begin
            if(wr_committed[q]) writes=writes+1;
            if(corrected[q]) ces=ces+1;
            if(check_stream) begin
                if(rd_valid[q]!==ev2[q/16]) $fatal(1,"valid/debt lane%0d got%b expected%b",q,rd_valid[q],ev2[q/16]);
                if(ev2[q/16]) begin
                    if(rd_data[32*q+:32] !== ((warm&&er2[q/16]==73&&q%2==0)?32'h40400000^q:value(er2[q/16],q)))
                        $fatal(1,"payload/identity/mask lane%0d row%0d got%x",q,er2[q/16],rd_data[32*q+:32]);
                    released=released+1;
                end
            end
        end
    end
    task idle(input integer n);
        begin rd_en=0;wr_en=0;wr_mask=0;repeat(n) @(negedge clk);end
    endtask
    task read_round(input integer row);
        begin for(integer q=0;q<4;q=q+1) rd_addr[24*q+:24]=4*row+q;
            rd_en=4'hf;accepted=accepted+64;@(negedge clk);end
    endtask
    task poison_read(input integer kind);
        begin
            check_stream=0;
            for(integer q=0;q<4;q=q+1) rd_addr[24*q+:24]=4*9+q;
            rd_en=4'hf;@(negedge clk);rd_en=0;
            @(negedge clk);#1;
            if(kind==1) dut.g_bank[0].raw_word_r=dut.g_bank[0].raw_word_r^55'b1;
            if(kind==2) dut.g_bank[0].raw_word_r=dut.g_bank[0].raw_word_r^55'b11;
            if(kind==3) dut.g_bank[0].raw_word_r=dut.g_bank[1].raw_word_r;
            @(negedge clk);#1;
            if(kind==1) begin
                if(fault||!corrected[0]||!rd_valid[0]||rd_data[31:0]!==value(9,0)) $fatal(1,"single-bit correction");
            end else if(!fault||rd_valid[0]||!poisoned[0]) $fatal(1,"bad word released kind%0d",kind);
            idle(5);
        end
    endtask
    initial begin
        repeat(4) @(negedge clk);rst_n=1;
        // Full rank shape, every independently masked lane and every used row.
        for(r=0;r<505;r=r+1) begin
            wr_en=4'hf;wr_mask=64'hffff_ffff_ffff_ffff;
            for(g=0;g<4;g=g+1) wr_addr[24*g+:24]=4*r+g;
            for(b=0;b<64;b=b+1) wr_data[32*b+:32]=value(r,b);
            @(negedge clk);
        end
        idle(8);check_stream=1;
        for(r=0;r<505;r=r+1) begin read_round(r);if(r%17==0) idle(1);end
        idle(8);
        if(fault||released!=accepted||writes!=505*64) $fatal(1,"full rank debt accepted%0d released%0d writes%0d",accepted,released,writes);
        check_stream=0;
        // Warm update writes only even lanes; odd lanes keep their old words.
        wr_en=4'hf;wr_mask=64'h5555_5555_5555_5555;
        for(g=0;g<4;g=g+1) wr_addr[24*g+:24]=4*73+g;
        for(b=0;b<64;b=b+1) wr_data[32*b+:32]=32'h40400000^b;
        @(negedge clk);idle(8);warm=1;check_stream=1;
        read_round(73);read_round(74);idle(8);
        if(fault||released!=accepted||writes!=505*64+32) $fatal(1,"warm masked debt");
        poison_read(1);poison_read(2);
        rst_n=0;idle(4);rst_n=1;idle(4);
        if(fault||(|rd_valid)) $fatal(1,"reset retained debt/fault");
        poison_read(3);
        rst_n=0;idle(4);rst_n=1;idle(4);check_stream=1;
        read_round(73);idle(8);
        if(fault||released!=accepted) $fatal(1,"warm contents after reset");
        check_stream=0;rd_en=1;rd_addr[23:0]=2020;
        @(negedge clk);rd_en=0;idle(5);
        if(!fault) $fatal(1,"505-row address bound missed");
        $display("PASS FH SRAM G4W16 rows505 accepted=%0d released=%0d writes=%0d CE=%0d protected-identity-warm-mask-debt",accepted,released,writes,ces);
        $finish;
    end
endmodule
