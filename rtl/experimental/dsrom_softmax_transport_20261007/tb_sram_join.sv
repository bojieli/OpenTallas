`timescale 1ps/1fs
module tb_sram_join;
    reg clk=0;always #416.666666667 clk=~clk;
    reg rst_n=0,begin_valid=0,begin_short=0,release_valid=0,wr_valid=0,wr_pv=0,replay_valid=0,replay_pv=0;
    reg [15:0] begin_tag=0,wr_tag=0,replay_tag=0;
    reg [2:0] wr_beat=0;
    reg [1023:0] wr_data=0;
    wire begin_ready,wr_ready,replay_ready,core_valid,core_pv,corrected,fault,busy,score_done,pv_done,write_commit;
    wire [8191:0] core_data;
    wire [15:0] core_tag;
    wire [6:0] core_addr,write_commit_addr;
    integer cycle=0,written=0,checked=0;
    ot_dsrom_softmax_sram_join dut(.*);
    always @(posedge clk)begin cycle<=cycle+1;if(write_commit)written<=written+1;end
    function automatic [63:0] payload(input integer address,input integer lane);
        payload=64'h9e3779b97f4a7c15*(64'(address*128+lane)+1);
    endfunction
    task automatic reset;
        @(negedge clk);rst_n=0;begin_valid=0;wr_valid=0;replay_valid=0;release_valid=0;
        repeat(2)@(negedge clk);rst_n=1;
        @(posedge clk);#1;if(fault||busy||!begin_ready)$fatal(1,"RESET");
    endtask
    task automatic begin_context(input short_t,input [15:0] tag_t);
        @(negedge clk);begin_valid=1;begin_short=short_t;begin_tag=tag_t;
        if(!begin_ready)$fatal(1,"BEGIN_NOT_READY");
        @(posedge clk);#1;if(!busy||fault)$fatal(1,"BEGIN_FAILED");
        @(negedge clk);begin_valid=0;begin_tag=16'hdead;
        if(replay_ready)$fatal(1,"UNWRITTEN_REPLAY_READY");
    endtask
    task automatic write_vector(input integer address,input [15:0] tag_t);
        integer old_written;
        old_written=written;
        for(integer beat=0;beat<8;beat=beat+1)begin
            @(negedge clk);wr_valid=1;wr_pv=(address>=40);wr_tag=tag_t;wr_beat=3'(beat);
            for(integer lane=0;lane<16;lane=lane+1)wr_data[64*lane +:64]=payload(address,beat*16+lane);
            #1;if(!wr_ready)$fatal(1,"WRITE_NOT_READY address=%0d beat=%0d",address,beat);
            @(posedge clk);#1;if(fault)$fatal(1,"WRITE_FAULT");
        end
        @(negedge clk);wr_valid=0;
        repeat(2)begin @(posedge clk);#1;end
        if(written!=old_written+1||fault)$fatal(1,"WRITE_COMMIT");
    endtask
    task automatic replay_vectors(input is_pv,input integer count,input [15:0] tag_t,input integer expected_corrected_addr);
        integer taken,steps,request_cycle,first,last,previous,corrections,base;
        base=is_pv?40:0;
        @(negedge clk);replay_pv=is_pv;replay_tag=tag_t;replay_valid=1;
        #1;if(!replay_ready)$fatal(1,"REPLAY_NOT_READY");
        @(posedge clk);request_cycle=cycle;
        @(negedge clk);replay_valid=0;replay_tag=16'hffff;
        taken=0;steps=0;first=0;last=0;previous=0;corrections=0;
        while(taken<count && steps<count+8)begin
            @(posedge clk);
            if(fault)$fatal(1,"REPLAY_FAULT taken=%0d",taken);
            if(core_valid)begin
                if(core_addr!=base+taken||core_tag!=tag_t||core_pv!=is_pv)$fatal(1,"CORE_IDENTITY");
                for(integer lane=0;lane<128;lane=lane+1)
                    if(core_data[64*lane +:64]!==payload(base+taken,lane))$fatal(1,"ACTUAL_SRAM_PAYLOAD addr=%0d lane=%0d",base+taken,lane);
                if(corrected!=(base+taken==expected_corrected_addr))$fatal(1,"BANK_CORRECTION_FLAG");
                if(taken==0)first=cycle-request_cycle;
                else if(cycle-previous!=1)$fatal(1,"CORE_BURST_STALLED");
                last=cycle-request_cycle;previous=cycle;corrections=corrections+corrected;
                taken=taken+1;checked=checked+1;
            end
            @(negedge clk);steps=steps+1;
        end
        if(taken!=count||first!=5||last!=count+4)$fatal(1,"BURST_BOUND count=%0d first=%0d last=%0d",taken,first,last);
        $display("BANK_BURST pv=%0d vectors=%0d first=%0d last=%0d corrected=%0d SS_clkq_ps=455.320549",is_pv,taken,first,last,corrections);
    endtask
    task automatic release_context;
        @(negedge clk);release_valid=1;
        @(posedge clk);#1;if(busy||!begin_ready||fault)$fatal(1,"RELEASE");
        @(negedge clk);release_valid=0;
    endtask
    initial begin
        reset();begin_context(0,16'h2410);
        for(integer row=0;row<40;row=row+1)write_vector(row,16'h2410);
        replay_vectors(0,40,16'h2410,-1);
        for(integer row=40;row<72;row=row+1)write_vector(row,16'h2410);
        // Flip an actual data cell in physical SRAM bank17, not the return bus.
        dut.g_sram[17].mem.arr[42][35]=~dut.g_sram[17].mem.arr[42][35];
        replay_vectors(1,32,16'h2410,42);release_context();
        begin_context(1,16'h2411);
        for(integer row=0;row<8;row=row+1)write_vector(row,16'h2411);
        replay_vectors(0,8,16'h2411,-1);
        for(integer row=40;row<72;row=row+1)write_vector(row,16'h2411);
        replay_vectors(1,32,16'h2411,-1);release_context();
        if(checked!=112)$fatal(1,"CHECKED_COUNT");
        begin_context(1,16'h2412);
        for(integer row=0;row<8;row=row+1)write_vector(row,16'h2412);
        // Two physical cells within final SECDED word in bank35 -> abort.
        dut.g_sram[35].mem.arr[0][186]=~dut.g_sram[35].mem.arr[0][186];
        dut.g_sram[35].mem.arr[0][187]=~dut.g_sram[35].mem.arr[0][187];
        @(negedge clk);replay_pv=0;replay_tag=16'h2412;replay_valid=1;
        @(posedge clk);@(negedge clk);replay_valid=0;
        repeat(8)begin @(posedge clk);if(core_valid)$fatal(1,"BAD_BANK_ROW_EMITTED");end
        #1;if(!fault)$fatal(1,"BANK_UE_ESCAPED");
        reset();begin_context(1,16'h2413);
        if(replay_ready)$fatal(1,"STALE_MEMORY_AFTER_RESET");
        @(negedge clk);wr_valid=1;wr_pv=0;wr_beat=0;wr_tag=16'h2412;
        @(posedge clk);#1;if(!fault)$fatal(1,"STALE_WRITE_TAG_ESCAPED");
        $display("PASS actual36macros vectors=%0d payload_bytes=%0d score40/PV32/score8/PV32 II1; realbank single/UE faults and reset identity",checked,checked*1024);
        $finish;
    end
endmodule
