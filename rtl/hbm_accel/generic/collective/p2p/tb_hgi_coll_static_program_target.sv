`timescale 1ns/1ps
`default_nettype none
module tb_hgi_coll_static_program_target;
    parameter integer MUT_DATA=0;
    reg clk=0,rst_n=0;always #0.5 clk=~clk;
    reg cv=0,dv=0,lv=0,active=0;
    reg [7:0] target=52;
    reg [11:0] address=0,base=0;
    reg [12:0] limit=64;
    reg [15:0] loops=1;
    reg [255:0] frame=0;
    wire [36:0] cfg;wire start;wire [5:0] start_pc;
    wire configured,init_busy,fault,busy,done,issuer_fault,v;
    wire [1535:0] data;wire [31:0] iteration;wire [5:0] pc;
    ot_hgi_coll_static_program_target #(.MUT_DATA(MUT_DATA)) transport(
        .clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_target(target),.cfg_addr(address),.cfg_data(frame),
        .desc_v(dv),.desc_base(base),.desc_limit(limit),.desc_loops(loops),.launch_v(lv),.program_active(active),
        .issuer_busy(busy),.issuer_fault(issuer_fault),.issuer_uop_v(v),.issuer_uop_pc(pc),
        .issuer_cfg(cfg),.issuer_start(start),.issuer_start_pc(start_pc),.configured(configured),.init_busy(init_busy),.fault(fault));
    ot_hgi_coll_static_issuer issuer(
        .clk_control(clk),.clk_mem({3{clk}}),.rst_n(rst_n),.cfg(cfg),.start(start),.start_pc(start_pc),
        .busy(busy),.done(done),.fault(issuer_fault),.uop_v(v),.uop(data),.iteration(iteration),.uop_pc(pc));
    integer cycle=0;
    always @(posedge clk)cycle<=cycle+1;
    function automatic [31:0] payload(input integer row_,input integer word_);
        return 32'hbafe0000^(32'(row_)*32'h01020409)^(32'(word_)*32'h9710ac57);
    endfunction
    function automatic [63:0] meta(input integer row_);
        reg [63:0] m;
        m=64'((row_+1)%64);
        m[50:45]=row_<32?31:(row_<56?55:63);
        if(row_==31)begin m[43:12]=2048;m[11:6]=0;end
        if(row_==55)begin m[43:12]=2;m[11:6]=32;end
        if(row_==63)m[44]=1;
        return m;
    endfunction
    task automatic send_frame(input integer row_,input integer segment);
        @(negedge clk);cv=1;dv=0;address=12'(row_*8+segment);frame=0;
        if(segment==6)frame[63:0]=meta(row_);
        else for(integer w=0;w<8;w=w+1)frame[w*32+:32]=payload(row_,segment*8+w);
    endtask
    task automatic idle(input integer edges);
        @(negedge clk);cv=0;dv=0;lv=0;
        repeat(edges-1)@(negedge clk);
    endtask
    task automatic descriptor;
        @(negedge clk);cv=0;dv=1;
        idle(66);
    endtask
    task automatic row_program(input integer r);
        integer last_edge;
        // Deliberately nonsequential segments; all six256b words and metadata.
        send_frame(r,6);send_frame(r,3);send_frame(r,0);send_frame(r,5);
        send_frame(r,1);send_frame(r,4);send_frame(r,2);
        last_edge=cycle+1;
        idle(1);
        while(init_busy)begin @(posedge clk);#0.01;end
        if(cycle-last_edge!=55)$fatal(1,"row completion latency got%d expected55",cycle-last_edge);
        @(negedge clk);
    endtask
    task automatic launch_and_check(input integer first_pc,input integer expected_count);
        integer launch_edge,first_edge,seen_,ep,ei,last_edge;
        @(negedge clk);lv=1;launch_edge=cycle+1;
        idle(1);seen_=0;ep=first_pc;ei=0;first_edge=-1;last_edge=-1;
        while(!done)begin
            @(posedge clk);#0.01;
            if(fault || issuer_fault)$fatal(1,"unexpected fault pc%0d",pc);
            if(v)begin
                if(first_edge<0)first_edge=cycle;
                else if(cycle!=last_edge+1)$fatal(1,"execution gap");
                last_edge=cycle;
                if(pc!=ep || iteration!=ei)$fatal(1,"pc/iteration got%0d/%0d expected%0d/%0d",pc,iteration,ep,ei);
                for(integer w=0;w<48;w=w+1)
                    if(data[w*32+:32]!==payload(ep,w))$fatal(1,"DATA mismatch pc%0d word%0d",pc,w);
                seen_=seen_+1;
                if(ep==31 && ei<2047)begin ep=0;ei=ei+1;end
                else if(ep==55 && ei<1)begin ep=32;ei=ei+1;end
                else begin ep=ep+1;if(ep==32 || ep==56)ei=0;end
            end
        end
        if(seen_!=expected_count || first_edge-launch_edge!=5)$fatal(1,"count/first edge %0d/%0d expected%0d/5",seen_,first_edge-launch_edge,expected_count);
        $display("PROGRAM_JOIN EXEC PASS start=%0d first=%0d latency=%0d words=%0d exact_bits=%0d",launch_edge,first_edge,first_edge-launch_edge,seen_,seen_*1536);
        idle(3);
    endtask
    integer scenario=0;
    initial begin
        if($value$plusargs("fault=%d",scenario))begin end
        repeat(5)@(negedge clk);rst_n=1;
        if(scenario!=0)begin
            case(scenario)
                1:begin send_frame(0,0);send_frame(0,0);end
                2:begin send_frame(0,0);send_frame(1,1);end
                3:send_frame(0,7);
                4:begin send_frame(0,6);frame[51]=1;end
                5:begin send_frame(0,0);address[9]=1;end
                6:begin
                    for(integer s=0;s<7;s=s+1)send_frame(0,s);
                    send_frame(1,0);
                end
                7:begin descriptor();@(negedge clk);lv=1;end
                8:begin loops=2;descriptor();end
                9:begin base=64;limit=65;descriptor();end
                10:begin descriptor();send_frame(0,0);@(negedge clk);cv=0;lv=1;end
                11:begin active=1;send_frame(0,0);end
                12:begin row_program(0);send_frame(0,0);end
                13:begin
                    for(integer r=0;r<64;r=r+1)row_program(r);
                    limit=1;descriptor();
                    if(configured || busy || issuer_fault)$fatal(1,"out-of-range metadata escaped prelaunch check");
                end
                14:begin send_frame(0,0);descriptor();end
                15:begin descriptor();send_frame(0,0);lv=1;end
                16:begin limit=0;descriptor();end
                17:begin send_frame(0,6);frame[192]=1;end
                19:begin
                    for(integer r=0;r<64;r=r+1)row_program(r);
                    @(negedge clk);dv=1;idle(2);@(negedge clk);lv=1;
                end
                20:begin
                    // Range is closed, but descriptor final row31 lacks halt.
                    for(integer r=0;r<32;r=r+1)row_program(r);
                    limit=32;descriptor();
                end
                18:begin
                    for(integer r=0;r<64;r=r+1)row_program(r);
                    descriptor();@(negedge clk);lv=1;idle(8);
                    if(!busy)$fatal(1,"expected actual native issuer busy");
                    send_frame(0,0);
                end
                default:$fatal(1,"bad scenario");
            endcase
            idle(8);
            if(!fault)$fatal(1,"fault scenario%0d not detected",scenario);
            $display("PROGRAM_JOIN FAULT PASS scenario=%0d",scenario);$finish;
        end
        // Other targets must neither program nor poison this local target.
        target=53;send_frame(2,7);idle(3);target=52;
        for(integer r=0;r<64;r=r+1)row_program(r);
        descriptor();
        launch_and_check(0,65592);
        base=32;descriptor();launch_and_check(32,56);
        $display("PROGRAM_JOIN PASS rows=64 native_macros=3 checked_uops=65648 metadata_loops=2048,2 frame_bits=256 instruction_bits=1536");$finish;
    end
    initial begin #200000;$fatal(1,"bench cycle bound");end
endmodule
`default_nettype wire
