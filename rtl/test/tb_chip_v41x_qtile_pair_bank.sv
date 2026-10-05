`timescale 1ns/1ps
module tb_chip_v41x_qtile_pair_bank;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, fp4=0;
    reg [7:0] req_v=0;
    reg [8*20-1:0] req_beat=0;
    wire [15:0] bank_re;
    wire [16*13-1:0] bank_addr;
    reg [16*274-1:0] bank_q=0;
    wire [7:0] rd_v;
    wire [8*264-1:0] rd_w;
    wire conflict,address_fault,reserved_fault;
    reg [273:0] mem [0:16*8192-1];
    reg [8*264-1:0] expected_fp8 [0:6399];
    reg [8*264-1:0] expected_fp4 [0:11519];
    string dir;
    integer beat, lane, errors=0, checked=0, skew_checked=0;
    ot_chip_v41x_qtile_pair_bank dut (
        .clk(clk),.rst_n(rst_n),.fp4(fp4),.req_v(req_v),.req_beat(req_beat),
        .bank_re(bank_re),.bank_addr(bank_addr),.bank_q(bank_q),
        .rd_v(rd_v),.rd_w(rd_w),.conflict(conflict),
        .address_fault(address_fault),.reserved_fault(reserved_fault));
    always @(posedge clk)
        for (integer i=0;i<16;i=i+1)
            if (bank_re[i]) bank_q[i*274 +:274] <= mem[i*8192+bank_addr[i*13 +:13]];
    task automatic one_beat(input bit format_fp4,input integer index);
        begin
            @(negedge clk);
            fp4=format_fp4;
            req_v=8'hff;
            for (lane=0;lane<8;lane=lane+1) req_beat[lane*20 +:20]=20'(index);
            #1;
            if (conflict || address_fault) $fatal(1,"request conflict/OOB fp4=%0d beat=%0d",format_fp4,index);
            @(negedge clk);
            req_v=0;
            @(negedge clk);
            if (rd_v!==8'hff) $fatal(1,"missing lane valid fp4=%0d beat=%0d got=%h",format_fp4,index,rd_v);
            if (rd_w !== (format_fp4 ? expected_fp4[index] : expected_fp8[index])) begin
                errors=errors+1;
                if (errors<4) $display("BAD fp4=%0d beat=%0d",format_fp4,index);
            end
            checked=checked+8;
        end
    endtask
    task automatic skewed(input bit format_fp4,input integer total);
        integer cyc,c,sk,idx,prior;
        reg [7:0] want_v;
        reg [263:0] want_w;
        begin
            for (cyc=0;cyc<total+21;cyc=cyc+1) begin
                @(negedge clk);
                fp4=format_fp4;
                req_v=0;
                for (c=0;c<8;c=c+1) begin
                    sk=(c<2) ? 0 : 3*(c-1);
                    idx=cyc-sk;
                    if (idx>=0 && idx<total) begin
                        req_v[c]=1;
                        req_beat[c*20 +:20]=20'(idx);
                    end
                end
                #1;
                if (conflict || address_fault) $fatal(1,"skew conflict/OOB fp4=%0d cycle=%0d",format_fp4,cyc);
                prior=cyc-2;
                want_v=0;
                for (c=0;c<8;c=c+1) begin
                    sk=(c<2) ? 0 : 3*(c-1);
                    idx=prior-sk;
                    if (idx>=0 && idx<total) begin
                        want_v[c]=1;
                        want_w=(format_fp4 ? expected_fp4[idx] : expected_fp8[idx]) >> (c*264);
                        if (rd_w[c*264 +:264] !== want_w) begin
                            errors=errors+1;
                            if (errors<4) $display("SKEW_BAD fp4=%0d cycle=%0d lane=%0d beat=%0d",format_fp4,cyc,c,idx);
                        end
                        skew_checked=skew_checked+1;
                    end
                end
                if (rd_v !== want_v) $fatal(1,"skew valid fp4=%0d cycle=%0d got=%h want=%h",format_fp4,cyc,rd_v,want_v);
            end
            @(negedge clk);
            req_v=0;
        end
    endtask
    initial begin
        if (!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
        $readmemh($sformatf("%s/banks.hex",dir),mem);
        $readmemh($sformatf("%s/expected_fp8.hex",dir),expected_fp8);
        $readmemh($sformatf("%s/expected_fp4.hex",dir),expected_fp4);
        repeat (3) @(negedge clk);
        rst_n=1;
        for (beat=0;beat<6400;beat=beat+1) one_beat(0,beat);
        for (beat=0;beat<11520;beat=beat+1) one_beat(1,beat);
        skewed(0,6400);
        skewed(1,11520);
        @(negedge clk);
        req_v=8'h01; fp4=0; req_beat[19:0]=20'd8192;
        #1;
        if (!address_fault) $fatal(1,"missing OOB guard");
        req_v=8'h03; fp4=1; req_beat[19:0]=20'd0; req_beat[39:20]=20'd2;
        #1;
        if (!conflict) $fatal(1,"missing same-bank different-row conflict guard");
        req_v=0;
        if (reserved_fault || errors) $fatal(1,"errors=%0d reserved=%0d",errors,reserved_fault);
        if (skew_checked != checked) $fatal(1,"skew count=%0d expected=%0d",skew_checked,checked);
        $display("QTILE_PAIR_PASS lanes=%0d skew_lanes=%0d fp8_beats=6400 fp4_beats=11520",checked,skew_checked);
        $finish;
    end
endmodule
