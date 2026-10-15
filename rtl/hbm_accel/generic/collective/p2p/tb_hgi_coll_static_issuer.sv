`timescale 1ns/1ps
`default_nettype none
module tb_hgi_coll_static_issuer;
    parameter integer MUT_DATA=0,MUT_BRANCH=0,REPEATS=2048;
    localparam integer N=32*REPEATS+24*2+8;
    reg clk=0,rst_n=0;always #0.5 clk=~clk;
    reg [36:0] cfg=0;reg start=0;
    wire busy,done,fault,v;wire [1535:0] data;wire [31:0] iteration;wire [5:0] pc;
    ot_hgi_coll_static_issuer #(.MUT_DATA(MUT_DATA),.MUT_BRANCH(MUT_BRANCH)) dut(
        .clk_control(clk),.clk_mem({3{clk}}),.rst_n(rst_n),.cfg(cfg),.start(start),.start_pc(6'd0),
        .busy(busy),.done(done),.fault(fault),.uop_v(v),.uop(data),.iteration(iteration),.uop_pc(pc));
    function automatic [31:0] payload(input integer row,input integer bank,input integer word_);
        return 32'hbafe0000^(32'(row)*32'h01020409)^(32'(bank)*32'h73431123)^(32'(word_)*32'h9710ac57);
    endfunction
    task automatic config_word(input [3:0] cmd,input [31:0] d);
        @(negedge clk);cfg={1'b1,cmd,d};
    endtask
    task automatic clear_config;
        @(negedge clk);cfg=0;
    endtask
    integer scenario=0,checked=0,fault_offset=0;bit fault_pass=0;
    integer expected_pc[0:N-1],expected_iteration[0:N-1],n=0;
    initial begin:test
        if($value$plusargs("fault=%d",scenario))begin end
        repeat(5)@(negedge clk);rst_n=1;
        // All 64 physical rows, all 3 native SRAM banks, and full metadata.
        for(integer r=0;r<64;r=r+1)begin
            reg [63:0] m;
            for(integer b=0;b<3;b=b+1)begin
                if(!(scenario==1 && r==7 && b==2))begin
                    config_word(0,32'(r)|(32'(b)<<6));
                    for(integer w=0;w<16;w=w+1)config_word(1,payload(r,b,w));
                end
            end
            config_word(0,32'(r));
            m=64'(r+1); // nextPC (63 halt ignores its wrapped nextPC)
            m[50:45]=r<32?31:(r<56?55:63);
            if(r==31)begin m[43:12]=REPEATS;m[11:6]=0;end
            if(r==55)begin m[43:12]=2;m[11:6]=32;end
            if(r==63)m[44]=1;
            config_word(2,m[31:0]);
            if(!(scenario==2 && r==5))config_word(3,m[63:32]);
        end
        clear_config();
        for(integer it=0;it<REPEATS;it=it+1)for(integer r=0;r<32;r=r+1)begin expected_pc[n]=r;expected_iteration[n]=it;n=n+1;end
        for(integer it=0;it<2;it=it+1)for(integer r=32;r<56;r=r+1)begin expected_pc[n]=r;expected_iteration[n]=it;n=n+1;end
        for(integer r=56;r<64;r=r+1)begin expected_pc[n]=r;expected_iteration[n]=0;n=n+1;end
        if(n!=N)$fatal(1,"bad bench trace");
        if(scenario>=3)begin
            case(scenario)
                3:config_word(15,0); // unexpected config command
                4:begin config_word(0,0);config_word(1,0);end // incomplete bank write at start
                6:config_word(0,32'hc0); // invalid bank3
                7:begin config_word(0,0);config_word(3,32'h80000000);end // metadata reserved bits
                default:begin end
            endcase
            clear_config();
        end
        for(integer run_=0;run_<2 && !fault_pass;run_=run_+1)begin
            @(negedge clk);start=1;
            @(posedge clk);#0.01;
            if(scenario==0 && (!busy || v || done || fault))$fatal(1,"start state");
            @(negedge clk);start=0;
            // offset3 from start is first result. At offsets1/2 pipeline empty.
            for(integer c=1;c<N+3 && !fault_pass;c=c+1)begin
                if(scenario==5 && c==1)start=1; // start while busy
                if(scenario==8 && c==1)cfg={1'b1,4'd0,32'b0}; // config while busy
                @(posedge clk);#0.01;
                if(scenario!=0 && fault)begin
                    fault_pass=1;fault_offset=c;
                end
                if(scenario==0)begin
                    if(fault)$fatal(1,"issuer fault at offset%0d",c);
                    if(v !== (c>=3 && c<N+3))$fatal(1,"issue timeline offset%0d v%0d",c,v);
                    if(c>=3)begin
                        integer idx;
                        idx=c-3;
                        if(pc!==6'(expected_pc[idx]) || iteration!==32'(expected_iteration[idx]))
                            $fatal(1,"program mismatch idx%0d pc%0d expected%0d iteration%0d expected%0d",idx,pc,expected_pc[idx],iteration,expected_iteration[idx]);
                        for(integer b=0;b<3;b=b+1)for(integer w=0;w<16;w=w+1)
                            if(data[b*512+w*32+:32]!==payload(expected_pc[idx],b,w))$fatal(1,"data mismatch idx%0d bank%0d word%0d",idx,b,w);
                        checked=checked+1;
                    end
                    if(done !== (c==N+2) || busy !== (c!=N+2))$fatal(1,"done timeline offset%0d done%0d busy%0d",c,done,busy);
                end
                @(negedge clk);start=0;cfg=0;
            end
            if(scenario!=0)begin
                if(!fault_pass)$fatal(1,"fault escaped scenario%0d",scenario);
            end else begin
                @(posedge clk);#0.01;if(v || done || busy)$fatal(1,"trailing issue after halt");
            end
        end
        if(scenario!=0)begin
            if(!fault_pass)$fatal(1,"missing fault");
            $display("STATIC_ISSUER FAULT PASS scenario=%0d offset=%0d",scenario,fault_offset);
        end else begin
            if(checked!=2*N)$fatal(1,"coverage");
            $display("STATIC_ISSUER PASS native_macros=3 rows=64 width=1536 instructions=%0d first=3 interval=1 end=%0d repeats=%0d",checked,N+2,REPEATS);
        end
        $finish;
    end
endmodule
`default_nettype wire
