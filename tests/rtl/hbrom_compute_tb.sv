`timescale 1ns/1fs
// One full selected tile: original NC1 HBM arithmetic, real personalized ROM
// macro models, local two-cycle capture and finite source service. No expected
// values enter this bench; the external checker compares every retired result.
module hbrom_compute_tb;
    parameter integer PAIR_COUNT=128, NOPS=30, RMAX=4096;
    parameter real PERIOD_NS=0.833, ROM_SS_CQ_NS=0.743963;
    localparam integer NM=2*PAIR_COUNT;
    reg clk=0;
    always #(PERIOD_NS/2) clk=~clk;
    reg rst_n=0;
    reg start=0;
    reg [12:0] op_rows=0;
    reg [15:0] op_c=8;
    reg [7:0] op_g=0;
    reg op_gs=1;
    reg [1:0] op_fmt=0;
    wire busy;
    reg d_valid=0;
    wire d_ready;
    reg [31:0] d_base=0;
    reg [23:0] d_lines=0;
    wire req_v,req_ready,feed_req_ready,rsp_v;
    wire [31:0] req_addr;
    wire [9:0] req_tag,rsp_tag;
    wire [1087:0] rsp_data;
    reg xw_en=0;
    reg [6:0] xw_addr=0,xw_grp=0;
    reg [2047:0] xw_data=0;
    wire rv;
    wire [11:0] rrow;
    wire [31:0] rdata;
    wire fault,arrive,released;
    reg release_in=0;
    integer cyc=0;
    integer stall_mode=0;
    wire throttle=stall_mode && ((cyc%11)==3 || (cyc%11)==4);
    assign req_ready=feed_req_ready && !throttle;
    ot_hbm_accel_sm_v #(.ENABLE(1),.SUB(4),.LBS(2),.LSB(16),.NC(1),
        .RMAX(RMAX),.LEV(4),.XD(128),.MAX_OUT(512),.IL(8),
        .DS(2),.DW(4),.DG(3),.PIO(2),.STK(1),.TCK(1)) dut (
        .clk(clk),.rst_n(rst_n),.start(start),.op_rows(op_rows),.op_c(op_c),.op_g(op_g),
        .op_gs(op_gs),.op_fmt(op_fmt),.busy(busy),.d_valid(d_valid),.d_ready(d_ready),
        .d_base(d_base),.d_lines(d_lines),.req_v(req_v),.req_ready(req_ready),
        .req_addr(req_addr),.req_tag(req_tag),.rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
        .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
        .rv(rv),.rrow(rrow),.rdata(rdata),.fault(fault),.arrive(arrive),
        .release_in(release_in),.released(released));
    reg cfg_valid=0;
    wire cfg_ready;
    reg [31:0] cfg_base_record=0,cfg_region_records=0;
    reg [15:0] cfg_epoch=0;
    wire feed_idle,feed_fault,cancel_done;
    wire [NM-1:0] rom_ce,capture_ce;
    wire [NM*12-1:0] rom_addr;
    wire [NM*274-1:0] rom_q;
    ot_hbrom_rom_feed #(.ENABLE(1),.PAIRS(PAIR_COUNT),.PROTECT(1)) feed (
        .clk(clk),.rst_n(rst_n),.cfg_valid(cfg_valid),.cfg_ready(cfg_ready),
        .cfg_fmt(op_fmt),.cfg_rows(op_rows),.cfg_groups(op_g),.cfg_group_slot(op_gs),
        .cfg_base_record(cfg_base_record),.cfg_region_records(cfg_region_records),
        .cfg_virtual_base(d_base),.cfg_epoch(cfg_epoch),
        .req_v(req_v && !throttle),.req_ready(feed_req_ready),.req_addr(req_addr),.req_tag(req_tag),
        .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
        .cancel(1'b0),.cancel_done(cancel_done),.idle(feed_idle),.fault(feed_fault),
        .rom_ce(rom_ce),.rom_addr(rom_addr),.rom_q(rom_q),.capture_ce(capture_ce));
    genvar m;
    generate for(m=0;m<NM;m=m+1) begin: g_rom
        localparam integer BG=m/8, STREAM=(m%8)/2, PARITY=m%2;
        localparam string INSTANCE_NAME=$sformatf("rom_g%0d_s%0d_p%0d",BG,STREAM,PARITY);
        wire [273:0] macro_q;
        ot_rom_4096x274_m8 #(.INSTANCE(INSTANCE_NAME)) macro (
            .clk(clk),.ce_in(rom_ce[m]),.addr_in(rom_addr[m*12+:12]),.rd_out(macro_q));
        // The existing macro behavioral view has zero timing; this explicit
        // SS delay supplies its source-pinned clk->q before the real feed capture.
        assign #(ROM_SS_CQ_NS) rom_q[m*274+:274]=macro_q;
    end endgenerate

    reg [31:0] configs[0:NOPS*8-1];
    reg [5199:0] activations[0:NOPS*128-1];
    string dir;
    integer fo,operation=-1,idx,beat;
    integer requests,responses,consumed,results,captures,spacing_failures,ready_stalls;
    integer macro_reads,last_macro[NM],start_cycle,activation_cycle,first_cycle,last_cycle,done_cycle;
    reg active=0;
    always @(posedge clk) begin
        cyc<=cyc+1;
        if(rst_n) release_in<=arrive;
        if(active && rst_n) begin
            if(fault || feed_fault) begin
                $fwrite(fo,"FAIL component fault operation %0d cycle %0d\n",operation,cyc);
                $fflush(fo);$fatal(1,"component fault");
            end
            if(req_v && req_ready) requests=requests+1;
            if(req_v && !req_ready) ready_stalls=ready_stalls+1;
            if(rsp_v) responses=responses+1;
            if(dut.g_new.w_valid && dut.g_new.w_ready) consumed=consumed+1;
            if(rv) begin
                if(results==0) first_cycle=cyc;
                last_cycle=cyc;
                results=results+1;
                $fwrite(fo,"R %0d %0d %08h\n",operation,rrow,rdata);
            end
            for(integer n=0;n<NM;n=n+1) begin
                if(rom_ce[n]) begin
                    macro_reads=macro_reads+1;
                    if(cyc-last_macro[n]<2) spacing_failures=spacing_failures+1;
                    last_macro[n]=cyc;
                end
                if(capture_ce[n]) captures=captures+1;
            end
        end
    end
    initial begin
        if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
        if($value$plusargs("STALL=%d",stall_mode)) begin end
        $readmemh({dir,"/config.hex"},configs);
        $readmemh({dir,"/activations.hex"},activations);
        fo=$fopen({dir,"/out.txt"},"w");
        if(!fo) $fatal(1,"cannot open output");
        for(integer n=0;n<NM;n=n+1) last_macro[n]=-100;
        repeat(5) @(negedge clk);
        rst_n=1;
        repeat(5) @(negedge clk);
        for(operation=0;operation<NOPS;operation=operation+1) begin
            @(negedge clk);
            requests=0;responses=0;consumed=0;results=0;captures=0;macro_reads=0;
            spacing_failures=0;ready_stalls=0;first_cycle=-1;last_cycle=-1;
            active=1;activation_cycle=cyc;
            op_rows=configs[operation*8];op_c=configs[operation*8+1];op_g=configs[operation*8+2];
            op_fmt=configs[operation*8+3];d_lines=configs[operation*8+4];op_gs=configs[operation*8+5];
            cfg_base_record=configs[operation*8+6];cfg_region_records=configs[operation*8+7];
            cfg_epoch=operation+1;cfg_valid=1;
            $display("HBROM operation %0d rows %0d groups %0d format %0d begin cycle %0d",operation,op_rows,op_g,op_fmt,cyc);
            do @(posedge clk); while(!cfg_ready);
            @(negedge clk);cfg_valid=0;
            for(idx=0;idx<128;idx=idx+1)
                for(beat=0;beat<2;beat=beat+1) begin
                    @(negedge clk);xw_en=1;xw_addr=idx;xw_grp=beat;
                    xw_data=activations[operation*128+idx][beat*2048+:2048];
                end
            @(negedge clk);xw_en=0;d_valid=1;
            do @(posedge clk); while(!d_ready);
            @(negedge clk);d_valid=0;start=1;start_cycle=cyc;
            @(negedge clk);start=0;
            wait(busy);wait(!busy);done_cycle=cyc;
            wait(released && feed_idle);
            repeat(4) @(negedge clk);
            $fwrite(fo,"M %0d requests %0d responses %0d consumed %0d results %0d fault %0d feed_fault %0d released %0d macro_spacing_failures %0d capture_count %0d macro_reads %0d ready_stalls %0d cycles_start_to_done %0d first_result %0d last_result %0d activation_to_release %0d\n",
                operation,requests,responses,consumed,results,fault,feed_fault,released,
                spacing_failures,captures,macro_reads,ready_stalls,done_cycle-start_cycle,
                first_cycle-start_cycle,last_cycle-start_cycle,cyc-activation_cycle);
            $fflush(fo);
            $display("HBROM operation %0d complete cycle %0d results %0d",operation,cyc,results);
            active=0;
            if(fault || feed_fault) begin
                $fwrite(fo,"FAIL sticky fault operation %0d\n",operation);
                $fclose(fo);$fatal(1,"component fault");
            end
        end
        $fclose(fo);$finish;
    end
endmodule
