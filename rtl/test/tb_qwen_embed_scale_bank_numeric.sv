`timescale 1ns/1ps
module ot_rom_4096x266_m8(input clk,ce_in,input [11:0] addr_in,output reg[265:0]rd_out);
    reg[265:0]mem[0:4095];
    always @(posedge clk) if(ce_in) begin
`ifdef SCALE_NEG_ADDRESS
        rd_out<=#0.739211 mem[addr_in^12'd1];
`else
        rd_out<=#0.739211 mem[addr_in];
`endif
    end
endmodule
module tb_qwen_embed_scale_bank_numeric;
    parameter integer BANK_ID=0;
    localparam integer ROWS=BANK_ID==2?20864:65536;
    reg clk=0;always #0.416667 clk=~clk;
    reg rst_n=0,i_v=0,o_cr=0;
    reg[17:0]i_row=0;
    wire i_cr,o_v,fault;wire[15:0]o_data;
    ot_qwen_embed_scale_bank_numeric #(.BANK_ID(BANK_ID)) dut(.*);
    integer i,j,k,cycle,sent,received,credits,owed,first_req,first_rsp,last_rsp,min_gap;
    integer expected[0:65535];
    reg[31:0]rng=32'h98765432;
    function[15:0]scale(input integer row);
        scale=(row&65535)^((row>>16)*16'h9e37)^16'ha529;
    endfunction
    task reset;
        begin
            @(negedge clk);rst_n=0;i_v=0;o_cr=0;
            repeat(4)@(negedge clk);rst_n=1;
        end
    endtask
    task require_fault;
        begin
            repeat(4) begin @(negedge clk);if(o_v)$fatal(1,"FAIL scale publication after invalid metadata");end
            if(!fault)$fatal(1,"FAIL scale invalid metadata undetected");
        end
    endtask
    initial begin
        for(i=0;i<4096;i=i+1) begin
            dut.u_scale.mem[i]=0;
            for(j=0;j<16;j=j+1) begin
`ifdef SCALE_NEG_LANE
                dut.u_scale.mem[i][j*16+:16]=scale(BANK_ID*65536+i*16+(j^1));
`else
                dut.u_scale.mem[i][j*16+:16]=scale(BANK_ID*65536+i*16+j);
`endif
            end
        end
        reset();sent=0;received=0;credits=2;owed=0;first_req=-1;first_rsp=-1;last_rsp=-1;min_gap=999;
        for(cycle=0;cycle<1500000 && received<ROWS;cycle=cycle+1) begin
            @(negedge clk);
            rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
            i_v=sent<ROWS && credits>0 && (cycle<80 || rng[2:0]!=0);
            // Reverse order covers EVERY valid bank/address/lane, including
            // final partial bank boundary; external return stalls are random.
            i_row=BANK_ID*65536+ROWS-1-sent;
            o_cr=owed>0 && (cycle<80 || rng[5:3]==3);
            @(posedge clk);
            if(i_v)begin expected[sent]=i_row;sent=sent+1;credits=credits-1;if(first_req<0)first_req=cycle;end
            if(o_cr)owed=owed-1;
            #0.01;
            if(i_cr)credits=credits+1;
            if(fault)$fatal(1,"FAIL scale unexpected fault bank=%0d cycle=%0d",BANK_ID,cycle);
            if(o_v)begin
                if(received>=sent || o_data!==scale(expected[received]))
                    $fatal(1,"FAIL scale payload/order bank=%0d row=%0d data=%h wanted=%h",BANK_ID,expected[received],o_data,scale(expected[received]));
                if(first_rsp<0)first_rsp=cycle;
                if(last_rsp>=0 && cycle-last_rsp<min_gap)min_gap=cycle-last_rsp;
                last_rsp=cycle;received=received+1;owed=owed+1;
            end
            if(credits<0 || credits>2 || owed<0 || owed>4)$fatal(1,"FAIL scale finite credit bound");
        end
        if(received!=ROWS)$fatal(1,"FAIL scale timeout");
        if(first_rsp-first_req!=7 || min_gap!=2)$fatal(1,"FAIL scale timing contract latency=%0d II=%0d",first_rsp-first_req,min_gap);
        // Bounds: wrong static bank, first out-of-vocabulary row, maximum row.
        for(k=0;k<3;k=k+1)begin
            reset();i_v=1;
            case(k)0:i_row=((BANK_ID+1)%3)*65536;1:i_row=151936;2:i_row=262143;endcase
            @(negedge clk);i_v=0;require_fault();
        end
        // Single mutable-state upset must fail-stop before publication.
        reset();i_v=1;i_row=BANK_ID*65536;@(negedge clk);i_v=0;
        @(negedge clk);dut.g_metadata_fifo[0].primary=dut.g_metadata_fifo[0].primary^18'd1;require_fault();
        reset();dut.credits=dut.credits^1;require_fault();
        reset();i_v=1;i_row=BANK_ID*65536;@(negedge clk);i_v=0;
        wait(dut.valid_pipe[2]);@(negedge clk);dut.lane_pipe[2]=dut.lane_pipe[2]^1;require_fault();
        reset();o_cr=1;@(negedge clk);o_cr=0;require_fault();
        reset();dut.fault_n=0;require_fault();
        $display("PASS scale bank=%0d rows=%0d latency=7 II=2 bounds=3 metadata_faults=4 duplicate_credit=detected SS_rom_delay_ps=739.211",BANK_ID,received);
        $finish;
    end
endmodule
