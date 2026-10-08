`timescale 1ns/1ps
module ot_rom_4096x266_m8(input clk, input ce_in, input [11:0] addr_in,
                         output reg [265:0] rd_out);
    reg [265:0] mem [0:4095];
    always @(posedge clk) if (ce_in) begin
`ifdef EMBED_NEG_BAD_ADDR
        rd_out <= #0.739211 mem[addr_in ^ 12'h001];
`else
        rd_out <= #0.739211 mem[addr_in];
`endif
    end
endmodule

module tb_qwen_embed_code_bank_parent;
    reg clk=0; always #0.416667 clk=~clk;
    reg rst_n=0, i_v=0, o_cr=0;
    reg [11:0] i_addr=0;
    wire i_cr,o_v,fault;
    wire [511:0] o_data;
    ot_qwen_embed_code_bank_parent dut(.*);
    integer i,j,cycle,sent=0,received=0,credits=2,owed=0,returned=0;
    integer first_request=-1,first_response=-1,last_response=-1,min_gap=999;
    reg [11:0] expected [0:4095];
    reg [31:0] rng=32'h5eed1234;
    reg drove;
    function [511:0] word(input [11:0] address);
        integer n;
        begin
            for(n=0;n<16;n=n+1)
                word[n*32+:32]=(32'h9e3779b9*(n+1)) ^ (32'h01010101*address) ^ (address<<(n%13));
        end
    endfunction
    task reset_dut;
        begin
            @(negedge clk);rst_n=0;i_v=0;o_cr=0;
            repeat(4)@(negedge clk);rst_n=1;
        end
    endtask
    task require_fault;
        begin
            repeat(5)begin @(negedge clk);if(o_v)$fatal(1,"FAIL embed corrupted metadata published");end
            if(!fault)$fatal(1,"FAIL embed metadata fault undetected");
        end
    endtask
    reg [511:0] w;
    initial begin
        for(i=0;i<4096;i=i+1) begin
            w=word(i);
            dut.u_lo.mem[i]={10'h155,w[255:0]};
            dut.u_hi.mem[i]={10'h2aa,w[511:256]};
        end
        repeat(4) @(negedge clk);
        rst_n=1;
        for(cycle=0;cycle<40000;cycle=cycle+1) begin
            @(negedge clk);
            rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
            i_v=(sent<4096 && credits>0 && (cycle<80 || rng[2:0]!=0));
            // Permutation covers all 4096 words, including both end addresses.
            i_addr=(sent*109+4095)&4095;
            o_cr=(owed>0 && (cycle<80 || rng[6:4]==3));
            drove=i_v;
            @(posedge clk);
            if(drove) begin
                expected[sent]=i_addr;sent=sent+1;credits=credits-1;
                if(first_request<0) first_request=cycle;
            end
            if(o_cr) begin owed=owed-1;returned=returned+1;end
            #0.01;
            if(i_cr) credits=credits+1;
            if(fault) begin $display("FAIL embed unexpected fault cycle=%0d",cycle);$fatal(1);end
            if(o_v) begin
                if(received>=sent || o_data!==word(expected[received])) begin
                    $display("FAIL embed payload/order at response=%0d address=%0d",received,expected[received]);$fatal(1);
                end
                if(first_response<0) first_response=cycle;
                if(last_response>=0 && cycle-last_response<min_gap) min_gap=cycle-last_response;
                last_response=cycle;
                received=received+1;owed=owed+1;
            end
            if(credits<0 || credits>2 || owed<0 || owed>4) begin $display("FAIL embed credit bound");$fatal(1);end
            if(received==4096) begin
                @(negedge clk); i_v=0; o_cr=0;
                repeat(3) @(negedge clk);
                for(j=0;j<owed;j=j+1) begin o_cr=1; @(negedge clk); end
                o_cr=0;
                repeat(3) @(negedge clk);
                if(fault) begin $display("FAIL embed legal drain fault");$fatal(1);end
                // A duplicate returned credit must be detected, never wrap.
                o_cr=1; @(negedge clk); o_cr=0;
                repeat(3) @(negedge clk);
                if(!fault) begin $display("FAIL embed duplicate credit undetected");$fatal(1);end
                if(first_response-first_request!=7 || min_gap!=2)$fatal(1,"FAIL embed protected timing contract");
                reset_dut();i_v=1;i_addr=0;@(negedge clk);i_v=0;
                @(negedge clk);dut.g_metadata_fifo[0].primary=dut.g_metadata_fifo[0].primary^12'd1;require_fault();
                reset_dut();dut.credits=dut.credits^1;require_fault();
                reset_dut();dut.phase=dut.phase^1;require_fault();
                reset_dut();i_v=1;i_addr=0;@(negedge clk);i_v=0;
                wait(dut.ce_q);@(negedge clk);dut.addr_q=dut.addr_q^1;require_fault();
                reset_dut();dut.u_ingress.valid_q=1;require_fault();
                reset_dut();dut.capture_en_q=16'h1;require_fault();
                reset_dut();dut.fault_n=0;require_fault();
                $display("PASS embed words=%0d cycles=%0d first_latency=%0d min_gap=%0d duplicate_credit=detected metadata_faults=7 SS_ROM_delay_ps=739.211",received,cycle,first_response-first_request,min_gap);
                $finish;
            end
        end
        $display("FAIL embed timeout sent=%0d received=%0d",sent,received);$fatal(1);
    end
endmodule
